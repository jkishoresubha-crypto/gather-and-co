from io import BytesIO

from django import forms
from django.conf import settings
from django.utils import timezone
from PIL import Image, UnidentifiedImageError

from core.forms import BootstrapFormMixin

from .models import Booking, Product

ALLOWED_IMAGE_FORMATS = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}
MAX_BOOKING_DAYS = 30
MAX_ADVANCE_DAYS = 365


class BookingForm(BootstrapFormMixin, forms.ModelForm):
    """Customers may only set these fields; status/reference are server-controlled."""

    class Meta:
        model = Booking
        fields = ["start_date", "end_date", "quantity", "contact_phone", "event_note"]
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
            "event_note": forms.Textarea(attrs={"rows": 2, "maxlength": 300}),
        }
        labels = {"event_note": "Event details (optional)", "contact_phone": "Contact phone (optional)"}

    def __init__(self, *args, product=None, **kwargs):
        self.product = product
        super().__init__(*args, **kwargs)
        self.fields["quantity"].widget.attrs.update({"min": 1, "max": product.quantity_total if product else 999})
        today = timezone.localdate().isoformat()
        self.fields["start_date"].widget.attrs["min"] = today
        self.fields["end_date"].widget.attrs["min"] = today

    def clean_contact_phone(self):
        phone = self.cleaned_data.get("contact_phone", "").strip()
        if phone and not all(c.isdigit() or c in "+-() " for c in phone):
            raise forms.ValidationError("Use digits, spaces and + - ( ) only.")
        return phone

    def clean(self):
        cleaned = super().clean()
        start, end, qty = cleaned.get("start_date"), cleaned.get("end_date"), cleaned.get("quantity")
        if not (start and end and qty):
            return cleaned
        today = timezone.localdate()
        if start < today:
            raise forms.ValidationError("The start date cannot be in the past.")
        if end < start:
            raise forms.ValidationError("The end date must be on or after the start date.")
        if (end - start).days + 1 > MAX_BOOKING_DAYS:
            raise forms.ValidationError(f"Bookings can be at most {MAX_BOOKING_DAYS} days long.")
        if (start - today).days > MAX_ADVANCE_DAYS:
            raise forms.ValidationError("Bookings can be made up to one year in advance.")
        if qty < 1:
            raise forms.ValidationError("Quantity must be at least 1.")
        return cleaned


class ProductForm(BootstrapFormMixin, forms.ModelForm):
    image = forms.ImageField(
        required=False, label="Product photo",
        help_text="JPEG, PNG or WebP, up to 2 MB. Leave empty to keep the current image.",
    )

    class Meta:
        model = Product
        fields = ["name", "category", "description", "daily_rate", "quantity_total", "image_alt", "is_active"]
        labels = {
            "daily_rate": "Daily rate ($)", "quantity_total": "Quantity in stock",
            "image_alt": "Image description (for screen readers)", "is_active": "Visible in catalogue",
        }
        widgets = {"description": forms.Textarea(attrs={"rows": 4})}

    def clean_daily_rate(self):
        rate = self.cleaned_data["daily_rate"]
        if rate <= 0:
            raise forms.ValidationError("The daily rate must be greater than zero.")
        return rate

    def clean_quantity_total(self):
        qty = self.cleaned_data["quantity_total"]
        if qty < 1 or qty > 10000:
            raise forms.ValidationError("Quantity must be between 1 and 10,000.")
        return qty

    def clean_image(self):
        upload = self.cleaned_data.get("image")
        if not upload:
            return None
        if upload.size > settings.MAX_PRODUCT_IMAGE_BYTES:
            raise forms.ValidationError("The image must be 2 MB or smaller.")
        data = upload.read()
        try:
            with Image.open(BytesIO(data)) as img:
                img.verify()
                fmt = img.format
        except (UnidentifiedImageError, OSError, SyntaxError):
            raise forms.ValidationError("Upload a valid JPEG, PNG or WebP image.")
        if fmt not in ALLOWED_IMAGE_FORMATS:
            raise forms.ValidationError("Only JPEG, PNG or WebP images are accepted.")
        return {"data": data, "content_type": ALLOWED_IMAGE_FORMATS[fmt]}

    def save(self, commit=True):
        product = super().save(commit=False)
        image = self.cleaned_data.get("image")
        if image:
            product.image_data = image["data"]
            product.image_content_type = image["content_type"]
        if not product.image_alt:
            product.image_alt = product.name
        if commit:
            product.save()
        return product


class BookingStatusForm(forms.Form):
    """Owner decision on a booking. Only whitelisted transitions are allowed."""

    ALLOWED = {
        Booking.Status.PENDING: [Booking.Status.CONFIRMED, Booking.Status.DECLINED],
        Booking.Status.CONFIRMED: [Booking.Status.COMPLETED, Booking.Status.DECLINED],
    }
    status = forms.ChoiceField(choices=Booking.Status.choices)
    owner_note = forms.CharField(max_length=300, required=False)

    def __init__(self, *args, booking=None, **kwargs):
        self.booking = booking
        super().__init__(*args, **kwargs)

    def clean_status(self):
        new = self.cleaned_data["status"]
        if new not in self.ALLOWED.get(self.booking.status, []):
            raise forms.ValidationError("That status change is not allowed for this booking.")
        return new
