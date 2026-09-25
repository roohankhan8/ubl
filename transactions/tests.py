from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase

from imports.models import DataSource, ImportBatch

from .models import Transaction


class TransactionConstraintTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        user = get_user_model().objects.create_user(username="analyst")
        source = DataSource.objects.create(name="Core Banking", code="CORE_BANKING")
        cls.batch = ImportBatch.objects.create(
            data_source=source,
            file="imports/core.csv",
            original_filename="core.csv",
            uploaded_by=user,
        )
        cls.values = {
            "batch": cls.batch,
            "external_id": "TX1001",
            "account_reference": "ACC001",
            "amount": Decimal("25000.00"),
            "currency": "PKR",
            "transaction_date": date(2026, 9, 20),
        }

    def test_external_id_is_unique_within_batch(self):
        Transaction.objects.create(**self.values)

        with self.assertRaises(IntegrityError), transaction.atomic():
            Transaction.objects.create(**self.values)

    def test_amount_must_be_positive(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Transaction.objects.create(**(self.values | {"amount": Decimal("0.00")}))
