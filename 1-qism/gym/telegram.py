"""Telegram bot: account linking, status, reminders and admin alerts.
Needs TELEGRAM_BOT_TOKEN (from @BotFather). Optional TELEGRAM_ADMIN_CHAT_ID receives staff alerts.
Run the bot with `python manage.py run_bot`; send reminders with `python manage.py send_reminders` (schedule it hourly).
Not exercised against the live Telegram API; the logic is covered by tests with a faked transport."""
import json
import logging
import os
import urllib.request
from datetime import timedelta

from django.utils import timezone

from .models import Booking, GymSettings, Membership, PTSession, User
from .templatetags.gym_tags import translate

log = logging.getLogger("gym.telegram")


def token():
    return os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()


def enabled():
    return bool(token())


def api(method, **params):
    if not enabled():
        return None
    req = urllib.request.Request(f"https://api.telegram.org/bot{token()}/{method}", data=json.dumps(params).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=40 if method == "getUpdates" else 10) as r:
            return json.load(r)
    except Exception:
        log.exception("Telegram %s failed", method)
        return None


def send(chat_id, text):
    return api("sendMessage", chat_id=chat_id, text=text)


def alert_admin(text):
    chat = os.environ.get("TELEGRAM_ADMIN_CHAT_ID", "").strip()
    if chat and enabled():
        send(chat, text)


def notify_user(user, key, **kw):
    if user.telegram_chat_id and enabled():
        send(user.telegram_chat_id, translate(user.lang or "uz", key, **kw))
        return True
    return False


def link_url(user):
    bot = GymSettings.load().telegram_bot.lstrip("@")
    if not bot:
        return ""
    if not user.tg_link_code:
        import secrets
        user.tg_link_code = secrets.token_hex(5)
        user.save(update_fields=["tg_link_code"])
    return f"https://t.me/{bot}?start={user.tg_link_code}"


def handle_message(chat_id, text):
    """Pure logic for one incoming message; returns the reply text."""
    text = (text or "").strip()
    user = User.objects.filter(telegram_chat_id=chat_id).first()
    lang = user.lang if user else "uz"
    if text.startswith("/start"):
        code = text[6:].strip()
        target = User.objects.filter(tg_link_code=code).first() if code else None
        if not target:
            return translate(lang, "tg_help")
        User.objects.filter(telegram_chat_id=chat_id).update(telegram_chat_id=None)
        target.telegram_chat_id, target.tg_link_code = chat_id, ""
        target.save(update_fields=["telegram_chat_id", "tg_link_code"])
        return translate(target.lang or "uz", "tg_linked", name=target.first_name)
    if not user:
        return translate(lang, "tg_help")
    if text.startswith("/stop"):
        user.telegram_chat_id = None
        user.save(update_fields=["telegram_chat_id"])
        return translate(lang, "tg_unlinked")
    if text.startswith("/status"):
        m = user.memberships.order_by("-expires").first()
        if m and m.expires > timezone.now():
            return translate(lang, "tg_status_active", date=timezone.localtime(m.expires).strftime("%d.%m.%Y"), days=(m.expires - timezone.now()).days)
        return translate(lang, "tg_status_none")
    return translate(lang, "tg_help")


def run_bot_once(offset):
    """One getUpdates round. Returns the next offset."""
    res = api("getUpdates", offset=offset, timeout=30, allowed_updates=["message"])
    for upd in (res or {}).get("result", []):
        offset = upd["update_id"] + 1
        msg = upd.get("message") or {}
        if msg.get("chat", {}).get("type") == "private" and "text" in msg:
            reply = handle_message(msg["chat"]["id"], msg["text"])
            send(msg["chat"]["id"], reply)
    return offset


def send_reminders(now=None):
    """Membership expiry, class tomorrow and personal training in the next 24 hours. Each reminder is sent once."""
    now = now or timezone.now()
    days = GymSettings.load().reminder_days
    sent = {"membership": 0, "class": 0, "pt": 0}
    for m in Membership.objects.filter(reminded=False, expires__gt=now, expires__lte=now + timedelta(days=days)).select_related("user"):
        if m.user.memberships.filter(expires__gt=m.expires).exists():
            continue  # a later membership already covers them
        if notify_user(m.user, "tg_expiring", days=max(0, (m.expires - now).days), date=timezone.localtime(m.expires).strftime("%d.%m.%Y")):
            m.reminded = True
            m.save(update_fields=["reminded"])
            sent["membership"] += 1
    tomorrow = timezone.localtime(now).date() + timedelta(days=1)
    for b in Booking.objects.filter(date=tomorrow, reminded=False).select_related("user", "gym_class"):
        if notify_user(b.user, "tg_class_tomorrow", name=b.gym_class.name, time=b.gym_class.start_time.strftime("%H:%M")):
            b.reminded = True
            b.save(update_fields=["reminded"])
            sent["class"] += 1
    for s in PTSession.objects.filter(status="confirmed", reminded=False, starts__gt=now, starts__lte=now + timedelta(hours=24)).select_related("user", "trainer"):
        if notify_user(s.user, "tg_pt_soon", trainer=s.trainer.name, time=timezone.localtime(s.starts).strftime("%d.%m %H:%M")):
            s.reminded = True
            s.save(update_fields=["reminded"])
            sent["pt"] += 1
    return sent
