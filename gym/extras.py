"""Business rules of the retention features: self-service freeze, expiry reminders, guest passes, class waitlist / no-shows,
trainer ratings, weekly streaks, gift certificates, calendar export, legal pages and account deletion.
Views stay thin and call these functions; the admin actions and the management command share them."""
import hashlib
import hmac
import os
import secrets
from datetime import datetime, time, timedelta
from datetime import timezone as dt_tz

from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from . import services
from .models import (Booking, ClassWaitlist, ExpiryReminder, FaqItem, GiftCertificate, GuestPass, GymClass, GymSettings, LegalPage, Membership,
                     MembershipFreeze, Payment, Plan, PTSession, Trainer, TrainerReview, User)
from .templatetags.gym_tags import translate


def site_url():
    """Absolute address of the site for messages sent outside the browser (Telegram, e-mail). Empty when unknown."""
    return (os.environ.get("FZ_SITE_URL") or os.environ.get("RENDER_EXTERNAL_URL") or "").strip().rstrip("/")


def _midnight(day):
    return timezone.make_aware(datetime.combine(day, time.min))


def _local_date(dt):
    return timezone.localtime(dt).date()


# ---------------------------------------------------------------- 1. freeze
def freeze_info(user):
    """Everything the freeze card needs: the rules, what is used and left on the active membership, and whether a new freeze is possible now."""
    gs = GymSettings.load()
    info = {"enabled": gs.freeze_max_days > 0, "min": gs.freeze_min_days, "max": gs.freeze_max_days, "m": None, "used": 0, "left": 0,
            "current": None, "scheduled": None, "can": False, "reason": ""}
    if not info["enabled"]:
        info["reason"] = "freeze_off"
        return info
    m = info["m"] = services.active_membership(user)
    if not m:
        info["reason"] = "freeze_no_member"
        return info
    today = timezone.localdate()
    freezes = list(m.freezes.all())
    info["used"] = sum(f.days for f in freezes)
    info["left"] = max(0, gs.freeze_max_days - info["used"])
    info["current"] = next((f for f in freezes if f.days and f.start_date <= today < f.end_date), None)
    info["scheduled"] = next((f for f in freezes if f.days and f.start_date > today), None)
    if info["current"] or info["scheduled"]:
        info["reason"] = "freeze_busy"
    elif info["left"] < gs.freeze_min_days:
        info["reason"] = "freeze_none_left"
    else:
        info["can"] = True
    return info


def _shift_later(m, later, delta):
    for o in later:
        o.starts += delta
        o.expires += delta
        o.save(update_fields=["starts", "expires"])


@transaction.atomic
def start_freeze(user, days, start=None):
    """Freezes the active membership for `days` days from `start` (today by default). Returns (freeze, None) or (None, error_key).
    The end date of the membership (and of any membership queued after it) moves forward by the same number of days."""
    info = freeze_info(user)
    if not info["enabled"]:
        return None, "freeze_off"
    m = info["m"]
    if not m:
        return None, "freeze_no_member"
    if info["current"] or info["scheduled"]:
        return None, "freeze_busy"
    if info["left"] < info["min"]:
        return None, "freeze_none_left"
    today = timezone.localdate()
    start = start or today
    if start < today or start >= _local_date(m.expires) or start > today + timedelta(days=180):
        return None, "freeze_bad_date"
    if days < info["min"]:
        return None, "freeze_min"
    if days > info["left"]:
        return None, "freeze_too_long"
    later = list(m.user.memberships.filter(starts__gte=m.expires).exclude(pk=m.pk))
    f = MembershipFreeze.objects.create(membership=m, start_date=start, end_date=start + timedelta(days=days), planned_days=days)
    delta = timedelta(days=days)
    m.expires += delta
    m.freeze_used, m.frozen_until, m.reminded = True, _midnight(f.end_date), False
    m.save(update_fields=["expires", "freeze_used", "frozen_until", "reminded"])
    _shift_later(m, later, delta)
    return f, None


def end_freeze_row(f):
    """Ends one freeze today (or cancels it if it has not begun) and gives the unused days back. Returns the number of days returned."""
    today = timezone.localdate()
    if f.days == 0 or f.end_date <= today:
        return 0
    m = f.membership
    unused = f.days if f.start_date > today else (f.end_date - today).days
    later = list(m.user.memberships.filter(starts__gte=m.expires).exclude(pk=m.pk))
    f.end_date = f.start_date if f.start_date > today else today
    f.ended_early, f.cancelled_at = True, timezone.now()
    f.save(update_fields=["end_date", "ended_early", "cancelled_at"])
    delta = timedelta(days=unused)
    m.expires -= delta
    m.frozen_until = None
    m.save(update_fields=["expires", "frozen_until"])
    _shift_later(m, later, -delta)
    return unused


@transaction.atomic
def end_freeze(user):
    """The member comes back early. Returns (days_returned, None) or (None, error_key)."""
    today = timezone.localdate()
    f = (MembershipFreeze.objects.select_related("membership").filter(membership__user=user, end_date__gt=today)
         .exclude(end_date=F("start_date")).order_by("start_date").first())
    if not f:
        return None, "unfreeze_none"
    return end_freeze_row(f), None


# ---------------------------------------------------------------- 2. expiry reminders
REMIND_AT = (7, 3, 1)  # days before the end


def send_expiry_reminders(today=None):
    """Tells members their membership ends in 7, 3 or 1 day(s): a message in the site inbox, Telegram when linked, e-mail when switched on.
    Safe to run as often as you like: an ExpiryReminder row is the proof that a threshold was handled, so each one goes out once per end date.
    If the command first runs late (say 2 days before the end) only the nearest threshold is sent, not a burst of three."""
    gs = GymSettings.load()
    now = timezone.now()
    today = today or timezone.localdate()
    out = {"sent": 0, "telegram": 0, "email": 0}
    horizon = _midnight(today + timedelta(days=max(REMIND_AT) + 1))
    for m in Membership.objects.filter(expires__gt=now, starts__lte=now, expires__lt=horizon).select_related("user", "plan"):
        user = m.user
        if not user.is_active or user.is_superuser:
            continue
        if user.memberships.filter(expires__gt=m.expires).exists():
            continue  # a later membership already covers them
        end_day = _local_date(m.expires)
        left = (end_day - today).days
        due = [t for t in REMIND_AT if left <= t]
        if left < 0 or not due:
            continue
        nearest, fresh = min(due), False
        for t in due:
            _, created = ExpiryReminder.objects.get_or_create(membership=m, expires_on=end_day, days_before=t)
            fresh = fresh or (created and t == nearest)
        if not fresh:
            continue
        lang = user.lang or "uz"
        title = translate(lang, "rem_title_today" if left == 0 else "rem_title", days=left)
        link = (site_url() + "/renew/") if site_url() else "/renew/"
        body = translate(lang, "rem_body", plan=m.plan.name, date=f"{timezone.localtime(m.expires):%d.%m.%Y}", link=link)
        sent = services.notify(user, title, body, email_too=gs.reminder_email)
        Membership.objects.filter(pk=m.pk).update(reminded=True)
        out["sent"] += 1
        out["telegram"] += int(bool(sent.get("tg")))
        out["email"] += int(bool(sent.get("email")))
    return out


def run_daily(force=False):
    """Lazy scheduler for hosts without cron (Render free): the first dashboard visit of the day runs the reminders. Returns the result or None if already done today."""
    key = f"fz:daily:{timezone.localdate()}"
    if not force and not cache.add(key, 1, 25 * 3600):
        return None
    try:
        return send_expiry_reminders()
    except Exception:  # a failing message service must never break a member's page
        import logging
        logging.getLogger(__name__).exception("daily reminders failed")
        cache.delete(key)
        return None


def renew_plan(user):
    """The plan the one-click Renew button buys again: the plan of the latest membership if it is still on sale, else the first plan on sale."""
    last = user.memberships.select_related("plan").order_by("-expires").first()
    if last and last.plan.active:
        return last.plan
    return Plan.objects.filter(active=True).first()


# ---------------------------------------------------------------- 3. guest passes
def guest_code(gp):
    sig = hmac.new(settings.SECRET_KEY.encode(), f"guest:{gp.pk}".encode(), hashlib.sha256).hexdigest()[:12]
    return f"GP-{gp.pk}-{sig}"


def guest_from_code(code):
    parts = (code or "").strip().split("-")
    if len(parts) != 3 or parts[0].upper() != "GP" or not parts[1].isdigit():
        return None
    gp = GuestPass.objects.select_related("owner", "membership").filter(pk=int(parts[1])).first()
    return gp if gp and hmac.compare_digest(guest_code(gp), f"GP-{parts[1]}-{parts[2]}") else None


def guest_quota(user):
    """(membership, allowed, used) for the active membership: how many guest passes its plan gives and how many are taken (cancelled ones are given back)."""
    m = services.active_membership(user)
    if not m:
        return None, 0, 0
    used = GuestPass.objects.filter(membership=m, cancelled_at__isnull=True).count()
    return m, m.plan.guest_passes, used


@transaction.atomic
def create_guest_pass(user, name, phone, day):
    """Returns (pass, None) or (None, error_key)."""
    from .forms import normalize_phone
    m, allowed, used = guest_quota(user)
    if not m:
        return None, "gp_no_member"
    if allowed <= 0 or used >= allowed:
        return None, "gp_none_left"
    name = " ".join((name or "").split())
    if len(name) < 2:
        return None, "gp_name"
    phone = (phone or "").strip()
    if phone and not normalize_phone(phone):
        return None, "err_phone"
    today = timezone.localdate()
    if not day or day < today or day >= _local_date(m.expires) or day > today + timedelta(days=90):
        return None, "gp_bad_date"
    gp = GuestPass.objects.create(owner=user, membership=m, guest_name=name[:60], guest_phone=normalize_phone(phone) or "", date=day)
    return gp, None


def cancel_guest_pass(user, pk):
    return GuestPass.objects.filter(pk=pk, owner=user, used_at__isnull=True, cancelled_at__isnull=True).update(cancelled_at=timezone.now())


def redeem_guest_pass(gp, staff=None):
    """The desk scans a guest QR. Returns (ok, error_key). Works once, on its date, while the member who gave it is still allowed in."""
    if gp.cancelled_at:
        return False, "gp_cancelled"
    if gp.used_at:
        return False, "gp_used"
    today = timezone.localdate()
    if gp.date < today:
        return False, "gp_expired"
    if gp.date > today:
        return False, "gp_early"
    if not services.can_enter(gp.owner):
        return False, "gp_owner_out"
    updated = GuestPass.objects.filter(pk=gp.pk, used_at__isnull=True, cancelled_at__isnull=True).update(used_at=timezone.now(), checked_by=staff)
    return (True, "") if updated else (False, "gp_used")


# ---------------------------------------------------------------- entry history
def entry_refusal(user):
    """Why this account cannot come in now (an EntryLog reason), or '' if it can."""
    if not user.is_active:
        return "blocked"
    m = services.active_membership(user)
    if m and m.is_frozen:
        return "frozen"
    if m:
        return ""
    return "expired" if user.memberships.exists() else "no_membership"


def log_entry(method, user=None, entered=True, reason="", repeat=False, staff=None, guest_pass=None):
    from .models import EntryLog
    result = "rejected" if not entered else ("repeat" if repeat else "ok")
    return EntryLog.objects.create(user=user, guest_pass=guest_pass, method=method, result=result, reason=reason if not entered else "", staff=staff)


def entry_history(user):
    from .models import EntryLog
    return EntryLog.objects.filter(user=user, result__in=("ok", "repeat"))


# ---------------------------------------------------------------- 5. classes: cancel window, waitlist, no-shows
def class_start(gym_class, day):
    return timezone.make_aware(datetime.combine(day, gym_class.start_time))


def cancel_deadline(booking):
    return class_start(booking.gym_class, booking.date) - timedelta(hours=GymSettings.load().class_cancel_hours)


def can_cancel(booking):
    return timezone.now() <= cancel_deadline(booking)


def cancel_booking(booking):
    """Returns (True, None) or (False, 'cancel_late'). A freed seat goes to the first person on the waitlist."""
    if not can_cancel(booking):
        return False, "cancel_late"
    booking.delete()  # the post_delete signal (below) promotes the waitlist
    return True, None


NOSHOW_LIMIT, NOSHOW_DAYS = 3, 30


def noshow_count(user):
    return Booking.objects.filter(user=user, no_show=True, date__gte=timezone.localdate() - timedelta(days=NOSHOW_DAYS)).count()


def active_bookings(user):
    return Booking.objects.filter(user=user, no_show=False, date__gte=timezone.localdate()).count()


def booking_limit_reason(user):
    """'book_limited' when 3+ no-shows in 30 days and the member already holds a booking, else None."""
    if noshow_count(user) >= NOSHOW_LIMIT and active_bookings(user) >= 1:
        return "book_limited"
    return None


def waitlist_position(user, gym_class, day):
    ids = list(ClassWaitlist.objects.filter(gym_class=gym_class, date=day).values_list("user_id", flat=True))
    return ids.index(user.pk) + 1 if user.pk in ids else 0


def join_waitlist(user, gym_class, day):
    """Returns (position, None) or (None, error_key)."""
    if not services.can_enter(user):
        return None, "err_member"
    if Booking.objects.filter(user=user, gym_class=gym_class, date=day).exists():
        return None, "book_fail"
    if services.seats_left(gym_class, day) > 0:
        return None, "wl_seats"  # there is room: just book
    if class_start(gym_class, day) <= timezone.now():
        return None, "book_fail"
    ClassWaitlist.objects.get_or_create(user=user, gym_class=gym_class, date=day)
    return waitlist_position(user, gym_class, day), None


def leave_waitlist(user, gym_class, day):
    return ClassWaitlist.objects.filter(user=user, gym_class=gym_class, date=day).delete()[0]


def promote_waitlist(gym_class, day):
    """Fills free seats from the waitlist, first come first served. Anyone who can no longer book (membership ended, blocked, no-show limit) is skipped."""
    if class_start(gym_class, day) <= timezone.now():
        return []
    booked = []
    while services.seats_left(gym_class, day) > 0:
        entry = ClassWaitlist.objects.select_related("user").filter(gym_class=gym_class, date=day).order_by("created", "id").first()
        if not entry:
            break
        entry.delete()
        u = entry.user
        if (not services.can_enter(u) or Booking.objects.filter(user=u, gym_class=gym_class, date=day).exists()
                or (noshow_count(u) >= NOSHOW_LIMIT and active_bookings(u) >= 1)):
            continue
        b = Booking.objects.create(user=u, gym_class=gym_class, date=day)
        booked.append(b)
        lang = u.lang or "uz"
        services.notify(u, translate(lang, "wl_booked_title"), translate(lang, "wl_booked_body", name=gym_class.name, date=f"{day:%d.%m.%Y}",
                                                                          time=f"{gym_class.start_time:%H:%M}"))
    return booked


def mark_booking(booking, action):
    """The desk records who came: 'came' (checked in), 'noshow' (booked but absent) or 'reset'."""
    if action == "came":
        booking.no_show, booking.checked_in_at = False, timezone.now()
    elif action == "noshow":
        booking.no_show, booking.checked_in_at = True, None
    elif action == "reset":
        booking.no_show, booking.checked_in_at = False, None
    else:
        return False
    booking.save(update_fields=["no_show", "checked_in_at"])
    return True


# ---------------------------------------------------------------- 6. trainer ratings
def attended_trainer(user, trainer):
    """Only members who really trained with the trainer may rate: a past confirmed personal session, or a past class they did not miss."""
    now = timezone.now()
    if PTSession.objects.filter(user=user, trainer=trainer, status="confirmed", starts__lt=now).exists():
        return True
    today = timezone.localdate()
    for b in Booking.objects.filter(user=user, gym_class__trainer=trainer, no_show=False, date__lte=today).select_related("gym_class"):
        if class_start(b.gym_class, b.date) < now:
            return True
    return False


def rate_trainer(user, trainer, rating, comment):
    """Returns (review, None) or (None, error_key). One review per member and trainer; sending again edits it (and un-hides nothing)."""
    if rating not in (1, 2, 3, 4, 5):
        return None, "tr_rate_bad"
    if not attended_trainer(user, trainer):
        return None, "tr_rate_not_allowed"
    review, _ = TrainerReview.objects.update_or_create(trainer=trainer, user=user, defaults={"rating": rating, "comment": (comment or "").strip()[:500]})
    return review, None


# ---------------------------------------------------------------- 7. weekly streak
def weekly_streak(user, need=2):
    """Consecutive calendar weeks (Monday-Sunday) with at least `need` visits. The current week does not break the streak while it is still in progress."""
    days = services.visit_days(user)
    today = timezone.localdate()
    monday = today - timedelta(days=today.weekday())
    per = {}
    for d in days:
        wk = d - timedelta(days=d.weekday())
        per[wk] = per.get(wk, 0) + 1
    this = per.get(monday, 0)
    weeks, wk = 0, monday
    if this >= need:
        weeks += 1
    wk -= timedelta(days=7)
    while per.get(wk, 0) >= need:
        weeks += 1
        wk -= timedelta(days=7)
    return {"weeks": weeks, "this_week": this, "need": need, "done": this >= need}


# ---------------------------------------------------------------- 8. gift certificates
GIFT_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no 0/O/1/I: a code is often read out loud or typed from a screenshot
GIFT_MIN, GIFT_MAX = 50_000, 5_000_000


def new_gift_code():
    while True:
        code = "GC-" + "".join(secrets.choice(GIFT_ALPHABET) for _ in range(8))
        if not GiftCertificate.objects.filter(code=code).exists():
            return code


def find_gift(code):
    code = (code or "").strip().upper().replace(" ", "")
    return GiftCertificate.objects.select_related("plan", "payment").filter(code=code).first() if code else None


@transaction.atomic
def buy_gift(user, plan, amount, method):
    """A member buys a certificate through the normal payment flow. Returns (payment, certificate, None) or (None, None, error_key)."""
    from .services import OFFLINE_METHODS, current_card
    if plan is None and not (GIFT_MIN <= (amount or 0) <= GIFT_MAX):
        return None, None, "gift_amount"
    card = current_card() if method == "card" else None
    if method == "card" and not card:
        return None, None, "err_method"
    price = plan.price if plan else amount
    paid = method not in OFFLINE_METHODS
    pay = Payment.objects.create(user=user, kind="gift", plan=plan, amount=price, method=method, pay_card=card, card_last4=card.last4 if card else "",
                                 status=Payment.Status.PAID if paid else Payment.Status.PENDING)
    g = GiftCertificate.objects.create(code=new_gift_code(), plan=plan, amount=0 if plan else amount, buyer=user, payment=pay,
                                       expires=timezone.localdate() + timedelta(days=365))
    return pay, g, None


def gift_error(g, plan=None):
    """Why this certificate cannot be used now (error key), or None."""
    if g is None:
        return "gift_bad"
    st = g.state
    if st != "valid":
        return {"redeemed": "gift_used", "expired": "gift_expired", "unpaid": "gift_unpaid"}[st]
    if plan is not None and g.plan_id and g.plan_id != plan.pk:
        return "gift_plan"
    return None


def release_gift(payment):
    """A cancelled payment gives its certificate back."""
    if payment.gift_code:
        GiftCertificate.objects.filter(code=payment.gift_code, redeemed_by=payment.user).update(redeemed_at=None, redeemed_by=None)


@transaction.atomic
def redeem_gift_plan(user, g):
    """A plan certificate typed on the /gift/ page: the membership starts at once. Returns (membership, None) or (None, error_key)."""
    err = gift_error(g)
    if err:
        return None, err
    if not g.plan_id:
        return None, "gift_amount_checkout"
    if not GiftCertificate.objects.filter(pk=g.pk, redeemed_at__isnull=True).update(redeemed_at=timezone.now(), redeemed_by=user):
        return None, "gift_used"
    return services.add_membership(user, g.plan), None


# ---------------------------------------------------------------- 9. calendar export
def ensure_calendar_token(user):
    if not user.calendar_token:
        user.calendar_token = secrets.token_hex(16)
        user.save(update_fields=["calendar_token"])
    return user.calendar_token


def rotate_calendar_token(user):
    user.calendar_token = secrets.token_hex(16)
    user.save(update_fields=["calendar_token"])
    return user.calendar_token


def _ics_text(s):
    return (s or "").replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\r", "").replace("\n", "\\n")


def _fold(line):
    """RFC 5545: lines are folded at 75 octets; the continuation starts with a space."""
    raw, out = line.encode("utf-8"), []
    while len(raw) > 74:
        cut = 74
        while cut > 0 and (raw[cut] & 0xC0) == 0x80:  # never split a multi-byte character
            cut -= 1
        out.append(raw[:cut].decode("utf-8"))
        raw = b" " + raw[cut:]
    out.append(raw.decode("utf-8"))
    return "\r\n".join(out)


def ics_calendar(bookings, name="Fitnes Zal"):
    gs = GymSettings.load()
    stamp = timezone.now().astimezone(dt_tz.utc).strftime("%Y%m%dT%H%M%SZ")
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Fitnes Zal//Classes//UZ", "CALSCALE:GREGORIAN", "METHOD:PUBLISH",
             f"X-WR-CALNAME:{_ics_text(name)}", "X-WR-TIMEZONE:Asia/Tashkent"]
    for b in bookings:
        start = class_start(b.gym_class, b.date)
        end = start + timedelta(minutes=b.gym_class.duration_min)
        fmt = lambda d: d.astimezone(dt_tz.utc).strftime("%Y%m%dT%H%M%SZ")
        desc = b.gym_class.trainer.name if b.gym_class.trainer_id else ""
        lines += ["BEGIN:VEVENT", f"UID:booking-{b.pk}@fitnes-zal", f"DTSTAMP:{stamp}", f"DTSTART:{fmt(start)}", f"DTEND:{fmt(end)}",
                  f"SUMMARY:{_ics_text(b.gym_class.name)}", f"LOCATION:{_ics_text(gs.address or 'Fitnes Zal')}"]
        if desc:
            lines.append(f"DESCRIPTION:{_ics_text(desc)}")
        lines += ["BEGIN:VALARM", "ACTION:DISPLAY", f"DESCRIPTION:{_ics_text(b.gym_class.name)}", "TRIGGER:-PT1H", "END:VALARM", "END:VEVENT"]
    lines.append("END:VCALENDAR")
    return "\r\n".join(_fold(ln) for ln in lines) + "\r\n"


# ---------------------------------------------------------------- 10-11. FAQ and legal pages
def faq_items(lang):
    gs = GymSettings.load()
    fill = {"hours": f"{gs.open_time:%H:%M}–{gs.close_time:%H:%M}", "phone": f"+998 {gs.phone}", "address": gs.address or "—",
            "freeze_min": gs.freeze_min_days, "freeze_max": gs.freeze_max_days, "bonus": gs.referral_bonus_days, "cancel_hours": gs.class_cancel_hours}
    rows = []
    for it in FaqItem.objects.filter(active=True):
        ans = it.a(lang)
        for k, v in fill.items():
            ans = ans.replace("{" + k + "}", str(v))
        rows.append({"q": it.q(lang), "a": ans})
    return rows


def get_legal(slug):
    from .legal_defaults import DEFAULTS
    if slug not in DEFAULTS:
        return None
    return LegalPage.objects.get_or_create(slug=slug, defaults=DEFAULTS[slug])[0]


def legal_placeholders():
    """Placeholders still left in any legal page: the admin warns about them because the texts must carry real company data."""
    for slug in ("oferta", "privacy", "refund"):
        get_legal(slug)
    found = []
    for page in LegalPage.objects.all():
        for token in page.placeholders():
            if token not in found:
                found.append(token)
    return found


def consent_given(request):
    """A purchase may go on when the member already accepted the offer and privacy policy, or ticked the box on this form (and then it is remembered)."""
    u = request.user
    if u.consent_at:
        return True
    if request.POST.get("consent"):
        stamp_consent(u)
        return True
    return False


def stamp_consent(user, payments=None):
    """Remembers that the member accepted the offer and privacy policy (once on the account, and on the payments made under it)."""
    now = timezone.now()
    if not user.consent_at:
        user.consent_at = now
        user.save(update_fields=["consent_at"])
    if payments is not None:
        payments.filter(consent_at__isnull=True).update(consent_at=user.consent_at)
    return user.consent_at


# ---------------------------------------------------------------- 11. delete my account (soft)
@transaction.atomic
def anonymize_user(user):
    """Deactivates the account and wipes what identifies the person. Payments, orders and memberships stay (accounting) but point to an anonymous record."""
    from django.contrib.sessions.models import Session
    from .models import ChatMessage, Order, Review
    uid = user.pk
    if user.avatar:
        try:
            user.avatar.delete(save=False)
        except OSError:
            pass
    user.username, user.first_name, user.last_name = f"deleted{uid}", "Deleted", ""
    user.email = user.phone = None
    user.phone_verified = user.show_in_leaderboard = user.chat_visible = False
    user.birth_date, user.goal, user.target_weight, user.sex = None, "", None, ""
    user.telegram_chat_id, user.tg_link_code, user.staff_note, user.calendar_token = None, "", "", ""
    user.avatar = None
    user.is_active, user.deleted_at = False, timezone.now()
    user.set_unusable_password()
    user.save()
    for rel in ("bodylogs", "records", "workout_sessions", "tracker_goals", "food_entries", "my_foods", "ai_messages", "notifications", "workout_plans", "water_logs", "waitlist",
                "trainer_reviews", "reviews", "guest_passes", "bookings"):
        getattr(user, rel).filter(**({"date__gte": timezone.localdate()} if rel == "bookings" else {})).delete()
    ChatMessage.objects.filter(sender=user).update(body="", image="", deleted=True)
    Order.objects.filter(user=user).update(address="", delivery_phone="", delivery_note="")
    for s in Session.objects.filter(expire_date__gt=timezone.now()).iterator():
        if str(s.get_decoded().get("_auth_user_id")) == str(uid):
            s.delete()
    return user


# ---------------------------------------------------------------- signals
def _on_booking_deleted(sender, instance, **kw):
    try:
        promote_waitlist(instance.gym_class, instance.date)
    except Exception:  # a seat that cannot be handed on must never break the cancellation itself
        import logging
        logging.getLogger(__name__).exception("waitlist promotion failed")


from django.db.models.signals import post_delete  # noqa: E402

post_delete.connect(_on_booking_deleted, sender=Booking, dispatch_uid="fz_booking_waitlist")
