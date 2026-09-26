from django.db import models

from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    class Action(models.TextChoices):
        LOGIN = "LOGIN", "Login"
        UPLOAD_DATASET = "UPLOAD_DATASET", "Upload dataset"
        START_RECONCILIATION = "START_RECONCILIATION", "Start reconciliation"
        COMPLETE_RECONCILIATION = "COMPLETE_RECONCILIATION", "Complete reconciliation"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    action = models.CharField(max_length=40, choices=Action.choices)
    entity_type = models.CharField(max_length=100)
    entity_id = models.CharField(max_length=100)
    metadata = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.action} {self.entity_type}:{self.entity_id}"
