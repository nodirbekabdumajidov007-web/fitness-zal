"""Sign in with a code sent by e-mail ("Kod bilan kirish"), and the e-mail step of the optional 2-step check.

The request page never says whether an account exists: every submit gets the same redirect to the code page and the same wording. A code
alone never opens the admin panel: admin mode needs the password with the ".admin" suffix (staff and the owner come in as a normal member)."""
import time

from django.contrib import messages
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme

from . import emailcode
from .forms import find_user
from .models import User
from .net import client_ip
from .views import flash, google_required, rl_check, rl_fail, safe_next, second_step, sms_login_on

PENDING_TTL = 900


def _pending(request):
    p = request.session.get("pending_email")
    if not p or time.time() - p.get("ts", 0) > PENDING_TTL:
        request.session.pop("pending_email", None)
        return None
    return p


def _mask(email):
    name, _, dom = (email or "").partition("@")
    return f"{name[:2]}{'*' * max(1, len(name) - 2)}@{dom}" if dom else ""


def email_login_view(request):
    """Step 1: the e-mail (or username) to send the code to."""
    if request.user.is_authenticated:
        return redirect("dashboard")
    if not emailcode.mail_ready():
        return redirect("login")
    error, text = None, ""
    if request.method == "POST":
        text = (request.POST.get("login") or "").strip()[:254]
        key = f"rl:ecreq:{client_ip(request)}"
        if not text:
            error = "err_fields"
        elif not rl_check(key):
            error = "err_rate"
        else:
            rl_fail(key)  # every request counts, so one address cannot flood anybody's inbox
            user = find_user(text)
            usable = bool(user and user.is_active and user.email and not (google_required() and not user.is_superuser))
            if usable:
                emailcode.issue(user, "login", request.lang)
            request.session["pending_email"] = {"uid": user.pk if usable else 0, "mode": "code", "admin": False, "ts": int(time.time()),
                                                "sent": time.time(), "next": safe_next(request, ""), "remember": True, "tries": 0}
            return redirect("login_email_code")
    return render(request, "gym/login_email.html", {"error": error, "login_text": text, "next": request.GET.get("next", "") or request.POST.get("next", "")})


def email_code_view(request):
    """Step 2: the 6-digit code. For an unknown account the page behaves the same and every code simply fails."""
    p = _pending(request)
    if not p:
        flash(request, messages.INFO, "login_expired")
        return redirect("login")
    user = User.objects.filter(pk=p["uid"], is_active=True).first() if p["uid"] else None
    error = None
    left = max(0, int(emailcode.COOLDOWN - (time.time() - p.get("sent", 0))))
    if request.method == "POST":
        if request.POST.get("action") == "resend":
            if left:
                error = "ec_wait"
            else:
                if user:
                    emailcode.issue(user, "login", request.lang)
                p["sent"], p["tries"] = time.time(), 0
                request.session["pending_email"] = p
                flash(request, messages.INFO, "ec_resent")
                return redirect("login_email_code")
        else:
            key = f"rl:eccheck:{client_ip(request)}"
            if not rl_check(key):
                error = "err_rate"
            elif p["tries"] >= emailcode.MAX_TRIES:
                request.session.pop("pending_email", None)
                flash(request, messages.ERROR, "ec_locked")
                return redirect("login")
            elif user and emailcode.check(user, "login", request.POST.get("code", "")):
                request.session.pop("pending_email", None)
                nxt = p.get("next") or ""
                if not url_has_allowed_host_and_scheme(nxt, {request.get_host()}):
                    nxt = ""
                if not sms_login_on():
                    flash(request, messages.SUCCESS, "welcome")
                # admin_mode is only ever carried over from a password login (2-step); the code by itself never grants it
                return second_step(request, user, bool(p["admin"]) and p["mode"] == "2fa", nxt, p.get("remember", True), skip_email=True)
            else:
                rl_fail(key)
                p["tries"] += 1
                request.session["pending_email"] = p
                if p["tries"] >= emailcode.MAX_TRIES:
                    request.session.pop("pending_email", None)
                    flash(request, messages.ERROR, "ec_locked")
                    return redirect("login")
                error = "ec_bad"
    left = max(0, int(emailcode.COOLDOWN - (time.time() - p.get("sent", 0))))
    return render(request, "gym/login_email_code.html", {"error": error, "left": left, "hint": _mask(user.email) if (user and p["mode"] == "2fa") else "",
                                                          "mode": p["mode"]})
