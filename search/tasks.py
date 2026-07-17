import logging
import threading

from celery import shared_task
from django.db import close_old_connections

from products.models import ProductImage
from search.models import ImageEmbedding
from search.services.embedding import get_embedding_service

logger = logging.getLogger(__name__)

# Serialize CLIP inference so we never load/run several models at once on a
# small (2GB) server. One embedding at a time = bounded memory, no OOM.
_embedding_lock = threading.Semaphore(1)


def generate_image_embedding_sync(product_image_id: int) -> None:
    """Run CLIP embedding + mark has_embedding=True. Safe to call from a worker/thread."""
    close_old_connections()
    try:
        try:
            image_obj = ProductImage.objects.select_related("product").get(pk=product_image_id)
        except ProductImage.DoesNotExist:
            logger.error("ProductImage %s not found", product_image_id)
            return

        if image_obj.has_embedding and ImageEmbedding.objects.filter(product_image=image_obj).exists():
            return

        service = get_embedding_service()
        embedding = service.embed_image(image_obj.image.path)

        ImageEmbedding.objects.update_or_create(
            product_image=image_obj,
            defaults={"embedding": embedding.tolist()},
        )
        ProductImage.objects.filter(pk=image_obj.pk).update(has_embedding=True)
        logger.info("Embedding generated for ProductImage %s", product_image_id)
    except Exception:
        # Never swallow silently — a stuck "Pending" image must be diagnosable.
        logger.exception("Embedding FAILED for ProductImage %s", product_image_id)
        raise
    finally:
        close_old_connections()


def enqueue_image_embedding(product_image_id: int) -> None:
    """
    MUST return instantly — never call CLIP/Redis on the HTTP thread.

    Embedding runs in an in-process daemon thread inside gunicorn. We do NOT
    depend on Celery/Redis here: if the broker is down or no worker is
    consuming, images would otherwise stay "Pending" forever. A semaphore
    keeps only one CLIP inference running at a time (memory-safe).
    """

    def _background():
        with _embedding_lock:
            close_old_connections()
            try:
                generate_image_embedding_sync(product_image_id)
            except Exception:
                pass  # already logged with traceback
            finally:
                close_old_connections()

    threading.Thread(
        target=_background,
        daemon=True,
        name=f"embed-{product_image_id}",
    ).start()


@shared_task(ignore_result=True)
def generate_image_embedding(product_image_id):
    generate_image_embedding_sync(product_image_id)


@shared_task(ignore_result=True)
def reindex_product_embeddings(product_id):
    images = ProductImage.objects.filter(product_id=product_id).values_list("id", flat=True)
    for image_id in images:
        enqueue_image_embedding(image_id)


@shared_task(ignore_result=True)
def reindex_all_embeddings():
    images = ProductImage.objects.filter(has_embedding=False).values_list("id", flat=True)
    for image_id in images:
        enqueue_image_embedding(image_id)
