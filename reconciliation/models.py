from django.conf import settings
from django.db import models


class ReconciliationRun(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PROCESSING = "PROCESSING", "Processing"
        COMPLETED = "COMPLETED", "Completed"
        FAILED = "FAILED", "Failed"

    source_batch = models.ForeignKey(
        "imports.ImportBatch",
        on_delete=models.PROTECT,
        related_name="source_reconciliation_runs",
    )
    target_batch = models.ForeignKey(
        "imports.ImportBatch",
        on_delete=models.PROTECT,
        related_name="target_reconciliation_runs",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    started_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="reconciliation_runs",
    )
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(source_batch=models.F("target_batch")),
                name="different_reconciliation_batches",
            )
        ]

    def __str__(self):
        return f"Run {self.pk}: {self.source_batch} vs {self.target_batch}"


class ReconciliationResult(models.Model):
    class Status(models.TextChoices):
        MATCHED = "MATCHED", "Matched"
        AMOUNT_MISMATCH = "AMOUNT_MISMATCH", "Amount mismatch"
        CURRENCY_MISMATCH = "CURRENCY_MISMATCH", "Currency mismatch"
        ACCOUNT_MISMATCH = "ACCOUNT_MISMATCH", "Account mismatch"
        DATE_MISMATCH = "DATE_MISMATCH", "Date mismatch"
        MISSING_SOURCE = "MISSING_SOURCE", "Missing source"
        MISSING_TARGET = "MISSING_TARGET", "Missing target"

    run = models.ForeignKey(
        ReconciliationRun,
        on_delete=models.CASCADE,
        related_name="results",
    )
    source_transaction = models.ForeignKey(
        "transactions.Transaction",
        on_delete=models.PROTECT,
        related_name="source_results",
        null=True,
        blank=True,
    )
    target_transaction = models.ForeignKey(
        "transactions.Transaction",
        on_delete=models.PROTECT,
        related_name="target_results",
        null=True,
        blank=True,
    )
    status = models.CharField(max_length=30, choices=Status.choices, db_index=True)
    difference = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        null=True,
        blank=True,
    )
    reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(
                fields=["run", "source_transaction"],
                condition=models.Q(source_transaction__isnull=False),
                name="unique_source_transaction_per_run",
            ),
            models.UniqueConstraint(
                fields=["run", "target_transaction"],
                condition=models.Q(target_transaction__isnull=False),
                name="unique_target_transaction_per_run",
            ),
        ]

    def __str__(self):
        return f"Run {self.run_id}: {self.status}"
