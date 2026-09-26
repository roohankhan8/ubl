from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.permissions import IsAnalystOrAdmin
from .models import ReconciliationResult, ReconciliationRun
from .serializers import (
    ReconciliationCreateSerializer,
    ReconciliationResultSerializer,
    ReconciliationRunSerializer,
)
from .services.engine import reconcile


class ReconciliationRunViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    queryset = ReconciliationRun.objects.select_related(
        "source_batch", "target_batch", "started_by"
    )
    serializer_class = ReconciliationRunSerializer
    filter_backends = (DjangoFilterBackend, filters.OrderingFilter)
    filterset_fields = ("status", "source_batch", "target_batch")
    ordering_fields = ("created_at", "status")

    def get_permissions(self):
        return [IsAnalystOrAdmin()] if self.action == "create" else [IsAuthenticated()]

    def get_serializer_class(self):
        return ReconciliationCreateSerializer if self.action == "create" else ReconciliationRunSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            run = reconcile(
                serializer.validated_data["source_batch"],
                serializer.validated_data["target_batch"],
                request.user,
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(ReconciliationRunSerializer(run).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=("get",), url_path="results")
    def results(self, request, pk=None):
        run = self.get_object()
        queryset = run.results.all()
        page = self.paginate_queryset(queryset)
        serializer = ReconciliationResultSerializer(page or queryset, many=True)
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)


class ReconciliationResultViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ReconciliationResult.objects.select_related(
        "run", "source_transaction", "target_transaction"
    )
    serializer_class = ReconciliationResultSerializer
    filter_backends = (DjangoFilterBackend, filters.OrderingFilter)
    filterset_fields = ("run", "status")
    ordering_fields = ("created_at", "difference")
