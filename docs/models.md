# Data model guide

This document explains the models currently implemented in the `imports`, `transactions`, and `reconciliation` apps.

## Relationship overview

```text
User ──< ImportBatch >── DataSource
              │
              ├──< Transaction
              └──< ImportValidationError

ImportBatch (source) ──< ReconciliationRun >── ImportBatch (target)
                                  │
                                  └──< ReconciliationResult
                                            ├── source_transaction
                                            └── target_transaction
```

The symbols `──<` mean “one-to-many.” For example, one `ImportBatch` can contain many `Transaction` records.

## Why the data is separated

The models represent different concepts:

- `DataSource` identifies an external system.
- `ImportBatch` represents one file uploaded from a system.
- `Transaction` represents one valid, normalized row from that file.
- `ImportValidationError` describes a row that could not be imported.
- `ReconciliationRun` represents one comparison between two batches.
- `ReconciliationResult` stores the outcome for one transaction pair or missing transaction.

Keeping these concepts separate preserves upload history and avoids duplicating source and file information on every transaction.

---

# Imports app

The `imports` app owns file sources, upload batches, and row-level validation errors.

## `DataSource`

`DataSource` represents an external system that produces transaction files.

Example records:

```text
Core Banking System | CORE_BANKING
Payment Gateway     | PAYMENT_GATEWAY
Settlement System   | SETTLEMENT_SYSTEM
```

### Fields

| Field | Purpose |
|---|---|
| `id` | Automatic primary key created by Django. |
| `name` | Human-readable source name. |
| `code` | Stable program-friendly identifier. It must be unique. |
| `description` | Optional explanation of the source. |
| `is_active` | Determines whether the source can be used for new imports. |
| `created_at` | Set automatically when the source is created. |
| `updated_at` | Updated automatically whenever the source is saved. |

`Meta.ordering = ["name"]` means source querysets are alphabetically ordered unless a query specifies another order.

`__str__()` returns the source name, producing readable values in Django Admin and the shell.

### Relationships and deletion

`ImportBatch.data_source` uses `on_delete=models.PROTECT`. Django will refuse to delete a source if import batches still reference it. This preserves the origin of historical data.

The reverse relationship is available through:

```python
source.import_batches.all()
```

---

## `ImportBatch`

`ImportBatch` represents one uploaded transaction file and its processing state.

Uploading two files from Core Banking creates two batches that reference the same `DataSource`.

### Status values

The nested `Status` class uses `models.TextChoices`:

| Status | Meaning |
|---|---|
| `PENDING` | The file was accepted but processing has not started. |
| `PROCESSING` | The import pipeline is reading and validating the file. |
| `COMPLETED` | Processing finished successfully. Invalid rows may still exist. |
| `FAILED` | An unexpected error prevented the import from completing. |

Expected state transitions are:

```text
PENDING → PROCESSING → COMPLETED
                     ↘ FAILED
```

Using `TextChoices` prevents status strings from being repeated throughout the code:

```python
batch.status = ImportBatch.Status.PROCESSING
```

### Fields

| Field | Purpose |
|---|---|
| `data_source` | System that produced the file. |
| `file` | Stored uploaded file. Files are organized under `imports/YYYY/MM/DD/`. |
| `original_filename` | Filename shown to users, kept separately from the storage path. |
| `status` | Current processing state. Indexed because it will be filtered frequently. |
| `total_rows` | Number of data rows encountered. |
| `valid_rows` | Number of rows converted into transactions. |
| `invalid_rows` | Number of rejected rows. |
| `uploaded_by` | Django user who uploaded the file. |
| `started_at` | Time processing started; empty while pending. |
| `completed_at` | Time processing ended; empty until completion or failure. |
| `created_at` | Time the batch record was created. |
| `updated_at` | Time the batch record was last saved. |

`PositiveIntegerField` prevents negative row counts.

`null=True` allows an absent timestamp in the database. `blank=True` allows it to be omitted by Django forms and serializers.

### Relationships and deletion

- `data_source` uses `PROTECT`, preserving the system that supplied the file.
- `uploaded_by` uses `PROTECT`, preserving who performed the upload.
- Deleting a batch cascades to its transactions and validation errors because those records have no meaning without their batch.
- A batch used by a reconciliation run cannot be deleted because the run references it with `PROTECT`.

Reverse relationships include:

```python
source.import_batches.all()
user.import_batches.all()
batch.transactions.all()
batch.validation_errors.all()
batch.source_reconciliation_runs.all()
batch.target_reconciliation_runs.all()
```

The default ordering is newest batch first.

---

## `ImportValidationError`

`ImportValidationError` stores a structured explanation of invalid input.

Example:

```text
Row: 14
Field: amount
Raw value: -200
Code: INVALID_AMOUNT
Message: Amount must be greater than zero.
```

### Fields

| Field | Purpose |
|---|---|
| `batch` | Import where the error occurred. |
| `row_number` | Original row number in the uploaded file. |
| `field` | Column responsible for the error; blank for row/file-wide errors. |
| `raw_value` | Original untrusted value for investigation. |
| `error_code` | Stable machine-readable category such as `INVALID_AMOUNT`. |
| `message` | Human-readable explanation. |
| `created_at` | Time the error was recorded. |

One invalid row may have several errors. Separate records make errors searchable, filterable, and pageable.

Deleting the parent batch deletes its errors through `CASCADE`.

Errors are ordered by row number and then primary key, keeping multiple errors for the same row stable.

---

# Transactions app

## `Transaction`

`Transaction` represents one valid, normalized transaction produced by the import pipeline.

Example:

```text
External ID: TX1001
Account: ACC001
Amount: 25000.00
Currency: PKR
Date: 2026-09-20
Status: SUCCESS
```

### Fields

| Field | Purpose |
|---|---|
| `batch` | Import batch containing this transaction. |
| `external_id` | Identifier supplied by the external system. |
| `account_reference` | Account associated with the transaction. |
| `amount` | Financial amount with up to 16 whole-number and 2 decimal digits. |
| `currency` | Three-character currency code such as `PKR` or `USD`. |
| `transaction_date` | Business date of the transaction. |
| `status` | Optional source-system status such as `SUCCESS`. |
| `created_at` | Time the normalized record was inserted. |

### Why `DecimalField` is required

Financial amounts must not use binary floating point. Values such as `0.1` cannot always be represented exactly by `float`, which can cause incorrect comparisons and totals.

```python
amount = Decimal("25000.00")
```

`DecimalField(max_digits=18, decimal_places=2)` stores exact values with two decimal places.

### Database constraints

`unique_transaction_per_batch` enforces uniqueness for:

```text
(batch, external_id)
```

The same external ID may appear in different batches, but it cannot appear twice in one batch.

`transaction_amount_positive` enforces:

```text
amount > 0
```

These rules live in PostgreSQL, so they apply even when data is inserted outside a form or serializer.

### Indexes and ordering

Indexes exist on:

- `external_id`, which is used for search and reconciliation matching;
- `transaction_date`, which is useful for date filtering and sorting.

The default order is newest transaction date first, then external ID.

### Relationships and deletion

The batch relationship uses `CASCADE`: deleting a batch deletes its transactions. A transaction cannot meaningfully exist without its originating file.

Reconciliation results reference transactions using `PROTECT`, preventing transactions that form part of historical results from being deleted accidentally.

---

# Reconciliation app

The reconciliation app compares transactions from two completed batches.

## `ReconciliationRun`

`ReconciliationRun` represents one comparison operation.

Example:

```text
Source batch: Core Banking file #12
Target batch: Payment Gateway file #13
Started by: analyst
Status: COMPLETED
```

### Fields

| Field | Purpose |
|---|---|
| `source_batch` | Batch treated as the source side. |
| `target_batch` | Batch treated as the target side. |
| `status` | `PENDING`, `PROCESSING`, `COMPLETED`, or `FAILED`. |
| `started_by` | User who requested reconciliation. |
| `started_at` | Time comparison processing started. |
| `completed_at` | Time comparison processing finished. |
| `created_at` | Time the run was requested. |

Its state lifecycle is the same as an import batch.

### Database constraint

`different_reconciliation_batches` prevents comparing a batch with itself:

```text
source_batch != target_batch
```

Application validation will later add rules such as requiring both batches to be completed.

### Relationships and deletion

Both batches and `started_by` use `PROTECT`, preserving reconciliation history. Deleting a run deletes its result rows through `CASCADE`.

Reverse relationships distinguish the two roles:

```python
batch.source_reconciliation_runs.all()
batch.target_reconciliation_runs.all()
user.reconciliation_runs.all()
run.results.all()
```

Runs are ordered newest first.

---

## `ReconciliationResult`

`ReconciliationResult` stores the outcome for a matched pair or for a transaction missing from one batch.

### Status values

| Status | Meaning |
|---|---|
| `MATCHED` | All compared fields agree. |
| `AMOUNT_MISMATCH` | Amounts differ. |
| `CURRENCY_MISMATCH` | Currency codes differ. |
| `ACCOUNT_MISMATCH` | Account references differ. |
| `DATE_MISMATCH` | Transaction dates differ. |
| `MISSING_SOURCE` | A target transaction has no source transaction. |
| `MISSING_TARGET` | A source transaction has no target transaction. |

### Fields

| Field | Purpose |
|---|---|
| `run` | Reconciliation operation that produced the result. |
| `source_transaction` | Source-side transaction; empty for `MISSING_SOURCE`. |
| `target_transaction` | Target-side transaction; empty for `MISSING_TARGET`. |
| `status` | Match or discrepancy category. Indexed for filtering. |
| `difference` | Numeric amount difference when relevant. |
| `reason` | Human-readable details about the comparison. |
| `created_at` | Time the result was stored. |

The intended amount calculation is:

```text
difference = target amount - source amount
```

For example, source `12000.00` and target `12500.00` produce `500.00`.

### Why transaction fields can be empty

Most results reference both transactions. Missing results reference only one:

| Result | Source transaction | Target transaction |
|---|---|---|
| `MATCHED` or mismatch | Required | Required |
| `MISSING_SOURCE` | Empty | Required |
| `MISSING_TARGET` | Required | Empty |

The reconciliation service will enforce this status-specific rule.

### Database uniqueness

Conditional constraints ensure that a non-null source or target transaction appears at most once in a run:

```text
(run, source_transaction) is unique when source_transaction exists
(run, target_transaction) is unique when target_transaction exists
```

This prevents the engine from matching the same transaction more than once during one reconciliation.

Transactions use `PROTECT`, while the run uses `CASCADE`. Therefore:

- deleting a run removes its generated results;
- deleting a transaction referenced by a result is blocked.

---

# Example lifecycle

## 1. Create sources

```text
CORE_BANKING
PAYMENT_GATEWAY
```

## 2. Upload files

Each file creates an `ImportBatch` in `PENDING` state.

## 3. Process each import

The pipeline changes the batch to `PROCESSING`. Valid rows create `Transaction` records, while invalid fields create `ImportValidationError` records. Counts are updated and the batch becomes `COMPLETED` or `FAILED`.

## 4. Reconcile two completed batches

A `ReconciliationRun` is created. Transactions are paired by `external_id` and compared by amount, currency, account, and date.

## 5. Store the results

Each pair or missing record creates one `ReconciliationResult`. The run becomes `COMPLETED` when every ID has been considered.

---

# Important Django terms

| Term | Meaning in this project |
|---|---|
| `ForeignKey` | A many-to-one relationship, such as many transactions belonging to one batch. |
| `related_name` | Name used to navigate the relationship backwards. |
| `PROTECT` | Block deletion while referenced historical records exist. |
| `CASCADE` | Delete dependent child records with their parent. |
| `null=True` | The database column may contain SQL `NULL`. |
| `blank=True` | Django validation allows the value to be omitted. |
| `db_index=True` | Create an index for frequent filtering. |
| `TextChoices` | Define a controlled set of stored string values. |
| `CheckConstraint` | Make PostgreSQL reject data that violates a rule. |
| `UniqueConstraint` | Prevent duplicate field combinations. |
| `auto_now_add` | Set the timestamp once when a record is created. |
| `auto_now` | Refresh the timestamp every time a record is saved. |
