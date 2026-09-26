from django.contrib import admin

from .models import DataSource, ImportBatch, ImportValidationError


@admin.register(DataSource)
class DataSourceAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("code", "name")


@admin.register(ImportBatch)
class ImportBatchAdmin(admin.ModelAdmin):
    list_display = (
        "id", "original_filename", "data_source", "status",
        "valid_rows", "invalid_rows", "created_at",
    )
    list_filter = ("status", "data_source")
    search_fields = ("original_filename",)
    readonly_fields = ("created_at", "updated_at")
    list_select_related = ("data_source", "uploaded_by")


@admin.register(ImportValidationError)
class ImportValidationErrorAdmin(admin.ModelAdmin):
    list_display = ("batch", "row_number", "field", "error_code")
    list_filter = ("error_code",)
    search_fields = ("message", "raw_value")
    readonly_fields = ("created_at",)
