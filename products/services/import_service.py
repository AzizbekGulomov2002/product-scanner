import io
import zipfile
from pathlib import Path

import pandas as pd
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import transaction
from django.utils import timezone

from products.models import ImportJob, Product, ProductImage


REQUIRED_COLUMNS = {"external_id", "name"}


class ImportService:
    def __init__(self, job: ImportJob):
        self.job = job
        self.errors = []

    def run(self):
        self.job.status = "processing"
        self.job.started_at = timezone.now()
        self.job.save(update_fields=["status", "started_at"])

        try:
            df = self._read_excel()
            self.job.total_rows = len(df)
            self.job.save(update_fields=["total_rows"])

            zip_contents = self._extract_zip_map()

            for idx, row in df.iterrows():
                try:
                    self._process_row(row, zip_contents)
                except Exception as exc:
                    self.errors.append(f"Row {idx + 2}: {exc}")
                    self.job.error_count += 1

                self.job.progress_percent = int((idx + 1) / len(df) * 100)
                self.job.save(
                    update_fields=["created_count", "updated_count", "error_count", "images_loaded", "progress_percent"]
                )

            self.job.status = "completed"
            self.job.error_log = "\n".join(self.errors)
            self.job.completed_at = timezone.now()
            self.job.save()

            self._queue_embeddings()

        except Exception as exc:
            self.job.status = "failed"
            self.job.error_log = str(exc) + "\n" + "\n".join(self.errors)
            self.job.completed_at = timezone.now()
            self.job.save()

    def _read_excel(self) -> pd.DataFrame:
        path = self.job.excel_file.path
        if path.endswith(".csv"):
            df = pd.read_csv(path)
        else:
            df = pd.read_excel(path)

        df.columns = [str(c).strip().lower() for c in df.columns]
        missing = REQUIRED_COLUMNS - set(df.columns)
        if missing:
            raise ValueError(f"Missing required columns: {', '.join(missing)}")
        return df

    def _extract_zip_map(self) -> dict:
        """Returns {external_id: [file_paths_in_zip]} or {filename: bytes}."""
        if not self.job.zip_file:
            return {}

        folder_map = {}
        file_map = {}

        with zipfile.ZipFile(self.job.zip_file.path, "r") as zf:
            for info in zf.infolist():
                if info.is_dir() or info.filename.startswith("__MACOSX"):
                    continue
                name = Path(info.filename).name
                if not name.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
                    continue

                parts = Path(info.filename).parts
                data = zf.read(info.filename)

                if len(parts) >= 2:
                    folder_id = parts[-2]
                    folder_map.setdefault(folder_id, []).append((name, data))
                else:
                    file_map[name] = data

        return {"folders": folder_map, "files": file_map}

    def _process_row(self, row, zip_contents):
        external_id = str(row["external_id"]).strip()
        name = str(row["name"]).strip()
        barcode = str(row.get("barcode", "")).strip() if pd.notna(row.get("barcode")) else ""

        product = Product.objects.filter(external_id=external_id).first()
        created = False

        if product is None:
            if self.job.mode == "update":
                self.errors.append(f"{external_id}: Product not found (update mode)")
                self.job.error_count += 1
                return
            product = Product(external_id=external_id)
            created = True
        elif self.job.mode == "create":
            self.errors.append(f"{external_id}: Product already exists (create mode)")
            self.job.error_count += 1
            return

        product.name = name
        if barcode:
            product.barcode = barcode
        product.save()

        if created:
            self.job.created_count += 1
        else:
            self.job.updated_count += 1

        self._attach_images(product, external_id, row, zip_contents)

    def _attach_images(self, product, external_id, row, zip_contents):
        if not zip_contents:
            return

        image_files_col = row.get("image_files")
        images_attached = 0

        folders = zip_contents.get("folders", {})
        files = zip_contents.get("files", {})

        if external_id in folders:
            for idx, (name, data) in enumerate(folders[external_id]):
                self._save_image(product, name, data, is_primary=(idx == 0))
                images_attached += 1
        elif pd.notna(image_files_col) and str(image_files_col).strip():
            for fname in str(image_files_col).split(","):
                fname = fname.strip()
                if fname in files:
                    self._save_image(product, fname, files[fname], is_primary=(images_attached == 0))
                    images_attached += 1
                else:
                    self.errors.append(f"{external_id}: Image not found in ZIP: {fname}")

        self.job.images_loaded += images_attached

    @transaction.atomic
    def _save_image(self, product, filename, data, is_primary=False):
        if is_primary:
            product.images.filter(is_primary=True).update(is_primary=False)

        content = ContentFile(data, name=filename)
        ProductImage.objects.create(
            product=product,
            image=content,
            is_primary=is_primary,
        )

    def _queue_embeddings(self):
        from search.tasks import enqueue_image_embedding

        for image in ProductImage.objects.filter(has_embedding=False).order_by("-id")[:5000]:
            enqueue_image_embedding(image.id)
