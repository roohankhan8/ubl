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
          │
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
```

Then:

```powershell
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

I would initially skip separate `reports` and `organizations` apps. Add them only when the domain actually needs them.

Your structure becomes:

```text
project/
├── config/
├── accounts/
├── imports/
├── transactions/
├── reconciliation/
├── audit/
├── manage.py
├── requirements.txt
├── .env
└── .gitignore
```

### Step 3: Configure settings

Add the applications:

```python
INSTALLED_APPS = [
    ...
    "rest_framework",
    "django_filters",

    "accounts",
    "imports",
    "transactions",
    "reconciliation",
    "audit",
]
```

Create `.env`:

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

Create:

```text
.env.example
```

containing only placeholder values.

**Checkpoint:** Django starts successfully with:

```powershell
python manage.py runserver
```

Commit:

```text
chore: configure project structure and environment
```

---

# Phase 2 — PostgreSQL

### Step 4: Create the PostgreSQL database

Create:

```text
reconciliation
```

Configure Django to use PostgreSQL rather than SQLite.

Run:

```powershell
python manage.py migrate
```

Verify that Django's tables exist in PostgreSQL.

Delete `db.sqlite3` once PostgreSQL works.

**Learn before moving on:** understand what `ENGINE`, `HOST`, `PORT`, database credentials, connections and migrations are doing.

Commit:

```text
chore: configure PostgreSQL database
```

---

# Phase 3 — Design the data model

Do not immediately write models.

First draw this:

```text
User
 │
 │ uploads
 ▼
ImportBatch ─────── DataSource
 │
 │ contains
 ▼
Transaction


ImportBatch ──────┐
                  │
                  ▼
          ReconciliationRun
                  │
                  ▼
          ReconciliationResult
             /           \
            /             \
Source Transaction     Target Transaction
```

### Step 5: Create `DataSource`

Example concept:

```text
DataSource
-----------
id
name
code
description
is_active
created_at
updated_at
```

Example records:

```text
CORE_BANKING
PAYMENT_GATEWAY
SETTLEMENT_SYSTEM
```

Don't hardcode source names throughout the application.

### Step 6: Create `ImportBatch`

Conceptually:

```text
ImportBatch
-----------
id
data_source
file
original_filename
status

total_rows
valid_rows
invalid_rows

uploaded_by

started_at
completed_at
created_at
updated_at
```

Possible statuses:

```text
PENDING
PROCESSING
COMPLETED
FAILED
```

Use Django `TextChoices` rather than random strings throughout the code.

### Step 7: Create `Transaction`

This is your most important table.

Start with:

```text
Transaction
-----------
id
batch
external_id
account_reference
amount
currency
transaction_date
status
created_at
```

Think carefully about:

```text
Decimal vs float
indexes
nullability
foreign keys
uniqueness
```

Use `DecimalField` for money. Never `FloatField`.

### Step 8: Create validation errors

```text
ImportValidationError
---------------------
id
batch
row_number
field
raw_value
error_code
message
created_at
```

This allows malformed input to be recorded rather than destroying the entire import.

### Step 9: Create reconciliation models

```text
ReconciliationRun
-----------------
id
source_batch
target_batch
status
started_by
started_at
completed_at

ReconciliationResult
--------------------
id
run
source_transaction
target_transaction
status
difference
reason
created_at
```

Statuses could include:

```text
MATCHED
AMOUNT_MISMATCH
MISSING_SOURCE
MISSING_TARGET
```

Now:

```powershell
python manage.py makemigrations
python manage.py migrate
```

Then inspect the actual PostgreSQL schema.

**Checkpoint:** you should be able to explain every FK, unique constraint and index.

Commit:

```text
feat: add transaction and reconciliation data models
```

---

# Phase 4 — Django Admin

### Step 10: Configure Django Admin

Before building APIs or React, make your data inspectable.

Register:

```text
DataSource
ImportBatch
Transaction
ImportValidationError
ReconciliationRun
ReconciliationResult
```

Add useful:

```python
list_display
list_filter
search_fields
readonly_fields
```

Create an admin:

```powershell
python manage.py createsuperuser
```

Open:

```text
/admin/
```

Create two sources manually:

```text
Core Banking System
Payment Gateway
```

This gives you an immediate internal debugging interface.

Commit:

```text
feat: configure administration interface
```

---

# Phase 5 — Build the REST API

### Step 11: Learn serializers before generating everything

Implement serializers for:

```text
DataSource
ImportBatch
Transaction
ReconciliationRun
ReconciliationResult
```

Understand this flow:

```text
HTTP JSON
    ↓
Serializer
    ↓ validation
Python values
    ↓
Model
    ↓
PostgreSQL
```

and backwards:

```text
PostgreSQL
    ↓
Model
    ↓
Serializer
    ↓
JSON
```

This is roughly where your Laravel API Resource/Form Request experience will help.

### Step 12: Build basic endpoints

Start with:

```text
GET /api/data-sources/

GET /api/imports/
GET /api/imports/{id}/

GET /api/transactions/
GET /api/transactions/{id}/

GET /api/reconciliations/
GET /api/reconciliations/{id}/
```

Don't build file upload yet.

### Step 13: Add pagination, filtering and searching

For transactions:

```http
GET /api/transactions/?page=2
GET /api/transactions/?status=SUCCESS
GET /api/transactions/?currency=PKR
GET /api/transactions/?external_id=TX100
```

Use `django-filter`.

Do not fetch 100,000 transactions into one API response.

Commit:

```text
feat: add transaction REST APIs
```

---

# Phase 6 — Authentication and authorization

### Step 14: Implement JWT

Using SimpleJWT:

```text
POST /api/auth/login/
POST /api/auth/refresh/
GET  /api/auth/me/
```

The login response provides:

```json
{
  "access": "...",
  "refresh": "..."
}
```

### Step 15: Add roles

Start simple:

```text
ADMIN
ANALYST
VIEWER
```

Then implement permissions.

For example:

| Action | Admin | Analyst | Viewer |
|---|---:|---:|---:|
| View transactions | ✓ | ✓ | ✓ |
| Upload files | ✓ | ✓ | ✗ |
| Run reconciliation | ✓ | ✓ | ✗ |
| Manage users | ✓ | ✗ | ✗ |
| View audit logs | ✓ | ✓ | ✗ |

Don't put this logic into individual views repeatedly.

Create reusable DRF permission classes.

Commit:

```text
feat: implement JWT authentication and role permissions
```

---

# Phase 7 — Build ETL

This is where the project becomes interesting.

### Step 16: Install data-processing dependencies

Now install:

```powershell
pip install pandas openpyxl
```

Update:

```powershell
pip freeze > requirements.txt
```

### Step 17: Create sample datasets

Create:

```text
sample_data/
├── core_transactions.csv
├── gateway_transactions.csv
├── invalid_transactions.csv
└── large_transactions.csv
```

Start with 20–50 rows.

Deliberately include:

```text
duplicates
missing IDs
negative amounts
invalid dates
different date formats
whitespace
missing accounts
invalid currency
amount mismatches
```

This is critical for testing.

### Step 18: Build extraction

Your import pipeline should conceptually have:

```text
extract()
validate()
transform()
load()
```

Don't write one giant:

```python
def import_transactions(file):
    # 300 lines
```

Prefer components such as:

```text
imports/
    services/
        extractor.py
        validator.py
        transformer.py
        loader.py
        pipeline.py
```

Mental model:

```text
Extractor
    ↓
raw rows

Validator
    ↓
valid/invalid rows

Transformer
    ↓
normalized records

Loader
    ↓
PostgreSQL
```

### Step 19: Build validation

Check things like:

```text
external_id required
amount required
amount > 0
date valid
currency supported
account reference required
duplicate transaction
```

Return structured errors:

```json
{
    "row": 14,
    "field": "amount",
    "value": "-200",
    "code": "INVALID_AMOUNT",
    "message": "Amount must be greater than zero."
}
```

Store those errors.

### Step 20: Build transformation

Convert dirty input:

```text
" tx001 "
```

into:

```text
TX001
```

Convert:

```text
"PKR 25,000"
```

into a proper decimal representation.

Normalize dates.

Be careful here: Pandas often pushes developers toward floats. **Don't let financial amounts silently become floating-point values.**

### Step 21: Build loading

Don't do:

```python
for row in rows:
    Transaction.objects.create(...)
```

for huge imports.

Learn and use:

```python
bulk_create()
```

Use database transactions where appropriate:

```python
transaction.atomic()
```

Now you have something meaningful to discuss in an interview:

> I optimized batch ingestion by validating and transforming records before using bulk inserts rather than performing individual database writes.

Commit:

```text
feat: implement transaction ETL pipeline
```

---

# Phase 8 — File upload

### Step 22: Build upload endpoint

Create:

```http
POST /api/imports/
```

Multipart request:

```text
file = transactions.csv
data_source = 1
```

Flow:

```text
HTTP upload
    ↓
validate extension/size
    ↓
create ImportBatch
    ↓
save file
    ↓
ETL pipeline
    ↓
update ImportBatch
```

Response:

```json
{
    "id": 42,
    "status": "completed",
    "total_rows": 1000,
    "valid_rows": 987,
    "invalid_rows": 13
}
```

### Step 23: Add validation-error endpoint

```text
GET /api/imports/42/errors/
```

Now users can investigate failed rows.

Commit:

```text
feat: add transaction file import API
```

---

# Phase 9 — Reconciliation engine

This should be the project's main business-logic feature.

### Step 24: Define matching rules

Start simple.

Match using:

```text
external_id
```

Then compare:

```text
amount
currency
account
date
```

Example:

```text
Source:
TX001
PKR 25,000

Target:
TX001
PKR 25,000

→ MATCHED
```

Another:

```text
Source:
TX002
PKR 12,000

Target:
TX002
PKR 12,500

→ AMOUNT_MISMATCH
difference = 500
```

And:

```text
Source:
TX003

Target:
nothing

→ MISSING_TARGET
```

### Step 25: Keep reconciliation separate from HTTP

Don't put reconciliation algorithms in:

```python
views.py
```

Instead:

```text
reconciliation/
    services/
        matcher.py
        engine.py
```

Think:

```python
engine.reconcile(source_batch, target_batch)
```

The HTTP view should orchestrate the operation, not implement the algorithm.

### Step 26: Add endpoint

```http
POST /api/reconciliations/
```

Request:

```json
{
    "source_batch_id": 12,
    "target_batch_id": 13
}
```

Response:

```json
{
    "id": 8,
    "status": "completed",
    "matched": 940,
    "mismatched": 42,
    "missing": 18
}
```

Then:

```text
GET /api/reconciliations/8/results/
```

Commit:

```text
feat: implement transaction reconciliation engine
```

---

# Phase 10 — Testing

Don't leave testing until the very end.

Install:

```powershell
pip install pytest pytest-django factory-boy
```

Organize tests roughly by:

```text
tests/
    test_models.py
    test_api.py
    test_permissions.py
    test_pipeline.py
    test_validator.py
    test_transformer.py
    test_reconciliation.py
```

Prioritize business behavior.

For example:

```text
test_valid_transaction_is_imported

test_negative_amount_is_rejected

test_duplicate_transaction_is_rejected

test_invalid_date_is_reported

test_identical_transactions_match

test_amount_difference_is_detected

test_missing_transaction_is_detected

test_viewer_cannot_upload

test_analyst_can_reconcile
```

This matters more than chasing an arbitrary coverage percentage.

---

# Phase 11 — Background processing

Only introduce Celery **after synchronous ETL works**.

### Step 27: Install Celery + Redis

```powershell
pip install celery redis
```

The architecture changes from:

```text
POST /imports
    ↓
Django
    ↓
process 100k rows
    ↓
wait...
    ↓
response
```

to:

```text
POST /imports
    ↓
Django
    ↓
ImportBatch(PENDING)
    ↓
Celery queue
    ↓
202 Accepted


Celery Worker
    ↓
PROCESSING
    ↓
ETL
    ↓
COMPLETED
```

### Step 28: Return asynchronous responses

Upload:

```http
POST /api/imports/
```

returns:

```json
{
    "id": 42,
    "status": "pending"
}
```

Then frontend checks:

```http
GET /api/imports/42/
```

Eventually:

```json
{
    "id": 42,
    "status": "completed",
    "total_rows": 100000,
    "valid_rows": 99782,
    "invalid_rows": 218
}
```

Do the same for reconciliation if it becomes expensive.

This gives you a good answer to:

> Why did you use Celery?

Not:

> Because Celery is popular.

But:

> Importing large datasets is long-running work. Keeping it inside the HTTP request ties up web workers and can cause timeouts, so I moved the processing into asynchronous workers.

That distinction is important.

---

# Phase 12 — Audit logging

### Step 29: Build audit logs

Track important actions:

```text
LOGIN
UPLOAD_DATASET
START_RECONCILIATION
COMPLETE_RECONCILIATION
RESOLVE_DISCREPANCY
```

Store:

```text
user
action
entity_type
entity_id
metadata
timestamp
```

Expose:

```text
GET /api/audit-logs/
```

Don't expose normal update/delete endpoints for audit entries.

---

# Phase 13 — Dashboard API

Don't make React calculate business metrics from thousands of transactions.

Create:

```text
GET /api/dashboard/summary/
```

Example:

```json
{
    "transactions": 124521,
    "imports": 28,
    "reconciliation": {
        "matched": 121403,
        "mismatched": 2841,
        "missing": 277
    },
    "match_rate": 97.49
}
```

Let PostgreSQL/Django aggregate this.

This gives you an opportunity to learn:

```text
Count
Sum
Avg
annotate()
aggregate()
grouping
indexes
query optimization
```

---

# Phase 14 — React frontend

Only now start the frontend.

Create:

```powershell
npm create vite@latest frontend -- --template react-ts
```

Use:

```text
React
TypeScript
React Router
TanStack Query
Axios/fetch
```

Build screens in this order:

```text
Login
  ↓
Dashboard
  ↓
Imports
  ↓
Upload
  ↓
Transactions
  ↓
Reconciliations
  ↓
Reconciliation Details
  ↓
Validation Errors
  ↓
Audit Logs
```

Do not spend two days choosing button colors.

The frontend exists primarily to demonstrate **frontend/backend integration**.

---

# Phase 15 — Make the frontend genuinely integrate with the backend

Implement an API layer:

```text
React
 │
 ├── authApi
 ├── importApi
 ├── transactionApi
 └── reconciliationApi
       │
       ▼
      DRF
```

Handle:

```text
JWT storage
Authorization header
401 responses
refresh tokens
loading
errors
pagination
filters
background-job polling
```

For example:

```text
Upload CSV
   ↓
POST /api/imports/
   ↓
{ id: 42, status: "pending" }
   ↓
React polls /api/imports/42/
   ↓
processing
   ↓
processing
   ↓
completed
   ↓
refresh dashboard
```

That is much more impressive than static dashboard cards.

---

# Phase 16 — API documentation

Add OpenAPI/Swagger.

For example, use `drf-spectacular`.

You want:

```text
/api/schema/
/api/docs/
```

Document:

```text
request schemas
response schemas
authentication
errors
filters
pagination
```

Someone reviewing your GitHub should be able to understand the backend without reading every Python file.

---

# Phase 17 — Performance work

Now create a larger dataset:

```text
100,000–500,000 transactions
```

Measure performance.

Check queries using:

```python
print(queryset.explain())
```

Learn when to use:

```text
select_related()
prefetch_related()
values()
only()
indexes
bulk_create()
iterator()
```

Do not add indexes randomly.

For example, if reconciliation repeatedly searches:

```sql
WHERE external_id = ?
```

then `external_id` becomes an obvious indexing candidate.

This phase gives you concrete performance decisions to discuss.

---

# Phase 18 — Docker

Once the application works normally, containerize it.

Your local architecture:

```text
docker-compose
│
├── backend
│     Django
│
├── worker
│     Celery
│
├── postgres
│
├── redis
│
└── frontend
      React
```

A developer should eventually be able to clone your repository and run something close to:

```powershell
docker compose up --build
```

---

# Phase 19 — CI

Add GitHub Actions:

```text
Push / PR
   ↓
Install Python
   ↓
Install dependencies
   ↓
Run linting
   ↓
Run migrations/checks
   ↓
Run pytest
   ↓
Build frontend
```

If tests fail:

```text
❌ CI fails
```

This demonstrates basic professional development workflow.

---

# Phase 20 — Deployment

Deploy something like:

```text
React
  ↓
Vercel

Django
  ↓
Render / Railway
  │
  ├── PostgreSQL
  ├── Redis
  └── Celery worker
```

Configure production:

```text
DEBUG=False
SECRET_KEY
DATABASE_URL
CORS_ALLOWED_ORIGINS
ALLOWED_HOSTS
```

Never commit production credentials.

---

# Phase 21 — Create demo data

A recruiter shouldn't need to upload files just to understand the application.

Create a seed command such as:

```powershell
python manage.py seed_demo
```

Generate:

```text
2 data sources
5 import batches
10,000 transactions
several reconciliation runs
matched transactions
amount mismatches
missing transactions
validation failures
demo users
```

Provide read-only demo credentials if appropriate.

---

# Phase 22 — Polish GitHub

Your README should have this structure:

```text
# Transaction Reconciliation Platform

Screenshot

Live Demo

## Problem

## Solution

## Architecture

## Features

## Tech Stack

## Data Pipeline

## Reconciliation Engine

## Database Design

## API

## Background Processing

## Security

## Testing

## Local Development

## Docker

## Deployment

## Design Decisions

## Future Improvements
```

Especially write the **Design Decisions** section yourself.

For example:

> Celery was introduced after implementing synchronous ingestion because large imports should not occupy HTTP workers.

and:

> PostgreSQL Decimal/Numeric types are used for monetary values rather than floating-point representations.

Those explanations show engineering understanding.

---

# Phase 23 — Prepare yourself to defend the project

This is as important as finishing it.

For every major technology, answer **why**.

You should be able to explain:

| Question | You should understand |
|---|---|
| Why Django? | batteries-included enterprise framework |
| Why DRF? | API abstraction |
| Why PostgreSQL? | relational integrity, SQL, transactions |
| Why Celery? | long-running asynchronous jobs |
| Why Redis? | message broker/cache |
| Why React? | interactive operations frontend |
| Why JWT? | API authentication tradeoffs |
| Why `Decimal`? | financial precision |
| Why indexes? | lookup/query performance |
| Why bulk inserts? | ingestion performance |
| Why transactions? | atomicity |
| Why ETL stages? | separation and testability |
| Why service classes? | domain logic outside HTTP |
| Why audit logs? | traceability |
| Why Docker? | reproducible environments |

Also understand the downsides. For example, JWT isn't automatically "better" than Django sessions.

---

# Recommended Git progression

Don't build the whole project and then make one commit.

Your history could look like:

```text
chore: initialize Django project

chore: configure PostgreSQL

feat: add transaction data models

feat: configure Django admin

feat: add transaction REST API

feat: implement JWT authentication

feat: add role-based permissions

feat: implement CSV transaction extraction

feat: add transaction validation pipeline

feat: implement transaction transformations

feat: implement bulk transaction loading

feat: add file import API

feat: implement reconciliation engine

test: add reconciliation tests

feat: add asynchronous import processing

feat: add audit logging

feat: add dashboard statistics API

feat: add React dashboard

feat: add transaction management interface

feat: add reconciliation interface

docs: add OpenAPI documentation

chore: dockerize application

ci: add GitHub Actions workflow

docs: add project documentation
```

This makes your GitHub activity look like an actual engineering project rather than an AI-generated code dump.

## Your immediate next milestone

Don't think about all 23 phases right now. Your **first milestone** should be:

```text
Django
   ↓
PostgreSQL
   ↓
Data models
   ↓
Django Admin
   ↓
DRF
   ↓
Basic API
```

So from your already-created project, do these next:

1. Install DRF, PostgreSQL driver, `django-filter`, SimpleJWT and environment configuration.
2. Create `accounts`, `imports`, `transactions`, `reconciliation`, and `audit`.
3. Connect PostgreSQL.
4. Design the database schema **before coding the models**.
5. Implement `DataSource`, `ImportBatch`, `Transaction`, `ImportValidationError`, `ReconciliationRun`, and `ReconciliationResult`.
6. Run migrations.
7. Register everything with Django Admin.
8. Insert some dummy data.
9. Build read-only DRF endpoints.
10. Verify them using Postman/Bruno.

Only after that should you touch the ETL pipeline.

The project should progress conceptually as **data model → API → business logic → asynchronous processing → UI → infrastructure**, rather than having an AI agent scaffold the entire stack at once. That ordering will force you to learn the parts of Django, SQL, ETL, APIs and architecture that this particular role is likely to test.