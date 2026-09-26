from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.contrib.auth import get_user_model
from unittest.mock import patch
from rest_framework.test import APIClient

from accounts.models import Profile
from .models import DataSource, ImportBatch, ImportValidationError
from .services.pipeline import process_import
from transactions.models import Transaction


class ImportPipelineTests(TestCase):
    def setUp(self):
        self.batch = ImportBatch.objects.create(
            data_source=DataSource.objects.create(name="Core Banking", code="CORE_BANKING"),
            file=SimpleUploadedFile("transactions.csv", b""),
            original_filename="transactions.csv",
            uploaded_by=get_user_model().objects.create_user(username="analyst"),
        )

    def import_csv(self, content):
        self.batch.file = SimpleUploadedFile("transactions.csv", content.encode())
        self.batch.save(update_fields=("file",))
        process_import(self.batch)
        self.batch.refresh_from_db()

    def test_normalizes_valid_rows_and_records_invalid_rows(self):
        self.import_csv(
            "external_id,account_reference,amount,currency,transaction_date,status\n"
            " TX1001 , ACC001 ,25000.00, pkR ,2026-09-20, success\n"
            "TX1002,ACC002,-2,USD,2026-09-20,FAILED\n"
            "TX1003,ACC003,4,GBP,not-a-date,SUCCESS\n"
            "TX1001,ACC004,5,EUR,2026-09-20,SUCCESS\n"
        )
        self.assertEqual(self.batch.status, ImportBatch.Status.COMPLETED)
        self.assertEqual((self.batch.total_rows, self.batch.valid_rows, self.batch.invalid_rows), (4, 1, 3))
        self.assertEqual(Transaction.objects.get().external_id, "TX1001")
        self.assertEqual(ImportValidationError.objects.count(), 4)

    @patch("imports.views.process_import_batch.delay")
    def test_upload_requires_analyst_and_queues_csv(self, delay):
        user = self.batch.uploaded_by
        Profile.objects.create(user=user, role=Profile.Role.ANALYST)
        client = APIClient()
        client.force_authenticate(user=user)
        upload = SimpleUploadedFile(
            "gateway.csv",
            b"external_id,account_reference,amount,currency,transaction_date,status\n"
            b"TX2001,ACC002,10.00,USD,2026-09-20,SUCCESS\n",
            content_type="text/csv",
        )

        response = client.post(
            "/api/imports/",
            {"file": upload, "data_source": self.batch.data_source_id},
            format="multipart",
        )

        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.data["status"], ImportBatch.Status.PENDING)
        delay.assert_called_once_with(response.data["id"])

    def test_upload_rejects_non_csv_and_viewer(self):
        client = APIClient()
        client.force_authenticate(user=self.batch.uploaded_by)
        upload = SimpleUploadedFile("data.txt", b"not csv", content_type="text/plain")

        response = client.post(
            "/api/imports/",
            {"file": upload, "data_source": self.batch.data_source_id},
            format="multipart",
        )

        self.assertEqual(response.status_code, 403)

# Create your tests here.
