import io

import cv2
import numpy as np
from PIL import Image


def to_pil_image(image_input) -> Image.Image:
    """Normalize various image inputs to PIL RGB Image."""
    if isinstance(image_input, Image.Image):
        return image_input.convert("RGB")
    if isinstance(image_input, bytes):
        return Image.open(io.BytesIO(image_input)).convert("RGB")
    if isinstance(image_input, str):
        return Image.open(image_input).convert("RGB")
    if isinstance(image_input, np.ndarray):
        return Image.fromarray(image_input).convert("RGB")
    if hasattr(image_input, "read"):
        if hasattr(image_input, "seek"):
            image_input.seek(0)
        return Image.open(image_input).convert("RGB")
    raise TypeError(f"Unsupported image type: {type(image_input)}")


def to_cv2_bgr(image_input):
    """Normalize various image inputs to OpenCV BGR numpy array."""
    if isinstance(image_input, np.ndarray):
        if len(image_input.shape) == 2:
            return cv2.cvtColor(image_input, cv2.COLOR_GRAY2BGR)
        if image_input.shape[2] == 4:
            return cv2.cvtColor(image_input, cv2.COLOR_BGRA2BGR)
        return image_input

    rgb = np.array(to_pil_image(image_input))
    return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)


def crop_center_for_scan(image_input, ratio=0.55) -> Image.Image:
    """Crop the center region — realtime camera frames include face/background noise."""
    image = to_pil_image(image_input)
    width, height = image.size
    crop_w = max(1, int(width * ratio))
    crop_h = max(1, int(height * ratio))
    left = (width - crop_w) // 2
    top = (height - crop_h) // 2
    return image.crop((left, top, left + crop_w, top + crop_h))
