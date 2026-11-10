"""Support widget: conversations between a visitor (member or guest) and the gym staff, plus "was this helpful?" votes on FAQ articles."""
import secrets

from django.conf import settings
from django.db import models
from django.utils import timezone

from .media import validate_image


def new_guest_token():
    return secrets.token_urlsafe(24)


class SupportThread(models.Model):
    """One conversation. A member has one open thread at a time; a guest is recognised by the token in a cookie."""
    class Status(models.TextChoices):
        OPEN = "open", "Ochiq"
        PENDING = "pending", "Kutilmoqda"
        CLOSED = "closed", "Yopilgan"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.CASCADE, related_name="support_threads", verbose_name="A'zo")
    guest_name = models.CharField("Mehmon ismi", max_length=80, blank=True)
    guest_phone = models.CharField("Mehmon telefoni", max_length=20, blank=True)
    guest_email = models.EmailField("Mehmon e-maili", blank=True)
    guest_token = models.CharField(max_length=64, blank=True, db_index=True, editable=False)
    status = models.CharField("Holat", max_length=8, choices=Status.choices, default=Status.OPEN, db_index=True)
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="assigned_support", verbose_name="Mas'ul xodim")
    last_message_at = models.DateTimeField("Oxirgi xabar", default=timezone.now, db_index=True)
    unread_by_staff = models.PositiveIntegerField("Xodim o'qimagan", default=0)
    unread_by_user = models.PositiveIntegerField("Mijoz o'qimagan", default=0)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-last_message_at", "-id"]
        verbose_name, verbose_name_plural = "Murojaat", "Murojaatlar"

    def __str__(self):
        return f"{self.display_name} · {self.get_status_display()}"

    @property
    def display_name(self):
        if self.user_id:
            return self.user.full_name
        return self.guest_name or "Mehmon"

    @property
    def phone(self):
        return self.user.phone if self.user_id else self.guest_phone


class SupportMessage(models.Model):
    thread = models.ForeignKey(SupportThread, on_delete=models.CASCADE, related_name="messages")
    sender_user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    is_staff = models.BooleanField("Xodim yozgan", default=False)
    text = models.TextField("Matn", max_length=2000, blank=True)
    image = models.FileField("Rasm", upload_to="support/", blank=True, validators=[validate_image])
    created = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField("O'qilgan", null=True, blank=True)

    class Meta:
        ordering = ["created", "id"]
        verbose_name, verbose_name_plural = "Murojaat xabari", "Murojaat xabarlari"

    def __str__(self):
        return (self.text or "[rasm]")[:60]


class FaqFeedback(models.Model):
    """"Was this helpful?" - one vote per person per article (a later vote replaces the earlier one)."""
    faq = models.ForeignKey("gym.FaqItem", on_delete=models.CASCADE, related_name="feedback")
    helpful = models.BooleanField("Foydali")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    session_key = models.CharField(max_length=64, blank=True, db_index=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created"]
        verbose_name, verbose_name_plural = "FAQ baho", "FAQ baholar"
