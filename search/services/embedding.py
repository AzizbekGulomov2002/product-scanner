import io
import logging

import numpy as np
import open_clip
import torch
from django.conf import settings
from PIL import Image

from search.services.image_utils import to_pil_image

logger = logging.getLogger(__name__)


class EmbeddingService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._loaded = False
        return cls._instance

    def _load_model(self):
        if self._loaded:
            return
        logger.info("Loading CLIP model: %s / %s", settings.CLIP_MODEL, settings.CLIP_PRETRAINED)
        self.model, _, self.preprocess = open_clip.create_model_and_transforms(
            settings.CLIP_MODEL,
            pretrained=settings.CLIP_PRETRAINED,
        )
        self.model.eval()
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = self.model.to(self.device)
        self.tokenizer = open_clip.get_tokenizer(settings.CLIP_MODEL)
        self._loaded = True
        logger.info("CLIP model loaded on %s", self.device)

    def embed_image(self, image_input) -> np.ndarray:
        self._load_model()
        image = to_pil_image(image_input)

        tensor = self.preprocess(image).unsqueeze(0).to(self.device)
        with torch.no_grad():
            features = self.model.encode_image(tensor)
            features = features / features.norm(dim=-1, keepdim=True)

        return features.cpu().numpy().flatten().astype(np.float32)

    def embed_text(self, text: str) -> np.ndarray:
        self._load_model()
        tokens = self.tokenizer([text]).to(self.device)
        with torch.no_grad():
            features = self.model.encode_text(tokens)
            features = features / features.norm(dim=-1, keepdim=True)
        return features.cpu().numpy().flatten().astype(np.float32)


def get_embedding_service() -> EmbeddingService:
    return EmbeddingService()
