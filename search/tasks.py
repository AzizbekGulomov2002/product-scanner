import logging
import threading

from celery import shared_task
from django.conf import settings

from products.models import ProductImage
from search.models import ImageEmbedding
from search.services.embedding import get_embedding_service

logger = logging.getLogger(__name__)


def generate_image_embedding_sync(product_image_id: int) -> None:
    """Run CLIP embedding + mark has_embedding=True. Safe to call from a worker/thread."""
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


def enqueue_image_embedding(product_image_id: int) -> None:
    """
    Always return immediately to the HTTP request.
    - Celery worker mode: queue via Redis
    - Eager / no worker: background daemon thread (still non-blocking)
    """
    if settings.CELERY_TASK_ALWAYS_EAGER:
        thread = threading.Thread(
            target=generate_image_embedding_sync,
            args=(product_image_id,),
            daemon=True,
            name=f"embed-{product_image_id}",
        )
        thread.start()
        logger.info("Embedding queued in background thread for ProductImage %s", product_image_id)
        return

    generate_image_embedding.delay(product_image_id)
    logger.info("Embedding queued in Celery for ProductImage %s", product_image_id)


@shared_task
def generate_image_embedding(product_image_id):
    generate_image_embedding_sync(product_image_id)


@shared_task
def reindex_product_embeddings(product_id):
    images = ProductImage.objects.filter(product_id=product_id)
    for image in images:
        enqueue_image_embedding(image.id)


@shared_task
def reindex_all_embeddings():
    images = ProductImage.objects.filter(has_embedding=False)
    for image in images:
        enqueue_image_embedding(image.id)
