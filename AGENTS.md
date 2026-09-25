# Project instructions

This is an enterprise transaction-reconciliation portfolio project using Django, Django REST Framework, PostgreSQL, Celery/Redis, and a later React frontend. Use `docs/plan.md` for product context and `docs/steps.md` for implementation order.

## Working rules

- Work on one documented phase at a time; do not scaffold future phases.
- Inspect existing code before adding files, helpers, abstractions, or dependencies.
- Keep business logic out of DRF views. Views validate/orchestrate; services import and reconcile.
- App ownership: `accounts` auth/roles, `imports` sources/batches/validation, `transactions` normalized transactions, `reconciliation` runs/results, `audit` append-only events.
- Use Django's built-in user initially. Do not introduce a custom user model after migrations without an explicit migration plan.
- Use `Decimal`/`DecimalField` for money; never pass money through `float`.
- Enforce durable invariants with database constraints where practical.
- Validate uploads and untrusted values at the boundary; never expose tracebacks or secrets.
- Do not edit/delete applied migrations; add a new migration.
- Never commit `.env`, media, database files, generated large data, credentials, or customer data.
- Add dependencies and infrastructure only in the phase that needs them.

## Local checks

Run the smallest relevant check while working, then before handoff:

```powershell
python manage.py check
python manage.py test
python manage.py makemigrations --check --dry-run
```

When `frontend/` exists, also run `npm run build` there. Never claim a check passed unless it ran; report database, Redis, or environment blockers plainly.

## Change style

- Prefer the smallest root-cause change and fewest files.
- Reuse Django/DRF and Python standard-library features before dependencies.
- Add one focused regression test for non-trivial behavior or bug fixes.
- Preserve unrelated user changes in the working tree.
- Keep commits phase-sized; use the subjects in `docs/steps.md` when appropriate.

## API and data conventions

- API paths use `/api/` and trailing slashes.
- List endpoints are paginated; never serialize large querysets unbounded.
- Use `TextChoices` for stored states and enum members instead of repeated strings.
- Import/reconciliation transitions are `PENDING -> PROCESSING -> COMPLETED` or `FAILED`.
- Audit APIs are read-only. Imported financial history has no casual destructive endpoints.
- Optimize only after measuring and record before/after results.
