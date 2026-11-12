"""One-time codes sent by e-mail: passwordless sign-in ("Kod bilan kirish") and the optional e-mail 2-step check.

A code is 6 digits, valid for 10 minutes, usable once, with at most 5 wrong guesses. Only an HMAC of the code (keyed with SECRET_KEY and
bound to the account and purpose) is kept in the cache, never the code itself. Trade-off: the cache is per process (LocMem) on a single
Render instance, which is what the project runs; with several instances switch CACHES to a shared one, otherwise a code issued by one
instance cannot be checked by another.
"""
import hashlib
import hmac
import logging
import secrets

from django.conf import settings
from django.core.cache import cache
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

from .i18n import LANGS
from .templatetags.gym_tags import translate

TTL = 600          # a code lives 10 minutes
MAX_TRIES = 5      # wrong guesses before the code dies
COOLDOWN = 60      # seconds before another code may be sent to the same account
PER_ACCOUNT_HOUR = 6
log = logging.getLogger(__name__)


def mail_ready():
    """True when a code can really reach an inbox: an SMTP server is set up (or we are developing and the mail prints to the console)."""
    return settings.EMAIL_BACKEND != "django.core.mail.backends.console.EmailBackend" or settings.DEBUG


def _key(uid, purpose):
    return f"ec:{purpose}:{uid}"


def _digest(uid, purpose, code):
    return hmac.new(settings.SECRET_KEY.encode(), f"{uid}:{purpose}:{code}".encode(), hashlib.sha256).hexdigest()


def issue(user, purpose="login", lang="uz", minutes=TTL // 60):
    """Make a fresh code for `user` and e-mail it. Returns (sent, code): `sent` is False when throttled (cooldown / hourly cap), has no
    e-mail or the mail failed; the caller shows the same neutral answer either way."""
    if not user or not user.email or not user.is_active:
        return False, None
    cool, hourly = f"ec:cool:{user.pk}", f"ec:hour:{user.pk}"
    if cache.get(cool) or cache.get(hourly, 0) >= PER_ACCOUNT_HOUR:
        return False, None
    code = f"{secrets.randbelow(10 ** 6):06d}"
    cache.set(_key(user.pk, purpose), {"h": _digest(user.pk, purpose, code), "tries": 0}, TTL)
    cache.set(cool, 1, COOLDOWN)
    try:
        cache.incr(hourly)
    except ValueError:
        cache.set(hourly, 1, 3600)
    ok = send_code_mail(user, code, purpose, lang, minutes)
    return ok, code if ok else None


def check(user, purpose, code):
    """True once for the right code; wrong guesses are counted and the code is burnt after MAX_TRIES."""
    if not user:
        return False
    key = _key(user.pk, purpose)
    rec = cache.get(key)
    code = (code or "").strip().replace(" ", "")
    if not rec or not (code.isdigit() and len(code) == 6):
        if rec:
            _miss(key, rec)
        return False
    if hmac.compare_digest(rec["h"], _digest(user.pk, purpose, code)):
        cache.delete(key)  # single use
        return True
    _miss(key, rec)
    return False


def _miss(key, rec):
    rec["tries"] += 1
    if rec["tries"] >= MAX_TRIES:
        cache.delete(key)
    else:
        cache.set(key, rec, TTL)


def send_code_mail(user, code, purpose, lang, minutes):
    lang = lang if lang in LANGS else "uz"
    ctx = {"code": code, "gym": "Fitnes Zal", "user": user, "lang": lang,
           "t": {k: translate(lang, k, minutes=minutes, gym="Fitnes Zal") for k in ("ec_mail_title", "ec_mail_intro", "ec_mail_valid", "ec_mail_ignore", "ec_mail_secret")}}
    subject = translate(lang, "ec_subject").format(code=code)
    try:
        msg = EmailMultiAlternatives(subject, render_to_string("gym/email/login_code.txt", ctx), None, [user.email])
        msg.attach_alternative(render_to_string("gym/email/login_code.html", ctx), "text/html")
        return bool(msg.send(fail_silently=False))
    except Exception:
        log.exception("login code e-mail to user %s failed", user.pk)
        return False
