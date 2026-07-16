from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from products.models import ProductImage


@receiver(post_save, sender=ProductImage)
def queue_embedding_on_image_save(sender, instance, created, **kwargs):
    if created or not instance.has_embedding:
        from search.tasks import generate_image_embedding

        image_id = instance.id
        transaction.on_commit(lambda: generate_image_embedding.delay(image_id))
