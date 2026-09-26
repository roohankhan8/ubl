from django.contrib import admin

from .models import ReconciliationResult, ReconciliationRun


@admin.register(ReconciliationRun)
class ReconciliationRunAdmin(admin.ModelAdmin):
    list_display = (
        "id", "source_batch", "target_batch", "status",
        "started_by", "created_at", "completed_at",
    )
    list_filter = ("status",)
    search_fields = ("source_batch__original_filename", "target_batch__original_filename")
    readonly_fields = ("created_at",)
    list_select_related = ("source_batch", "target_batch", "started_by")


@admin.register(ReconciliationResult)
class ReconciliationResultAdmin(admin.ModelAdmin):
    list_display = ("run", "status", "source_transaction", "target_transaction", "difference")
    list_filter = ("status",)
    search_fields = (
        "source_transaction__external_id",
        "target_transaction__external_id",
        "reason",
    )
    readonly_fields = ("created_at",)
    list_select_related = ("run", "source_transaction", "target_transaction")
