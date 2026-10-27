import json
import logging
import re
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta

import segno
from django import forms
from django.conf import settings as dj
from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import make_password
from django.contrib.staticfiles import finders
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import connection, transaction
from django.db.models import Avg, Count, Q
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.safestring import mark_safe
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from . import click, services, sms, telegram
from .media import ranged_file_response, video_embed
from .forms import AccountForm, BodyLogForm, LoginForm, PasswordForm, PhoneField, ProfileForm, RegisterForm, ReviewForm, find_user, normalize_phone
from .i18n import LANGS
from .models import (Announcement, BodyLog, Booking, Category, Exercise, ExerciseLog, GymClass, GymSettings, Membership, Order, Payment,
                     Plan, Product, PTSession, Review, Trainer, User, Visit, WorkoutPlan)
from .templatetags.gym_tags import translate
from django.template.loader import render_to_string

BACKEND = "django.contrib.auth.backends.ModelBackend"
DEMO_METHODS = ["Payme", "Click", "Uzum"]


def flash(request, level, key, **kw):
    messages.add_message(request, level, translate(request.lang, key, **kw))


def allowed_methods(gs):
    return (["cash"] + (["card"] if services.current_card() else []) + (["click"] if click.enabled() else [])
            + (DEMO_METHODS if services.demo_enabled(gs) else []))


def safe_next(request, default="dashboard"):
    nxt = request.POST.get("next") or request.GET.get("next") or ""
    return nxt if nxt and url_has_allowed_host_and_scheme(nxt, {request.get_host()}) else default


def rl_check(*keys):
    return not any(cache.get(k, 0) >= 8 for k in keys)


def rl_fail(*keys):
    for k in keys:
        try:
            cache.incr(k)
        except ValueError:
            cache.set(k, 1, 600)


def json_field(request, name):
    """One text field from a JSON body. Anything malformed (not JSON, not an object, not a string) reads as empty instead of crashing."""
    try:
        data = json.loads(request.body)
    except ValueError:
        return ""
    value = data.get(name, "") if isinstance(data, dict) else ""
    return value if isinstance(value, str) else ""


def safe_date(text):
    """parse_date that never raises: a well-formed but impossible date such as 2026-02-30 counts as missing."""
    from django.utils.dateparse import parse_date
    try:
        return parse_date(text or "")
    except ValueError:
        return None


def staff_required(view):
    def wrapper(request, *a, **kw):
        if not (request.user.is_authenticated and request.user.is_staff and request.session.get("admin_mode")):
            raise Http404()
        return view(request, *a, **kw)
    wrapper.__name__ = view.__name__
    return wrapper


def verify_gate(request):
    """When phone verification is switched on, purchases and bookings need a verified number."""
    gs = GymSettings.load()
    if gs.require_phone_verify and not request.user.phone_verified:
        flash(request, messages.INFO, "verify_needed")
        return redirect("verify")
    return None


def abs_url(request, name):
    return request.build_absolute_uri(reverse(name))


# ---------------------------------------------------------------- public pages
def crowd_level():
    """How busy the gym is right now: distinct members checked in during the last 2 hours against a comfortable capacity."""
    gs = GymSettings.load()
    n = Visit.objects.filter(ts__gte=timezone.now() - timedelta(hours=2)).values("user").distinct().count()
    pct = min(100, round(n / gs.gym_capacity * 100)) if gs.gym_capacity else 0
    return {"n": n, "pct": max(pct, 4), "level": "calm" if pct < 40 else ("mid" if pct < 75 else "busy")}


def home(request):
    reviews = Review.objects.filter(approved=True).select_related("user")
    now = timezone.now()
    return render(request, "gym/home.html", {
        "crowd": crowd_level(),
        "plans": Plan.objects.filter(active=True), "trainers": Trainer.objects.filter(active=True)[:3],
        "announcements": Announcement.objects.filter(active=True)[:3],
        "reviews": reviews[:3], "rating": reviews.aggregate(a=Avg("rating"), n=Count("id")),
        "classes_count": GymClass.objects.filter(active=True).count(),
        "members_count": Membership.objects.filter(starts__lte=now, expires__gt=now).values("user").distinct().count(),
        "trainers_count": Trainer.objects.filter(active=True).count(),
    })


def set_lang(request, code):
    resp = redirect(safe_next(request, "home"))
    if code in LANGS:
        resp.set_cookie("fz_lang", code, max_age=365 * 86400, samesite="Lax")
    return resp


def healthz(request):
    with connection.cursor() as c:
        c.execute("select 1")
    return HttpResponse("ok", content_type="text/plain")


def offline(request):
    return render(request, "gym/offline.html")


def manifest(request):
    icons = [{"src": f"{dj.STATIC_URL.rstrip('/')}/img/icon-{s}.png", "sizes": f"{s}x{s}", "type": "image/png", "purpose": p} for s in (192, 512) for p in ("any", "maskable")]
    return JsonResponse({"name": "Fitnes Zal", "short_name": "Fitnes Zal", "start_url": "/dashboard/", "scope": "/", "display": "standalone",
                         "background_color": "#101318", "theme_color": "#d6301f", "lang": request.lang, "icons": icons}, content_type="application/manifest+json")


def service_worker(request):
    path = finders.find("js/sw.js")
    if not path:
        raise Http404()
    with open(path, encoding="utf-8") as f:
        resp = HttpResponse(f.read(), content_type="application/javascript")
    resp["Service-Worker-Allowed"] = "/"
    resp["Cache-Control"] = "no-cache"
    return resp


# ---------------------------------------------------------------- sign-in: first factor (password or Google), then an SMS code
PENDING_TTL = 600  # seconds to type the SMS code


def sms_login_on(gs=None):
    """The SMS step only runs when a real SMS service is connected (or in development, where the code is shown on screen)."""
    gs = gs or GymSettings.load()
    return gs.login_sms_code and (sms.real_backend() or dj.DEBUG)


def google_required(gs=None):
    gs = gs or GymSettings.load()
    return gs.require_google and bool(gs.google_id())  # never locks everyone out if Google gets disconnected


def mask_phone(phone):
    d = (phone or "").replace("+998", "")
    return f"+998 {d[:2]} *** ** {d[-2:]}" if len(d) == 9 else ""


def do_login(request, user, admin_mode=False, remember=True):
    prev = user.last_login  # read before login() overwrites it
    login(request, user, backend=BACKEND)
    request.session["admin_mode"] = bool(admin_mode)
    # "remember me": 30 days on this device (7 for the admin door); unticked, the session ends when the browser closes
    request.session.set_expiry((7 if admin_mode else 30) * 86400 if remember else 0)
    if prev:  # a sign-in the member does not recognise is the first hint that someone else has the password
        flash(request, messages.INFO, "last_seen", when=timezone.localtime(prev).strftime("%d.%m.%Y %H:%M"))


def send_login_code(request, user):
    code, err = sms.issue_otp(user.phone, "login")
    if err:
        flash(request, messages.ERROR, err)
    else:
        dev_code_note(request, code)
        flash(request, messages.INFO, "otp_sent_to", phone=mask_phone(user.phone))


def second_step(request, user, admin_mode=False, nxt="", remember=True):
    """After the password or Google check: either log in now, or ask for the SMS code (or the phone number first)."""
    if not sms_login_on():
        do_login(request, user, admin_mode, remember)
        return redirect("/django-admin/" if admin_mode else (nxt or "dashboard"))
    request.session["pending_login"] = {"uid": user.pk, "admin": bool(admin_mode), "ts": int(time.time()), "next": nxt, "remember": remember}
    if not user.phone:
        return redirect("login_phone")  # e.g. a new Google account: ask for the number, then text it
    send_login_code(request, user)
    return redirect("login_code")


def pending_user(request):
    p = request.session.get("pending_login")
    if not p or time.time() - p.get("ts", 0) > PENDING_TTL:
        request.session.pop("pending_login", None)
        return None, None
    user = User.objects.filter(pk=p["uid"], is_active=True).first()
    return (user, p) if user else (None, None)


def login_code(request):
    user, p = pending_user(request)
    if not user or not user.phone:
        flash(request, messages.INFO, "login_expired")
        return redirect("login")
    error = None
    if request.method == "POST":
        if request.POST.get("action") == "resend":
            send_login_code(request, user)
            return redirect("login_code")
        key = f"rl:code:{request.META.get('REMOTE_ADDR')}"
        if not rl_check(key):
            error = "err_rate"
        elif sms.check_otp(user.phone, "login", request.POST.get("code", "")):
            request.session.pop("pending_login", None)
            if not user.phone_verified:
                user.phone_verified = True
                user.save(update_fields=["phone_verified"])
            flash(request, messages.SUCCESS, "welcome")  # first the greeting, then do_login's "previous sign-in" note
            do_login(request, user, p["admin"], p.get("remember", True))
            nxt = p.get("next") or ""
            return redirect("/django-admin/" if p["admin"] else (nxt if nxt and url_has_allowed_host_and_scheme(nxt, {request.get_host()}) else "dashboard"))
        else:
            rl_fail(key)
            error = "otp_bad"
    return render(request, "gym/login_code.html", {"phone": mask_phone(user.phone), "error": error})


def login_phone(request):
    """A Google account without a phone number: ask for it, then send the code there (this also verifies the number)."""
    user, p = pending_user(request)
    if not user:
        flash(request, messages.INFO, "login_expired")
        return redirect("login")
    if user.phone:
        return redirect("login_code")
    error = None
    if request.method == "POST":
        phone = normalize_phone(request.POST.get("phone", ""))
        if not phone:
            error = "err_phone"
        elif User.objects.filter(phone=phone).exclude(pk=user.pk).exists():
            error = "err_exists"
        else:
            user.phone, user.phone_verified = phone, False
            user.save(update_fields=["phone", "phone_verified"])
            send_login_code(request, user)
            return redirect("login_code")
    return render(request, "gym/login_phone.html", {"error": error})


def register_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    ref = (request.GET.get("ref") or request.session.get("ref") or "").upper()[:8]
    if ref:
        request.session["ref"] = ref
    referrer = User.objects.filter(referral_code=ref).first() if ref else None
    google_only = google_required()
    form = RegisterForm(request.POST or None)
    if request.method == "POST" and not google_only and form.is_valid():
        d = form.cleaned_data
        try:
            with transaction.atomic():
                user = User.objects.create_user(d["username"], d["password"], email=d["email"], phone=d["phone"],
                                                first_name=d["first_name"], last_name=d["last_name"], referred_by=referrer, lang=request.lang)
        except Exception:  # two people taking the same username/e-mail at the same moment
            form.add_error("username", "err_username_taken")
        else:
            request.session.pop("ref", None)
            services.send_welcome_email(user, request)
            if not sms_login_on():
                flash(request, messages.SUCCESS, "welcome")
            return second_step(request, user, False, safe_next(request, ""))  # with SMS on, the new number is verified right away
    return render(request, "gym/register.html", {"form": form, "referrer": referrer, "google_only": google_only, "sms_on": sms_login_on()})


def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    data = request.POST.copy() if request.method == "POST" else None
    if data is not None and not data.get("login") and data.get("phone"):  # older forms and scripts send the box as "phone"
        data["login"] = data["phone"]
    form = LoginForm(data)
    error = None
    if request.method == "POST" and form.is_valid():
        login_text, pw = form.cleaned_data["login"], form.cleaned_data["password"]
        user = find_user(login_text)
        keys = (f"rl:ip:{request.META.get('REMOTE_ADDR')}", f"rl:ph:{(user.pk if user else login_text.lower())}")
        admin_mode = False
        if user and user.is_staff and pw.endswith(".admin"):
            pw, admin_mode = pw[:-6], True
        if not rl_check(*keys):
            error = "err_rate"
        else:
            ok = bool(user and user.has_usable_password() and user.check_password(pw))
            if not user:
                make_password(pw)  # same cost for unknown numbers
            if not ok:
                rl_fail(*keys)
                error = "err_cred"
            elif not user.is_active:
                error = "err_blocked"
            elif google_required() and not user.is_superuser:
                error = "google_required"  # members must use their Google account; only the owner keeps the phone+password door
            elif request.POST.get("role") == "trainer" and not Trainer.objects.filter(user=user, active=True).exists():
                error = "not_trainer"  # the trainer door is only for accounts the owner linked to a trainer profile
            else:
                cache.delete(keys[1])
                nxt = "/coach/" if request.POST.get("role") == "trainer" else safe_next(request, "")
                return second_step(request, user, admin_mode, nxt, remember=bool(request.POST.get("remember")))
    return render(request, "gym/login.html", {"form": form, "error": error, "next": request.GET.get("next", ""),
                                              "remember": request.method != "POST" or bool(request.POST.get("remember")),
                                              "role": "trainer" if request.POST.get("role") == "trainer" or request.GET.get("as") == "trainer" else "member",
                                              "google_only": google_required(), "sms_on": sms_login_on()})


@require_POST
def logout_view(request):
    logout(request)
    return redirect("home")


@require_POST
def google_login(request):
    def fail(key, status=400):
        return JsonResponse({"error": translate(request.lang, key)}, status=status)
    client_id = GymSettings.load().google_id()
    if not client_id:
        return fail("google_off", 501)
    try:
        cred = json.loads(request.body).get("credential", "")
        assert isinstance(cred, str) and len(cred) < 4096
        with urllib.request.urlopen("https://oauth2.googleapis.com/tokeninfo?id_token=" + urllib.parse.quote(cred), timeout=6) as r:
            info = json.load(r)
    except Exception:
        return fail("err_google", 401)
    if info.get("aud") != client_id or info.get("email_verified") not in ("true", True) or not info.get("email"):
        return fail("err_google", 401)
    email = info["email"].lower()
    user = User.objects.filter(email=email).first()
    if not user:
        user = User.objects.create_user(email=email, first_name=(info.get("given_name") or email.split("@")[0])[:40],
                                        last_name=(info.get("family_name") or "-")[:40], lang=request.lang)
    if not user.is_active:
        return fail("err_blocked", 403)
    resp = second_step(request, user, False, "")
    return JsonResponse({"ok": True, "next": resp.url})


@require_POST
def apple_login(request):
    """Sign in with Apple (iCloud). Same rules as Google: verified e-mail, then the SMS step if it is switched on."""
    from . import apple

    def fail(key, status=400):
        return JsonResponse({"error": translate(request.lang, key)}, status=status)
    client_id = GymSettings.load().apple_id()
    if not client_id:
        return fail("apple_off", 501)
    try:
        data = json.loads(request.body)
        token = data.get("id_token", "")
        assert isinstance(token, str) and len(token) < 8192
    except Exception:
        return fail("err_apple", 400)
    claims = apple.verify(token, client_id)
    if not claims or not claims.get("email") or str(claims.get("email_verified")).lower() != "true":
        return fail("err_apple", 401)
    email = claims["email"].lower()
    user = User.objects.filter(email=email).first()
    if not user:
        name = data.get("name") if isinstance(data.get("name"), dict) else {}
        first = str(name.get("firstName") or email.split("@")[0])[:40]
        last = str(name.get("lastName") or "-")[:40]
        user = User.objects.create_user(email=email, first_name=first, last_name=last, lang=request.lang)
    if not user.is_active:
        return fail("err_blocked", 403)
    resp = second_step(request, user, False, "")
    return JsonResponse({"ok": True, "next": resp.url})


# ---------------------------------------------------------------- password reset & phone verification (SMS)
def dev_code_note(request, code):
    """Console SMS backend + DEBUG: show the code on screen so the flow can be tried without an SMS account."""
    if code and dj.DEBUG and not sms.real_backend():
        messages.add_message(request, messages.INFO, f"DEV · SMS: {code}")


def forgot_view(request):
    class ForgotForm(forms.Form):
        phone = PhoneField(error_messages={"required": "err_fields"})
    form = ForgotForm(request.POST or None)
    error = None
    if request.method == "POST" and form.is_valid():
        phone = form.cleaned_data["phone"]
        user = User.objects.filter(phone=phone, is_active=True).first()
        if user:  # the answer is identical for unknown numbers, so this cannot be used to find who is registered
            code, err = sms.issue_otp(phone, "reset")
            if err == "err_rate":
                error = err
            else:
                dev_code_note(request, code)
        if not error:
            flash(request, messages.INFO, "otp_sent")
            return redirect(f"/reset/?phone={urllib.parse.quote(phone)}")
    return render(request, "gym/forgot.html", {"form": form, "error": error})


def reset_view(request):
    phone = normalize_phone(request.POST.get("phone") or request.GET.get("phone") or "")
    form = PasswordForm(request.POST or None)
    form.fields.pop("current")
    error = None
    if request.method == "POST" and form.is_valid():
        keys = (f"rl:reset:{request.META.get('REMOTE_ADDR')}",)
        user = User.objects.filter(phone=phone, is_active=True).first() if phone else None
        if not rl_check(*keys):
            error = "err_rate"
        elif user and sms.check_otp(phone, "reset", request.POST.get("code", "")):
            user.set_password(form.cleaned_data["new"])
            user.phone_verified = True
            user.save(update_fields=["password", "phone_verified"])
            flash(request, messages.SUCCESS, "reset_ok")
            return redirect("login")
        else:
            rl_fail(*keys)
            error = "otp_bad"
    return render(request, "gym/reset.html", {"form": form, "phone": phone or "", "error": error})


@login_required
def verify_view(request):
    u = request.user
    if not u.phone:
        flash(request, messages.INFO, "add_phone_first")
        return redirect("profile")
    if u.phone_verified:
        return redirect("profile")
    error = None
    if request.method == "POST":
        if request.POST.get("action") == "send":
            code, err = sms.issue_otp(u.phone, "verify")
            if err:
                error = err
            else:
                dev_code_note(request, code)
                flash(request, messages.INFO, "otp_sent")
                return redirect("verify")
        elif sms.check_otp(u.phone, "verify", request.POST.get("code", "")):
            u.phone_verified = True
            u.save(update_fields=["phone_verified"])
            flash(request, messages.SUCCESS, "verified_ok")
            return redirect("dashboard")
        else:
            error = "otp_bad"
    return render(request, "gym/verify.html", {"error": error})


# ---------------------------------------------------------------- trainers & personal training
def trainers_view(request):
    sessions = request.user.pt_sessions.exclude(status="cancelled").filter(starts__gte=timezone.now()).select_related("trainer") if request.user.is_authenticated else []
    return render(request, "gym/trainers.html", {"trainers": Trainer.objects.filter(active=True), "sessions": sessions})


def trainer_detail(request, pk):
    tr = get_object_or_404(Trainer, pk=pk, active=True)
    classes = [{"c": c, "wd": str(c.weekday)} for c in GymClass.objects.filter(active=True, trainer=tr)]
    return render(request, "gym/trainer_detail.html", {"tr": tr, "classes": classes})


def image_view(request, kind, pk):
    """Serves an uploaded product/trainer picture. The type is read from the file's bytes, and the response can never run as a page."""
    from .media import image_type
    model, field = {"product": (Product, "image"), "trainer": (Trainer, "photo"), "avatar": (User, "avatar")}.get(kind, (None, None))
    if not model:
        raise Http404()
    obj = get_object_or_404(model, pk=pk)
    f = getattr(obj, field)
    if not f:
        raise Http404()
    from .media import is_local
    if not is_local(f):  # Cloudinary: the picture comes straight from its CDN
        return redirect(f.url)
    try:
        fh = f.open("rb")
    except (FileNotFoundError, ValueError):
        raise Http404()
    ctype = image_type(fh.read(16))
    fh.seek(0)
    if not ctype:
        fh.close()
        raise Http404()
    from django.http import FileResponse
    resp = FileResponse(fh, content_type=ctype)
    resp["Cache-Control"] = "public, max-age=604800"  # the URL carries a version, so a new upload gets a new URL
    resp["X-Content-Type-Options"] = "nosniff"
    resp["Content-Security-Policy"] = "default-src 'none'; sandbox"
    return resp


@require_POST
@login_required
def pt_request(request, pk):
    tr = get_object_or_404(Trainer, pk=pk, active=True)
    starts = parse_datetime(request.POST.get("starts", ""))
    now = timezone.now()
    if starts is None:
        flash(request, messages.ERROR, "err_fields")
        return redirect("trainers")
    if timezone.is_naive(starts):
        starts = timezone.make_aware(starts)
    gs = GymSettings.load()
    local = timezone.localtime(starts).time()
    inside = (gs.open_time <= local < gs.close_time) if gs.open_time <= gs.close_time else (local >= gs.open_time or local < gs.close_time)
    pending = request.user.pt_sessions.filter(status="requested", starts__gte=now).count()
    if not (now + timedelta(hours=1) <= starts <= now + timedelta(days=60)) or not inside or pending >= 3:
        flash(request, messages.ERROR, "pt_bad")
        back = request.POST.get("back", "")
        return redirect(back if back.startswith("/trainers/") else "trainers")
    PTSession.objects.create(user=request.user, trainer=tr, starts=starts, note=request.POST.get("note", "")[:200])
    telegram.alert_admin(f"PT so'rovi: {request.user.full_name} → {tr.name}, {timezone.localtime(starts):%d.%m %H:%M}")
    flash(request, messages.SUCCESS, "pt_sent")
    back = request.POST.get("back", "")
    return redirect(back if back.startswith("/trainers/") else "trainers")


@require_POST
@login_required
def pt_cancel(request, pk):
    s = get_object_or_404(PTSession, pk=pk, user=request.user)
    s.status = PTSession.Status.CANCELLED
    s.save(update_fields=["status"])
    flash(request, messages.SUCCESS, "cancel_ok")
    return redirect("trainers")


# ---------------------------------------------------------------- member area
@login_required
def dashboard(request):
    u, now = request.user, timezone.now()
    m = services.active_membership(u)
    last = u.memberships.order_by("-expires").first()
    upcoming = u.memberships.filter(starts__gt=now).order_by("starts").first()
    days_left = pct = None
    if m:
        days_left = max(0, (m.expires - now).days)
        total = max(1, (m.expires - m.starts).days)
        pct = max(4, min(100, round(days_left / total * 100)))
    notes = []
    if m and days_left <= 5 and not upcoming:
        notes.append(("warn", translate(request.lang, "expiring", days=days_left)))
    pending = u.payments.filter(status=Payment.Status.PENDING)
    if pending.exists():
        notes.append(("info", translate(request.lang, "pending_card_note" if pending.filter(method="card").exists() else "pending_note")))
    if GymSettings.load().require_phone_verify and not u.phone_verified:
        notes.append(("warn", translate(request.lang, "verify_needed")))
    stats = services.visit_stats(u)
    today_ex = ExerciseLog.objects.none()
    plan = u.workout_plans.filter(active=True).first()
    todays = plan.exercises.filter(weekday=timezone.localdate().weekday()).count() if plan else 0
    done_today = ExerciseLog.objects.filter(user=u, date=timezone.localdate()).count() if plan else 0
    today = timezone.localdate()
    # 12-week activity map (Monday-first columns), like a contributions calendar
    vdays = services.visit_days(u)
    start = today - timedelta(days=today.weekday() + 7 * 11)
    heat = [[{"d": start + timedelta(days=w * 7 + i), "on": (start + timedelta(days=w * 7 + i)) in vdays,
              "future": start + timedelta(days=w * 7 + i) > today} for i in range(7)] for w in range(12)]
    # weight trend sparkline from the last body measurements
    logs = list(u.bodylogs.order_by("-date", "-id")[:8])[::-1]
    spark, w_change = "", None
    if len(logs) >= 2:
        ws = [float(x.weight) for x in logs]
        lo, hi = min(ws), max(ws)
        span = (hi - lo) or 1
        spark = " ".join(f"{round(i / (len(ws) - 1) * 100, 1)},{round(90 - (w - lo) / span * 80, 1)}" for i, w in enumerate(ws))
        w_change = round(ws[-1] - ws[0], 1)
    nxt = u.bookings.filter(date__gte=today).select_related("gym_class").order_by("date", "gym_class__start_time").first()
    next_at = None
    if nxt:
        next_at = timezone.make_aware(datetime.combine(nxt.date, nxt.gym_class.start_time))
        if next_at < now:
            next_at = None
    return render(request, "gym/dashboard.html", {
        "heat": heat, "spark": spark, "w_change": w_change, "w_last": logs[-1].weight if logs else None,
        "next_booking": nxt if next_at else None,
        "next_at": next_at.isoformat() if next_at else "", "crowd": crowd_level(), "stats_total": stats["total"],
        "m": m, "last": last, "upcoming": upcoming, "days_left": days_left, "pct": pct, "stats": stats, "notes": notes,
        "announcements": Announcement.objects.filter(active=True)[:3],
        "bookings": u.bookings.filter(date__gte=timezone.localdate()).select_related("gym_class", "gym_class__trainer")[:5],
        "can_enter": services.can_enter(u), "points": services.points(u),
        "referral_url": request.build_absolute_uri(reverse("register")) + f"?ref={u.referral_code}",
        "referred": u.referrals.count(), "referred_ok": u.referrals.filter(referral_rewarded=True).count(),
        "bonus_days": GymSettings.load().referral_bonus_days, "todays": todays, "done_today": done_today,
    })


@require_POST
@login_required
def checkin(request):
    if services.check_in(request.user):
        flash(request, messages.SUCCESS, "check_ok")
    else:
        m = services.active_membership(request.user)
        flash(request, messages.ERROR, "err_frozen" if m else "err_member")
    return redirect("dashboard")


@login_required
def card_view(request):
    code = services.card_token(request.user)
    q = segno.make(code, error="m")
    svg = q.svg_inline(scale=7, border=2, dark="#111111", light="#ffffff")
    modules = ",".join("".join("1" if v else "0" for v in row) for row in q.matrix)  # for the 3D view: one string per row
    return render(request, "gym/card.html", {"qr": mark_safe(svg), "code": code, "m": services.active_membership(request.user), "modules": modules})


@login_required
def achievements_view(request):
    ach = services.achievements(request.user)
    return render(request, "gym/achievements.html", {"ach": ach, "got": sum(a["got"] for a in ach), "points": services.points(request.user),
                                                     "board": services.leaderboard(), "stats": services.visit_stats(request.user)})


@login_required
def workouts_view(request):
    plan = request.user.workout_plans.filter(active=True).order_by("-created").first()
    days, today = [], timezone.localdate()
    week_start = today - timedelta(days=today.weekday())
    strip, week_total, week_done = [], 0, 0
    if plan:
        done_today = set(ExerciseLog.objects.filter(user=request.user, date=today).values_list("exercise_id", flat=True))
        done_week = {}
        for d, eid in ExerciseLog.objects.filter(user=request.user, date__gte=week_start, exercise__plan=plan).values_list("date", "exercise_id"):
            done_week.setdefault(d.weekday(), set()).add(eid)
        for wd in range(7):
            exs = list(plan.exercises.filter(weekday=wd))
            n_done = len(done_week.get(wd, set()))
            strip.append({"wd": str(wd), "today": wd == today.weekday(), "total": len(exs), "done": n_done, "past": wd < today.weekday(),
                          "pct": round(n_done / len(exs) * 100) if exs else 0})
            week_total += len(exs)
            week_done += n_done
            if exs:
                days.append({"wd": str(wd), "today": wd == today.weekday(), "ex": [{"e": e, "done": e.id in done_today} for e in exs]})
        days.sort(key=lambda x: (not x["today"], (int(x["wd"]) - today.weekday()) % 7))  # today first, then the coming days
    from_trainer = bool(plan and plan.trainer_id)
    return render(request, "gym/workouts.html", {
        "plan": plan, "days": days, "strip": strip, "from_trainer": from_trainer,
        "week_pct": round(week_done / week_total * 100) if week_total else 0, "week_done": week_done, "week_total": week_total,
        "programs": [{"key": k, **{x: v[x] for x in ("title", "days", "about", "emoji", "level")}, "count": len({e[1] for e in v["ex"]})}
                     for k, v in services.PROGRAMS.items()],
    })


@require_POST
@login_required
def workout_toggle(request, pk):
    ex = get_object_or_404(Exercise, pk=pk, plan__user=request.user)
    today = timezone.localdate()
    log, created = ExerciseLog.objects.get_or_create(user=request.user, exercise=ex, date=today)
    if not created:
        log.delete()
    elif ex.weekday == today.weekday():
        todays = set(ex.plan.exercises.filter(weekday=today.weekday()).values_list("id", flat=True))
        done = set(ExerciseLog.objects.filter(user=request.user, date=today, exercise_id__in=todays).values_list("exercise_id", flat=True))
        if todays and todays == done:
            flash(request, messages.SUCCESS, "workout_all_done")  # the confetti moment
    return redirect("workouts")


@require_POST
@login_required
def start_program(request, key):
    if services.start_program(request.user, key):
        flash(request, messages.SUCCESS, "program_started")
    else:
        flash(request, messages.ERROR, "program_trainer")
    return redirect("workouts")


@require_POST
@login_required
def stop_plan(request):
    request.user.workout_plans.filter(active=True, trainer__isnull=True).update(active=False)  # a trainer's plan stays
    return redirect("workouts")


@login_required
def notifications_view(request):
    """The member's inbox: personal messages from the gym. Opening it marks everything as read."""
    from .models import Notification
    items = list(Notification.objects.filter(user=request.user).select_related("sender")[:100])
    unread_ids = [n.pk for n in items if not n.read_at]
    if unread_ids:
        Notification.objects.filter(pk__in=unread_ids).update(read_at=timezone.now())
    return render(request, "gym/notifications.html", {"items": items, "unread_ids": set(unread_ids)})


def tools_view(request):
    """Fitness calculators (BMI, calories, macros, 1RM, water, heart-rate zones). They run in the browser; for members
    the form starts from their latest measurements."""
    last = request.user.bodylogs.order_by("-date", "-id").first() if request.user.is_authenticated else None
    return render(request, "gym/tools.html", {"w": float(last.weight) if last else "", "h": last.height_cm if last and last.height_cm else ""})


@login_required
def records_view(request):
    from .models import PersonalRecord
    if request.method == "POST":
        lift = request.POST.get("lift", "")
        try:
            weight, reps = float(request.POST.get("weight", "").replace(",", ".")), int(request.POST.get("reps", "1"))
        except ValueError:
            weight, reps = -1, 0
        if lift not in dict(PersonalRecord.LIFTS) or not (0 <= weight <= 500) or not (1 <= reps <= 30):
            flash(request, messages.ERROR, "record_bad")
            return redirect("records")
        prev = max((r.one_rm for r in PersonalRecord.objects.filter(user=request.user, lift=lift)), default=0)
        rec = PersonalRecord.objects.create(user=request.user, lift=lift, weight=round(weight, 1), reps=reps)
        flash(request, messages.SUCCESS if rec.one_rm > prev else messages.INFO, "record_new" if rec.one_rm > prev else "record_saved")
        return redirect("records")
    recs = list(PersonalRecord.objects.filter(user=request.user))
    lifts = []
    for key, label in PersonalRecord.LIFTS:
        mine = sorted((r for r in recs if r.lift == key), key=lambda r: (r.date, r.id))
        if not mine:
            lifts.append({"key": key, "label": label, "best": None})
            continue
        best = max(mine, key=lambda r: r.one_rm)
        lo, hi = min(r.one_rm for r in mine), max(r.one_rm for r in mine)
        span = (hi - lo) or 1
        pts = " ".join(f"{round(i / max(1, len(mine) - 1) * 100, 1)},{round(90 - (r.one_rm - lo) / span * 80, 1)}" for i, r in enumerate(mine[-10:]))
        lifts.append({"key": key, "label": label, "best": best, "n": len(mine), "spark": pts if len(mine) > 1 else "",
                      "gain": round(mine[-1].one_rm - mine[0].one_rm, 1) if len(mine) > 1 else 0})
    return render(request, "gym/records.html", {"lifts": lifts, "recent": recs[:12], "choices": PersonalRecord.LIFTS})


@require_POST
@login_required
def record_delete(request, pk):
    from .models import PersonalRecord
    get_object_or_404(PersonalRecord, pk=pk, user=request.user).delete()
    return redirect("records")


def pay_tiles(gs):
    """The payment choices of the plan form as tiles: what works now is selectable, the rest is shown as "soon"."""
    ok = set(allowed_methods(gs))
    rows = [("cash", "cash", "cash"), ("Payme", "Payme", "payme"), ("Click", "Click", "click"), ("Uzum", "Uzum", "uzum")]
    tiles = [{"value": v, "label": lab, "brand": b, "ok": v in ok} for v, lab, b in rows]
    if "click" in ok:  # the real Click gateway replaces the demo tile
        tiles[2].update(value="click", ok=True)
    if "card" in ok:
        tiles.append({"value": "card", "label": "card", "brand": "card", "ok": True})
    return tiles


def plans_view(request):
    gs = GymSettings.load()
    m = services.active_membership(request.user) if request.user.is_authenticated else None
    return render(request, "gym/plans.html", {
        "plans": Plan.objects.filter(active=True), "methods": allowed_methods(gs), "pay_tiles": pay_tiles(gs), "m": m,
        "max_freeze": gs.freeze_max_days, "freeze_options": [d for d in (7, 14, 30) if d <= gs.freeze_max_days],
    })


@require_POST
def buy_plan(request, code):
    if not request.user.is_authenticated:
        flash(request, messages.INFO, "login_first")
        return redirect("/login/?next=/plans/")
    gate = verify_gate(request)
    if gate:
        return gate
    plan = get_object_or_404(Plan, code=code, active=True)
    method = request.POST.get("method")
    if method not in allowed_methods(GymSettings.load()):
        flash(request, messages.ERROR, "err_method")
        return redirect("plans")
    pay, err = services.buy_plan(request.user, plan, method, request.POST.get("promo", ""))
    if err:
        flash(request, messages.ERROR, err)
        return redirect("plans")
    if method == "click":
        return redirect(click.pay_url(pay, abs_url(request, "dashboard")))
    if method == "card":
        return redirect("pay", pk=pay.pk)
    if pay.status == Payment.Status.PENDING:
        telegram.alert_admin(f"Yangi to'lov (tasdiq kutadi): {request.user.full_name} · {plan.name} · {pay.amount} so'm")
    flash(request, messages.SUCCESS, "bought_pending" if pay.status == Payment.Status.PENDING else "bought_paid")
    return redirect("dashboard")


def hero_video(request):
    """The home-page background clip uploaded in the settings (public, with Range support so it starts fast)."""
    gs = GymSettings.load()
    from .media import is_local
    if gs.hero_video and not is_local(gs.hero_video):
        return redirect(gs.hero_video.url)
    try:
        path = gs.hero_video.path if gs.hero_video else ""
    except ValueError:
        path = ""
    import os
    if not path or not os.path.isfile(path):
        raise Http404()
    resp = ranged_file_response(request, path, "video/webm" if path.lower().endswith(".webm") else "video/mp4")
    resp["Cache-Control"] = "public, max-age=86400"  # the URL carries the file name, so a new upload gets a new URL
    resp["X-Content-Type-Options"] = "nosniff"
    return resp


@csrf_exempt
@require_POST
def click_callback(request):
    return JsonResponse(click.handle(request.POST.dict()))


@require_POST
@login_required
def freeze_view(request):
    try:
        days = int(request.POST.get("days", 0))
    except ValueError:
        days = 0
    if 1 <= days <= GymSettings.load().freeze_max_days and services.freeze(request.user, days):
        flash(request, messages.SUCCESS, "freeze_ok")
    else:
        flash(request, messages.ERROR, "freeze_fail")
    return redirect("dashboard")


def shop(request):
    qs = Product.objects.filter(active=True).select_related("category")
    cat, q = request.GET.get("cat"), request.GET.get("q", "").strip()
    if cat and cat.isdigit():
        qs = qs.filter(category_id=int(cat))
    if q:
        qs = qs.filter(name__icontains=q)
    from django.core.paginator import Paginator
    page = Paginator(qs.order_by("category__order", "id"), SHOP_PAGE_SIZE).get_page(request.GET.get("page"))
    keep = urllib.parse.urlencode({k: v for k, v in (("cat", cat or ""), ("q", q)) if v})  # the pager links keep the filters
    return render(request, "gym/shop.html", {"products": page, "page": page, "pages": page_window(page), "keep": keep and keep + "&",
                                             "categories": Category.objects.all(), "cat": cat or "", "q": q,
                                             "popular": popular_ids(), **cart_context(request)})


SHOP_PAGE_SIZE = 20


def page_window(page, around=2):
    """Page numbers for the pager: first, last and a few around the current one; None marks a gap ("...")."""
    n, cur = page.paginator.num_pages, page.number
    nums = sorted({1, n, *range(max(1, cur - around), min(n, cur + around) + 1)})
    out, prev = [], 0
    for x in nums:
        if x - prev > 1:
            out.append(None)
        out.append(x)
        prev = x
    return out if n > 1 else []


def cart_context(request):
    """What the shop pages need to draw the − n + controls and the floating cart bar."""
    cart = request.session.get("cart", {})
    _, total = cart_items(request)
    return {"in_cart": {int(k): v for k, v in cart.items()}, "cart_total": total}


def local_back(request, default):
    """A same-site path from the form's "back" field, or the default. Rejects //other-site.com style tricks."""
    back = request.POST.get("back", "")
    return back if back.startswith("/") and url_has_allowed_host_and_scheme(back, {request.get_host()}) else default


def popular_ids(days=60, top=3):
    """The best sellers of the last two months get an "Ommabop" badge."""
    from django.db.models import Sum
    from .models import OrderItem
    since = timezone.now() - timedelta(days=days)
    rows = (OrderItem.objects.filter(order__created__gte=since, product__isnull=False).exclude(order__status="cancelled")
            .values("product_id").annotate(n=Sum("qty")).order_by("-n")[:top])
    return {r["product_id"] for r in rows}


def product_detail(request, pk):
    p = get_object_or_404(Product.objects.select_related("category"), pk=pk, active=True)
    related = Product.objects.filter(active=True, category=p.category).exclude(pk=p.pk)[:4] if p.category_id else []
    return render(request, "gym/product.html", {"p": p, "related": related, "popular": popular_ids(), **cart_context(request)})


def cart_items(request):
    cart, items, total = request.session.get("cart", {}), [], 0
    for pid, qty in cart.items():
        p = Product.objects.filter(pk=pid, active=True).first()
        if p:
            items.append({"p": p, "qty": qty, "sub": p.price * qty})
            total += p.price * qty
    return items, total


def cart_view(request):
    items, total = cart_items(request)
    gs = GymSettings.load()
    return render(request, "gym/cart.html", {"items": items, "total": total, "methods": allowed_methods(gs),
                                             "in_cart": {i["p"].pk: i["qty"] for i in items}})


CART_MAX = 50


def cart_reply(request, pid, error=None):
    """JSON for the shop's − n + controls: this product's quantity plus the cart totals for the badge and the bar."""
    cart = request.session.get("cart", {})
    items, total = cart_items(request)
    p = Product.objects.filter(pk=pid).first()
    qty = cart.get(str(pid), 0)
    return JsonResponse({"ok": error is None, "error": translate(request.lang, error) if error else "", "pid": pid, "qty": qty,
                         "max": min(p.stock, CART_MAX) if p else 0, "count": sum(cart.values()), "total": total,
                         "line": p.price * qty if p else 0})


def wants_json(request):
    return request.headers.get("X-Requested-With") == "fetch"


@require_POST
def cart_add(request, pid):
    p = get_object_or_404(Product, pk=pid, active=True)
    cart = request.session.get("cart", {})
    error = None
    if p.stock < 1:
        cart.pop(str(pid), None)
        error = "err_stock"
    elif cart.get(str(pid), 0) >= min(p.stock, CART_MAX):
        error = "cart_max"
    else:
        cart[str(pid)] = cart.get(str(pid), 0) + 1
    request.session["cart"] = cart
    if wants_json(request):
        return cart_reply(request, pid, error)
    if error:
        flash(request, messages.ERROR, error)
    return redirect(local_back(request, "shop"))


@require_POST
def cart_update(request, pid):
    cart = request.session.get("cart", {})
    try:
        qty = int(request.POST.get("qty", 0))
    except ValueError:
        qty = 0
    p = Product.objects.filter(pk=pid, active=True).first()
    error = None
    if qty <= 0 or not p:
        cart.pop(str(pid), None)
    else:
        limit = min(p.stock, CART_MAX)
        if qty > limit:
            error = "cart_max" if limit else "err_stock"
        cart[str(pid)] = min(qty, limit)
        if cart[str(pid)] < 1:
            cart.pop(str(pid))
    request.session["cart"] = cart
    if wants_json(request):
        return cart_reply(request, pid, error)
    return redirect(local_back(request, "cart"))


@require_POST
def checkout(request):
    if not request.user.is_authenticated:
        flash(request, messages.INFO, "login_first")
        return redirect("/login/?next=/cart/")
    gate = verify_gate(request)
    if gate:
        return gate
    method = request.POST.get("method")
    cart = {int(k): v for k, v in request.session.get("cart", {}).items()}
    if method not in allowed_methods(GymSettings.load()):
        flash(request, messages.ERROR, "err_method")
        return redirect("cart")
    if not cart:
        return redirect("cart")
    delivery = None
    if request.POST.get("delivery") == "courier":
        address = " ".join(request.POST.get("address", "").split())
        phone = normalize_phone(request.POST.get("delivery_phone", "")) or request.user.phone
        if len(address) < 8:
            flash(request, messages.ERROR, "err_address")
            return redirect("cart")
        if not phone:
            flash(request, messages.ERROR, "err_phone")
            return redirect("cart")
        delivery = {"address": address, "phone": phone, "note": request.POST.get("delivery_note", "").strip()}
    order, err = services.place_order(request.user, cart, method, delivery)
    if err:
        flash(request, messages.ERROR, err)
        return redirect("cart")
    if delivery:
        telegram.alert_admin(f"🛵 Yetkazish #{order.pk}: {order.total} so'm · {delivery['address']} · {delivery['phone']}")
    try:  # SMS to the owner when something runs low; a failing SMS provider must never break a paid checkout
        services.check_low_stock([it.product for it in order.items.select_related("product")])
    except Exception:
        logging.getLogger(__name__).exception("low stock alert failed")
    request.session["cart"] = {}
    if method == "click":
        return redirect(click.pay_url(order.payments.first(), abs_url(request, "orders")))
    if method == "card":
        return redirect("pay", pk=order.payments.first().pk)
    flash(request, messages.SUCCESS, "order_ok")
    return redirect("orders")


@login_required
def orders_view(request):
    return render(request, "gym/orders.html", {"orders": request.user.orders.prefetch_related("items")})


@login_required
def payments_view(request):
    return render(request, "gym/payments.html", {"payments": request.user.payments.select_related("plan", "order")})


@login_required
def pay_view(request, pk):
    """Instructions for a card transfer: which card, the exact amount, the reference to put in the transfer comment."""
    pay = get_object_or_404(Payment.objects.select_related("pay_card", "plan", "order"), pk=pk, user=request.user)
    if pay.status == Payment.Status.PAID:
        return redirect("receipt", pk=pay.pk)
    return render(request, "gym/pay.html", {"p": pay, "card": pay.pay_card, "deadline": pay.created + timedelta(hours=services.CARD_HOLD_HOURS),
                                            "items": pay.order.items.all() if pay.order else []})


@require_POST
@login_required
def pay_report(request, pk):
    pay = get_object_or_404(Payment, pk=pk, user=request.user)
    if services.report_transfer(pay, request.POST.get("sender_last4")):
        telegram.alert_admin(f"Karta o'tkazmasi: {request.user.full_name} · {pay.amount} so'm · {pay.reference} · jo'natuvchi ••••{pay.sender_last4}")
        flash(request, messages.SUCCESS, "report_sent")
    else:
        flash(request, messages.ERROR, "err_last4")
    return redirect("pay", pk=pay.pk)


@require_POST
@login_required
def pay_cancel(request, pk):
    pay = get_object_or_404(Payment, pk=pk, user=request.user)
    if not pay.proof_at and services.cancel_payment(pay):
        flash(request, messages.SUCCESS, "pay_cancelled")
        return redirect("payments")
    return redirect("pay", pk=pay.pk)


@login_required
def receipt(request, pk):
    pay = get_object_or_404(Payment.objects.select_related("user", "plan", "order"), pk=pk)
    if pay.user_id != request.user.id and not (request.user.is_staff and request.session.get("admin_mode")):
        raise Http404()
    return render(request, "gym/receipt.html", {"p": pay, "items": pay.order.items.all() if pay.order else []})


def classes_view(request):
    rows = []
    mine = set()
    if request.user.is_authenticated:
        mine = set(request.user.bookings.filter(date__gte=timezone.localdate()).values_list("gym_class_id", "date"))
    for c in GymClass.objects.filter(active=True).select_related("trainer"):
        d = c.next_date()
        rows.append({"c": c, "date": d, "left": services.seats_left(c, d), "booked": (c.id, d) in mine})
    by_day = [(str(i), [r for r in rows if r["c"].weekday == i]) for i in range(7)]
    return render(request, "gym/classes.html", {"by_day": [(i, rs) for i, rs in by_day if rs]})


@require_POST
@login_required
def book_class(request, pk):
    gate = verify_gate(request)
    if gate:
        return gate
    c = get_object_or_404(GymClass, pk=pk, active=True)
    if not services.can_enter(request.user):
        flash(request, messages.ERROR, "err_member")
        return redirect("classes")
    d = c.next_date()
    with transaction.atomic():
        full = services.seats_left(c, d) < 1
        if full or Booking.objects.filter(user=request.user, gym_class=c, date=d).exists():
            flash(request, messages.ERROR, "book_fail")
        else:
            Booking.objects.create(user=request.user, gym_class=c, date=d)
            flash(request, messages.SUCCESS, "book_ok")
    return redirect("classes")


@require_POST
@login_required
def cancel_booking(request, pk):
    get_object_or_404(Booking, pk=pk, user=request.user).delete()
    flash(request, messages.SUCCESS, "cancel_ok")
    return redirect(local_back(request, "dashboard"))


def bmi_label(v):
    return None if v is None else "bmi_low" if v < 18.5 else "bmi_ok" if v < 25 else "bmi_high" if v < 30 else "bmi_obese"


@login_required
def progress_view(request):
    last = request.user.bodylogs.exclude(height_cm=None).last()
    form = BodyLogForm(request.POST or None, initial={"height_cm": last.height_cm if last else None})
    if request.method == "POST" and form.is_valid():
        log = form.save(commit=False)
        log.user = request.user
        log.save()
        flash(request, messages.SUCCESS, "saved")
        return redirect("progress")
    logs = list(request.user.bodylogs.order_by("date", "id")[:120])
    chart = None
    if len(logs) >= 2:
        W, H, P = 640, 220, 34
        ws = [float(l.weight) for l in logs]
        lo, hi = min(ws) - 1, max(ws) + 1
        d0, d1 = logs[0].date.toordinal(), logs[-1].date.toordinal()
        span = max(1, d1 - d0)
        pts = [(P + (l.date.toordinal() - d0) / span * (W - 2 * P), H - P - (float(l.weight) - lo) / (hi - lo) * (H - 2 * P), l) for l in logs]
        chart = {"w": W, "h": H, "points": " ".join(f"{x:.1f},{y:.1f}" for x, y, _ in pts), "dots": [(round(x, 1), round(y, 1), l) for x, y, l in pts],
                 "lo": round(lo + 1, 1), "hi": round(hi - 1, 1), "y_lo": H - P, "y_hi": P, "delta": round(ws[-1] - ws[0], 1)}
    rows = [{"l": l, "bmi": l.bmi, "label": bmi_label(l.bmi)} for l in reversed(logs)]
    return render(request, "gym/progress.html", {"form": form, "chart": chart, "rows": rows})


@require_POST
@login_required
def progress_delete(request, pk):
    get_object_or_404(BodyLog, pk=pk, user=request.user).delete()
    return redirect("progress")


def reviews_view(request):
    approved = Review.objects.filter(approved=True).select_related("user")
    mine = request.user.reviews.first() if request.user.is_authenticated else None
    form = ReviewForm(request.POST or None, instance=mine)
    if request.method == "POST":
        if not request.user.is_authenticated:
            return redirect("/login/?next=/reviews/")
        if form.is_valid():
            r = form.save(commit=False)
            r.user, r.approved = request.user, False  # an edited review needs approval again
            r.save()
            flash(request, messages.SUCCESS, "review_ok")
            return redirect("reviews")
    agg = approved.aggregate(a=Avg("rating"), n=Count("id"))
    per = dict(approved.values_list("rating").annotate(c=Count("id")))
    dist = [{"stars": s, "n": per.get(s, 0), "pct": round(per.get(s, 0) / agg["n"] * 100) if agg["n"] else 0} for s in range(5, 0, -1)]
    raw = request.POST.get("rating", "")
    my_rating = int(raw) if raw.isdigit() else (mine.rating if mine else 5)
    return render(request, "gym/reviews.html", {"reviews": approved, "form": form, "mine": mine, "agg": agg, "dist": dist, "my_rating": my_rating})


@login_required
def profile_view(request):
    pform = ProfileForm(instance=request.user)
    wform = PasswordForm()
    if request.method == "POST":
        kind = request.POST.get("form")
        if kind == "profile":
            old_phone = request.user.phone
            pform = ProfileForm(request.POST, instance=request.user)
            if pform.is_valid():
                u = pform.save(commit=False)
                if u.phone != old_phone:
                    u.phone_verified = False  # a changed number has to be verified again
                u.show_in_leaderboard = bool(request.POST.get("show_in_leaderboard"))
                u.chat_visible = bool(request.POST.get("chat_visible"))
                u.save()
                flash(request, messages.SUCCESS, "saved")
                return redirect("profile")
        elif kind == "avatar":
            u = request.user
            if request.POST.get("remove"):
                if u.avatar:
                    try:
                        u.avatar.delete(save=False)
                    except OSError:  # e.g. the file is busy on Windows; the account no longer points to it either way
                        pass
                u.avatar = None
                u.save(update_fields=["avatar"])
                flash(request, messages.SUCCESS, "avatar_removed")
                return redirect("profile")
            f = request.FILES.get("avatar")
            from .media import validate_image
            try:
                if not f:
                    raise ValidationError("err_avatar")
                validate_image(f)
            except ValidationError:
                flash(request, messages.ERROR, "err_avatar")
                return redirect("profile")
            old = u.avatar.name if u.avatar else ""
            u.avatar = f
            u.save(update_fields=["avatar"])
            if old and old != u.avatar.name:
                try:
                    u.avatar.storage.delete(old)  # the previous picture is not kept around
                except OSError:
                    pass
            flash(request, messages.SUCCESS, "avatar_saved")
            return redirect("profile")
        elif kind == "telegram_unlink":
            User.objects.filter(pk=request.user.pk).update(telegram_chat_id=None)
            return redirect("profile")
        elif kind == "goals":
            u = request.user
            bd = safe_date(request.POST.get("birth_date"))
            today = timezone.localdate()
            # day arithmetic instead of year.replace(), which would crash on 29 February
            u.birth_date = bd if bd and today - timedelta(days=36525) < bd < today - timedelta(days=2922) else None
            u.goal = request.POST.get("goal", "") if request.POST.get("goal", "") in dict(User.GOALS) else ""
            try:
                tw = float(request.POST.get("target_weight", "").replace(",", ".") or 0)
            except ValueError:
                tw = 0
            u.target_weight = round(tw, 1) if 30 <= tw <= 250 else None
            u.save(update_fields=["birth_date", "goal", "target_weight"])
            flash(request, messages.SUCCESS, "pf_saved_goals")
            return redirect("/profile/#goals")
        else:
            wform = PasswordForm(request.POST)
            if wform.is_valid():
                u, key = request.user, f"rl:pw:{request.user.id}"
                if u.has_usable_password() and (not rl_check(key) or not u.check_password(wform.cleaned_data["current"])):
                    rl_fail(key)
                    wform.add_error("current", "err_wrong_pass")
                else:
                    u.set_password(wform.cleaned_data["new"])
                    u.save(update_fields=["password"])
                    update_session_auth_hash(request, u)
                    flash(request, messages.SUCCESS, "saved")
                    return redirect("profile")
    u = request.user
    last = u.bodylogs.order_by("-date", "-id").first()
    to_goal = round(float(last.weight) - float(u.target_weight), 1) if last and u.target_weight else None
    age = None
    if u.birth_date:
        t = timezone.localdate()
        age = t.year - u.birth_date.year - ((t.month, t.day) < (u.birth_date.month, u.birth_date.day))
    return render(request, "gym/profile.html", {
        "pform": pform, "wform": wform, "tg_url": telegram.link_url(u) if telegram.enabled() else "",
        "tg_linked": bool(u.telegram_chat_id), "sms_on": GymSettings.load().require_phone_verify or sms.real_backend(),
        "m": services.active_membership(u), "stats": services.visit_stats(u), "points": services.points(u), "last": last,
        "to_goal": to_goal, "age": age, "goals": User.GOALS, "referral_url": request.build_absolute_uri(reverse("register")) + f"?ref={u.referral_code}",
        "since_days": (timezone.now() - u.created).days,
    })


@require_POST
@login_required
def logout_others(request):
    """Signs this account out everywhere except this browser (lost phone, shared computer...)."""
    from django.contrib.sessions.models import Session
    keep, n = request.session.session_key, 0
    for s in Session.objects.filter(expire_date__gt=timezone.now()).exclude(session_key=keep).iterator():
        if str(s.get_decoded().get("_auth_user_id")) == str(request.user.pk):
            s.delete()
            n += 1
    flash(request, messages.SUCCESS, "sessions_closed", n=n)
    return redirect("/profile/#security")


@login_required
def export_my_data(request):
    """Everything the gym stores about the member, as one JSON file (their right to see their data)."""
    u = request.user
    data = {
        "member": {"code": u.member_code, "first_name": u.first_name, "last_name": u.last_name, "phone": u.phone, "email": u.email,
                   "joined": u.created.isoformat(), "birth_date": u.birth_date.isoformat() if u.birth_date else None, "goal": u.goal,
                   "target_weight": float(u.target_weight) if u.target_weight else None},
        "memberships": [{"plan": m.plan.name, "starts": m.starts.isoformat(), "expires": m.expires.isoformat()} for m in u.memberships.select_related("plan")],
        "payments": [{"id": p.pk, "amount": p.amount, "method": p.method, "status": p.status, "date": p.created.isoformat()} for p in u.payments.all()],
        "orders": [{"id": o.pk, "total": o.total, "status": o.status, "items": [[i.name, i.qty, i.price] for i in o.items.all()]} for o in u.orders.all()],
        "visits": [timezone.localtime(v.ts).isoformat() for v in u.visits.all()[:1000]],
        "body": [{"date": b.date.isoformat(), "weight": float(b.weight), "height_cm": b.height_cm} for b in u.bodylogs.all()],
        "records": [{"lift": r.lift, "weight": float(r.weight), "reps": r.reps, "date": r.date.isoformat()} for r in u.records.all()],
    }
    resp = JsonResponse(data, json_dumps_params={"ensure_ascii": False, "indent": 2})
    resp["Content-Disposition"] = f'attachment; filename="fitnes-zal-{u.member_code}.json"'
    return resp


# ---------------------------------------------------------------- staff front desk
@staff_required
def desk(request):
    q = request.GET.get("q", "").strip()
    results = []
    if q:
        card = services.user_from_card(q)
        if card and not card.is_superuser:  # the desk manages members; the owner's card is handled by the scanner page
            results = [card]
        else:
            cond = Q(first_name__icontains=q) | Q(last_name__icontains=q) | Q(email__icontains=q) | Q(username__icontains=q)
            digits = re.sub(r"\D", "", q)
            if digits:
                cond |= Q(phone__contains=digits)
            m = re.fullmatch(r"(?i)(?:fz-?)?0*(\d+)", q)
            if m:
                cond |= Q(pk=int(m.group(1)))
            results = list(User.objects.filter(cond, is_superuser=False).order_by("-id")[:20])
        for u in results:
            u.mem = services.active_membership(u)
    now = timezone.now()
    return render(request, "gym/staff/desk.html", {
        "q": q, "results": results, "plans": Plan.objects.filter(active=True), "today": timezone.localdate(),
        "pending": Payment.objects.filter(status=Payment.Status.PENDING).select_related("user", "plan")[:50],
        "new_orders": Order.objects.filter(status__in=(Order.Status.NEW, Order.Status.SHIPPING)).select_related("user").prefetch_related("items")[:50],
        "pt_requests": PTSession.objects.filter(status="requested", starts__gte=now).select_related("user", "trainer")[:30],
        "visits_today": Visit.objects.filter(ts__date=timezone.localdate()).count(),
        "active_members": Membership.objects.filter(starts__lte=now, expires__gt=now).values("user").distinct().count(),
        "recent_visits": Visit.objects.filter(ts__date=timezone.localdate()).select_related("user").order_by("-ts")[:12],
        "crowd": crowd_level(),
    })


def barcode_bars(text):
    """Decorative barcode for the printed ticket: bar/gap widths derived from the receipt number, so each ticket looks unique."""
    import hashlib
    digest = hashlib.sha256(text.encode()).digest()
    return [1 + b % 3 for b in digest[:30]]


def entry_ticket(request, **kw):
    """The entry receipt that "prints" on the scanner page. Rendered on the server so every value is escaped and translated."""
    now = timezone.localtime()
    ctx = {"gs": GymSettings.load(), "now": now, "staff": request.user, "lang": request.lang, **kw}
    ctx["bars"] = barcode_bars(ctx.get("no") or f"X-{now:%H%M%S}")
    return render_to_string("gym/staff/_ticket.html", ctx, request=request)


@staff_required
def scan_view(request):
    if request.method == "POST":
        code = json_field(request, "code")
        today = timezone.localdate()
        u = services.user_from_card(code)
        if not u:
            return JsonResponse({"ok": False, "error": translate(request.lang, "scan_bad")}, status=404)
        earlier = Visit.objects.filter(user=u, ts__date=today).order_by("ts").first()  # a second scan the same day is not a new visit
        entered = services.check_in(u)
        m = services.active_membership(u)
        # a refused entry never gets a receipt number, even if the member came in earlier today
        visit = (earlier or Visit.objects.filter(user=u, ts__date=today).first()) if entered else None
        reason = "" if entered else ("err_blocked" if not u.is_active else "err_frozen" if m else "err_member")
        now = timezone.localtime()
        ticket = entry_ticket(
            request, entered=entered, member=u, m=m, reason=reason,
            no=f"V-{visit.pk:06d}" if visit else "", repeat_at=timezone.localtime(earlier.ts) if earlier and entered else None,
            # calendar days, so a membership ending tomorrow says "1 day left", not "0"
            days_left=max(0, (timezone.localtime(m.expires).date() - today).days) if m else None,
            month_visits=Visit.objects.filter(user=u, ts__year=now.year, ts__month=now.month).count(),
            total_visits=Visit.objects.filter(user=u).count())
        return JsonResponse({"ok": True, "entered": entered, "name": u.full_name, "code": u.member_code,
                             "plan": m.plan.name if m else "", "until": timezone.localtime(m.expires).strftime("%d.%m.%Y") if m else "",
                             "message": translate(request.lang, "scan_ok" if entered else reason), "ticket": ticket,
                             "today": Visit.objects.filter(ts__date=today).count()})
    return render(request, "gym/staff/scan.html", {"today_count": Visit.objects.filter(ts__date=timezone.localdate()).count()})


def desk_back(request):
    return redirect(request.POST.get("back") if url_has_allowed_host_and_scheme(request.POST.get("back", ""), {request.get_host()}) else "desk")


@require_POST
@staff_required
def desk_checkin(request, uid):
    u = get_object_or_404(User, pk=uid, is_superuser=False)
    ok = services.check_in(u)
    flash(request, messages.SUCCESS if ok else messages.ERROR, "check_ok" if ok else "err_member")
    return desk_back(request)


@require_POST
@staff_required
def desk_sell(request, uid):
    u = get_object_or_404(User, pk=uid, is_superuser=False)
    plan = get_object_or_404(Plan, code=request.POST.get("plan"), active=True)
    with transaction.atomic():
        Payment.objects.create(user=u, kind="plan", plan=plan, amount=plan.price, method="cash", status=Payment.Status.PAID)
        services.add_membership(u, plan)
    flash(request, messages.SUCCESS, "done_ok")
    return desk_back(request)


@require_POST
@staff_required
def desk_confirm(request, pid):
    services.confirm_payment(get_object_or_404(Payment, pk=pid))
    flash(request, messages.SUCCESS, "done_ok")
    return desk_back(request)


@require_POST
@staff_required
def desk_reject(request, pid):
    services.cancel_payment(get_object_or_404(Payment, pk=pid), notify=True)
    flash(request, messages.SUCCESS, "done_ok")
    return desk_back(request)


@require_POST
@staff_required
def desk_ship(request, oid):
    if services.ship_order(get_object_or_404(Order, pk=oid)):
        flash(request, messages.SUCCESS, "done_ok")
    return desk_back(request)


@require_POST
@staff_required
def desk_handover(request, oid):
    services.hand_over(get_object_or_404(Order, pk=oid))
    flash(request, messages.SUCCESS, "done_ok")
    return desk_back(request)


@require_POST
@staff_required
def desk_block(request, uid):
    u = get_object_or_404(User, pk=uid, is_superuser=False)
    u.is_active = not u.is_active
    u.save(update_fields=["is_active"])
    return desk_back(request)


@require_POST
@staff_required
def desk_pt(request, pk, action):
    s = get_object_or_404(PTSession, pk=pk)
    if action == "confirm":
        s.status = PTSession.Status.CONFIRMED
        telegram.notify_user(s.user, "tg_pt_confirmed", trainer=s.trainer.name, time=timezone.localtime(s.starts).strftime("%d.%m %H:%M"))
    else:
        s.status = PTSession.Status.CANCELLED
        telegram.notify_user(s.user, "tg_pt_cancelled", trainer=s.trainer.name)
    s.save(update_fields=["status"])
    flash(request, messages.SUCCESS, "done_ok")
    return desk_back(request)


# ---------------------------------------------------------------- AI coach and AI workout plans
def ai_view(request):
    """The AI coach page: the conversation, a question box and the plan generator. Guests see what it does and a sign-in button."""
    from . import ai
    ctx = {"ai_on": ai.enabled(), "limit": ai.daily_limit(), "levels": [("beginner", "level_beginner"), ("intermediate", "level_intermediate"),
                                                                          ("advanced", "level_advanced")]}
    if request.user.is_authenticated:
        ctx.update({"chat": request.user.ai_messages.order_by("-id")[:40][::-1], "used": ai.used_today(request.user),
                    "has_trainer_plan": request.user.workout_plans.filter(active=True, trainer__isnull=False).exists()})
    return render(request, "gym/ai.html", ctx)


@require_POST
@login_required
def ai_ask(request):
    from . import ai
    try:
        msg = ai.ask(request.user, request.POST.get("q", ""), request.lang)
    except ai.AIError as e:
        if wants_json(request):
            return JsonResponse({"ok": False, "error": translate(request.lang, e.key)}, status=400)
        flash(request, messages.ERROR, e.key)
        return redirect("/ai/#chat")
    if wants_json(request):
        return JsonResponse({"ok": True, "answer": msg.content, "used": ai.used_today(request.user), "limit": ai.daily_limit()})
    return redirect("/ai/#chat")


@require_POST
@login_required
def ai_plan(request):
    from . import ai
    try:
        days = max(2, min(6, int(request.POST.get("days", 3))))
        minutes = max(20, min(120, int(request.POST.get("minutes", 60))))
    except ValueError:
        days, minutes = 3, 60
    try:
        ai.make_plan(request.user, request.POST.get("level", "beginner"), days, minutes, request.POST.get("notes", ""), request.lang)
    except ai.AIError as e:
        flash(request, messages.ERROR, e.key)
        return redirect("/ai/#plan")
    flash(request, messages.SUCCESS, "ai_plan_ok")
    return redirect("workouts")


@require_POST
@login_required
def ai_clear(request):
    request.user.ai_messages.all().delete()
    return redirect("/ai/#chat")


@login_required
def account_view(request):
    """Account settings: username, e-mail, shown name, phone, profile picture and password on one page (one Save button)."""
    from .media import validate_image
    u = request.user
    form = AccountForm(request.POST or None, instance=u)
    pw_errors, photo_error = [], None
    if request.method == "POST":
        current, new = request.POST.get("current_password", ""), request.POST.get("new_password", "")
        if new:  # the password changes only when a new one is typed
            key = f"rl:pw:{u.pk}"
            if len(new) < 6 or len(new) > 128:
                pw_errors.append("err_pass")
            elif u.has_usable_password() and (not rl_check(key) or not u.check_password(current)):
                rl_fail(key)
                pw_errors.append("err_wrong_pass")
        upload = request.FILES.get("avatar")
        if upload:
            try:
                validate_image(upload)
            except ValidationError:
                photo_error = "err_avatar"
        if form.is_valid() and not pw_errors and not photo_error:
            old_phone, old_photo = User.objects.get(pk=u.pk).phone, u.avatar.name if u.avatar else ""
            user = form.save(commit=False)
            if user.phone != old_phone:
                user.phone_verified = False  # a changed number has to be verified again
            if upload:
                user.avatar = upload
            elif request.POST.get("avatar_clear"):
                user.avatar = None
            if new:
                user.set_password(new)
            user.save()
            if old_photo and old_photo != (user.avatar.name if user.avatar else ""):
                try:
                    default_storage_for(user).delete(old_photo)
                except OSError:
                    pass
            if new:
                update_session_auth_hash(request, user)  # stay signed in on this device after a password change
            flash(request, messages.SUCCESS, "account_saved")
            return redirect("account")
    role = "admin" if u.is_superuser else "trainer" if Trainer.objects.filter(user=u, active=True).exists() else "member"
    return render(request, "gym/account.html", {"form": form, "pw_errors": pw_errors, "photo_error": photo_error, "role": role})


def default_storage_for(user):
    return user._meta.get_field("avatar").storage


# ---------------------------------------------------------------- calorie tracker

@login_required
def calories_view(request):
    from . import ai, calories
    day = calories.parse_day(request.GET.get("d"))
    today = timezone.localdate()
    ctx = calories.day_summary(request.user, day)
    ctx.update({"foods": calories.food_table(), "ai_on": ai.enabled(), "is_today": day == today,
                "prev_day": day - timedelta(days=1), "next_day": day + timedelta(days=1) if day < today else None,
                "meal_choices": [(m, calories.MEAL_ICON[m]) for m in calories.MEALS], "ai_left": max(0, ai.daily_limit() - ai.used_today(request.user)),
                "default_meal": _meal_now()})
    return render(request, "gym/calories.html", ctx)


def _meal_now():
    h = timezone.localtime().hour
    return "breakfast" if h < 11 else "lunch" if h < 16 else "dinner" if h < 21 else "snack"


def _decimal(raw, hi=6000):
    from decimal import Decimal, InvalidOperation
    try:
        d = Decimal(str(raw).replace(",", ".").strip() or "0")
    except InvalidOperation:
        return None
    return d.quantize(Decimal("0.1")) if 0 <= d <= hi else None


@require_POST
@login_required
def calories_add(request):
    """Adds one entry: either a food from the built-in table + grams, or a typed name with its own numbers."""
    from . import calories
    day = calories.parse_day(request.POST.get("d"))
    meal = request.POST.get("meal") if request.POST.get("meal") in calories.MEALS else "snack"
    back = redirect(f"{reverse('calories')}?d={day.isoformat()}")
    try:
        grams = int(request.POST.get("grams", ""))
    except ValueError:
        grams = 0
    if not 1 <= grams <= 5000:
        flash(request, messages.ERROR, "cal_bad_grams")
        return back
    idx = request.POST.get("food", "")
    if idx.isdigit() and int(idx) < len(calories.FOODS):
        food = calories.FOODS[int(idx)]
        kcal, p, f, c = calories.per_portion(food, grams)
        name = food[0]
    else:
        name = " ".join(request.POST.get("name", "").split())[:80]
        kcal, p, f, c = (_decimal(request.POST.get(k, "0")) for k in ("kcal", "protein", "fat", "carbs"))
        if not name or kcal is None or p is None or f is None or c is None:
            flash(request, messages.ERROR, "cal_bad_food")
            return back
    request.user.food_entries.create(date=day, meal=meal, name=name, grams=grams, kcal=kcal, protein=p, fat=f, carbs=c)
    flash(request, messages.SUCCESS, "cal_added")
    return back


@require_POST
@login_required
def calories_delete(request, pk):
    entry = get_object_or_404(request.user.food_entries, pk=pk)
    day = entry.date
    entry.delete()
    return redirect(f"{reverse('calories')}?d={day.isoformat()}")


@require_POST
@login_required
def calories_ai(request):
    """Free text -> AI estimate -> saved as entries of the chosen meal (JSON for the fetch call, redirect otherwise)."""
    from . import ai, calories
    day = calories.parse_day(request.POST.get("d"))
    meal = request.POST.get("meal") if request.POST.get("meal") in calories.MEALS else "snack"
    try:
        items = calories.estimate(request.user, request.POST.get("text", ""), request.lang)
    except ai.AIError as e:
        if wants_json(request):
            return JsonResponse({"ok": False, "error": translate(request.lang, e.key)}, status=400)
        flash(request, messages.ERROR, e.key)
        return redirect(f"{reverse('calories')}?d={day.isoformat()}")
    request.user.food_entries.bulk_create([request.user.food_entries.model(user=request.user, date=day, meal=meal, **it) for it in items])
    if wants_json(request):
        return JsonResponse({"ok": True, "n": len(items)})
    flash(request, messages.SUCCESS, "cal_added")
    return redirect(f"{reverse('calories')}?d={day.isoformat()}")
