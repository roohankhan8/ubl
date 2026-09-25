Given that posting, I would build **one focused enterprise-style project**, not a generic e-commerce CRUD app.

The strongest portfolio project for this role would be:

## Enterprise Transaction Reconciliation & Data Pipeline System

Build an internal web application that imports transaction data from multiple sources, validates and transforms it, reconciles records, flags discrepancies, provides APIs, and gives operations staff a React dashboard.

This maps unusually well to the requirements in the posting.

| Job requirement | What your project demonstrates |
|---|---|
| Python | Django backend |
| OOP / fundamentals | Services, domain logic, abstractions |
| Web applications | Full internal operations system |
| Django/FastAPI/Flask | Django + DRF |
| SQL | PostgreSQL |
| Data modelling | Transactions, imports, reconciliation |
| ETL/ELT | CSV/Excel ingestion pipeline |
| Transformation | Normalization and cleaning |
| Validation | Schema + business-rule validation |
| REST APIs | Django REST Framework |
| Authentication | JWT + role-based permissions |
| Business logic | Reconciliation engine |
| React | React/Next.js dashboard |
| Git/GitHub | Clean repository/history |
| Deployment | Render/Railway + Vercel |
| Automation | Scheduled/background processing |

It also fits a bank much better than another store, blog, or task-management app.

### What the application does

Imagine an operations team receives transaction files from different systems.

**Source A — Core system**

```csv
transaction_id,account_no,amount,date,status
TX1001,ACC001,25000,2026-09-20,SUCCESS
TX1002,ACC002,12000,2026-09-20,SUCCESS
```

**Source B — Payment processor**

```csv
reference,account,transaction_amount,transaction_date
TX1001,ACC001,25000,2026-09-20
TX1002,ACC002,12500,2026-09-20
```

Your system imports both.

The ETL pipeline:

```text
Files
  ↓
Extract
  ↓
Validate
  ↓
Normalize
  ↓
Transform
  ↓
Store in PostgreSQL
  ↓
Reconciliation Engine
  ↓
Matched / Mismatched / Missing
  ↓
React Dashboard
```

For `TX1001`:

```text
System A: 25,000
System B: 25,000

MATCHED
```

For `TX1002`:

```text
System A: 12,000
System B: 12,500

AMOUNT_MISMATCH
Difference: 500
```

That gives you real backend business logic instead of:

```python
Product.objects.all()
```

which doesn't demonstrate much engineering depth.

## Recommended stack

I would use:

```text
Backend
Python
Django
Django REST Framework
Celery

Database
PostgreSQL

Data
Pandas
openpyxl

Queue / Cache
Redis

Frontend
React
TypeScript
Vite
TanStack Query

Authentication
JWT

Testing
pytest
pytest-django

DevOps
Docker
GitHub Actions

Deployment
Frontend → Vercel
Backend → Render/Railway
PostgreSQL → managed PostgreSQL
Redis → managed Redis
```

Don't introduce Kafka, Kubernetes, microservices, Elasticsearch, etc. They would mostly be résumé decoration at this project's scale.

### Core modules

Structure the Django side around domains:

```text
backend/

config/

apps/
    accounts/
    organizations/
    imports/
    transactions/
    reconciliation/
    audit/
    reports/

manage.py
```

The React application could contain:

```text
frontend/

src/
    api/
    components/
    features/
        auth/
        dashboard/
        imports/
        transactions/
        reconciliation/
        reports/
    hooks/
    pages/
    types/
```

### Database model

Start with something approximately like:

```text
User
 ├── id
 ├── email
 └── role

DataSource
 ├── id
 ├── name
 └── source_type

ImportBatch
 ├── id
 ├── data_source_id
 ├── filename
 ├── status
 ├── uploaded_by
 ├── total_rows
 ├── valid_rows
 ├── invalid_rows
 └── created_at

Transaction
 ├── id
 ├── batch_id
 ├── external_id
 ├── account_reference
 ├── amount
 ├── currency
 ├── transaction_date
 └── status

ReconciliationRun
 ├── id
 ├── source_batch_id
 ├── target_batch_id
 ├── status
 ├── started_at
 └── completed_at

ReconciliationResult
 ├── id
 ├── reconciliation_run_id
 ├── source_transaction_id
 ├── target_transaction_id
 ├── status
 ├── difference
 └── reason

ValidationError
 ├── id
 ├── batch_id
 ├── row_number
 ├── field
 └── message

AuditLog
 ├── id
 ├── user_id
 ├── action
 ├── entity_type
 ├── entity_id
 └── created_at
```

This is where you can demonstrate something the posting explicitly asks for: **relational modelling fundamentals**.

Don't blindly build these tables. Be able to explain why `ImportBatch` and `Transaction` are separate, why reconciliation results reference transactions, which relationships require indexes, where uniqueness constraints belong, and what should happen when referenced records are deleted.

### API design

Your DRF API might expose:

```text
POST   /api/auth/login
POST   /api/auth/refresh
GET    /api/auth/me

POST   /api/imports
GET    /api/imports
GET    /api/imports/{id}
GET    /api/imports/{id}/errors

GET    /api/transactions
GET    /api/transactions/{id}

POST   /api/reconciliations
GET    /api/reconciliations
GET    /api/reconciliations/{id}
GET    /api/reconciliations/{id}/results

GET    /api/dashboard/summary
GET    /api/reports/reconciliation
GET    /api/audit-logs
```

Implement pagination, filtering, sorting, permissions and proper HTTP error responses.

## Make the ETL pipeline the centerpiece

This is probably the most valuable part for this particular vacancy.

Don't make file upload simply:

```python
pd.read_csv(file)
```

Build an actual pipeline:

```text
Upload
 ↓
File validation
 ↓
Extract rows
 ↓
Schema validation
 ↓
Normalize fields
 ↓
Business validation
 ↓
Transform
 ↓
Bulk database load
 ↓
Reconciliation
 ↓
Statistics
```

For example:

```text
Input

" PKR 25,000 "
"25/09/2026"
" tx-001 "
```

becomes:

```text
amount = Decimal("25000.00")
date = 2026-09-25
transaction_id = "TX-001"
currency = "PKR"
```

Then validate things such as:

```text
amount > 0
transaction_id required
transaction_id unique within source
valid currency
valid date
account exists
duplicate detection
```

Invalid records shouldn't crash the entire import.

Instead:

```text
10,000 rows processed

9,921 valid
79 invalid
```

The user should be able to inspect or download those 79 failures.

That demonstrates actual data-engineering thinking.

## Add asynchronous processing

Uploading 100,000 transactions shouldn't cause an HTTP request to sit there processing for 40 seconds.

Instead:

```text
React
   │
   │ POST /imports
   ▼
Django
   │
   ├── save file
   ├── create ImportBatch
   └── enqueue job
             │
             ▼
           Redis
             │
             ▼
           Celery
             │
             ├── extract
             ├── validate
             ├── transform
             ├── load
             └── reconcile
```

API responds quickly:

```json
{
    "id": 123,
    "status": "processing"
}
```

Frontend can poll:

```http
GET /api/imports/123
```

until:

```json
{
    "id": 123,
    "status": "completed",
    "total_rows": 100000,
    "valid_rows": 99734,
    "invalid_rows": 266
}
```

Now you're demonstrating APIs, queues, background jobs, data pipelines and frontend/backend integration in one feature.

## Build an actual operations dashboard

Don't spend excessive time making it visually elaborate.

Have:

```text
┌─────────────────────────────────────────────────────┐
│ Reconciliation Dashboard                            │
├────────────┬────────────┬────────────┬───────────────┤
│ 124,521    │ 121,403    │ 2,841      │ 277           │
│ Processed  │ Matched    │ Mismatched │ Missing       │
└────────────┴────────────┴────────────┴───────────────┘

Recent Imports
──────────────────────────────────────────────────────
core_transactions_2509.csv   ✓ Completed    50,000
gateway_2509.csv              ✓ Completed    49,872
settlement_2509.csv           ⟳ Processing  32%

Reconciliation
──────────────────────────────────────────────────────
Reference   Source      Target      Difference   Status
TX10021     25,000      25,000      0            MATCH
TX10022     12,000      12,500      500          MISMATCH
TX10023     8,500       —           8,500        MISSING
```

Clicking a mismatch should show why it failed.

## Authentication and authorization

Implement roles such as:

```text
Admin
Analyst
Viewer
```

For example:

```text
Admin
→ manage users
→ upload data
→ run reconciliation
→ view everything

Analyst
→ upload
→ reconcile
→ investigate discrepancies

Viewer
→ read-only
```

This lets you demonstrate authentication **and authorization**, which are different concepts.

## Audit trail

For an enterprise application, this is an excellent feature.

Store:

```text
2026-09-25 14:31
Roohan
UPLOAD
transactions_25092026.csv

2026-09-25 14:33
Roohan
START_RECONCILIATION
Run #182

2026-09-25 14:40
Admin
RESOLVE_MISMATCH
TX10022
```

Do not allow audit records to be edited through ordinary application APIs.

### Testing

This is another place where you can distinguish the project from tutorial projects.

Write tests for:

```text
authentication
permissions
CSV validation
duplicate transactions
transformations
reconciliation matching
amount mismatches
missing transactions
API responses
database constraints
```

Especially test the reconciliation engine independently of HTTP.

For example:

```python
def test_detects_amount_mismatch():
    ...
```

and:

```python
def test_matching_transactions_are_reconciled():
    ...
```

## Deployment

You specifically need a deployed project because the posting asks candidates to provide deployed work.

A sensible deployment architecture is:

```text
                    Internet
                       │
             ┌─────────┴─────────┐
             │                   │
          Vercel              Render
          React                Django
                                 │
                         ┌───────┴───────┐
                         │               │
                     PostgreSQL        Redis
                                         │
                                       Celery
```

Dockerize the backend.

Also create:

```text
.env.example
Dockerfile
docker-compose.yml
README.md
```

Never commit actual secrets.

## Your README matters

The repository landing page should immediately explain:

```text
Transaction Reconciliation Platform

Enterprise-style transaction reconciliation and data processing
platform built using Django, Django REST Framework, PostgreSQL,
Celery, Redis and React.

Features

• CSV/XLSX transaction ingestion
• ETL data processing pipeline
• Schema and business-rule validation
• Asynchronous processing
• Transaction reconciliation
• Discrepancy investigation
• REST API
• JWT authentication
• Role-based authorization
• Audit logging
• Dashboard and reporting
• Dockerized development environment
• Automated tests
```

Then include an architecture diagram, screenshots, database schema, API documentation, installation instructions, demo credentials and deployment link.

## One important problem: the deadline

The deadline in the posting is **September 25 before 6 PM**, so don't attempt to build this entire system before applying.

Apply first.

Since they ask for **2–3 projects you have actually built and deployed**, send your existing relevant work rather than presenting a rushed new project as completed. Then build this project properly and add it to your GitHub/CV afterward.

You already have backend experience that can be framed around APIs, payments, Laravel systems, databases and application business logic. The Django project should broaden your Python portfolio rather than replace your existing experience. 

### Build order

I would implement it in this order:

1. **Django + PostgreSQL foundation** — project, apps, environment variables and Docker.
2. **Data model** — `DataSource`, `ImportBatch`, `Transaction`, reconciliation models.
3. **DRF** — serializers, ViewSets, URLs, pagination and filtering.
4. **Authentication** — JWT and roles.
5. **ETL** — CSV/XLSX → validation → normalization → PostgreSQL.
6. **Reconciliation engine** — matched, mismatched and missing.
7. **Celery + Redis** — move ETL/reconciliation to workers.
8. **React frontend** — login, dashboard, upload and discrepancy screens.
9. **Testing** — particularly domain and ETL logic.
10. **Docker + CI/CD + deployment.**

The critical constraint is: **don't let an AI coding agent build the entire thing while you merely supervise it.** For this project to help in an interview, you need to be able to explain why every major architectural decision exists. Given the posting's emphasis on fundamentals, I'd deliberately implement the first Django/DRF models, serializers, services and tests yourself before using agents heavily.

A strong interview explanation then becomes: *“I built an internal transaction-reconciliation platform. Django/DRF handles the API and domain logic, PostgreSQL stores normalized transaction data, Celery/Redis handles long-running ETL jobs, and React provides the operations interface.”* That's considerably more aligned with this vacancy than saying you built another CRUD application.

Because the application deadline is today at 6 PM, I can also help you prepare the **application email and decide which 2–3 of your existing projects to submit** before you start building this.