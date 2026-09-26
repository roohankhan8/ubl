from django.db import transaction
from django.utils import timezone

from ..models import ReconciliationResult, ReconciliationRun


def reconcile(source_batch, target_batch, started_by):
    if source_batch == target_batch:
        raise ValueError("Source and target batches must be different.")
    if source_batch.status != source_batch.Status.COMPLETED or target_batch.status != target_batch.Status.COMPLETED:
        raise ValueError("Both batches must be completed.")

    run = ReconciliationRun.objects.create(
        source_batch=source_batch,
        target_batch=target_batch,
        started_by=started_by,
        status=ReconciliationRun.Status.PROCESSING,
        started_at=timezone.now(),
    )
    try:
        source = {row.external_id: row for row in source_batch.transactions.all()}
        target = {row.external_id: row for row in target_batch.transactions.all()}
        results = []

        for external_id in source.keys() | target.keys():
            source_row = source.get(external_id)
            target_row = target.get(external_id)
            if source_row is None:
                results.append(ReconciliationResult(run=run, target_transaction=target_row, status=ReconciliationResult.Status.MISSING_SOURCE))
                continue
            if target_row is None:
                results.append(ReconciliationResult(run=run, source_transaction=source_row, status=ReconciliationResult.Status.MISSING_TARGET))
                continue

            differences = []
            if source_row.amount != target_row.amount:
                differences.append(("amount", ReconciliationResult.Status.AMOUNT_MISMATCH))
            if source_row.currency != target_row.currency:
                differences.append(("currency", ReconciliationResult.Status.CURRENCY_MISMATCH))
            if source_row.account_reference != target_row.account_reference:
                differences.append(("account", ReconciliationResult.Status.ACCOUNT_MISMATCH))
            if source_row.transaction_date != target_row.transaction_date:
                differences.append(("date", ReconciliationResult.Status.DATE_MISMATCH))

            status = differences[0][1] if differences else ReconciliationResult.Status.MATCHED
            reason = ", ".join(field for field, _ in differences)
            difference = target_row.amount - source_row.amount if source_row.amount != target_row.amount else None
            results.append(ReconciliationResult(
                run=run,
                source_transaction=source_row,
                target_transaction=target_row,
                status=status,
                difference=difference,
                reason=reason,
            ))

        with transaction.atomic():
            ReconciliationResult.objects.bulk_create(results)
            run.status = ReconciliationRun.Status.COMPLETED
            run.completed_at = timezone.now()
            run.save(update_fields=("status", "completed_at"))
        return run
    except Exception:
        run.status = ReconciliationRun.Status.FAILED
        run.completed_at = timezone.now()
        run.save(update_fields=("status", "completed_at"))
        raise
