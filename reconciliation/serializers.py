from rest_framework import serializers

from .models import ReconciliationResult, ReconciliationRun
from imports.models import ImportBatch


class ReconciliationRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReconciliationRun
        fields = "__all__"
        read_only_fields = (
            "id", "source_batch", "target_batch", "status", "started_by",
            "started_at", "completed_at", "created_at",
        )


class ReconciliationResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReconciliationResult
        fields = "__all__"
        read_only_fields = (
            "id", "run", "source_transaction", "target_transaction", "status",
            "difference", "reason", "created_at",
        )


class ReconciliationCreateSerializer(serializers.Serializer):
    source_batch = serializers.PrimaryKeyRelatedField(queryset=ImportBatch.objects.all())
    target_batch = serializers.PrimaryKeyRelatedField(queryset=ImportBatch.objects.all())
