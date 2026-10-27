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
    """Django's usual sign-up: username, e-mail, password twice. Name and phone are optional (the phone enables SMS and the desk search)."""
    username = forms.CharField(max_length=30, strip=True, error_messages=REQUIRED)
    email = forms.EmailField(max_length=254, error_messages={"required": "err_fields", "invalid": "err_email"})
    password = forms.CharField(max_length=128, strip=False, error_messages={**REQUIRED, "max_length": "err_pass"})
    password2 = forms.CharField(max_length=128, strip=False, error_messages=REQUIRED)
    first_name = forms.CharField(max_length=40, strip=True, required=False)
    last_name = forms.CharField(max_length=40, strip=True, required=False)
    phone = forms.CharField(max_length=20, required=False)

    def clean_username(self):
        u = self.cleaned_data["username"]
        if not re.fullmatch(r"[A-Za-z0-9_.]{3,30}", u):
            raise ValidationError("err_username")
        if User.objects.filter(username__iexact=u).exists():
            raise ValidationError("err_username_taken")
        return u

    def clean_email(self):
        e = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=e).exists():
            raise ValidationError("err_email_taken")
        return e

    def clean_phone(self):
        raw = (self.cleaned_data.get("phone") or "").strip()
        if not raw:
            return None
        p = normalize_phone(raw)
        if not p:
            raise ValidationError("err_phone")
        if User.objects.filter(phone=p).exists():
            raise ValidationError("err_exists")
        return p

    def clean_password(self):
        pw = self.cleaned_data["password"]
        if len(pw) < 6:
            raise ValidationError("err_pass")
        return pw

    def clean(self):
        d = super().clean()
        if d.get("password") and d.get("password2") is not None and d["password"] != d["password2"]:
            self.add_error("password2", "err_pass_match")
        return d


class LoginForm(forms.Form):
    """One box for the username, the e-mail or the phone number."""
    login = forms.CharField(max_length=254, strip=True, error_messages=REQUIRED)
    password = forms.CharField(max_length=140, strip=False, error_messages=REQUIRED)


def find_user(login):
    """The account a sign-in box refers to: a phone number, an e-mail or a username (case does not matter)."""
    login = (login or "").strip()
    if not login:
        return None
    phone = normalize_phone(login) if not re.search(r"[A-Za-z@]", login) else None
    if phone:
        return User.objects.filter(phone=phone).first()
    if "@" in login:
        return User.objects.filter(email__iexact=login).first()
    return User.objects.filter(username__iexact=login).first()


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


class AccountForm(forms.ModelForm):
    """Account settings: login details and the shown name. Picture and password are handled next to it in the same view."""
    phone = forms.CharField(max_length=20, required=False)

    class Meta:
        model = User
        fields = ["username", "email", "first_name", "last_name", "phone"]
        error_messages = {"username": REQUIRED, "email": {"required": "err_fields", "invalid": "err_email"}}

    def clean_username(self):
        u = (self.cleaned_data.get("username") or "").strip()
        if not re.fullmatch(r"[A-Za-z0-9_.]{3,30}", u):
            raise ValidationError("err_username")
        if User.objects.filter(username__iexact=u).exclude(pk=self.instance.pk).exists():
            raise ValidationError("err_username_taken")
        return u

    def clean_email(self):
        e = (self.cleaned_data.get("email") or "").strip().lower()
        if not e:
            raise ValidationError("err_fields")
        if User.objects.filter(email__iexact=e).exclude(pk=self.instance.pk).exists():
            raise ValidationError("err_email_taken")
        return e

    def clean_phone(self):
        raw = (self.cleaned_data.get("phone") or "").strip()
        if not raw:
            return None
        p = normalize_phone(raw)
        if not p:
            raise ValidationError("err_phone")
        if User.objects.filter(phone=p).exclude(pk=self.instance.pk).exists():
            raise ValidationError("err_exists")
        return p
