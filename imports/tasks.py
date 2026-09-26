from celery import shared_task

from .models import ImportBatch
from .services.pipeline import process_import


@shared_task
def process_import_batch(batch_id):
    batch = ImportBatch.objects.get(pk=batch_id)
    process_import(batch)
