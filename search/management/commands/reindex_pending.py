from django.core.management.base import BaseCommand

from products.models import ProductImage
from search.tasks import generate_image_embedding_sync


class Command(BaseCommand):
    help = "Generate embeddings for all Pending images synchronously (no Celery needed)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--all",
            action="store_true",
            help="Re-embed every image, not only the Pending ones.",
        )

    def handle(self, *args, **options):
        qs = ProductImage.objects.all()
        if not options["all"]:
            qs = qs.filter(has_embedding=False)

        ids = list(qs.values_list("id", flat=True))
        if not ids:
            self.stdout.write(self.style.SUCCESS("No pending images. Everything is indexed."))
            return

        self.stdout.write(f"Processing {len(ids)} image(s)...")
        ok, failed = 0, 0
        for image_id in ids:
            try:
                generate_image_embedding_sync(image_id)
                ok += 1
                self.stdout.write(self.style.SUCCESS(f"  [OK] ProductImage {image_id}"))
            except Exception as exc:  # noqa: BLE001
                failed += 1
                self.stdout.write(self.style.ERROR(f"  [FAIL] ProductImage {image_id}: {exc}"))

        self.stdout.write(
            self.style.SUCCESS(f"Done. {ok} indexed, {failed} failed.")
        )
