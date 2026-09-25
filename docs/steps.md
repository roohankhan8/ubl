Since the Django project is already initialized, build it in **vertical stages** so each stage leaves you with something working. Avoid starting React, Celery, Docker, and ETL simultaneously.

Use this as the target architecture:

```text
React
  │ REST/JSON
  ▼
Django REST Framework
  │
  ├── Authentication / Permissions
  ├── Import Service
  ├── Validation / Transformation
  ├── Reconciliation Engine
  ├── Reporting
  └── Audit Logging
          │
          ├── PostgreSQL
          └── Celery → Redis
```

# Phase 1 — Establish the backend structure

### Step 1: Install the initial dependencies

Start with only what you need now:

```powershell
pip install djangorestframework
pip install psycopg[binary]
pip install python-dotenv
pip install django-filter
pip install djangorestframework-simplejwt
pip freeze > requirements.txt
```

Don't install Pandas, Celery, Redis, React-related tooling, etc. yet.

### Step 2: Create domain-oriented Django apps

```powershell
python manage.py startapp accounts
python manage.py startapp imports
python manage.py startapp transactions
python manage.py startapp reconciliation
python manage.py startapp audit
```

Skip separate `reports` and `organizations` apps until the domain actually needs them.

### Step 3: Configure settings

Add `rest_framework`, `django_filters`, and the five project apps to `INSTALLED_APPS`. Load these values from `.env` and keep placeholder-only values in `.env.example`:

```text
DEBUG=True
SECRET_KEY=your-local-secret
DB_NAME=reconciliation
DB_USER=postgres
DB_PASSWORD=password
DB_HOST=localhost
DB_PORT=5432
```

Make sure `.env` is ignored by Git.

**Checkpoint:** `python manage.py runserver` starts successfully.

Commit: `chore: configure project structure and environment`

---

# Phase 2 — PostgreSQL

### Step 4: Create the PostgreSQL database

Create the `reconciliation` database, configure Django to use it, then run:

```powershell
python manage.py migrate
```

Verify Django's tables exist in PostgreSQL. Delete `db.sqlite3` once PostgreSQL works.

**Learn before moving on:** understand `ENGINE`, `HOST`, `PORT`, credentials, connections, and migrations.

Commit: `chore: configure PostgreSQL database`

---

# How to use Phase 3 onward

Complete one phase at a time. At every phase boundary run:

```powershell
python manage.py check
python manage.py test
git status --short
```

Do not continue until its **Done when** list passes. Commit each green phase.

Before Phase 3, resolve one current-project inconsistency: both `accounts/` and `users/` exist, and `users` is installed. Pick one owner for user-related code. This guide keeps Django's built-in `User` and uses `accounts` for authentication endpoints. Remove the unused `users` app from `INSTALLED_APPS`, and delete it only after confirming it contains no work you need.

# Phase 3 — Design and implement the data model

Goal: represent imports, normalized transactions, and reconciliation results with database-enforced relationships.

## Step 5: Draw the relationships

```text
User ──< ImportBatch >── DataSource
              │
              └──< Transaction

ImportBatch (source) ──< ReconciliationRun >── ImportBatch (target)
                                  │
                                  └──< ReconciliationResult
                                            ├── source_transaction
                                            └── target_transaction
```

Keep these decisions:

- `DataSource` is an external system; `ImportBatch` is one uploaded file.
- A transaction belongs to one batch.
- `external_id` is unique within a batch, not globally.
- Money uses `DecimalField`, never `FloatField`.
- Protect historical references unless a child has no meaning without its parent.

## Step 6: Add import models

Put `DataSource` and `ImportBatch` in `imports/models.py`:

```python
from django.conf import settings
from django.db import models


class DataSource(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class ImportBatch(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PROCESSING = "PROCESSING", "Processing"
        COMPLETED = "COMPLETED", "Completed"
        FAILED = "FAILED", "Failed"

    data_source = models.ForeignKey(
        DataSource, on_delete=models.PROTECT, related_name="import_batches"
    )
    file = models.FileField(upload_to="imports/%Y/%m/%d/")
    original_filename = models.CharField(max_length=255)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True
    )
    total_rows = models.PositiveIntegerField(default=0)
    valid_rows = models.PositiveIntegerField(default=0)
    invalid_rows = models.PositiveIntegerField(default=0)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="import_batches",
    )
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.original_filename} ({self.status})"
```

Add local file settings to `config/settings.py`:

```python
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"
```

Add `media/` to `.gitignore`; uploaded financial data must not be committed.

## Step 7: Add `Transaction`

Put this in `transactions/models.py`:

```python
from django.db import models


class Transaction(models.Model):
    batch = models.ForeignKey(
        "imports.ImportBatch", on_delete=models.CASCADE, related_name="transactions"
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
```

`CASCADE` fits because transactions have no meaning without their batch. Do not offer casual batch deletion in the API.

## Step 8: Store validation errors

Append to `imports/models.py`:

```python
class ImportValidationError(models.Model):
    batch = models.ForeignKey(
        ImportBatch, on_delete=models.CASCADE, related_name="validation_errors"
    )
    row_number = models.PositiveIntegerField()
    field = models.CharField(max_length=100, blank=True)
    raw_value = models.TextField(blank=True)
    error_code = models.CharField(max_length=50)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["row_number", "id"]

    def __str__(self):
        return f"Row {self.row_number}: {self.error_code}"
```

One bad row may have several errors. Separate rows remain searchable and filterable; a JSON blob on the batch would not.

## Step 9: Add reconciliation models

Put these in `reconciliation/models.py`:

```python
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
        max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True
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
        ReconciliationRun, on_delete=models.CASCADE, related_name="results"
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
        max_digits=18, decimal_places=2, null=True, blank=True
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
```

## Step 10: Create and inspect migrations

```powershell
python manage.py makemigrations imports transactions reconciliation
python manage.py sqlmigrate transactions 0001
python manage.py migrate
python manage.py check
```

Use the actual migration number if it is not `0001`. Read the SQL and identify foreign keys, uniqueness, check constraints, and indexes. Add one model test proving duplicate IDs within a batch and non-positive amounts are rejected.

**Done when:** migrations apply to a clean database; checks/tests pass; you can explain every `on_delete` choice.

Commit: `feat: add import transaction and reconciliation models`

---

# Phase 4 — Django Admin

Goal: inspect backend data before building APIs.

## Step 11: Register each app's models

Example for `imports/admin.py`:

```python
from django.contrib import admin

from .models import DataSource, ImportBatch, ImportValidationError


@admin.register(DataSource)
class DataSourceAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("code", "name")


@admin.register(ImportBatch)
class ImportBatchAdmin(admin.ModelAdmin):
    list_display = (
        "id", "original_filename", "data_source", "status",
        "valid_rows", "invalid_rows", "created_at",
    )
    list_filter = ("status", "data_source")
    search_fields = ("original_filename",)
    readonly_fields = ("created_at", "updated_at")
    list_select_related = ("data_source", "uploaded_by")


@admin.register(ImportValidationError)
class ImportValidationErrorAdmin(admin.ModelAdmin):
    list_display = ("batch", "row_number", "field", "error_code")
    list_filter = ("error_code",)
    search_fields = ("message", "raw_value")
```

Apply the same pattern to transactions and reconciliation. Mark generated result fields read-only.

## Step 12: Create initial records

```powershell
python manage.py createsuperuser
python manage.py runserver
```

At `/admin/`, create `Core Banking System / CORE_BANKING` and `Payment Gateway / PAYMENT_GATEWAY`.

**Done when:** every model is viewable, useful fields can be searched/filtered, and both sources exist.

Commit: `feat: configure administration interface`

---

# Phase 5 — Read-only REST API

Goal: expose data safely before accepting uploads or commands.

## Step 13: Add serializers

Create one `serializers.py` per owning app. Start with `ModelSerializer`; do not add a shared base class.

```python
# transactions/serializers.py
from rest_framework import serializers
from .models import Transaction


class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = "__all__"
        read_only_fields = ("id", "created_at")
```

Add equivalents for `DataSource`, `ImportBatch`, validation errors, runs, and results. Prefer explicit field lists before exposing writes.

## Step 14: Add viewsets and routes

```python
# transactions/views.py
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, viewsets
from .models import Transaction
from .serializers import TransactionSerializer


class TransactionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Transaction.objects.select_related("batch", "batch__data_source")
    serializer_class = TransactionSerializer
    filter_backends = (DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter)
    filterset_fields = ("batch", "status", "currency", "transaction_date")
    search_fields = ("external_id", "account_reference")
    ordering_fields = ("transaction_date", "amount", "created_at")
```

Register all viewsets with one router in `config/api_urls.py`, then include it at `/api/`.

## Step 15: Configure pagination

```python
REST_FRAMEWORK = {
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 50,
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
    ],
}
```

Verify list/detail endpoints, pagination, `?currency=PKR`, `?search=TX100`, and `?ordering=-amount`. Test pagination, one filter, one search, 404, and POST returning 405.

**Done when:** all lists are paginated and unsupported writes are unavailable.

Commit: `feat: add read-only transaction APIs`

---

# Phase 6 — Authentication and authorization

Goal: authenticate with JWT and centralize role checks.

## Step 16: Add JWT

Configure `JWTAuthentication` and `IsAuthenticated` as DRF defaults. Add:

```text
POST /api/auth/login/    -> TokenObtainPairView
POST /api/auth/refresh/  -> TokenRefreshView
GET  /api/auth/me/       -> id, username/email, role
```

## Step 17: Add roles

Keep Django's user model. Add an `accounts.Profile` with a one-to-one user and `TextChoices`: `ADMIN`, `ANALYST`, `VIEWER`. Create profiles explicitly; avoid signals until every creation path truly requires them.

Create reusable `IsAdmin` and `IsAnalystOrAdmin` permissions. Reads use `IsAuthenticated`; uploads/reconciliation use analyst-or-admin; user management uses admin.

Test:

| Action | Admin | Analyst | Viewer |
|---|---:|---:|---:|
| View data | Yes | Yes | Yes |
| Upload | Yes | Yes | No |
| Reconcile | Yes | Yes | No |
| Manage users | Yes | No | No |
| View audit | Yes | Yes | No |

**Done when:** anonymous users get 401, disallowed roles get 403, and refresh works.

Commit: `feat: implement JWT authentication and role permissions`

---

# Phase 7 — Synchronous CSV ETL

Goal: correctly import a small CSV before adding Celery.

## Step 18: Create sample files

Create `sample_data/core_transactions.csv`, `gateway_transactions.csv`, and `invalid_transactions.csv`. Start with this canonical schema:

```csv
external_id,account_reference,amount,currency,transaction_date,status
TX1001,ACC001,25000.00,PKR,2026-09-20,SUCCESS
```

Include duplicates, missing values, negative/zero amounts, invalid dates, whitespace, and bad currencies. Keep samples below 50 rows.

## Step 19: Implement the pipeline

Start with Python's `csv.DictReader`; add Pandas only after measurement. Create `imports/services/pipeline.py` with one public function:

```python
process_import(batch) -> None
```

It should:

1. Set `PROCESSING` and `started_at`.
2. Read with `utf-8-sig`.
3. Validate headers once.
4. Normalize and validate each row.
5. Collect transactions and structured errors.
6. `bulk_create` both inside `transaction.atomic()`.
7. Update counts, status, and `completed_at`.
8. On unexpected failure, mark `FAILED` and re-raise.

Use `Decimal`, `datetime.strptime`, `strip`, and `upper`. Never parse money through `float`.

## Step 20: Validate rules

Require ID, account, amount, currency, and date. Amount must be decimal and positive. Initially support `PKR`, `USD`, and `EUR`. Accept only documented date formats. Reject duplicate IDs within the file/batch.

Store `row_number`, `field`, `raw_value`, `error_code`, and `message` for each issue; continue processing other rows.

Test valid normalization, negative amount, invalid date, duplicate ID, and final batch counts/status.

**Done when:** one direct service test imports valid rows and records all invalid ones with correct counts.

Commit: `feat: implement synchronous CSV import pipeline`

---

# Phase 8 — File upload API

Goal: connect multipart upload to the tested pipeline.

## Step 21: Validate uploads

Create an upload serializer accepting `file` and `data_source`. Validate `.csv`, non-empty content, a configurable maximum size (for example 10 MB), and an active source. Save only the basename as `original_filename`; never trust it as a path.

## Step 22: Create and process the batch

Implement `POST /api/imports/`:

```text
validate -> create PENDING batch -> process_import(batch) -> serialize result
```

Return 201 for success and 400 for input errors. Unexpected failures must leave the batch `FAILED` without exposing tracebacks. Add paginated `GET /api/imports/{id}/errors/`.

Test valid upload, invalid extension, oversize, viewer denial, and mixed rows.

**Done when:** an analyst uploads a sample, sees counts/transactions/errors, and a viewer gets 403.

Commit: `feat: add transaction file import API`

---

# Phase 9 — Reconciliation engine

Goal: compare completed batches by `external_id` outside HTTP code.

## Step 23: Define rules

1. Batches must be completed and different.
2. Pair rows by normalized `external_id`.
3. Source-only is `MISSING_TARGET`; target-only is `MISSING_SOURCE`.
4. Compare amount, currency, account, then date.
5. Equal pairs are `MATCHED`.
6. Amount difference is `target.amount - source.amount`.

If several fields differ, use the first status in that order and list all differences in `reason`.

## Step 24: Implement the service

Create `reconciliation/services/engine.py`:

```python
reconcile(source_batch, target_batch, started_by) -> ReconciliationRun
```

Use dictionaries keyed by ID for the first implementation, then `bulk_create` results in a transaction. Mark unexpected failures `FAILED`. Replace the in-memory approach only when Phase 17 proves it is necessary.

## Step 25: Add endpoints

```text
POST /api/reconciliations/
GET  /api/reconciliations/
GET  /api/reconciliations/{id}/
GET  /api/reconciliations/{id}/results/?status=AMOUNT_MISMATCH
```

Test every result status, same/incomplete batch rejection, and viewer denial.

**Done when:** result count equals the union of IDs and each transaction occurs at most once per run.

Commit: `feat: implement transaction reconciliation engine`

---

# Phase 10 — Consolidate testing

Goal: protect behavior before adding infrastructure.

The Django test runner is sufficient. Do not install pytest unless you will use it consistently. Keep tests beside each app and split `tests.py` only when navigation becomes difficult.

Prioritize database constraints, JWT/roles, CSV validation, state/count updates, all match outcomes, and API responses.

```powershell
python manage.py test
python manage.py check
```

**Done when:** tests start from an empty database, need no manual seed data, and cover each reconciliation outcome and upload permission.

Commit: `test: cover imports permissions and reconciliation`

---

# Phase 11 — Background processing

Goal: move proven long work out of HTTP.

## Step 26: Add Celery/Redis

```powershell
pip install celery redis
pip freeze > requirements.txt
```

Add `config/celery.py`, import it from `config/__init__.py`, and configure broker/result URLs via environment variables. Keep tasks thin: fetch a batch by ID and call the existing service.

## Step 27: Return asynchronous responses

Upload now validates, creates `PENDING`, calls `task.delay(batch.id)`, and returns `202 Accepted`. Poll `GET /api/imports/{id}/`. Move reconciliation to Celery only if it is also slow.

Run locally:

```powershell
redis-server
celery -A config worker -l INFO --pool=solo
python manage.py runserver
```

`--pool=solo` is the simple Windows development option; use Linux workers in production.

**Done when:** HTTP returns immediately and the worker transitions `PENDING -> PROCESSING -> COMPLETED/FAILED`.

Commit: `feat: process imports in background workers`

---

# Phase 12 — Audit logging

Goal: append-only history for important actions.

Add `AuditLog` fields: nullable `user`, `action`, `entity_type`, `entity_id`, `metadata = JSONField(default=dict)`, and `created_at`. Start with `LOGIN`, `UPLOAD_DATASET`, `START_RECONCILIATION`, and `COMPLETE_RECONCILIATION`.

Create one explicit `record_event(...)` service; do not hide actor-aware business events in signals. Expose only read-only, paginated endpoints filtered by user/action/date. Admin and analyst can read; viewer cannot.

**Done when:** successful upload/reconciliation actions create rows and API mutations return 405.

Commit: `feat: add append-only audit logging`

---

# Phase 13 — Dashboard API

Goal: aggregate server-side rather than downloading all transactions.

Create `GET /api/dashboard/summary/` returning transaction/import counts, matched/mismatched/missing totals, match rate, and recent imports. Use `Count` and filtered aggregates. Define match rate as matched divided by all results times 100; return `0.00` when empty.

**Done when:** empty data returns zeros, seeded totals are correct, and query count stays constant as rows increase.

Commit: `feat: add dashboard summary API`

---

# Phase 14 — React frontend

Goal: a functional operations UI backed by real APIs.

```powershell
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install
npm install react-router-dom @tanstack/react-query
```

Use native `fetch`; add Axios only if it removes meaningful repetition. Build `/login`, `/dashboard`, `/imports`, `/imports/new`, `/imports/:id`, `/transactions`, `/reconciliations`, `/reconciliations/:id`, and `/audit-logs` in that order.

Start with tables, forms, loading/empty/error states, keyboard access, and responsive laptop/tablet layout. Avoid a component library until repeated patterns justify one.

**Done when:** every page uses real API data and is usable without a mouse.

Commit: `feat: add React operations interface`

---

# Phase 15 — Frontend/backend integration

Goal: complete auth, upload, polling, filtering, and errors.

Create one fetch wrapper that prefixes `VITE_API_URL`, sends access tokens, avoids setting JSON headers on `FormData`, attempts one refresh on 401, logs out on refresh failure, and parses errors consistently.

For a portfolio SPA, `sessionStorage` is acceptable if documented; production should prefer secure HttpOnly cookies. Use TanStack Query `refetchInterval` for pending jobs and stop on terminal status/unmount.

Verify: login, upload/poll, transaction filters, reconcile/poll, results, logout, and helpful 400/401/403/404/network errors.

**Done when:** a fresh browser can complete the full workflow without hardcoded data.

Commit: `feat: integrate frontend with reconciliation API`

---

# Phase 16 — API documentation

```powershell
pip install drf-spectacular
pip freeze > requirements.txt
```

Expose `/api/schema/` and `/api/docs/`. Annotate upload, dashboard, and reconciliation creation when inference is insufficient. Document auth, pagination, filters, errors, and 202 jobs.

**Done when:** the schema validates, Swagger loads, and every public endpoint has the right method/body.

Commit: `docs: publish OpenAPI schema and Swagger UI`

---

# Phase 17 — Performance measurement

Generate 100,000 fictional rows with Python's `csv` module; ignore the generated file. Measure import time, rows/second, peak memory, reconciliation time, and list/dashboard query counts.

Use `QuerySet.explain()` and apply only evidenced fixes: `select_related`, `prefetch_related`, batch-sized `bulk_create`, `iterator`, or a justified index. Record before/after numbers in README.

**Done when:** at least one repeatable measurement justifies each claimed optimization.

Commit: `perf: optimize measured import and query bottlenecks`

---

# Phase 18 — Docker

Add `Dockerfile`, `compose.yaml`, and `.dockerignore`. Compose `web`, `worker`, PostgreSQL, and Redis; web/worker share an image with different commands. Use volumes for database/media and environment variables for secrets.

```powershell
docker compose build
docker compose up
docker compose exec web python manage.py migrate
docker compose exec web python manage.py test
```

Skip local Nginx unless hosting requires it.

**Done when:** a clean clone starts, migrates, tests, uploads, and runs a worker task.

Commit: `chore: add reproducible Docker environment`

---

# Phase 19 — Continuous integration

Create one GitHub Actions workflow with PostgreSQL/Redis services. Check out, set up Python, install requirements, run `check`, `makemigrations --check --dry-run`, and tests; if `frontend/` exists, set up Node and build it.

**Done when:** clean checkout passes and tests or missing migrations make CI fail.

Commit: `ci: run backend tests and frontend build`

---

# Phase 20 — Deployment

Deploy React static hosting, Django web, Celery worker, managed PostgreSQL/Redis, and persistent/object file storage. Production settings need environment-driven secrets, `DEBUG=False`, hosts/origins, HTTPS cookies, database, Redis, and storage.

```powershell
python manage.py check --deploy
```

Run migrations as a release step. Verify login, upload/worker, reconciliation, dashboard, docs, and logout with fictional data.

**Done when:** the public demo works in a fresh browser and exposes no secrets, real data, debug pages, or local-only URLs.

Commit: `chore: configure production deployment`

---

# Phase 21 — Demo data

Create an idempotent `python manage.py seed_demo` command using `get_or_create`/`update_or_create`. Add three roles/users, two sources, two completed batches, matched/mismatched/missing examples, one completed run, and audit events. Use obviously fictional data.

**Done when:** running twice succeeds without logical duplicates and immediately populates the dashboard.

Commit: `feat: add repeatable demo data`

---

# Phase 22 — README and repository polish

README order: summary; live demo/credentials; screenshots; problem/workflow; Mermaid architecture; features; stack; data model; local setup; environment; web/worker/frontend commands; tests; API docs; measured performance; decisions/trade-offs; deployment; known limitations.

Test every command from a clean clone/container. Remove generated datasets, uploads, local databases, secrets, dead screenshots, and unused dependencies.

**Done when:** another developer can run it without asking for missing instructions.

Commit: `docs: complete project documentation`

---

# Phase 23 — Prepare to defend the project

Be ready to explain model separation, per-batch uniqueness, decimal money, deletion rules, 202 responses, partial row failures, duplicate prevention, missing matches, measured optimization, and scaling to millions of rows or multiple organizations.

Practice this five-minute demo:

1. Log in as analyst.
2. Upload two fixtures.
3. Show background progress and validation errors.
4. Reconcile them.
5. Filter/open a mismatch.
6. Show dashboard and audit history.
7. Show API docs and green CI.

**Done when:** the demo is repeatable and you can explain each major model, state transition, and security boundary.

---

# Recommended Git progression

```text
feat: add import transaction and reconciliation models
feat: configure administration interface
feat: add read-only transaction APIs
feat: implement JWT authentication and role permissions
feat: implement synchronous CSV import pipeline
feat: add transaction file import API
feat: implement transaction reconciliation engine
test: cover imports permissions and reconciliation
feat: process imports in background workers
feat: add append-only audit logging
feat: add dashboard summary API
feat: add React operations interface
feat: integrate frontend with reconciliation API
docs: publish OpenAPI schema and Swagger UI
perf: optimize measured import and query bottlenecks
chore: add reproducible Docker environment
ci: run backend tests and frontend build
chore: configure production deployment
feat: add repeatable demo data
docs: complete project documentation
```

# Immediate next milestone

Do only Phase 3 now: resolve `accounts` versus `users`, implement the six models, make/inspect migrations, add the two constraint tests, run checks/tests, and commit. Do not begin serializers, uploads, Celery, or React until it is green.
