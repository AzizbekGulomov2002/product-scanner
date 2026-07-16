from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from products.models import ProductImage


@receiver(post_save, sender=ProductImage)
def queue_embedding_on_image_save(sender, instance, created, **kwargs):
    """Save product instantly; embedding runs in background and flips has_embedding."""
    update_fields = kwargs.get("update_fields")
    if update_fields is not None and set(update_fields) <= {"has_embedding"}:
        return

    if created or not instance.has_embedding:
        from search.tasks import enqueue_image_embedding

        image_id = instance.id
        transaction.on_commit(lambda: enqueue_image_embedding(image_id))
