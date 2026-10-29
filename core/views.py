from django.contrib import messages
from django.contrib.auth import login
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from inventory.models import Category, Product

from .forms import SignUpForm
from .weather import get_weather


def home(request):
    city = request.GET.get("city", "").strip()
    weather = get_weather(city or None)
    context = {
        "featured": Product.objects.filter(is_active=True).select_related("category")[:6],
        "categories": Category.objects.all(),
        "weather": weather,
        "weather_city": city,
    }
    return render(request, "core/home.html", context)


@require_http_methods(["GET", "POST"])
def signup(request):
    if request.user.is_authenticated:
        return redirect("inventory:catalog")
    form = SignUpForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, f"Welcome to Gather & Co., {user.first_name or user.username}! You can now reserve items.")
        return redirect("inventory:catalog")
    return render(request, "registration/signup.html", {"form": form})


def page_not_found(request, exception=None):
    return render(request, "404.html", {"chat_context": "error_404"}, status=404)


def server_error(request):
    # Rendered without a request context processor dependency on the DB user,
    # so it still works if the database is the reason for the failure.
    return render(request, "500.html", {"chat_context": "error_500"}, status=500)
