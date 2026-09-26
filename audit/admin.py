from django.contrib import admin

from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("action", "entity_type", "entity_id", "user", "created_at")
    list_filter = ("action", "entity_type")
    search_fields = ("entity_id", "user__username")
    readonly_fields = tuple(field.name for field in AuditLog._meta.fields)
