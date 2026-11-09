"""Qabulxona (front desk) inside the admin panel: /django-admin/desk/...

Every view here is registered by GymAdminSite.get_urls (so it gets the admin sidebar, top bar, theme and the staff + admin-mode
check). The pages are server-rendered; the small JSON endpoints answer {"ok": true, ...} or {"ok": false, "error": "..."} with a
proper status code, and member panels travel as HTML that was rendered (and escaped) on the server."""
import hashlib
import json
import re
import secrets
from datetime import timedelta

import segno
from django.contrib import admin
from django.core.cache import cache
from django.db import IntegrityError, transaction
from django.db.models import Count, Q, Sum
from django.http import Http404, HttpResponsePermanentRedirect, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.safestring import mark_safe

from . import extras, services, telegram
from .forms import normalize_phone
from .models import (Booking, ClassWaitlist, EntryLog, GuestPass, GymClass, GymSettings, Order, Payment, Plan, PTSession, User, Visit)
from .templatetags.gym_tags import translate
from .views import barcode_bars, crowd_level, entry_ticket, safe_date  # noqa: F401

METHODS = {"cash": "Naqd pul", "card": "Karta o'tkazmasi", "click": "Click", "gift": "Sertifikat"}
REASON_LABELS = dict(EntryLog.REASONS)
SOON_DAYS = 7  # a membership with this many days (or fewer) left is shown as "expiring"


# ---------------------------------------------------------------- small helpers
def ok(**kw):
    return JsonResponse({"ok": True, **kw})


def fail(error, status=400, **kw):
    return JsonResponse({"ok": False, "error": error, **kw}, status=status)


def body_of(request):
    """The POST fields from a JSON body or from a form post."""
    if (request.content_type or "").startswith("application/json"):
        try:
            data = json.loads(request.body or b"{}")
        except ValueError:
            return {}
        return data if isinstance(data, dict) else {}
    return {k: v for k, v in request.POST.items()}


def text_of(data, key, limit=120):
    v = data.get(key, "")
    return " ".join(v.split())[:limit] if isinstance(v, str) else ""


def post_only(view):
    def wrapper(request, *a, **kw):
        if request.method != "POST":
            return fail("Faqat POST so'rov qabul qilinadi.", 405)
        return view(request, *a, **kw)
    wrapper.__name__ = view.__name__
    return wrapper


def get_member(pk):
    """A member account the desk may handle (never the owner's superuser account)."""
    u = User.objects.filter(pk=pk, is_superuser=False).first()
    if not u:
        raise Http404("Bunday a'zo yo'q")
    return u


def money_text(v):
    return f"{int(v or 0):,}".replace(",", " ")


def initials_of(u):
    return ((u.first_name or "")[:1] + (u.last_name or "")[:1]).upper() or (u.username or "?")[:1].upper()


# ---------------------------------------------------------------- search
def search_users(q, limit=8):
    """Name (every word must match), phone digits, FZ-0012 code, e-mail/login, or the text of a member's QR card."""
    q = (q or "").strip()
    if not q:
        return []
    card = services.user_from_card(q)
    if card:
        return [] if card.is_superuser else [card]
    cond = Q()
    words = q.split()
    name_cond = Q()
    for w in words:
        name_cond &= Q(first_name__icontains=w) | Q(last_name__icontains=w) | Q(username__icontains=w) | Q(email__icontains=w)
    cond |= name_cond
    digits = re.sub(r"\D", "", q)
    if len(digits) >= 3 and re.fullmatch(r"[\d\s+()-]+", q):
        cond |= Q(phone__contains=digits)
    m = re.fullmatch(r"(?i)(?:fz-?)?0*(\d+)", q)
    if m:
        cond |= Q(pk=int(m.group(1)))
    return list(User.objects.filter(cond, is_superuser=False).order_by("first_name", "-id")[:limit])


def search_limited(request):
    """True when this staff member already searched 40 times in the last 10 seconds (typing is debounced, so that is a lot)."""
    key = f"dk:rl:{request.user.pk}"
    cache.add(key, 0, 10)
    try:
        return cache.incr(key) > 40
    except ValueError:
        cache.set(key, 1, 10)
        return False


# ---------------------------------------------------------------- a member's state
def member_state(u):
    """Everything the member panel shows, as plain values."""
    today = timezone.localdate()
    m = services.active_membership(u)
    last = u.memberships.select_related("plan").order_by("-expires").first()
    st = {"key": "none", "label": "Abonement yo'q", "tone": "mute", "m": m, "last": last, "days_left": None, "pct": 0, "total": 0}
    if m:
        st["days_left"] = max(0, (timezone.localtime(m.expires).date() - today).days)
        st["total"] = max(1, (m.expires - m.starts).days)
        st["pct"] = max(3, min(100, round(st["days_left"] / st["total"] * 100)))
    if not u.is_active:
        st.update(key="blocked", label="Bloklangan", tone="bad")
    elif m and m.is_frozen:
        st.update(key="frozen", label="Muzlatilgan", tone="info")
    elif m:
        soon = st["days_left"] <= SOON_DAYS
        st.update(key="expiring" if soon else "active", label="Tugayapti" if soon else "Faol", tone="warn" if soon else "good")
    elif last:
        st.update(key="expired", label="Tugagan", tone="bad")
    return st


def member_row(u):
    st = member_state(u)
    return {"id": u.pk, "name": u.full_name, "code": u.member_code, "phone": u.phone or "", "initials": initials_of(u),
            "status": st["key"], "label": st["label"], "tone": st["tone"],
            "plan": st["m"].plan.name if st["m"] else (st["last"].plan.name if st["last"] else ""),
            "days_left": st["days_left"]}


def member_html(request, u, **extra):
    st = member_state(u)
    plans = list(Plan.objects.filter(active=True))
    renew = extras.renew_plan(u)
    ctx = {"u": u, "st": st, "initials": initials_of(u), "plans": plans, "renew": renew, "freeze": extras.freeze_info(u),
           "refusal": REASON_LABELS.get(extras.entry_refusal(u), ""), "can_enter": services.can_enter(u),
           "recent": EntryLog.objects.filter(user=u).select_related("staff")[:5],
           "pending": Payment.objects.filter(user=u, status=Payment.Status.PENDING).select_related("plan"),
           "month_visits": Visit.objects.filter(user=u, ts__year=timezone.localdate().year, ts__month=timezone.localdate().month).count(),
           "total_visits": Visit.objects.filter(user=u).count(), "today_in": Visit.objects.filter(user=u, ts__date=timezone.localdate()).exists(),
           "methods": [("cash", "Naqd pul"), ("card", "Karta o'tkazmasi")], "freeze_days": [7, 14, 30], **extra}
    return render_to_string("admin/desk/_member.html", ctx, request=request)


def member_reply(request, u, message="", **kw):
    return ok(message=message, id=u.pk, html=member_html(request, u), **kw)


# ---------------------------------------------------------------- entry (shared by the desk button and the QR scanner)
def banner_for(request, u, entered, repeat_at=None):
    m = services.active_membership(u)
    reason = "" if entered else extras.entry_refusal(u) or "no_membership"
    label = REASON_LABELS.get(reason, "")
    if reason == "frozen" and m and m.frozen_until:
        label += f" ({timezone.localtime(m.frozen_until):%d.%m.%Y} gacha)"
    return {"entered": entered, "name": u.full_name, "code": u.member_code, "plan": m.plan.name if m else "",
            "until": f"{timezone.localtime(m.expires):%d.%m.%Y}" if m else "", "reason": reason, "reason_label": label,
            "title": "Kirishga ruxsat" if entered else "Kirish taqiqlangan",
            "note": f"Bugun {timezone.localtime(repeat_at):%H:%M} da kirgan" if (entered and repeat_at) else ""}


def do_entry(request, u, method):
    """Check a member in (one Visit per day), write the EntryLog row with the staff member. Returns (entered, banner, earlier_visit)."""
    today = timezone.localdate()
    earlier = Visit.objects.filter(user=u, ts__date=today).order_by("ts").first()  # a second pass the same day is not a new visit
    refusal = extras.entry_refusal(u)
    entered = services.check_in(u)
    extras.log_entry(method, u, entered=entered, reason=refusal or "no_membership", repeat=bool(earlier), staff=request.user)
    return entered, banner_for(request, u, entered, earlier.ts if earlier else None), earlier


# ---------------------------------------------------------------- today's numbers
def shift_summary(day, staff=None):
    paid = Payment.objects.filter(status=Payment.Status.PAID, created__date=day)
    by_method = []
    for r in paid.values("method").annotate(n=Count("id"), s=Sum("amount")).order_by("-s"):
        by_method.append({"method": r["method"], "label": METHODS.get(r["method"], r["method"]), "n": r["n"], "sum": r["s"] or 0})
    total = sum(r["sum"] for r in by_method)
    plans = paid.filter(kind="plan")
    mine = paid.filter(staff=staff).aggregate(s=Sum("amount"), n=Count("id")) if staff else {"s": 0, "n": 0}
    by_staff = [{"name": (r["staff__first_name"] or r["staff__username"] or "—"), "n": r["n"], "sum": r["s"] or 0}
                for r in paid.filter(staff__isnull=False).values("staff__first_name", "staff__username").annotate(n=Count("id"), s=Sum("amount")).order_by("-s")]
    cash = next((r["sum"] for r in by_method if r["method"] == "cash"), 0)
    return {"day": day, "by_method": by_method, "total": total, "count": sum(r["n"] for r in by_method), "cash": cash,
            "sold": plans.count(), "sold_sum": plans.aggregate(s=Sum("amount"))["s"] or 0,
            "entries": Visit.objects.filter(ts__date=day).count(),
            "rejected": EntryLog.objects.filter(ts__date=day, result="rejected").count(),
            "guest_entries": GuestPass.objects.filter(used_at__date=day).count(),
            "mine": mine["s"] or 0, "mine_n": mine["n"] or 0, "by_staff": by_staff}


def today_context(request):
    today = timezone.localdate()
    now = timezone.now()
    pending = list(Payment.objects.filter(status=Payment.Status.PENDING).select_related("user", "plan")[:50])
    for p in pending:
        p.method_label = METHODS.get(p.method, p.method)
    orders = list(Order.objects.filter(status__in=(Order.Status.NEW, Order.Status.SHIPPING)).select_related("user").prefetch_related("items")[:50])
    pt = list(PTSession.objects.filter(status="requested", starts__gte=now).select_related("user", "trainer")[:30])
    classes = []
    for c in GymClass.objects.filter(active=True, weekday=today.weekday()).select_related("trainer"):
        bookings = list(Booking.objects.filter(gym_class=c, date=today).select_related("user").order_by("user__first_name"))
        classes.append({"c": c, "bookings": bookings, "started": extras.class_start(c, today) <= now,
                        "waiting": ClassWaitlist.objects.filter(gym_class=c, date=today).count()})
    guests = list(GuestPass.objects.filter(date=today, cancelled_at__isnull=True).select_related("owner"))
    entries = list(EntryLog.objects.filter(ts__date=today).select_related("user", "guest_pass", "staff")[:60])
    for e in entries:
        e.reason_label = REASON_LABELS.get(e.reason, "")
    return {"pending": pending, "orders": orders, "pt_requests": pt, "classes": classes, "guests": guests, "entries": entries,
            "today": today, "methods": METHODS, "bookings_today": sum(len(c["bookings"]) for c in classes)}


def tab_fragments(request, ctx):
    names = {"pay": "_pay", "orders": "_orders", "pt": "_pt", "classes": "_classes", "guests": "_guests", "visits": "_entries"}
    out = {}
    for key, tpl in names.items():
        html = render_to_string(f"admin/desk/{tpl}.html", {"ctx": ctx}, request=request)
        out[key] = {"html": html, "hash": hashlib.md5(html.encode()).hexdigest()[:10]}
    return out


def counts_of(ctx, summary):
    return {"pay": len(ctx["pending"]), "orders": len(ctx["orders"]), "pt": len(ctx["pt_requests"]), "classes": ctx["bookings_today"],
            "guests": len(ctx["guests"]), "visits": summary["entries"]}


def summary_html(request, summary):
    return render_to_string("admin/desk/_shift.html", {"s": summary, "methods": METHODS}, request=request)


# ---------------------------------------------------------------- pages
def shell(request, template, ctx):
    """Render inside the admin shell: each_context() supplies the sidebar, top bar and theme."""
    return render(request, template, {**admin.site.each_context(request), **ctx})


def desk_page(request):
    ctx = today_context(request)
    summary = shift_summary(ctx["today"], request.user)
    gs = GymSettings.load()
    return shell(request, "admin/desk.html", {
        "title": "Qabulxona", "ctx": ctx, "frags": tab_fragments(request, ctx), "counts": counts_of(ctx, summary), "summary_html": summary_html(request, summary),
        "plans": Plan.objects.filter(active=True), "q": (request.GET.get("q") or "")[:80], "gs": gs,
        "crowd": crowd_level(),
        "tabs": [("pay", "Kutayotgan to'lovlar", "card"), ("orders", "Buyurtmalar", "bag"), ("pt", "PT so'rovlari", "user-check"),
                 ("classes", "Bugungi mashg'ulotlar", "calendar"), ("guests", "Mehmonlar", "gift"), ("visits", "Bugungi kirishlar", "door")],
    })


def classes_page(request):
    ctx = today_context(request)
    return shell(request, "admin/desk_classes.html", {"title": "Mashg'ulotlar davomati", "ctx": ctx})


def scan_page(request):
    return shell(request, "admin/desk_scan.html", {"title": "QR skaner", "today_count": Visit.objects.filter(ts__date=timezone.localdate()).count()})


def shift_page(request):
    day = safe_date(request.GET.get("d")) or timezone.localdate()
    if day > timezone.localdate():
        day = timezone.localdate()
    s = shift_summary(day, request.user)
    return render(request, "admin/desk_shift.html", {"s": s, "methods": METHODS, "gs": GymSettings.load(), "staff": request.user, "now": timezone.localtime()})


def receipt_page(request, pid):
    p = get_object_or_404(Payment.objects.select_related("user", "plan", "staff"), pk=pid, kind="plan")
    m = p.user.memberships.filter(plan=p.plan).order_by("-created").first() if p.user and p.plan else None
    return render(request, "admin/desk_receipt.html", {"p": p, "m": m, "gs": GymSettings.load(), "method_label": METHODS.get(p.method, p.method), "now": timezone.localtime()})


def card_page(request, uid):
    u = get_member(uid)
    return render(request, "admin/desk_card.html", {"u": u, "qr": mark_safe(member_qr(u)), "gs": GymSettings.load(), "initials": initials_of(u)})


def member_qr(u):
    return segno.make(services.card_token(u), error="m").svg_inline(scale=6, border=2, dark="#111111", light="#ffffff")


# ---------------------------------------------------------------- JSON: search, member panel, polling
def search_api(request):
    if search_limited(request):
        return fail("Juda tez-tez qidiryapsiz. Bir lahza kuting.", 429)
    q = (request.GET.get("q") or "").strip()[:80]
    if q.upper().startswith("GP-"):
        gp = extras.guest_from_code(q)
        if not gp:
            return ok(results=[], guest=None)
        return ok(results=[], guest=guest_info(gp))
    return ok(results=[member_row(u) for u in search_users(q)], q=q)


def member_api(request, pk):
    u = get_member(pk)
    return ok(id=u.pk, html=member_html(request, u))


def today_api(request):
    ctx = today_context(request)
    summary = shift_summary(ctx["today"], request.user)
    return ok(counts=counts_of(ctx, summary), tabs=tab_fragments(request, ctx), shift=summary_html(request, summary), stamp=f"{timezone.localtime():%H:%M:%S}",
              crowd=crowd_level())


# ---------------------------------------------------------------- JSON: actions
@post_only
def checkin_api(request, uid):
    u = get_member(uid)
    entered, banner, _ = do_entry(request, u, "manual")
    return member_reply(request, u, message=banner["title"], banner=banner, entered=entered)


def sell(request, u, plan, method):
    """A sale at the desk: money is taken now, so the payment is confirmed at once and the membership starts. The member's consent to the
    offer and privacy policy is recorded as given at the desk. Returns the payment."""
    card = services.current_card() if method == "card" else None
    now = timezone.now()
    with transaction.atomic():
        pay = Payment.objects.create(user=u, kind="plan", plan=plan, amount=plan.price, method=method, status=Payment.Status.PAID,
                                     pay_card=card, card_last4=card.last4 if card else "", consent_at=u.consent_at or now, staff=request.user)
        services.add_membership(u, plan)
        extras.stamp_consent(u, Payment.objects.filter(pk=pay.pk))
    return pay


@post_only
def sell_api(request, uid):
    u = get_member(uid)
    data = body_of(request)
    plan = Plan.objects.filter(code=text_of(data, "plan", 40), active=True).first()
    method = text_of(data, "method", 8) or "cash"
    if not plan:
        return fail("Abonement turini tanlang.", 400)
    if method not in ("cash", "card"):
        return fail("To'lov usuli noto'g'ri: naqd yoki karta.", 400)
    if not u.is_active:
        return fail("Akkaunt bloklangan: abonement sotib bo'lmaydi.", 409)
    if not u.consent_at and not data.get("consent"):
        return fail("A'zoning oferta va maxfiylik siyosatiga roziligi belgilanmagan.", 400, field="consent")
    pay = sell(request, u, plan, method)
    return member_reply(request, u, message=f"{plan.name} sotildi: {money_text(pay.amount)} so'm", receipt=f"/django-admin/desk/receipt/{pay.pk}/", payment=pay.pk)


@post_only
def freeze_api(request, uid):
    u = get_member(uid)
    data = body_of(request)
    try:
        days = int(data.get("days"))
    except (TypeError, ValueError):
        return fail("Necha kunga muzlatishni tanlang.", 400)
    f, err = extras.start_freeze(u, days)
    if err:
        return fail(translate("uz", err), 409)
    return member_reply(request, u, message=f"{days} kunga muzlatildi")


@post_only
def unfreeze_api(request, uid):
    u = get_member(uid)
    back, err = extras.end_freeze(u)
    if err:
        return fail(translate("uz", err), 409)
    return member_reply(request, u, message=f"Muzlatish tugatildi, {back} kun qaytarildi")


@post_only
def block_api(request, uid):
    u = get_member(uid)
    u.is_active = not u.is_active
    u.save(update_fields=["is_active"])
    return member_reply(request, u, message="Akkaunt bloklandi" if not u.is_active else "Akkaunt ochildi")


@post_only
def new_member_api(request):
    data = body_of(request)
    first, last = text_of(data, "first_name", 40), text_of(data, "last_name", 40)
    phone = normalize_phone(text_of(data, "phone", 20))
    if len(first) < 2:
        return fail("Ismni kiriting (kamida 2 harf).", 400, field="first_name")
    if not phone:
        return fail("Telefon raqami noto'g'ri. Masalan: 90 123 45 67.", 400, field="phone")
    if User.objects.filter(phone=phone).exists():
        return fail("Bu telefon raqami allaqachon ro'yxatdan o'tgan.", 409, field="phone")
    plan = None
    if text_of(data, "plan", 40):
        plan = Plan.objects.filter(code=text_of(data, "plan", 40), active=True).first()
        if not plan:
            return fail("Abonement turi topilmadi.", 400, field="plan")
    method = text_of(data, "method", 8) or "cash"
    if plan and method not in ("cash", "card"):
        return fail("To'lov usuli noto'g'ri: naqd yoki karta.", 400)
    if plan and not data.get("consent"):
        return fail("A'zoning oferta va maxfiylik siyosatiga roziligi belgilanmagan.", 400, field="consent")
    try:
        with transaction.atomic():
            u = User.objects.create_user(first_name=first, last_name=last, phone=phone, password=secrets.token_urlsafe(12))
            pay = sell(request, u, plan, method) if plan else None
    except IntegrityError:
        return fail("Bu telefon raqami allaqachon ro'yxatdan o'tgan.", 409, field="phone")
    card = render_to_string("admin/desk/_newcard.html", {"u": u, "qr": mark_safe(member_qr(u)), "initials": initials_of(u), "pay": pay}, request=request)
    return ok(message=f"{u.full_name} ro'yxatga olindi ({u.member_code})", id=u.pk, html=member_html(request, u), card=card,
              card_url=f"/django-admin/desk/card/{u.pk}/", receipt=f"/django-admin/desk/receipt/{pay.pk}/" if pay else "")


def guest_info(gp):
    today = timezone.localdate()
    if gp.cancelled_at:
        state, label = "bad", "Bekor qilingan"
    elif gp.used_at:
        state, label = "bad", f"Ishlatilgan ({timezone.localtime(gp.used_at):%d.%m %H:%M})"
    elif gp.date < today:
        state, label = "bad", "Muddati o'tgan"
    elif gp.date > today:
        state, label = "warn", f"Boshqa kunga: {gp.date:%d.%m.%Y}"
    elif not services.can_enter(gp.owner):
        state, label = "bad", "Taklif qilgan a'zo kira olmaydi"
    else:
        state, label = "good", "Yaroqli: bugun kirishi mumkin"
    return {"id": gp.pk, "guest": gp.guest_name, "phone": gp.guest_phone, "owner": gp.owner.full_name, "owner_code": gp.owner.member_code,
            "date": f"{gp.date:%d.%m.%Y}", "state": state, "label": label, "can": state == "good"}


@post_only
def guest_api(request):
    """Check a guest pass by its QR text (or id from today's list); with redeem=true the guest is let in and the entry is written down."""
    data = body_of(request)
    gp = None
    if data.get("id") not in (None, ""):
        try:
            gp = GuestPass.objects.select_related("owner").filter(pk=int(data["id"])).first()
        except (TypeError, ValueError):
            gp = None
    else:
        gp = extras.guest_from_code(text_of(data, "code", 80))
    if not gp:
        return fail("Mehmon taklifnomasi topilmadi. Kodni tekshiring.", 404)
    if not data.get("redeem"):
        return ok(guest=guest_info(gp))
    entered, err = extras.redeem_guest_pass(gp, request.user)
    extras.log_entry("guest", gp.owner, entered=entered, reason={"gp_used": "guest_used", "gp_expired": "guest_expired", "gp_cancelled": "guest_cancelled",
                                                                "gp_early": "guest_early"}.get(err, "guest_owner_out"), staff=request.user, guest_pass=gp)
    gp.refresh_from_db()
    info = guest_info(gp)
    return ok(guest=info, entered=entered, message=f"{gp.guest_name}: kirishga ruxsat" if entered else info["label"],
              banner={"entered": entered, "name": gp.guest_name, "code": "MEHMON", "plan": f"{gp.owner.full_name} taklifi", "until": f"{gp.date:%d.%m.%Y}",
                      "reason_label": "" if entered else info["label"], "title": "Kirishga ruxsat" if entered else "Kirish taqiqlangan", "note": ""})


@post_only
def confirm_api(request, pid):
    p = get_object_or_404(Payment, pk=pid)
    if not services.confirm_payment(p, staff=request.user):
        return fail("Bu to'lov allaqachon ko'rib chiqilgan.", 409)
    return ok(message="To'lov tasdiqlandi")


@post_only
def reject_api(request, pid):
    p = get_object_or_404(Payment, pk=pid)
    if not services.cancel_payment(p, notify=True, staff=request.user):
        return fail("Bu to'lov allaqachon ko'rib chiqilgan.", 409)
    return ok(message="To'lov rad etildi")


@post_only
def ship_api(request, oid):
    if not services.ship_order(get_object_or_404(Order, pk=oid)):
        return fail("Buyurtmani yo'lga chiqarib bo'lmaydi.", 409)
    return ok(message="Buyurtma yo'lga chiqdi")


@post_only
def handover_api(request, oid):
    services.hand_over(get_object_or_404(Order, pk=oid))
    return ok(message="Buyurtma topshirildi")


@post_only
def pt_api(request, pk, action):
    s = get_object_or_404(PTSession, pk=pk)
    if action == "confirm":
        s.status = PTSession.Status.CONFIRMED
        telegram.notify_user(s.user, "tg_pt_confirmed", trainer=s.trainer.name, time=timezone.localtime(s.starts).strftime("%d.%m %H:%M"))
    elif action == "cancel":
        s.status = PTSession.Status.CANCELLED
        telegram.notify_user(s.user, "tg_pt_cancelled", trainer=s.trainer.name)
    else:
        return fail("Noma'lum amal.", 400)
    s.save(update_fields=["status"])
    return ok(message="Tasdiqlandi" if action == "confirm" else "Bekor qilindi")


@post_only
def booking_api(request, pk, action):
    b = get_object_or_404(Booking, pk=pk)
    if not extras.mark_booking(b, action):
        return fail("Noma'lum amal.", 400)
    return ok(message={"came": "Keldi deb belgilandi", "noshow": "Kelmadi deb belgilandi", "reset": "Belgi olib tashlandi"}[action])


@post_only
def scan_api(request):
    """The QR scanner (and the manual code box): a member card or a guest pass. Same answer shape as before, plus the banner fields."""
    data = body_of(request)
    code = text_of(data, "code", 120)
    today = timezone.localdate()
    if code.upper().startswith("GP-"):
        return scan_guest(request, code)
    u = services.user_from_card(code)
    if not u:
        extras.log_entry("qr", None, entered=False, reason="invalid", staff=request.user)
        return fail(translate(request.lang, "scan_bad"), 404, reason_label=REASON_LABELS["invalid"])
    entered, banner, earlier = do_entry(request, u, "qr")
    m = services.active_membership(u)
    visit = (earlier or Visit.objects.filter(user=u, ts__date=today).first()) if entered else None  # a refusal never gets a receipt number
    reason = "" if entered else ("err_blocked" if not u.is_active else "err_frozen" if m else "err_member")
    now = timezone.localtime()
    ticket = entry_ticket(
        request, entered=entered, member=u, m=m, reason=reason,
        no=f"V-{visit.pk:06d}" if visit else "", repeat_at=timezone.localtime(earlier.ts) if earlier and entered else None,
        days_left=max(0, (timezone.localtime(m.expires).date() - today).days) if m else None,  # calendar days, so "ends tomorrow" says 1
        month_visits=Visit.objects.filter(user=u, ts__year=now.year, ts__month=now.month).count(),
        total_visits=Visit.objects.filter(user=u).count(),
        frozen_until=m.frozen_until if m and m.is_frozen and not entered else None)
    message = (translate(request.lang, "scan_ok" if entered else reason) if not (m and m.is_frozen and not entered)
               else translate(request.lang, "scan_frozen", date=f"{timezone.localtime(m.frozen_until):%d.%m.%Y}"))
    return ok(entered=entered, name=u.full_name, code=u.member_code, plan=m.plan.name if m else "",
              until=f"{timezone.localtime(m.expires):%d.%m.%Y}" if m else "", message=message, ticket=ticket, banner=banner, member_id=u.pk,
              today=Visit.objects.filter(ts__date=today).count())


def scan_guest(request, code):
    gp = extras.guest_from_code(code)
    if not gp:
        extras.log_entry("guest", None, entered=False, reason="invalid", staff=request.user)
        return fail(translate(request.lang, "scan_bad"), 404, reason_label=REASON_LABELS["invalid"])
    entered, err = extras.redeem_guest_pass(gp, request.user)
    extras.log_entry("guest", gp.owner, entered=entered, reason={"gp_used": "guest_used", "gp_expired": "guest_expired", "gp_cancelled": "guest_cancelled",
                                                                "gp_early": "guest_early"}.get(err, "guest_owner_out"), staff=request.user, guest_pass=gp)
    now = timezone.localtime()
    ticket = render_to_string("gym/staff/_guest_ticket.html", {"gs": GymSettings.load(), "now": now, "staff": request.user, "lang": request.lang, "gp": gp,
                                                   "entered": entered, "reason": err, "no": f"G-{gp.pk:06d}" if entered else ""}, request=request)
    info = guest_info(gp)
    banner = {"entered": entered, "name": gp.guest_name, "code": "MEHMON", "plan": f"{gp.owner.full_name} taklifi", "until": f"{gp.date:%d.%m.%Y}",
              "reason": "", "reason_label": "" if entered else REASON_LABELS.get({"gp_used": "guest_used", "gp_expired": "guest_expired",
                                                                                  "gp_cancelled": "guest_cancelled", "gp_early": "guest_early"}.get(err, "guest_owner_out"), info["label"]),
              "title": "Kirishga ruxsat" if entered else "Kirish taqiqlangan", "note": ""}
    return ok(entered=entered, name=gp.guest_name, code="GUEST", plan=translate(request.lang, "gp_guest_of", name=gp.owner.full_name), until=f"{gp.date:%d.%m.%Y}",
              message=translate(request.lang, "gp_ok" if entered else err), ticket=ticket, banner=banner, today=Visit.objects.filter(ts__date=timezone.localdate()).count())


# ---------------------------------------------------------------- URL table (mounted by GymAdminSite.get_urls)
def desk_urls(site):
    from django.urls import path
    v = site.admin_view  # staff + admin mode, and CSRF protection on every POST
    return [
        path("desk/", v(desk_page), name="desk"),
        path("desk/scan/", v(lambda r: scan_api(r) if r.method == "POST" else scan_page(r)), name="desk_scan"),
        path("desk/classes/", v(classes_page), name="desk_classes"),
        path("desk/shift/", v(shift_page), name="desk_shift"),
        path("desk/search/", v(search_api), name="desk_search"),
        path("desk/today/", v(today_api), name="desk_today"),
        path("desk/member/<int:pk>/", v(member_api), name="desk_member"),
        path("desk/card/<int:uid>/", v(card_page), name="desk_card"),
        path("desk/receipt/<int:pid>/", v(receipt_page), name="desk_receipt"),
        path("desk/new-member/", v(new_member_api), name="desk_new_member"),
        path("desk/guest/", v(guest_api), name="desk_guest"),
        path("desk/checkin/<int:uid>/", v(checkin_api), name="desk_checkin"),
        path("desk/sell/<int:uid>/", v(sell_api), name="desk_sell"),
        path("desk/freeze/<int:uid>/", v(freeze_api), name="desk_freeze"),
        path("desk/unfreeze/<int:uid>/", v(unfreeze_api), name="desk_unfreeze"),
        path("desk/block/<int:uid>/", v(block_api), name="desk_block"),
        path("desk/confirm/<int:pid>/", v(confirm_api), name="desk_confirm"),
        path("desk/reject/<int:pid>/", v(reject_api), name="desk_reject"),
        path("desk/handover/<int:oid>/", v(handover_api), name="desk_handover"),
        path("desk/ship/<int:oid>/", v(ship_api), name="desk_ship"),
        path("desk/pt/<int:pk>/<str:action>/", v(pt_api), name="desk_pt"),
        path("desk/booking/<int:pk>/<str:action>/", v(booking_api), name="desk_booking_mark"),
    ]


def legacy_redirect(request, rest=""):
    """/staff/... (the old public-site front desk) -> /django-admin/desk/... with the query string kept (301)."""
    qs = request.META.get("QUERY_STRING", "")
    return HttpResponsePermanentRedirect("/django-admin/desk/" + rest + ("?" + qs if qs else ""))
