import secrets
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import Sum
from django.templatetags.static import static
from django.urls import reverse
from django.utils.text import slugify


class Category(models.Model):
    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(max_length=90, unique=True)
    description = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name


class Product(models.Model):
    """An inventory item that customers can reserve for a date range."""

    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="products")
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True)
    description = models.TextField()
    daily_rate = models.DecimalField(max_digits=8, decimal_places=2)
    quantity_total = models.PositiveIntegerField(default=1)
    # Seeded demo products ship with an illustration in /static/img/products/.
    static_image = models.CharField(max_length=200, blank=True)
    # Owner-uploaded photos are kept in PostgreSQL so they survive redeploys
    # on hosts with an ephemeral filesystem.
    image_data = models.BinaryField(blank=True, null=True, editable=False)
    image_content_type = models.CharField(max_length=40, blank=True, editable=False)
    image_alt = models.CharField(max_length=160, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["category__name", "name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name)[:120] or "item"
            slug = base
            while Product.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{secrets.token_hex(2)}"
            self.slug = slug
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("inventory:detail", args=[self.slug])

    @property
    def image_url(self):
        if self.image_data:
            stamp = int(self.updated_at.timestamp()) if self.updated_at else 0
            return reverse("inventory:image", args=[self.slug]) + f"?v={stamp}"
        if self.static_image:
            return static(self.static_image)
        return static("img/products/placeholder.svg")

    def reserved_quantity(self, start, end, exclude_booking=None):
        """Units already held by pending/confirmed bookings that overlap the range."""
        qs = self.bookings.filter(
            status__in=Booking.ACTIVE_STATUSES,
            start_date__lte=end,
            end_date__gte=start,
        )
        if exclude_booking is not None:
            qs = qs.exclude(pk=exclude_booking.pk)
        return qs.aggregate(total=Sum("quantity"))["total"] or 0

    def available_quantity(self, start, end, exclude_booking=None):
        return max(self.quantity_total - self.reserved_quantity(start, end, exclude_booking), 0)


def generate_booking_reference():
    return "BK-" + secrets.token_hex(3).upper()


class Booking(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending review"
        CONFIRMED = "confirmed", "Confirmed"
        DECLINED = "declined", "Declined"
        CANCELLED = "cancelled", "Cancelled by customer"
        COMPLETED = "completed", "Completed"

    ACTIVE_STATUSES = [Status.PENDING, Status.CONFIRMED]

    reference = models.CharField(max_length=12, unique=True, default=generate_booking_reference, editable=False)
    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="bookings")
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="bookings")
    quantity = models.PositiveIntegerField(default=1)
    start_date = models.DateField()
    end_date = models.DateField()
    event_note = models.CharField(max_length=300, blank=True)
    contact_phone = models.CharField(max_length=30, blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    owner_note = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["product", "start_date", "end_date"])]

    def __str__(self):
        return f"{self.reference} – {self.product} x{self.quantity}"

    @property
    def days(self):
        return (self.end_date - self.start_date).days + 1

    @property
    def total_price(self):
        return (self.product.daily_rate * self.quantity * self.days).quantize(Decimal("0.01"))

    @property
    def can_cancel(self):
        return self.status in self.ACTIVE_STATUSES
