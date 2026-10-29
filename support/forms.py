from django import forms

from core.forms import BootstrapFormMixin

from .models import SupportTicket


class SupportTicketForm(BootstrapFormMixin, forms.ModelForm):
    """Only user-facing fields. Status and priority are never accepted from the
    public form, which prevents mass assignment of those fields."""

    class Meta:
        model = SupportTicket
        fields = ["name", "email", "category", "subject", "description"]
        labels = {"name": "Your name (optional)", "email": "Email for replies (optional)"}
        widgets = {
            "subject": forms.TextInput(attrs={"maxlength": 150}),
            "description": forms.Textarea(attrs={"rows": 5, "maxlength": 3000}),
        }

    def clean_subject(self):
        subject = self.cleaned_data["subject"].strip()
        if len(subject) < 4:
            raise forms.ValidationError("Please write a subject of at least 4 characters.")
        return subject

    def clean_description(self):
        description = self.cleaned_data["description"].strip()
        if len(description) < 10:
            raise forms.ValidationError("Please describe the problem in at least 10 characters.")
        return description
