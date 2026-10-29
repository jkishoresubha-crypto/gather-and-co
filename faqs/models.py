from django.db import models


class FAQ(models.Model):
    class Category(models.TextChoices):
        GENERAL = "general", "General"
        BOOKINGS = "bookings", "Bookings"
        ASSISTANT = "assistant", "AI Assistant"
        ERRORS = "errors", "Error Codes"
        SUPPORT = "support", "Support"

    question = models.CharField(max_length=255, unique=True)
    answer = models.TextField()
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.GENERAL)
    keywords = models.CharField(
        max_length=255, blank=True,
        help_text="Extra comma-separated search terms used by the assistant.",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["category", "id"]
        verbose_name = "FAQ"
        verbose_name_plural = "FAQs"

    def __str__(self):
        return self.question


class ErrorCode(models.Model):
    class Kind(models.TextChoices):
        HTTP = "http", "HTTP status code"
        APP = "app", "Application error code"

    code = models.PositiveIntegerField(unique=True)
    name = models.CharField(max_length=80)
    kind = models.CharField(max_length=4, choices=Kind.choices, default=Kind.HTTP)
    meaning = models.TextField()
    common_causes = models.TextField(help_text="One cause per line.")
    troubleshooting = models.TextField(help_text="One step per line.")
    next_action = models.TextField()

    class Meta:
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} {self.name}"

    @property
    def causes_list(self):
        return [line for line in self.common_causes.splitlines() if line.strip()]

    @property
    def steps_list(self):
        return [line for line in self.troubleshooting.splitlines() if line.strip()]
