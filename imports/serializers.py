import os

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


class ImportUploadSerializer(serializers.Serializer):
    file = serializers.FileField()
    data_source = serializers.PrimaryKeyRelatedField(
        queryset=DataSource.objects.filter(is_active=True)
    )

    def validate_file(self, value):
        if not value.name.lower().endswith(".csv"):
            raise serializers.ValidationError("Only .csv files are accepted.")
        if not value.size:
            raise serializers.ValidationError("The uploaded file is empty.")
        if value.size > 10 * 1024 * 1024:
            raise serializers.ValidationError("The uploaded file exceeds the 10 MB limit.")
        return value

    def create(self, validated_data):
        upload = validated_data["file"]
        return ImportBatch.objects.create(
            file=upload,
            original_filename=os.path.basename(upload.name),
            data_source=validated_data["data_source"],
            uploaded_by=self.context["request"].user,
        )
