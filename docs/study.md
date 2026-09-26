# Django Codebase Study Plan

## Summary

Study the project backend first through hands-on lessons, following the real data flow:

`HTTP request → DRF view → serializer → service → model/database → response`

The goal is to understand both Django concepts and why this project separates authentication, imports, transactions, reconciliation, and audit logging.

Each lesson should follow this loop:

1. Read the selected files.
2. Predict what the code will do.
3. Run a command or test.
4. Make one small exercise.
5. Explain the design decision in your own words.

## Study sequence

### 1. Django project foundation

Read:

- `manage.py`
- `config/settings.py`
- `config/urls.py`
- `config/asgi.py`
- `config/wsgi.py`
- `requirements.txt`
- `.env.example`

Learn:

- Django project vs app
- Settings and `INSTALLED_APPS`
- URL routing
- Middleware
- Environment configuration
- WSGI/ASGI roles
- Why `manage.py` is the project entry point

Exercises:

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py showmigrations
.\.venv\Scripts\python.exe manage.py diffsettings
```

### 2. Domain model and database design

Read:

- `docs/models.md`
- `imports/models.py`
- `transactions/models.py`
- `reconciliation/models.py`
- `accounts/models.py`
- `audit/models.py`
- All `migrations/0001_initial.py` files

Learn:

- Django models and fields
- Foreign keys and reverse relationships
- `PROTECT`, `CASCADE`, and `SET_NULL`
- `TextChoices`
- `DecimalField`
- database indexes
- check constraints
- unique constraints
- migrations as versioned database changes

Trace this lifecycle:

```text
DataSource
  → ImportBatch
      → Transaction
          → ReconciliationResult
              → ReconciliationRun
```

Exercises:

- Use Django shell to query related objects.
- Create an invalid transaction and observe the database constraint.
- Explain why imported financial history is not casually deletable.
- Run:

```powershell
.\.venv\Scripts\python.exe manage.py sqlmigrate imports 0001
```

### 3. Django Admin

Read:

- `imports/admin.py`
- `transactions/admin.py`
- `reconciliation/admin.py`
- `accounts/admin.py`
- `audit/admin.py`

Learn:

- Model registration
- `list_display`
- `list_filter`
- `search_fields`
- read-only fields
- `select_related` in admin

Exercise:

- Add one useful admin filter or display field.
- Create the two data sources through admin.
- Compare admin behavior with direct ORM queries.

### 4. Django ORM and testing

Read:

- `transactions/tests.py`
- `imports/tests.py`
- `reconciliation/tests.py`
- `config/tests.py`

Learn:

- `TestCase`
- test database isolation
- `setUp`
- fixtures created through ORM
- testing constraints
- testing services and API endpoints
- why tests should not depend on manually seeded data

Exercises:

```powershell
.\.venv\Scripts\python.exe manage.py test
```

Then write small tests for:

- a completed import with zero invalid rows
- an empty dashboard
- a viewer denied from reconciliation
- a missing reconciliation target

### 5. Django REST Framework basics

Read:

- `imports/serializers.py`
- `transactions/serializers.py`
- `reconciliation/serializers.py`
- `config/api_urls.py`
- `imports/views.py`
- `transactions/views.py`
- `reconciliation/views.py`

Learn:

- serializers as API boundaries
- `ModelSerializer`
- `ReadOnlyModelViewSet`
- routers
- URL naming
- pagination
- filtering
- search
- ordering
- HTTP status codes
- why unsupported writes return `405`

Trace:

```text
GET /api/transactions/
  → router
  → TransactionViewSet
  → queryset
  → TransactionSerializer
  → paginated JSON
```

Exercises:

- Test an endpoint with the browsable API.
- Try filters such as:

```text
/api/transactions/?currency=PKR
/api/transactions/?search=TX1001
/api/transactions/?ordering=-amount
```

- Add one safe read-only filter.

### 6. Authentication and authorization

Read:

- `accounts/models.py`
- `accounts/permissions.py`
- `accounts/serializers.py`
- `accounts/views.py`
- `accounts/urls.py`
- JWT settings in `config/settings.py`

Learn:

- Django’s built-in user model
- one-to-one profile models
- role-based authorization
- authentication vs permission checks
- access and refresh tokens
- `401` vs `403`

Trace:

```text
POST /api/auth/login/
  → SimpleJWT
  → access/refresh tokens

GET /api/auth/me/
  → JWTAuthentication
  → IsAuthenticated
  → profile role
```

Exercises:

- Create admin, analyst, and viewer profiles.
- Verify the permission matrix manually.
- Expire or remove the access token and observe `401`.
- Explain why the project keeps the built-in user model.

### 7. CSV pipeline and services

Read:

- `imports/services/pipeline.py`
- `imports/tasks.py`
- `sample_data/*.csv`
- `imports/tests.py`

Learn:

- keeping business logic out of views
- CSV parsing with `csv.DictReader`
- `Decimal`
- normalization
- validation error collection
- duplicate detection
- `bulk_create`
- `transaction.atomic`
- state transitions
- service-level testing

Trace:

```text
CSV upload
  → ImportBatch
  → process_import(batch)
  → normalize rows
  → collect transactions/errors
  → atomic bulk insert
  → COMPLETED or FAILED
```

Exercises:

- Add one validation rule and its test.
- Explain why invalid rows do not abort valid rows.
- Explain why unexpected exceptions mark the batch `FAILED`.
- Upload `invalid_transactions.csv` and inspect stored errors.

### 8. File upload API and Celery

Read:

- `imports/views.py`
- `imports/serializers.py`
- `imports/tasks.py`
- `config/celery.py`
- Celery settings

Learn:

- multipart requests
- upload validation
- file size and extension checks
- asynchronous jobs
- thin Celery tasks
- `PENDING → PROCESSING → COMPLETED/FAILED`
- why the service remains reusable by both HTTP and workers

Trace:

```text
POST /api/imports/
  → validate multipart file
  → create PENDING batch
  → enqueue Celery task
  → return 202

Celery worker
  → fetch batch by ID
  → call process_import(batch)
```

Exercises:

- Run Redis and a Celery worker.
- Upload a sample file.
- Poll the batch endpoint.
- Stop the worker and explain what remains in the database.

### 9. Reconciliation engine

Read:

- `reconciliation/services/engine.py`
- `reconciliation/models.py`
- `reconciliation/views.py`
- `reconciliation/tests.py`

Learn:

- service-layer business rules
- dictionary-based matching
- union of source and target IDs
- status precedence
- difference calculation
- atomic result creation
- failure state transitions

Trace:

```text
POST /api/reconciliation-runs/
  → validate permissions
  → validate completed batches
  → reconcile(source, target, user)
  → compare by external_id
  → bulk-create results
  → audit events
```

Exercises:

- Add a test for currency mismatch.
- Predict the result for source-only and target-only records.
- Explain why the result count equals the union of IDs.
- Inspect the generated `reason` and `difference` fields.

### 10. Audit logging and dashboard aggregation

Read:

- `audit/models.py`
- `audit/services.py`
- `audit/views.py`
- `config/dashboard.py`

Learn:

- append-only audit design
- explicit business events
- read-only audit APIs
- aggregate queries
- filtered `Count`
- match-rate calculation
- server-side summaries

Exercises:

- Upload a file and locate its audit event.
- Run reconciliation and compare start/completion events.
- Query dashboard summary with no data.
- Explain why the dashboard should not download every transaction.

### 11. Frontend integration

Read:

- `frontend/src/App.tsx`
- `frontend/src/App.css`
- `frontend/src/index.css`
- `frontend/vite.config.ts`
- `frontend/package.json`

Learn:

- Vite and React entry points
- React state and effects
- client-side routing
- JWT storage
- API client wrappers
- multipart upload requests
- polling-style workflows
- frontend loading/error/empty states
- Vite proxy vs Django CORS

Trace these flows:

```text
Login
  → POST /api/auth/login/
  → store tokens
  → GET /api/auth/me/
  → dashboard

Upload
  → FormData
  → POST /api/imports/
  → 202 response
  → refresh import list

Reconciliation
  → select completed batches
  → POST /api/reconciliation-runs/
  → inspect result endpoint
```

Exercises:

- Add an import detail route.
- Add polling for `PENDING` and `PROCESSING` imports.
- Add a visible API error for expired sessions.
- Explain why `FormData` must not receive a manually-set JSON content type.

### 12. Production and portfolio readiness

Read:

- remaining sections of `docs/steps.md`
- `docs/plan.md`
- `frontend/README.md`
- `.gitignore`
- `.env.example`

Study:

- OpenAPI documentation
- performance measurement
- Docker
- CI
- deployment
- demo data
- README quality
- security checks
- environment-specific configuration

Exercises:

```powershell
.\.venv\Scripts\python.exe manage.py check --deploy
cd frontend
npm run build
```

Then document:

- architecture
- major trade-offs
- security boundaries
- scaling limitations
- measured performance
- local setup

## Weekly checkpoint structure

At the end of each unit, write a short note answering:

- What problem does this part solve?
- Which Django feature is being used?
- What enters the system?
- What leaves the system?
- Where is validation performed?
- Which database invariant protects it?
- Which test proves it works?
- What would fail if this code were removed?

## Final capstone exercise

Reproduce the full workflow without copying implementation details:

1. Create an analyst user.
2. Create the two data sources.
3. Start Django, Redis, Celery, and Vite.
4. Log in through the React frontend.
5. Upload `core_transactions.csv`.
6. Upload `gateway_transactions.csv`.
7. Wait for both imports to complete.
8. Start a reconciliation.
9. Inspect mismatches and missing records.
10. Open the dashboard.
11. Open the audit log.
12. Explain the request, database, worker, and frontend flow end to end.

## Success criteria

You should be able to explain:

- why the project uses multiple Django apps
- how a migration changes the database
- how a request reaches a viewset
- why serializers are API boundaries
- why money uses `Decimal`
- why services own import and reconciliation logic
- how permissions differ from authentication
- how Celery changes the HTTP response
- how a reconciliation result is selected
- how audit events are created
- how the frontend refreshes and displays backend state

## Assumptions

- Study emphasis: Django backend first.
- Method: hands-on lessons with commands and small exercises.
- The current repository is the source of truth; `docs/steps.md` is treated as historical implementation guidance where it differs from the current code.
- Use the existing dependency set and built-in Django/DRF features before adding new libraries.
- Do not begin a new feature during study unless it is the exercise for that lesson.
