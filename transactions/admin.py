from django.contrib import admin

from .models import Transaction


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = (
        "external_id", "account_reference", "amount", "currency",
        "transaction_date", "status", "batch",
    )
    list_filter = ("currency", "status", "transaction_date")
    search_fields = ("external_id", "account_reference")
    readonly_fields = ("created_at",)
    list_select_related = ("batch",)
