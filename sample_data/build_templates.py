#!/usr/bin/env python3
"""Generate Excel template and example ZIP for bulk import."""

import shutil
import zipfile
from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parent
IMGS = BASE.parent / "imgs"

# Folder-based import (recommended)
FOLDER_PRODUCTS = [
    {"external_id": "001", "name": "Skovorodka", "barcode": "", "image_files": ""},
    {"external_id": "002", "name": "Sopol idish", "barcode": "", "image_files": ""},
    {"external_id": "003", "name": "Idish yuvgich", "barcode": "", "image_files": ""},
    {"external_id": "004", "name": "Qozon xitoy", "barcode": "", "image_files": ""},
    {"external_id": "005", "name": "Termos", "barcode": "", "image_files": ""},
    {"external_id": "006", "name": "Airpods pro 3", "barcode": "", "image_files": ""},
]

FOLDER_IMAGES = {
    "001": ["SkovorodkaA-1.jpg", "SkovorodkaA-2.jpg"],
    "002": ["sopol.jpg", "sopol2.jpg"],
    "003": ["dishwasherA-1.jpg", "dishwasherA-2.jpg"],
    "004": ["QozonA-1.jpg", "QozonA-2.jpg"],
    "005": ["termizA-1.jpg", "termizA-2.jpg"],
    "006": ["airpods-pro-3a.jpeg", "airpods-pro-c.jpg", "airpods-pro-3c.webp"],
}


def build_excel():
    df = pd.DataFrame(FOLDER_PRODUCTS)
    out = BASE / "products_template.xlsx"
    df.to_excel(out, index=False, sheet_name="products")
    print(f"Created {out}")


def build_zip_folder_mode():
    out = BASE / "product_images_folder_example.zip"
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for ext_id, filenames in FOLDER_IMAGES.items():
            for fname in filenames:
                src = IMGS / fname
                if not src.exists():
                    print(f"  skip missing: {src}")
                    continue
                arcname = f"{ext_id}/{fname}"
                zf.write(src, arcname)
                print(f"  + {arcname}")
    print(f"Created {out}")


def build_zip_flat_mode():
    """Flat ZIP — filenames listed in Excel image_files column."""
    mapping = {
        "001_front.jpg": "SkovorodkaA-1.jpg",
        "001_back.jpg": "SkovorodkaA-2.jpg",
        "002_front.jpg": "sopol.jpg",
        "002_back.jpg": "sopol2.jpg",
        "006_1.jpeg": "airpods-pro-3a.jpeg",
        "006_2.jpg": "airpods-pro-c.jpg",
        "006_3.webp": "airpods-pro-3c.webp",
    }
    out = BASE / "product_images_flat_example.zip"
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for zip_name, src_name in mapping.items():
            src = IMGS / src_name
            if src.exists():
                zf.write(src, zip_name)
                print(f"  + {zip_name}")
    print(f"Created {out}")


if __name__ == "__main__":
    build_excel()
    build_zip_folder_mode()
    build_zip_flat_mode()
