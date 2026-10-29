from django.urls import path

from . import views

app_name = "faqs"
urlpatterns = [
    path("", views.faq_list, name="list"),
    path("error-codes/", views.error_codes, name="error_codes"),
]
