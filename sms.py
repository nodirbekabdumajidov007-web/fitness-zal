"""SMS one-time codes. Backend picked by SMS_BACKEND: `console` (logs the text, for development) or `eskiz` (Eskiz.uz).
The Eskiz branch follows their public API but has not been run against a live account; test it with a real number before relying on it."""
import hashlib
import hmac
import json
import logging
import os
import secrets
import urllib.parse
import urllib.request
from datetime import timedelta

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

from .models import OtpCode

log = logging.getLogger("gym.sms")
OTP_TTL = timedelta(minutes=10)
MAX_ATTEMPTS = 5
MAX_SENDS_PER_HOUR = 3


def backend():
    return os.environ.get("SMS_BACKEND", "console")


def real_backend():
    return backend() != "console"


def _eskiz_token():
    tok = cache.get("eskiz:token")
    if tok:
        return tok
    data = urllib.parse.urlencode({"email": os.environ["ESKIZ_EMAIL"], "password": os.environ["ESKIZ_PASSWORD"]}).encode()
    with urllib.request.urlopen(urllib.request.Request("https://notify.eskiz.uz/api/auth/login", data=data), timeout=10) as r:
        tok = json.load(r)["data"]["token"]
    cache.set("eskiz:token", tok, 20 * 86400)
    return tok


def send_sms(phone, text):
    """Returns True when the provider accepted the message."""
    if backend() == "eskiz":
        try:
            data = urllib.parse.urlencode({"mobile_phone": phone.lstrip("+"), "message": text, "from": os.environ.get("ESKIZ_FROM", "4546")}).encode()
            req = urllib.request.Request("https://notify.eskiz.uz/api/message/sms/send", data=data,
                                         headers={"Authorization": "Bearer " + _eskiz_token()})
            with urllib.request.urlopen(req, timeout=10):
                return True
        except Exception:
            log.exception("Eskiz SMS failed")
            return False
    log.warning("SMS (console backend) to %s: %s", phone, text)
    return True


def _hash(phone, code):
    return hmac.new(settings.SECRET_KEY.encode(), f"{phone}:{code}".encode(), hashlib.sha256).hexdigest()


def issue_otp(phone, purpose):
    """Returns (code, error_key). The code is returned only so DEBUG/console setups can show it; never show it otherwise."""
    key = f"otp:send:{phone}"
    if cache.get(key, 0) >= MAX_SENDS_PER_HOUR:
        return None, "err_rate"
    try:
        cache.incr(key)
    except ValueError:
        cache.set(key, 1, 3600)
    code = f"{secrets.randbelow(10 ** 6):06d}"
    OtpCode.objects.filter(phone=phone, purpose=purpose, used=False).update(used=True)
    OtpCode.objects.create(phone=phone, purpose=purpose, code_hash=_hash(phone, code))
    if not send_sms(phone, f"Fitnes Zal: {code}"):
        return None, "sms_fail"
    return code, None


def check_otp(phone, purpose, code):
    otp = OtpCode.objects.filter(phone=phone, purpose=purpose, used=False, created__gte=timezone.now() - OTP_TTL).first()
    if not otp:
        return False
    otp.attempts += 1
    ok = otp.attempts <= MAX_ATTEMPTS and hmac.compare_digest(otp.code_hash, _hash(phone, (code or "").strip()))
    if ok or otp.attempts >= MAX_ATTEMPTS:
        otp.used = True
    otp.save(update_fields=["attempts", "used"])
    return ok
