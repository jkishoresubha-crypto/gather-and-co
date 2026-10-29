from django.urls import path

from . import views

app_name = "inventory"
urlpatterns = [
    # Customer-facing catalogue and bookings
    path("inventory/", views.catalog, name="catalog"),
    path("inventory/my-bookings/", views.my_bookings, name="my_bookings"),
    path("inventory/my-bookings/<str:reference>/cancel/", views.cancel_booking, name="cancel_booking"),
    path("inventory/<slug:slug>/", views.product_detail, name="detail"),
    path("inventory/<slug:slug>/image/", views.product_image, name="image"),
    # Owner area (staff / "Owners" group only)
    path("owner/", views.owner_dashboard, name="owner_dashboard"),
    path("owner/bookings/<str:reference>/status/", views.owner_update_booking, name="owner_update_booking"),
    path("owner/products/", views.owner_products, name="owner_products"),
    path("owner/products/new/", views.owner_product_form, name="owner_product_new"),
    path("owner/products/<slug:slug>/edit/", views.owner_product_form, name="owner_product_edit"),
]
