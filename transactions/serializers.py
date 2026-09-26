from rest_framework import serializers

from .models import Transaction


class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = "__all__"
        read_only_fields = (
            "id", "batch", "external_id", "account_reference", "amount",
            "currency", "transaction_date", "status", "created_at",
        )
