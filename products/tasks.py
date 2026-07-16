from celery import shared_task


@shared_task
def process_import_job(job_id):
    from products.models import ImportJob
    from products.services.import_service import ImportService

    job = ImportJob.objects.get(pk=job_id)
    ImportService(job).run()
