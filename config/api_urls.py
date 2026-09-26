from rest_framework.routers import DefaultRouter

from imports.views import (
    DataSourceViewSet,
    ImportBatchViewSet,
    ImportValidationErrorViewSet,
)
from reconciliation.views import ReconciliationResultViewSet, ReconciliationRunViewSet
from transactions.views import TransactionViewSet

router = DefaultRouter()
router.register("data-sources", DataSourceViewSet, basename="data-source")
router.register("imports", ImportBatchViewSet, basename="import-batch")
router.register("import-errors", ImportValidationErrorViewSet, basename="import-error")
router.register("transactions", TransactionViewSet, basename="transaction")
router.register(
    "reconciliation-runs", ReconciliationRunViewSet, basename="reconciliation-run"
)
router.register(
    "reconciliation-results",
    ReconciliationResultViewSet,
    basename="reconciliation-result",
)

urlpatterns = router.urls
