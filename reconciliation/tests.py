from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import Profile
from imports.models import DataSource, ImportBatch
from transactions.models import Transaction

from .models import ReconciliationResult
from .services.engine import reconcile


class ReconciliationTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="analyst")
        Profile.objects.create(user=self.user, role=Profile.Role.ANALYST)
        source = DataSource.objects.create(name="Core", code="CORE")
        target = DataSource.objects.create(name="Gateway", code="GATEWAY")
        self.source_batch = self.batch(source, "source.csv")
        self.target_batch = self.batch(target, "target.csv")
        self.source_batch.status = ImportBatch.Status.COMPLETED
        self.target_batch.status = ImportBatch.Status.COMPLETED
        ImportBatch.objects.filter(pk__in=(self.source_batch.pk, self.target_batch.pk)).update(status=ImportBatch.Status.COMPLETED)

    def batch(self, data_source, filename):
        return ImportBatch.objects.create(
            data_source=data_source,
            file=SimpleUploadedFile(filename, b""),
            original_filename=filename,
            uploaded_by=self.user,
        )

    def row(self, batch, external_id, amount="10.00", account="ACC", day=date(2026, 9, 20)):
        return Transaction.objects.create(
            batch=batch, external_id=external_id, account_reference=account,
            amount=Decimal(amount), currency="PKR", transaction_date=day, status="SUCCESS",
        )

    def test_reconcile_creates_all_outcomes(self):
        source = self.row(self.source_batch, "MATCH")
        self.row(self.target_batch, "MATCH")
        self.row(self.source_batch, "AMOUNT", "10.00")
        self.row(self.target_batch, "AMOUNT", "12.00")
        self.row(self.source_batch, "ONLY_SOURCE")
        self.row(self.target_batch, "ONLY_TARGET")

        run = reconcile(self.source_batch, self.target_batch, self.user)

        self.assertEqual(run.status, run.Status.COMPLETED)
        self.assertEqual(ReconciliationResult.objects.filter(run=run).count(), 4)
        self.assertSetEqual(
            set(ReconciliationResult.objects.filter(run=run).values_list("status", flat=True)),
            {"MATCHED", "AMOUNT_MISMATCH", "MISSING_SOURCE", "MISSING_TARGET"},
        )

    def test_api_rejects_viewer_and_allows_analyst(self):
        client = APIClient()
        client.force_authenticate(user=self.user)
        response = client.post("/api/reconciliation-runs/", {"source_batch": self.source_batch.pk, "target_batch": self.target_batch.pk})
        self.assertEqual(response.status_code, 201)

        viewer = get_user_model().objects.create_user(username="viewer")
        client.force_authenticate(user=viewer)
        response = client.post("/api/reconciliation-runs/", {"source_batch": self.source_batch.pk, "target_batch": self.target_batch.pk})
        self.assertEqual(response.status_code, 403)

    def test_same_batch_is_rejected(self):
        with self.assertRaises(ValueError):
            reconcile(self.source_batch, self.source_batch, self.user)

    def test_incomplete_batch_is_rejected(self):
        self.target_batch.status = ImportBatch.Status.PENDING
        self.target_batch.save(update_fields=("status",))
        with self.assertRaises(ValueError):
            reconcile(self.source_batch, self.target_batch, self.user)

    def test_field_priority_and_amount_difference_are_recorded(self):
        self.row(self.source_batch, "TX1", "10.00", "SOURCE")
        self.row(self.target_batch, "TX1", "12.00", "TARGET", date(2026, 9, 21))

        run = reconcile(self.source_batch, self.target_batch, self.user)
        result = run.results.get()

        self.assertEqual(result.status, ReconciliationResult.Status.AMOUNT_MISMATCH)
        self.assertEqual(result.difference, Decimal("2.00"))
        self.assertEqual(result.reason, "amount, account, date")

# Create your tests here.
