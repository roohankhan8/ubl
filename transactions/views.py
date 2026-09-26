from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, viewsets

from .models import Transaction
from .serializers import TransactionSerializer


class TransactionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Transaction.objects.select_related("batch", "batch__data_source")
    serializer_class = TransactionSerializer
    filter_backends = (DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter)
    filterset_fields = ("batch", "status", "currency", "transaction_date")
    search_fields = ("external_id", "account_reference")
    ordering_fields = ("transaction_date", "amount", "created_at")
