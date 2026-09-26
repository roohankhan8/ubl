import csv
from datetime import datetime
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.utils import timezone

from transactions.models import Transaction

from ..models import ImportBatch, ImportValidationError

REQUIRED_HEADERS = {
    "external_id",
    "account_reference",
    "amount",
    "currency",
    "transaction_date",
    "status",
}
SUPPORTED_CURRENCIES = {"PKR", "USD", "EUR"}


def _error(batch, row_number, field, raw_value, error_code, message):
    return ImportValidationError(
        batch=batch,
        row_number=row_number,
        field=field,
        raw_value=raw_value,
        error_code=error_code,
        message=message,
    )


def _validate_row(batch, row_number, raw, seen_ids):
    row = {key: (value or "").strip() for key, value in raw.items()}
    errors = []
    values = {}

    for field in ("external_id", "account_reference", "amount", "currency", "transaction_date"):
        if not row.get(field):
            errors.append(_error(batch, row_number, field, row.get(field, ""), "REQUIRED", f"{field} is required"))

    external_id = row.get("external_id", "")
    if external_id and external_id in seen_ids:
        errors.append(_error(batch, row_number, "external_id", external_id, "DUPLICATE", "external_id is duplicated in this file"))
    elif external_id:
        seen_ids.add(external_id)

    try:
        values["amount"] = Decimal(row.get("amount", ""))
        if values["amount"] <= 0:
            raise ValueError
    except (InvalidOperation, ValueError):
        errors.append(_error(batch, row_number, "amount", row.get("amount", ""), "INVALID_AMOUNT", "amount must be a positive decimal"))

    currency = row.get("currency", "").upper()
    if currency and currency not in SUPPORTED_CURRENCIES:
        errors.append(_error(batch, row_number, "currency", row["currency"], "INVALID_CURRENCY", "currency must be PKR, USD, or EUR"))

    try:
        values["transaction_date"] = datetime.strptime(row.get("transaction_date", ""), "%Y-%m-%d").date()
    except ValueError:
        errors.append(_error(batch, row_number, "transaction_date", row.get("transaction_date", ""), "INVALID_DATE", "date must use YYYY-MM-DD format"))

    if errors:
        return None, errors

    return Transaction(
        batch=batch,
        external_id=external_id,
        account_reference=row["account_reference"],
        amount=values["amount"],
        currency=currency,
        transaction_date=values["transaction_date"],
        status=row.get("status", "").upper(),
    ), []


def process_import(batch):
    batch.status = ImportBatch.Status.PROCESSING
    batch.started_at = timezone.now()
    batch.save(update_fields=("status", "started_at", "updated_at"))

    try:
        with batch.file.open("rb") as source:
            reader = csv.DictReader(source.read().decode("utf-8-sig").splitlines())
            headers = set(reader.fieldnames or [])
            missing = REQUIRED_HEADERS - headers
            if missing:
                raise ValueError(f"Missing required headers: {', '.join(sorted(missing))}")

            transactions = []
            errors = []
            seen_ids = set()
            total_rows = 0
            for row_number, raw in enumerate(reader, start=2):
                total_rows += 1
                transaction_row, row_errors = _validate_row(batch, row_number, raw, seen_ids)
                if transaction_row:
                    transactions.append(transaction_row)
                errors.extend(row_errors)

        with transaction.atomic():
            Transaction.objects.bulk_create(transactions)
            ImportValidationError.objects.bulk_create(errors)
            batch.total_rows = total_rows
            batch.valid_rows = len(transactions)
            batch.invalid_rows = total_rows - len(transactions)
            batch.status = ImportBatch.Status.COMPLETED
            batch.completed_at = timezone.now()
            batch.save(update_fields=("total_rows", "valid_rows", "invalid_rows", "status", "completed_at", "updated_at"))
    except Exception:
        batch.status = ImportBatch.Status.FAILED
        batch.completed_at = timezone.now()
        batch.save(update_fields=("status", "completed_at", "updated_at"))
        raise
