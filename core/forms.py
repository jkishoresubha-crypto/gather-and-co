from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User


class BootstrapFormMixin:
    """Adds Bootstrap 5 classes to every widget so templates stay simple."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                css = "form-check-input"
            elif isinstance(widget, forms.Select):
                css = "form-select"
            else:
                css = "form-control"
            if self.is_bound and name in self.errors:
                css += " is-invalid"
            widget.attrs["class"] = (widget.attrs.get("class", "") + " " + css).strip()

    def full_clean(self):
        super().full_clean()
        # Re-apply the invalid state after validation for bound forms.
        for name in self.errors:
            if name in self.fields:
                attrs = self.fields[name].widget.attrs
                if "is-invalid" not in attrs.get("class", ""):
                    attrs["class"] = attrs.get("class", "") + " is-invalid"


class SignUpForm(BootstrapFormMixin, UserCreationForm):
    first_name = forms.CharField(max_length=60, required=True, label="First name")
    email = forms.EmailField(required=True, label="Email address")

    class Meta:
        model = User
        fields = ["username", "first_name", "email"]

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email


class LoginForm(BootstrapFormMixin, AuthenticationForm):
    pass
