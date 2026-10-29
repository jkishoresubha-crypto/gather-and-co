from datetime import date

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Count, Q, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from core.context_processors import user_is_owner
from core.ratelimit import is_rate_limited

from .forms import BookingForm, BookingStatusForm, ProductForm
from .models import Booking, Category, Product


def owner_required(view):
    def check(user):
        if not user.is_authenticated:
            return False
        if not user_is_owner(user):
            raise PermissionDenied
        return True
    return user_passes_test(check)(view)


def parse_date(value):
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def catalog(request):
    products = Product.objects.filter(is_active=True).select_related("category")
    query = request.GET.get("q", "").strip()[:80]
    category = request.GET.get("category", "").strip()
    if query:
        products = products.filter(Q(name__icontains=query) | Q(description__icontains=query))
    if category:
        products = products.filter(category__slug=category)

    start = parse_date(request.GET.get("start"))
    end = parse_date(request.GET.get("end"))
    check_dates = bool(start and end and start <= end)
    items = []
    for product in products:
        available = product.available_quantity(start, end) if check_dates else None
        items.append({"product": product, "available": available})

    return render(request, "inventory/catalog.html", {
        "items": items, "categories": Category.objects.all(), "query": query,
        "selected_category": category, "start": start, "end": end, "check_dates": check_dates,
    })


def product_detail(request, slug):
    product = get_object_or_404(Product.objects.select_related("category"), slug=slug, is_active=True)
    form = BookingForm(product=product)
    if request.method == "POST":
        if not request.user.is_authenticated:
            messages.info(request, "Please sign in to reserve items.")
            return redirect_to_login(product.get_absolute_url())
        if is_rate_limited(request, "booking", settings.BOOKING_RATE_LIMIT, window=600):
            messages.error(request, "Too many booking attempts (429). Please wait a few minutes and try again.")
            return render(request, "inventory/detail.html", {"product": product, "form": form}, status=429)
        form = BookingForm(request.POST, product=product)
        if form.is_valid():
            booking = create_booking(form, product, request.user)
            if booking:
                messages.success(
                    request,
                    f"Reservation received! Your booking reference is {booking.reference}. "
                    "The owner will review it shortly.",
                )
                return redirect("inventory:my_bookings")
    upcoming = (
        product.bookings.filter(status__in=Booking.ACTIVE_STATUSES, end_date__gte=timezone.localdate())
        .order_by("start_date").values("start_date", "end_date").annotate(units=Sum("quantity"))[:8]
    )
    return render(request, "inventory/detail.html", {"product": product, "form": form, "upcoming": upcoming})


def create_booking(form, product, user):
    """Create the booking inside a transaction that locks the product row so two
    customers cannot both take the last units."""
    with transaction.atomic():
        locked = Product.objects.select_for_update().get(pk=product.pk)
        start, end, qty = (form.cleaned_data[k] for k in ("start_date", "end_date", "quantity"))
        available = locked.available_quantity(start, end)
        if qty > available:
            form.add_error(
                "quantity",
                f"Only {available} unit(s) available for those dates." if available else
                "This item is fully booked for those dates. Try different dates.",
            )
            return None
        booking = form.save(commit=False)
        booking.product = locked
        booking.customer = user
        booking.save()
        return booking


def product_image(request, slug):
    product = get_object_or_404(Product, slug=slug)
    if not product.image_data:
        return redirect(product.image_url)
    response = HttpResponse(bytes(product.image_data), content_type=product.image_content_type or "image/jpeg")
    response["Cache-Control"] = "public, max-age=86400"
    response["Content-Security-Policy"] = "default-src 'none'"
    return response


@login_required
def my_bookings(request):
    bookings = request.user.bookings.select_related("product").all()
    return render(request, "inventory/my_bookings.html", {"bookings": bookings})


@login_required
@require_POST
def cancel_booking(request, reference):
    booking = get_object_or_404(Booking, reference=reference, customer=request.user)
    if booking.can_cancel:
        booking.status = Booking.Status.CANCELLED
        booking.save(update_fields=["status", "updated_at"])
        messages.success(request, f"Booking {booking.reference} was cancelled.")
    else:
        messages.error(request, "This booking can no longer be cancelled.")
    return redirect("inventory:my_bookings")


# --- Owner area ---------------------------------------------------------------

@owner_required
def owner_dashboard(request):
    status = request.GET.get("status", "")
    bookings = Booking.objects.select_related("product", "customer")
    if status in Booking.Status.values:
        bookings = bookings.filter(status=status)
    counts = dict(Booking.objects.values_list("status").annotate(n=Count("id")))
    today = timezone.localdate()
    stats = {
        "pending": counts.get(Booking.Status.PENDING, 0),
        "confirmed": counts.get(Booking.Status.CONFIRMED, 0),
        "products": Product.objects.filter(is_active=True).count(),
        "upcoming": Booking.objects.filter(status=Booking.Status.CONFIRMED, start_date__gte=today).count(),
    }
    return render(request, "inventory/owner_dashboard.html", {
        "bookings": bookings[:200], "stats": stats, "status": status,
        "status_choices": Booking.Status.choices,
    })


@owner_required
@require_POST
def owner_update_booking(request, reference):
    booking = get_object_or_404(Booking, reference=reference)
    form = BookingStatusForm(request.POST, booking=booking)
    if form.is_valid():
        booking.status = form.cleaned_data["status"]
        booking.owner_note = form.cleaned_data["owner_note"]
        booking.save(update_fields=["status", "owner_note", "updated_at"])
        messages.success(request, f"Booking {booking.reference} marked as {booking.get_status_display().lower()}.")
    else:
        messages.error(request, "; ".join(e for errs in form.errors.values() for e in errs))
    return redirect(request.POST.get("next") if request.POST.get("next", "").startswith("/owner/") else "inventory:owner_dashboard")


@owner_required
def owner_products(request):
    products = Product.objects.select_related("category").annotate(
        active_bookings=Count("bookings", filter=Q(bookings__status__in=Booking.ACTIVE_STATUSES))
    )
    return render(request, "inventory/owner_products.html", {"products": products})


@owner_required
def owner_product_form(request, slug=None):
    product = get_object_or_404(Product, slug=slug) if slug else None
    form = ProductForm(request.POST or None, request.FILES or None, instance=product)
    if request.method == "POST" and form.is_valid():
        saved = form.save()
        messages.success(request, f"“{saved.name}” was {'updated' if product else 'posted to the catalogue'}.")
        return redirect("inventory:owner_products")
    return render(request, "inventory/owner_product_form.html", {"form": form, "product": product})
