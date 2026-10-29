from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

from core import views as core_views
from core.forms import LoginForm
from monitoring.views import health

admin.site.site_header = "Gather & Co. administration"
admin.site.site_title = "Gather & Co. admin"

urlpatterns = [
    path("", include("core.urls")),
    path("", include("inventory.urls")),
    path("faq/", include("faqs.urls")),
    path("support/", include("support.urls")),
    path("assistant/", include("assistant.urls")),
    path("health/", health, name="health"),
    path("accounts/signup/", core_views.signup, name="signup"),
    path("accounts/login/", auth_views.LoginView.as_view(redirect_authenticated_user=True, authentication_form=LoginForm), name="login"),
    path("accounts/logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("admin/", admin.site.urls),
]

handler404 = "core.views.page_not_found"
handler500 = "core.views.server_error"
