from django.core.management.base import BaseCommand

from search.tasks import reindex_all_embeddings


class Command(BaseCommand):
    help = "Queue embedding generation for all images without embeddings"

    def handle(self, *args, **options):
        reindex_all_embeddings.delay()
        self.stdout.write(self.style.SUCCESS("Reindex task queued for all pending images."))
