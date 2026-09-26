from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.permissions import IsAnalystOrAdmin
from .models import DataSource, ImportBatch, ImportValidationError
from .serializers import (
    DataSourceSerializer,
    ImportBatchSerializer,
    ImportValidationErrorSerializer,
    ImportUploadSerializer,
)
from .tasks import process_import_batch


class DataSourceViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = DataSource.objects.all()
    serializer_class = DataSourceSerializer
    filter_backends = (DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter)
    filterset_fields = ("is_active",)
    search_fields = ("code", "name")
    ordering_fields = ("name", "created_at")


class ImportBatchViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    queryset = ImportBatch.objects.select_related("data_source", "uploaded_by")
    serializer_class = ImportBatchSerializer
    filter_backends = (DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter)
    filterset_fields = ("data_source", "status")
    search_fields = ("original_filename",)
    ordering_fields = ("created_at", "original_filename", "status")

    def get_permissions(self):
        if self.action == "create":
            return [IsAnalystOrAdmin()]
        return [IsAuthenticated()]

    def get_serializer_class(self):
        if self.action == "create":
            return ImportUploadSerializer
        return ImportBatchSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        batch = serializer.save()
        process_import_batch.delay(batch.pk)
        return Response(ImportBatchSerializer(batch).data, status=status.HTTP_202_ACCEPTED)

    @action(detail=True, methods=("get",), url_path="errors")
    def errors(self, request, pk=None):
        batch = self.get_object()
        queryset = batch.validation_errors.all()
        page = self.paginate_queryset(queryset)
        serializer = ImportValidationErrorSerializer(page or queryset, many=True)
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)


class ImportValidationErrorViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ImportValidationError.objects.select_related("batch")
    serializer_class = ImportValidationErrorSerializer
    filter_backends = (DjangoFilterBackend, filters.OrderingFilter)
    filterset_fields = ("batch", "error_code", "field")
    ordering_fields = ("row_number", "created_at")
