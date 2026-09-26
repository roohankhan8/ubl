from rest_framework import serializers

from .models import DataSource, ImportBatch, ImportValidationError


class DataSourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataSource
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")


class ImportBatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImportBatch
        fields = "__all__"
        read_only_fields = (
            "id", "status", "total_rows", "valid_rows", "invalid_rows",
            "started_at", "completed_at", "created_at", "updated_at",
        )


class ImportValidationErrorSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImportValidationError
        fields = "__all__"
        read_only_fields = (
            "id", "batch", "row_number", "field", "raw_value",
            "error_code", "message", "created_at",
        )
