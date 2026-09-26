from rest_framework import serializers

from .models import ReconciliationResult, ReconciliationRun


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
