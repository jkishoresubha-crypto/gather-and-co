from django.contrib import admin

from .models import FAQ, ErrorCode


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ("question", "category", "is_active", "updated_at")
    list_filter = ("category", "is_active")
    search_fields = ("question", "answer", "keywords")


@admin.register(ErrorCode)
class ErrorCodeAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "kind")
