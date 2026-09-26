from django.db import models

from django.conf import settings
from django.db import models


class Profile(models.Model):
    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Admin"
        ANALYST = "ANALYST", "Analyst"
        VIEWER = "VIEWER", "Viewer"

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.VIEWER)

    def __str__(self):
        return f"{self.user} ({self.role})"
