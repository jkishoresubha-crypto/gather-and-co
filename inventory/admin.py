from django.contrib import admin

from .models import Booking, Category, Product


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "daily_rate", "quantity_total", "is_active")
    list_filter = ("category", "is_active")
    search_fields = ("name", "description")


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ("reference", "product", "customer", "quantity", "start_date", "end_date", "status")
    list_filter = ("status", "product__category")
    search_fields = ("reference", "customer__username", "product__name")
    readonly_fields = ("reference", "created_at", "updated_at")
