from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User

from .models import (
    CUSTOM_PURPOSE, LANGUAGES, PURPOSES, RECIPIENTS, TONES, GeneratedEmail, as_choices,
)


class StyledFormMixin:
    """Adds the 'form-control' CSS class to every field widget."""

    def style_fields(self):
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")


class LoginForm(StyledFormMixin, AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.style_fields()


class RegisterForm(StyledFormMixin, UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.style_fields()

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
        return user


class GenerateEmailForm(StyledFormMixin, forms.Form):
    purpose = forms.ChoiceField(choices=as_choices(PURPOSES + [CUSTOM_PURPOSE]), label="Email purpose")
    custom_purpose = forms.CharField(
        max_length=100, required=False, label="Custom purpose",
        widget=forms.TextInput(attrs={"placeholder": "e.g. Scholarship enquiry"}),
    )
    recipient_type = forms.ChoiceField(choices=as_choices(RECIPIENTS), label="Recipient")
    tone = forms.ChoiceField(choices=as_choices(TONES))
    language = forms.ChoiceField(choices=as_choices(LANGUAGES))
    important_points = forms.CharField(
        max_length=2000,
        widget=forms.Textarea(attrs={
            "rows": 6,
            "placeholder": "I am a B.Tech CSE student.\nI completed Python and Django training.\nMy resume is attached.",
        }),
    )
    additional_instructions = forms.CharField(
        max_length=1000, required=False, label="Additional instructions (optional)",
        widget=forms.Textarea(attrs={"rows": 3, "placeholder": "e.g. Keep it under 150 words."}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.style_fields()

    def clean(self):
        cleaned = super().clean()
        purpose = cleaned.get("purpose")
        if purpose == CUSTOM_PURPOSE:
            custom = (cleaned.get("custom_purpose") or "").strip()
            if not custom:
                self.add_error("custom_purpose", "Please describe the purpose of your email.")
            cleaned["final_purpose"] = custom
        else:
            cleaned["final_purpose"] = purpose
        return cleaned


class EmailEditForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = GeneratedEmail
        fields = ("subject", "body")
        widgets = {"body": forms.Textarea(attrs={"rows": 16})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.style_fields()


class EmailFilterForm(StyledFormMixin, forms.Form):
    """GET form for searching / filtering the history page."""

    q = forms.CharField(required=False, label="Search", widget=forms.TextInput(attrs={"placeholder": "Search subject or purpose"}))
    purpose = forms.ChoiceField(required=False)
    tone = forms.ChoiceField(required=False, choices=[("", "All tones")] + as_choices(TONES))
    date = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        purposes = []
        if user is not None:
            purposes = (
                GeneratedEmail.objects.filter(user=user)
                .order_by("purpose").values_list("purpose", flat=True).distinct()
            )
        self.fields["purpose"].choices = [("", "All purposes")] + as_choices(purposes)
        self.style_fields()
