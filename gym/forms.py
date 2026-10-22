import re

from django import forms
from django.core.exceptions import ValidationError

from .models import BodyLog, Review, User


def normalize_phone(raw):
    """'90 877 55 05', '+998908775505' or '998908775505' -> '+998908775505'; anything else -> None."""
    d = re.sub(r"\D", "", raw or "")
    if len(d) == 12 and d.startswith("998"):
        return "+" + d
    if len(d) == 9:
        return "+998" + d
    return None


REQUIRED = {"required": "err_fields", "invalid": "err_fields"}


class PhoneField(forms.CharField):
    def clean(self, value):
        value = super().clean(value)
        phone = normalize_phone(value)
        if not phone:
            raise ValidationError("err_phone")
        return phone


class RegisterForm(forms.Form):
    first_name = forms.CharField(max_length=40, strip=True, error_messages=REQUIRED)
    last_name = forms.CharField(max_length=40, strip=True, error_messages=REQUIRED)
    phone = PhoneField(error_messages=REQUIRED)
    password = forms.CharField(max_length=128, strip=False, error_messages={**REQUIRED, "max_length": "err_pass"})

    def clean_phone(self):
        p = self.cleaned_data["phone"]
        if User.objects.filter(phone=p).exists():
            raise ValidationError("err_exists")
        return p

    def clean_password(self):
        pw = self.cleaned_data["password"]
        if len(pw) < 6:
            raise ValidationError("err_pass")
        return pw


class LoginForm(forms.Form):
    phone = PhoneField(error_messages=REQUIRED)
    password = forms.CharField(max_length=140, strip=False, error_messages=REQUIRED)


class ProfileForm(forms.ModelForm):
    phone = PhoneField(required=False, error_messages=REQUIRED)

    class Meta:
        model = User
        fields = ["first_name", "last_name", "phone"]
        error_messages = {f: REQUIRED for f in fields}

    def clean_phone(self):
        p = self.cleaned_data.get("phone") or None
        if p is None and not self.instance.email:
            raise ValidationError("err_phone")
        if p and User.objects.filter(phone=p).exclude(pk=self.instance.pk).exists():
            raise ValidationError("err_exists")
        return p


class PasswordForm(forms.Form):
    current = forms.CharField(max_length=128, strip=False, required=False)
    new = forms.CharField(max_length=128, strip=False, error_messages={**REQUIRED, "max_length": "err_pass"})

    def clean_new(self):
        if len(self.cleaned_data["new"]) < 6:
            raise ValidationError("err_pass")
        return self.cleaned_data["new"]


class BodyLogForm(forms.ModelForm):
    class Meta:
        model = BodyLog
        fields = ["date", "weight", "height_cm", "note"]
        widgets = {"date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")}
        error_messages = {f: REQUIRED for f in fields}


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ["rating", "comment"]
        error_messages = {f: REQUIRED for f in fields}
