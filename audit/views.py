from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, viewsets

from accounts.permissions import IsAnalystOrAdmin

from .models import AuditLog
from .serializers import AuditLogSerializer


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AuditLog.objects.select_related("user")
    serializer_class = AuditLogSerializer
    permission_classes = (IsAnalystOrAdmin,)
    filter_backends = (DjangoFilterBackend, filters.OrderingFilter)
    filterset_fields = ("user", "action", "entity_type")
    ordering_fields = ("created_at", "action")
