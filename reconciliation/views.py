from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, viewsets

from .models import ReconciliationResult, ReconciliationRun
from .serializers import ReconciliationResultSerializer, ReconciliationRunSerializer


class ReconciliationRunViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ReconciliationRun.objects.select_related(
        "source_batch", "target_batch", "started_by"
    )
    serializer_class = ReconciliationRunSerializer
    filter_backends = (DjangoFilterBackend, filters.OrderingFilter)
    filterset_fields = ("status", "source_batch", "target_batch")
    ordering_fields = ("created_at", "status")


class ReconciliationResultViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ReconciliationResult.objects.select_related(
        "run", "source_transaction", "target_transaction"
    )
    serializer_class = ReconciliationResultSerializer
    filter_backends = (DjangoFilterBackend, filters.OrderingFilter)
    filterset_fields = ("run", "status")
    ordering_fields = ("created_at", "difference")
