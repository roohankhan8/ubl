from django.db import models


class Transaction(models.Model):
    batch = models.ForeignKey(
        "imports.ImportBatch",
        on_delete=models.CASCADE,
        related_name="transactions",
    )
    external_id = models.CharField(max_length=100)
    account_reference = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=18, decimal_places=2)
    currency = models.CharField(max_length=3)
    transaction_date = models.DateField()
    status = models.CharField(max_length=30, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-transaction_date", "external_id"]
        constraints = [
            models.UniqueConstraint(
                fields=["batch", "external_id"],
                name="unique_transaction_per_batch",
            ),
            models.CheckConstraint(
                condition=models.Q(amount__gt=0),
                name="transaction_amount_positive",
            ),
        ]
        indexes = [
            models.Index(fields=["external_id"]),
            models.Index(fields=["transaction_date"]),
        ]

    def __str__(self):
        return f"{self.external_id} — {self.amount} {self.currency}"
