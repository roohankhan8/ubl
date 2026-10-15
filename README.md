# Ledgerline

Transaction reconciliation portal: import bank/ledger files, normalize transactions, run reconciliations, and keep an append-only audit trail.

Stack: Django 5.2, Django REST Framework, SimpleJWT, PostgreSQL, Celery/Redis, React + Vite frontend.

See `docs/plan.md` for product context and `docs/steps.md` for the implementation order.

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env   # edit DB_* values to match your PostgreSQL
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

The backend runs at http://127.0.0.1:8000. Celery is optional locally: set `CELERY_TASK_ALWAYS_EAGER=True` in `.env` to run imports inline, or start a worker with Redis running:

```powershell
celery -A config worker -l info
```

Frontend:

```powershell
cd frontend
npm install
npm run dev
```

The app runs at http://localhost:5173 and proxies `/api` to the Django server.

## Logging in

There is no sign-up page. Create a user first, then sign in with that username and password.

1. Create an account: `python manage.py createsuperuser` (or add a user in Django admin at http://127.0.0.1:8000/admin/).
2. Open http://localhost:5173 and enter the username and password.
3. The frontend calls `POST /api/auth/login/`, stores the JWT access/refresh tokens in session storage, and loads `/api/auth/me/`.

Roles come from the `accounts.Profile` model (`ADMIN`, `ANALYST`, `VIEWER`). A superuser passes admin checks via `is_staff` even without a profile. For other users, create a Profile in Django admin (Accounts > Profiles) and pick the role.

API login without the frontend:

```bash
curl -X POST http://127.0.0.1:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "yourpassword"}'
# -> {"access": "...", "refresh": "..."}
curl http://127.0.0.1:8000/api/auth/me/ -H "Authorization: Bearer <access>"
```

## Main endpoints

All under `/api/`, JWT required, paginated lists:

- `data-sources/`, `imports/`, `import-errors/`
- `transactions/`
- `reconciliation-runs/`, `reconciliation-results/`
- `audit-logs/` (read-only)
- `dashboard/summary/`

## Checks

```powershell
python manage.py check
python manage.py test
python manage.py makemigrations --check --dry-run
cd frontend; npm run build
```
