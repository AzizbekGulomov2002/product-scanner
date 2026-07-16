import logging

from celery import shared_task
from django.conf import settings

from products.models import ProductImage
from search.models import ImageEmbedding
from search.services.embedding import get_embedding_service

logger = logging.getLogger(__name__)


@shared_task
def generate_image_embedding(product_image_id):
    try:
        image_obj = ProductImage.objects.select_related("product").get(pk=product_image_id)
    except ProductImage.DoesNotExist:
        logger.error("ProductImage %s not found", product_image_id)
        return

    service = get_embedding_service()
    embedding = service.embed_image(image_obj.image.path)

    ImageEmbedding.objects.update_or_create(
        product_image=image_obj,
        defaults={"embedding": embedding.tolist()},
    )
    image_obj.has_embedding = True
    image_obj.save(update_fields=["has_embedding"])
    logger.info("Embedding generated for ProductImage %s", product_image_id)


@shared_task
def reindex_product_embeddings(product_id):
    images = ProductImage.objects.filter(product_id=product_id)
    for image in images:
        generate_image_embedding.delay(image.id)


@shared_task
def reindex_all_embeddings():
    images = ProductImage.objects.filter(has_embedding=False)
    for image in images:
        generate_image_embedding.delay(image.id)
