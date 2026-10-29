from django.contrib import admin

from .models import SupportTicket


@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = ("reference", "subject", "category", "status", "priority", "created_at")
    list_filter = ("status", "priority", "category")
    search_fields = ("reference", "subject", "description", "email", "name")
    list_editable = ("status", "priority")
    readonly_fields = ("reference", "conversation_id", "created_at", "updated_at")
