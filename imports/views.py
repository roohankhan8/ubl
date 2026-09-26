from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, viewsets

from .models import DataSource, ImportBatch, ImportValidationError
from .serializers import (
    DataSourceSerializer,
    ImportBatchSerializer,
    ImportValidationErrorSerializer,
)


class DataSourceViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = DataSource.objects.all()
    serializer_class = DataSourceSerializer
    filter_backends = (DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter)
    filterset_fields = ("is_active",)
    search_fields = ("code", "name")
    ordering_fields = ("name", "created_at")


class ImportBatchViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ImportBatch.objects.select_related("data_source", "uploaded_by")
    serializer_class = ImportBatchSerializer
    filter_backends = (DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter)
    filterset_fields = ("data_source", "status")
    search_fields = ("original_filename",)
    ordering_fields = ("created_at", "original_filename", "status")


class ImportValidationErrorViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ImportValidationError.objects.select_related("batch")
    serializer_class = ImportValidationErrorSerializer
    filter_backends = (DjangoFilterBackend, filters.OrderingFilter)
    filterset_fields = ("batch", "error_code", "field")
    ordering_fields = ("row_number", "created_at")
