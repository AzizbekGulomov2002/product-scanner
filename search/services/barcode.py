import logging
import re

import cv2
import numpy as np

from search.services.image_utils import to_cv2_bgr

logger = logging.getLogger(__name__)

_pyzbar = None


def normalize_barcode(value: str) -> str:
    """Strip spaces/dashes so EAN-13 variants match (6976918640031)."""
    return re.sub(r"\D", "", (value or "").strip())


def _get_pyzbar():
    global _pyzbar
    if _pyzbar is None:
        try:
            from pyzbar import pyzbar as pz
            _pyzbar = pz
        except ImportError as exc:
            logger.warning("pyzbar not available: %s. Install: brew install zbar", exc)
            _pyzbar = False
    return _pyzbar if _pyzbar is not False else None


def _decode_gray(pyzbar, gray: np.ndarray) -> list[str]:
    found = []
    seen = set()
    for image in (gray, cv2.bitwise_not(gray)):
        for bc in pyzbar.decode(image):
            data = bc.data.decode("utf-8", errors="ignore").strip()
            if data and data not in seen:
                seen.add(data)
                found.append(data)
    return found


def _gray_variants(bgr: np.ndarray) -> list[np.ndarray]:
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    variants = [gray]

    clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
    variants.append(clahe.apply(gray))

    for scale in (1.5, 2.0, 2.5, 3.0):
        variants.append(
            cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
        )

    blur = cv2.GaussianBlur(gray, (3, 3), 0)
    sharp = cv2.addWeighted(gray, 1.6, blur, -0.6, 0)
    variants.append(cv2.resize(sharp, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC))

    adaptive = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 5
    )
    variants.append(adaptive)
    variants.append(cv2.resize(adaptive, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_NEAREST))

    h, w = gray.shape
    for y0, y1, x0, x1 in (
        (0, h, 0, w),
        (h // 6, 5 * h // 6, w // 8, 7 * w // 8),
        (h // 4, 3 * h // 4, w // 6, 5 * w // 6),
    ):
        crop = gray[y0:y1, x0:x1]
        if crop.size:
            variants.append(crop)
            variants.append(cv2.resize(crop, None, fx=2.5, fy=2.5, interpolation=cv2.INTER_CUBIC))

    for channel in (0, 1, 2):
        ch = bgr[:, :, channel]
        variants.append(ch)
        variants.append(cv2.resize(ch, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC))

    return variants


class BarcodeService:
    @staticmethod
    def decode(image_input) -> list[dict]:
        pyzbar = _get_pyzbar()
        if pyzbar is None:
            return []

        try:
            bgr = to_cv2_bgr(image_input)
        except (TypeError, OSError) as exc:
            logger.warning("Could not load image for barcode: %s", exc)
            return []

        if bgr is None or bgr.size == 0:
            return []

        results = []
        seen = set()

        for gray in _gray_variants(bgr):
            for data in _decode_gray(pyzbar, gray):
                if data in seen:
                    continue
                seen.add(data)
                results.append({"data": data, "type": "UNKNOWN"})

        return results

    @staticmethod
    def decode_first(image_input) -> str | None:
        results = BarcodeService.decode(image_input)
        return results[0]["data"] if results else None
