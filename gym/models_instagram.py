"""Instagram Direct inbox: one thread per Instagram user, their messages, and the (single) access token of our account.
Imported at the bottom of models.py so Django registers these with the `gym` app. Logic lives in instagram_api / instagram_bot."""
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone

__all__ = ["IgThread", "IgMessage", "IgToken"]

WINDOW = timedelta(hours=24)  # Instagram lets us send only within 24 hours after the user's last message


class IgThread(models.Model):
    igsid = models.CharField("Instagram ID (IGSID)", max_length=64, unique=True)
    username = models.CharField("Username", max_length=100, blank=True)
    name = models.CharField("Ism", max_length=200, blank=True)
    profile_pic_url = models.CharField("Rasm (vaqtinchalik havola)", max_length=1000, blank=True)
    profile_fetched_at = models.DateTimeField(null=True, blank=True)
    last_user_message_at = models.DateTimeField("Foydalanuvchining oxirgi xabari", null=True, blank=True)
    last_message_at = models.DateTimeField("Oxirgi xabar", null=True, blank=True, db_index=True)
    unread = models.PositiveIntegerField("O'qilmagan", default=0)
    needs_human = models.BooleanField("Administrator javobi kerak", default=False)
    auto_reply_paused = models.BooleanField("Bot shu suhbatda to'xtatilgan", default=False)
    bot_paused_until = models.DateTimeField("Bot shu vaqtgacha jim (xodim javob bergan)", null=True, blank=True)
    member = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="ig_threads", verbose_name="A'zo")
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-last_message_at", "-id"]
        verbose_name, verbose_name_plural = "Instagram suhbat", "Instagram suhbatlar"

    def __str__(self):
        return self.display_name

    @property
    def display_name(self):
        return self.name or (f"@{self.username}" if self.username else f"IG {self.igsid[-6:]}")

    @property
    def initials(self):
        src = (self.name or self.username or "?").strip().lstrip("@")
        return src[:2].upper() or "?"

    def window_open(self, now=None):
        return bool(self.last_user_message_at) and (now or timezone.now()) - self.last_user_message_at < WINDOW

    def window_left(self, now=None):
        if not self.last_user_message_at:
            return timedelta(0)
        return max(timedelta(0), WINDOW - ((now or timezone.now()) - self.last_user_message_at))

    def bot_paused(self, now=None):
        return self.auto_reply_paused or bool(self.bot_paused_until and self.bot_paused_until > (now or timezone.now()))


class IgMessage(models.Model):
    DIRECTIONS = [("in", "Kiruvchi"), ("out", "Chiquvchi")]
    KINDS = [("user", "Foydalanuvchi"), ("bot", "Bot"), ("staff", "Xodim (panel)"), ("echo", "Xodim (Instagram ilovasi)")]
    thread = models.ForeignKey(IgThread, on_delete=models.CASCADE, related_name="messages")
    mid = models.CharField(max_length=300, unique=True, null=True, blank=True)
    direction = models.CharField(max_length=3, choices=DIRECTIONS)
    kind = models.CharField(max_length=5, choices=KINDS)
    text = models.TextField(blank=True)
    attachments = models.JSONField(default=list, blank=True)
    created = models.DateTimeField(default=timezone.now, db_index=True)
    sent_ok = models.BooleanField(default=True)
    error = models.CharField(max_length=300, blank=True)
    processed = models.BooleanField("Bot ko'rib chiqdi", default=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")

    class Meta:
        ordering = ["created", "id"]
        verbose_name, verbose_name_plural = "Instagram xabar", "Instagram xabarlar"
        indexes = [models.Index(fields=["thread", "created"])]

    def __str__(self):
        return f"{self.direction}/{self.kind}: {self.text[:30]}"


class IgToken(models.Model):
    """Single row (pk=1). The token itself is never shown anywhere in the admin and never logged."""
    access_token = models.TextField(blank=True)
    seed_hash = models.CharField(max_length=16, blank=True)  # fingerprint of the env token this row was seeded from
    expires_at = models.DateTimeField(null=True, blank=True)
    refreshed_at = models.DateTimeField(null=True, blank=True)
    last_attempt_at = models.DateTimeField(null=True, blank=True)
    last_error = models.CharField(max_length=300, blank=True)
    last_webhook_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = verbose_name_plural = "Instagram token"

    def __str__(self):
        return f"IgToken({self.masked})"

    @property
    def masked(self):
        return "••••••••" if self.access_token else "—"

    @classmethod
    def load(cls):
        return cls.objects.get_or_create(pk=1)[0]
