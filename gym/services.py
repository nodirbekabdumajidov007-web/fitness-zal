"""Business rules, kept out of the views so the site, the staff desk and the admin actions share them."""
import hashlib
import hmac
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.db.models import Count, F
from django.utils import timezone

from . import telegram
from .models import (BodyLog, Booking, GymSettings, Membership, Order, Payment, PaymentCard, Plan, Product, PromoCode, Review, User, Visit)

OFFLINE_METHODS = ("cash", "click", "card")  # not marked paid on the spot: cash and card transfers wait for staff, click for the gateway callback
CARD_HOLD_HOURS = 24  # an unpaid card transfer is cancelled after this long, which also releases the reserved stock


def current_card():
    """The card that receives transfers right now: the primary one, else the first active card."""
    cards = PaymentCard.objects.filter(active=True)
    return cards.filter(is_primary=True).first() or cards.first()


def demo_enabled(gs=None):
    gs = gs or GymSettings.load()
    return bool(gs.demo_payments and settings.ALLOW_DEMO_PAYMENTS)


# ---------------------------------------------------------------- memberships
def active_membership(user):
    now = timezone.now()
    return user.memberships.filter(starts__lte=now, expires__gt=now).select_related("plan").order_by("-expires").first()


def paid_until(user):
    m = user.memberships.order_by("-expires").first()
    return m.expires if m else None


def grant_days(user, days):
    """Adds free days: extends the latest membership, or starts a short one for someone who never had any."""
    last = user.memberships.select_related("plan").order_by("-expires").first()
    if last:
        last.expires += timedelta(days=days)
        last.reminded = False
        last.save(update_fields=["expires", "reminded"])
        return last
    plan = Plan.objects.filter(active=True).order_by("order", "id").first()
    if not plan:
        return None
    now = timezone.now()
    return Membership.objects.create(user=user, plan=plan, starts=now, expires=now + timedelta(days=days))


extend_member = grant_days


def add_membership(user, plan):
    """Stacks on top of existing coverage, so buying early never wastes days. The first ever purchase rewards a referral."""
    first = not user.memberships.exists()
    now = timezone.now()
    last = user.memberships.order_by("-expires").first()
    start = max(now, last.expires) if last else now
    m = Membership.objects.create(user=user, plan=plan, starts=start, expires=start + timedelta(days=30 * plan.months))
    if first:
        reward_referral(user)
    return m


def month_start():
    now = timezone.localtime()
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def seats_left(gym_class, date):
    return max(0, gym_class.capacity - gym_class.bookings.filter(date=date).count())


def reward_referral(user):
    if user.referred_by_id and not user.referral_rewarded:
        bonus = GymSettings.load().referral_bonus_days
        if bonus:
            grant_days(user.referred_by, bonus)
            grant_days(user, bonus)
        user.referral_rewarded = True
        user.save(update_fields=["referral_rewarded"])


def freeze(user, days):
    """Pauses the active membership: all coverage from now on shifts forward by `days`; check-in is blocked meanwhile."""
    m = active_membership(user)
    if not m or m.freeze_used or m.is_frozen:
        return False
    delta = timedelta(days=days)
    with transaction.atomic():
        for other in user.memberships.filter(expires__gt=timezone.now()):
            other.expires += delta
            if other.starts > timezone.now():
                other.starts += delta
            other.save(update_fields=["expires", "starts"])
        m.refresh_from_db()
        m.freeze_used, m.frozen_until = True, timezone.now() + delta
        m.save(update_fields=["freeze_used", "frozen_until"])
    return True


def can_enter(user):
    if not user.is_active:  # a blocked account stays outside even with a paid membership
        return False
    m = active_membership(user)
    return bool(m and not m.is_frozen)


def check_in(user):
    """One visit per local day. Returns False when the membership does not allow entry."""
    if not can_enter(user):
        return False
    if not Visit.objects.filter(user=user, ts__date=timezone.localdate()).exists():
        Visit.objects.create(user=user)
    return True


# ---------------------------------------------------------------- QR member card
def card_token(user):
    """Signed code for the QR card: FZ:<id>:<sig>. The signature stops anyone from inventing codes for other members."""
    sig = hmac.new(settings.SECRET_KEY.encode(), f"card:{user.pk}".encode(), hashlib.sha256).hexdigest()[:12]
    return f"FZ:{user.pk}:{sig}"


def user_from_card(code):
    parts = (code or "").strip().split(":")
    if len(parts) != 3 or parts[0] != "FZ" or not parts[1].isdigit():
        return None
    # every account's card works, the owner's too (they train here as well); blocked accounts are refused later, at entry
    user = User.objects.filter(pk=int(parts[1])).first()
    if user and hmac.compare_digest(card_token(user), ":".join(parts)):
        return user
    return None


# ---------------------------------------------------------------- stats, achievements, leaderboard
def visit_days(user):
    return {timezone.localtime(ts).date() for ts in user.visits.values_list("ts", flat=True)[:1000]}


def visit_stats(user):
    days = visit_days(user)
    today = timezone.localdate()
    month = sum(1 for d in days if (d.year, d.month) == (today.year, today.month))
    streak, d = 0, today
    if d not in days:
        d -= timedelta(days=1)
    while d in days:
        streak += 1
        d -= timedelta(days=1)
    return {"month": month, "streak": streak, "today": today in days, "total": len(days)}


def best_streak(days):
    best = run = 0
    prev = None
    for d in sorted(days):
        run = run + 1 if prev and d - prev == timedelta(days=1) else 1
        best, prev = max(best, run), d
    return best


MILESTONES = [("visits_1", 1), ("visits_10", 10), ("visits_25", 25), ("visits_50", 50), ("visits_100", 100), ("visits_250", 250)]


def achievements(user):
    days = visit_days(user)
    out = [{"key": k, "have": min(len(days), n), "target": n} for k, n in MILESTONES]
    for k, n in (("streak_7", 7), ("streak_30", 30)):
        out.append({"key": k, "have": min(best_streak(days), n), "target": n})
    out.append({"key": "classes_5", "have": min(Booking.objects.filter(user=user).count(), 5), "target": 5})
    out.append({"key": "first_order", "have": min(user.orders.count(), 1), "target": 1})
    out.append({"key": "tracker_3", "have": min(BodyLog.objects.filter(user=user).count(), 3), "target": 3})
    out.append({"key": "reviewer", "have": min(Review.objects.filter(user=user).count(), 1), "target": 1})
    out.append({"key": "referrer", "have": min(user.referrals.filter(referral_rewarded=True).count(), 1), "target": 1})
    for a in out:
        a["got"] = a["have"] >= a["target"]
    return out


def points(user):
    base = (len(visit_days(user)) * 10 + Booking.objects.filter(user=user).count() * 5 + user.orders.count() * 2
            + user.referrals.filter(referral_rewarded=True).count() * 50)
    return base


def leaderboard(limit=10):
    today = timezone.localdate()
    rows = (Visit.objects.filter(ts__year=today.year, ts__month=today.month, user__show_in_leaderboard=True, user__is_active=True, user__is_superuser=False)
            .values("user").annotate(n=Count("id")).order_by("-n", "user")[:limit])
    users = {u.pk: u for u in User.objects.filter(pk__in=[r["user"] for r in rows])}
    return [{"name": f"{users[r['user']].first_name} {users[r['user']].last_name[:1]}.", "visits": r["n"], "user_id": r["user"]} for r in rows]


# ---------------------------------------------------------------- personal messages & stock alerts
def send_email(user, subject, body):
    """One plain-text e-mail through SMTP (settings.EMAIL_*). Returns True when it went out; a mail failure never breaks the page."""
    import logging
    from django.core.mail import send_mail
    if not user.email:
        return False
    try:
        return bool(send_mail(subject[:150], body, None, [user.email], fail_silently=False))
    except Exception:
        logging.getLogger(__name__).exception("e-mail to user %s failed", user.pk)
        return False


def send_welcome_email(user, request=None):
    site = request.build_absolute_uri("/") if request else ""
    body = (f"Assalomu alaykum, {user.full_name}!\n\n"
            f"Fitnes Zal saytida ro'yxatdan o'tdingiz. Login: {user.username}\n"
            f"Kabinetingiz: {site}dashboard/\n\n"
            "Abonement oling, mashq rejangizni tuzing yoki AI murabbiydan savol so'rang.\n\n"
            "Agar bu siz bo'lmasangiz, bu xatga e'tibor bermang.\n— Fitnes Zal")
    return send_email(user, "Fitnes Zal'ga xush kelibsiz!", body)


def notify(user, title, body="", sender=None, telegram_too=True, sms_too=False, email_too=False):
    """A message in the member's inbox on the site, optionally also by Telegram, SMS and e-mail. Returns which channels went out."""
    from . import sms
    from .models import Notification
    Notification.objects.create(user=user, sender=sender, title=title[:120], body=body[:2000])
    sent = {"site": True, "tg": False, "sms": False, "email": False}
    if telegram_too and user.telegram_chat_id and telegram.enabled():
        sent["tg"] = bool(telegram.send(user.telegram_chat_id, f"{title}\n\n{body}".strip()))
    if sms_too and user.phone:
        sent["sms"] = sms.send_sms(user.phone, f"Fitnes Zal: {title}. {body}"[:320])
    if email_too:
        sent["email"] = send_email(user, f"Fitnes Zal: {title}", f"{body}\n\n— Fitnes Zal" if body else title)
    return sent


def restock_need(product, days=14):
    """How many to bring: two weeks of the last month's sales, never less than 4× the alert threshold. Returns (need, sold_30d)."""
    import math
    from django.db.models import Sum
    from .models import OrderItem
    since = timezone.now() - timedelta(days=30)
    sold = (OrderItem.objects.filter(product=product, order__created__gte=since).exclude(order__status=Order.Status.CANCELLED)
            .aggregate(s=Sum("qty"))["s"] or 0)
    target = max(GymSettings.load().low_stock_threshold * 4, math.ceil(sold / 30 * days))
    return max(1, target - product.stock), sold


def check_low_stock(products):
    """After a sale: products at or under the threshold send the admin one SMS (+ Telegram, + site inbox) per day each."""
    from . import sms
    from .forms import normalize_phone
    gs = GymSettings.load()
    today = timezone.localdate()
    phone = normalize_phone(gs.alert_phone or gs.phone)
    alerted, lines = [], []
    for p in {p.pk: p for p in products if p}.values():
        p.refresh_from_db(fields=["stock", "low_alert_on", "name"])
        if p.stock > gs.low_stock_threshold or p.low_alert_on == today:
            continue
        need, sold = restock_need(p)
        state = "tugadi" if p.stock == 0 else "tugayapti"
        lines.append(f"«{p.name}» {state}: omborda {p.stock} ta qoldi. Kamida {need} ta olib keling (30 kunda {sold} ta sotildi).")
        Product.objects.filter(pk=p.pk).update(low_alert_on=today)
        alerted.append((p, need))
    if not lines:
        return alerted
    # one checkout that empties several shelves sends one message listing them all, not a burst of SMS
    title = (f"📦 {alerted[0][0].name} " + ("tugadi" if alerted[0][0].stock == 0 else "tugayapti")) if len(lines) == 1 else f"📦 {len(lines)} ta mahsulot kam qoldi"
    text = "\n".join(lines)
    if phone:
        sms.send_sms(phone, "Fitnes Zal: " + " ".join(lines))
    telegram.alert_admin(f"{title}\n{text}")
    for admin in User.objects.filter(is_superuser=True, is_active=True):
        notify(admin, title, text, telegram_too=False)
    return alerted


# ---------------------------------------------------------------- ready-made training programs
# weekday: 0 = Monday. Exercise names are written for members in Uzbek with the usual gym name in brackets.
from . import programs as _programs  # the program data lives in gym/programs.py


def _flat_program(p):
    rows = _programs.rows(p)
    return {**p, "ex": [(wd, n, s, r) for wd, n, s, r, _rest in rows], "rest": {i: row[4] for i, row in enumerate(rows)}, "rows": rows}


PROGRAMS = {k: _flat_program(p) for k, p in _programs.PROGRAMS.items()}


@transaction.atomic
def start_program(user, key):
    """Gives the member a ready-made plan. A plan from a trainer always wins, so it is never replaced here."""
    from .models import Exercise, WorkoutPlan
    prog = PROGRAMS.get(key)
    if not prog or user.workout_plans.filter(active=True, trainer__isnull=False).exists():
        return None
    user.workout_plans.filter(active=True).update(active=False)
    plan = WorkoutPlan.objects.create(user=user, title=prog["title"], notes=prog["about"], active=True)
    plan.exercises.bulk_create([Exercise(plan=plan, weekday=wd, name=name, sets=sets, reps=reps, order=i, note=f"Dam: {rest}" if rest else "")
                                for i, (wd, name, sets, reps, rest) in enumerate(prog["rows"])])
    return plan


# ---------------------------------------------------------------- payments & orders
def check_promo(code, price):
    """Returns (promo or None, discount, error_key)."""
    code = (code or "").strip().upper()
    if not code:
        return None, 0, None
    promo = PromoCode.objects.filter(code=code).first()
    if not promo or not promo.is_valid():
        return None, 0, "promo_bad"
    return promo, price * promo.percent // 100, None


@transaction.atomic
def buy_plan(user, plan, method, promo_code=""):
    """Cash waits for staff, Click for its callback; demo gateways are marked paid straight away (no real gateway behind them)."""
    card = current_card() if method == "card" else None
    if method == "card" and not card:
        return None, "err_method"
    promo, discount, err = check_promo(promo_code, plan.price)
    if err:
        return None, err
    if promo:
        updated = PromoCode.objects.filter(pk=promo.pk).exclude(max_uses__isnull=False, used__gte=F("max_uses")).update(used=F("used") + 1)
        if not updated:
            return None, "promo_bad"
    paid = method not in OFFLINE_METHODS
    pay = Payment.objects.create(user=user, kind="plan", plan=plan, amount=plan.price - discount, discount=discount,
                                 promo=promo.code if promo else "", method=method,
                                 pay_card=card, card_last4=card.last4 if card else "",
                                 status=Payment.Status.PAID if paid else Payment.Status.PENDING)
    if paid:
        add_membership(user, plan)
    return pay, None


@transaction.atomic
def confirm_payment(payment):
    if payment.status != Payment.Status.PENDING:
        return False
    payment.status = Payment.Status.PAID
    payment.save(update_fields=["status"])
    if payment.kind == "plan" and payment.user and payment.plan:
        add_membership(payment.user, payment.plan)
    if payment.user:
        telegram.notify_user(payment.user, "tg_payment_ok", amount=f"{payment.amount:,}".replace(",", " "), ref=payment.reference)
    return True


@transaction.atomic
def cancel_payment(payment, notify=False):
    """Cancels an unpaid payment. For shop orders the reserved stock goes back; a used promo code is released."""
    if payment.status != Payment.Status.PENDING:
        return False
    payment.status = Payment.Status.CANCELLED
    payment.save(update_fields=["status"])
    order = payment.order
    if order and order.status == Order.Status.NEW:
        for it in order.items.exclude(product=None):
            Product.objects.filter(pk=it.product_id).update(stock=F("stock") + it.qty)
        order.status = Order.Status.CANCELLED
        order.save(update_fields=["status"])
    if payment.promo and payment.kind == "plan":
        PromoCode.objects.filter(code=payment.promo, used__gt=0).update(used=F("used") - 1)
    if notify and payment.user:
        telegram.notify_user(payment.user, "tg_payment_rejected", ref=payment.reference)
    return True


def report_transfer(payment, sender_last4):
    """The member says the transfer is done. Staff still has to see the money in the bank app before confirming."""
    sender_last4 = (sender_last4 or "").strip()
    if payment.status != Payment.Status.PENDING or payment.method != "card" or not (sender_last4.isdigit() and len(sender_last4) == 4):
        return False
    payment.sender_last4, payment.proof_at = sender_last4, timezone.now()
    payment.save(update_fields=["sender_last4", "proof_at"])
    return True


def expire_pending(hours=CARD_HOLD_HOURS):
    """Cancels card transfers that were never reported within `hours`. Run hourly (manage.py expire_pending)."""
    cutoff = timezone.now() - timedelta(hours=hours)
    n = 0
    for p in Payment.objects.filter(status=Payment.Status.PENDING, method="card", proof_at__isnull=True, created__lt=cutoff):
        n += cancel_payment(p)
    return n


@transaction.atomic
def place_order(user, cart, method, delivery=None):
    """cart: {product_id: qty}. Prices, stock and the delivery fee are always worked out here, never taken from the browser.
    delivery: None for pickup at the gym, or {"address", "phone", "note"} for a courier."""
    card = current_card() if method == "card" else None
    if method == "card" and not card:
        return None, "err_method"
    gs = GymSettings.load()
    if delivery is not None and not gs.delivery_on:
        return None, "delivery_off"
    items, total = [], 0
    for pid, qty in cart.items():
        p = Product.objects.filter(pk=pid, active=True).first()
        if not p or qty < 1:
            return None, "cart_bad"
        if not Product.objects.filter(pk=pid, stock__gte=qty).update(stock=F("stock") - qty):
            return None, "err_stock"  # atomic check-and-decrement; the whole order rolls back
        items.append((p, qty))
        total += p.price * qty
    fee = gs.delivery_cost(total) if delivery is not None else 0
    total += fee
    extra = {}
    if delivery is not None:
        extra = {"delivery": Order.Delivery.COURIER, "address": delivery["address"][:200], "delivery_phone": delivery["phone"],
                 "delivery_note": delivery.get("note", "")[:200], "delivery_fee": fee}
    order = Order.objects.create(user=user, total=total, method=method, **extra)
    for p, qty in items:
        order.items.create(product=p, name=p.name, price=p.price, qty=qty)
    Payment.objects.create(user=user, kind="shop", order=order, amount=total, method=method,
                           pay_card=card, card_last4=card.last4 if card else "",
                           status=Payment.Status.PENDING if method in OFFLINE_METHODS else Payment.Status.PAID)
    return order, None


@transaction.atomic
def ship_order(order):
    """The courier has left with a delivery order; the member is told by Telegram if it is linked."""
    if order.status != Order.Status.NEW or order.delivery != Order.Delivery.COURIER:
        return False
    order.status, order.shipped_at = Order.Status.SHIPPING, timezone.now()
    order.save(update_fields=["status", "shipped_at"])
    if order.user:
        telegram.notify_user(order.user, "tg_order_shipping", n=order.pk)
    return True


@transaction.atomic
def hand_over(order):
    """Picked up at the desk, or delivered by the courier."""
    if order.status not in (Order.Status.NEW, Order.Status.SHIPPING):
        return False
    order.status, order.done_at = Order.Status.DONE, timezone.now()
    order.save(update_fields=["status", "done_at"])
    order.payments.filter(status=Payment.Status.PENDING, method="cash").update(status=Payment.Status.PAID)  # cash is collected at pickup
    return True
