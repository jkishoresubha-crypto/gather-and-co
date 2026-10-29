import secrets

from django.db import models


def generate_ticket_reference():
    return "GC-" + secrets.token_hex(4).upper()


class SupportTicket(models.Model):
    class Category(models.TextChoices):
        BOOKING = "booking", "Booking or reservation"
        PRODUCT = "product", "Product question"
        ACCOUNT = "account", "Account or login"
        TECHNICAL = "technical", "Website or error code"
        ASSISTANT = "assistant", "Unanswered assistant question"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        IN_PROGRESS = "in_progress", "In progress"
        RESOLVED = "resolved", "Resolved"
        CLOSED = "closed", "Closed"

    class Priority(models.TextChoices):
        LOW = "low", "Low"
        NORMAL = "normal", "Normal"
        HIGH = "high", "High"

    reference = models.CharField(max_length=12, unique=True, default=generate_ticket_reference, editable=False)
    name = models.CharField(max_length=100, blank=True)
    email = models.EmailField(blank=True)
    subject = models.CharField(max_length=150)
    description = models.TextField(max_length=3000)
    category = models.CharField(max_length=12, choices=Category.choices, default=Category.OTHER)
    # Status and priority are only changed by staff in Django Admin; public
    # forms never expose these fields.
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.OPEN)
    priority = models.CharField(max_length=8, choices=Priority.choices, default=Priority.NORMAL)
    conversation_id = models.CharField(max_length=64, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.reference} – {self.subject}"
