import csv
from datetime import timedelta

from django.contrib import admin
from django.db.models import Count, ExpressionWrapper, F, Max, Sum
from django.db.models.fields import BigIntegerField
from django.db.models.functions import ExtractHour, ExtractWeekDay, TruncDate, TruncMonth
from django.http import HttpResponse
from django.template.response import TemplateResponse
from django.urls import path
from django.utils import timezone


def dashboard_stats():
    from .models import ChatReport, Membership, Order, Payment, Product, PTSession, User, VipPass, Visit
    now, today = timezone.now(), timezone.localdate()
    paid = Payment.objects.filter(status="paid")
    by_day = {r["d"]: r["s"] for r in paid.filter(created__date__gte=today - timedelta(days=13))
              .annotate(d=TruncDate("created")).values("d").annotate(s=Sum("amount"))}
    days = [{"d": today - timedelta(days=i), "sum": by_day.get(today - timedelta(days=i), 0)} for i in range(13, -1, -1)]
    top = max([x["sum"] for x in days] + [1])
    for i, x in enumerate(days):
        x["h"] = max(3, round(x["sum"] / top * 100)) if x["sum"] else 3
        x["x"] = round((i + .5) / len(days) * 100, 2)
    line = " ".join(f"{x['x']},{100 - x['h']}" for x in days)  # the trend line drawn over the bars
    hours = {r["h"]: r["c"] for r in Visit.objects.filter(ts__date=today).annotate(h=ExtractHour("ts")).values("h").annotate(c=Count("id"))}
    pulse = _bars([{"label": f"{h:02d}", "v": hours.get(h, 0)} for h in range(6, 24)])
    joined = {r["d"]: r["c"] for r in User.objects.filter(is_superuser=False, created__date__gte=today - timedelta(days=6))
              .annotate(d=TruncDate("created")).values("d").annotate(c=Count("id"))}
    signups = _bars([{"label": f"{today - timedelta(days=i):%d}", "v": joined.get(today - timedelta(days=i), 0)} for i in range(6, -1, -1)])
    soon = (User.objects.filter(is_superuser=False).annotate(until=Max("memberships__expires"))
            .filter(until__gt=now, until__lte=now + timedelta(days=7)).order_by("until")[:8])
    revenue_month = paid.filter(created__year=today.year, created__month=today.month).aggregate(s=Sum("amount"))["s"] or 0
    return {
        **extra_stats(now, today, revenue_month),
        "kpis": kpi_data(now, revenue_month),
        "revenue_month": revenue_month, "revenue_today": days[-1]["sum"], "line": line, "pulse": pulse, "signups": signups,
        "signups_week": sum(r["v"] for r in signups),
        "revenue_total": paid.aggregate(s=Sum("amount"))["s"] or 0,
        "members": User.objects.filter(is_superuser=False).count(),
        "active_members": Membership.objects.filter(starts__lte=now, expires__gt=now).values("user").distinct().count(),
        "visits_today": Visit.objects.filter(ts__date=today).count(),
        "pending_payments": Payment.objects.filter(status="pending").count(),
        "new_orders": Order.objects.filter(status="new").count(),
        "pt_requests": PTSession.objects.filter(status="requested", starts__gte=now).count(),
        "vip_active": VipPass.objects.filter(starts__lte=now, expires__gt=now).values("user").distinct().count(),
        "chat_reports": ChatReport.objects.filter(resolved=False).count(),
        "low_stock": low_stock_rows(),
        "expiring": soon, "days": days,
        "recent_payments": Payment.objects.select_related("user")[:6],
    }


def kpi_data(now, revenue_month):
    """The handful of numbers gym-software guides agree on: active members, 30-day churn, revenue per member, visit frequency
    (the earliest warning that someone is about to leave) and how many new sign-ups actually buy a membership.
    Colours follow common industry ranges, but every gym should compare mostly with its own history."""
    from .models import Membership, User, Visit
    def money(v):
        return f"{v:,}".replace(",", " ")
    mem = Membership.objects.filter(user__is_superuser=False)
    active_ids = set(mem.filter(starts__lte=now, expires__gt=now).values_list("user", flat=True))
    active = len(active_ids)
    covered_later = set(mem.filter(expires__gt=now).values_list("user", flat=True))  # renewed in advance: not churn
    ended = set(mem.filter(expires__gte=now - timedelta(days=30), expires__lt=now).values_list("user", flat=True)) - covered_later
    base = active + len(ended)
    churn = round(len(ended) / base * 100) if base else 0
    visits = Visit.objects.filter(ts__gte=now - timedelta(days=28), user_id__in=active_ids).count()
    freq = round(visits / active / 4, 1) if active else 0
    arpu = revenue_month // active if active else 0
    new = User.objects.filter(is_superuser=False, created__gte=now - timedelta(days=30))
    new_n = new.count()
    bought = new.filter(memberships__isnull=False).distinct().count()
    conv = round(bought / new_n * 100) if new_n else 0
    total = User.objects.filter(is_superuser=False, is_active=True).count()
    return [
        {"name": "Faol a'zolar", "value": active, "unit": "", "tone": "", "note": f"jami {total} ta akkauntdan",
         "help": "Hozir amal qilayotgan abonementi bor odamlar soni."},
        {"name": "Ketib qolish (30 kun)", "value": churn, "unit": "%", "tone": "good" if churn <= 5 else "warn" if churn <= 10 else "bad",
         "note": f"{len(ended)} kishi uzaytirmadi",
         "help": "Abonementi oxirgi 30 kunda tugab, yangisini olmaganlar ulushi. Oyiga 5% dan pasti yaxshi; ularga «Shaxsiy xabar» yozing."},
        {"name": "Haftalik tashrif", "value": str(freq).replace(".", ","), "unit": "marta", "tone": "good" if freq >= 1.5 else "warn" if freq >= 1 else "bad",
         "note": "me'yor: haftasiga 1,5–3",
         "help": "Faol a'zo haftasiga o'rtacha necha marta keladi (oxirgi 4 hafta). Bu ko'rsatkich tushsa, odamlar tez orada ketishi mumkin."},
        {"name": "A'zo boshiga daromad", "value": money(arpu), "unit": "so'm", "tone": "", "note": "shu oy, faol a'zoga",
         "help": "Shu oydagi barcha tushum (abonement, do'kon, VIP) faol a'zolar soniga bo'lingan."},
        {"name": "Mehmondan a'zoga", "value": conv, "unit": "%", "tone": "good" if conv >= 20 else "warn" if conv >= 10 else "bad" if new_n else "",
         "note": f"30 kunda {new_n} yangi, {bought} tasi xarid qildi",
         "help": "Saytda ro'yxatdan o'tganlarning qanchasi abonement sotib olgani. 20–35% yaxshi deb hisoblanadi; qolganlarga taklif yuboring."},
    ]


def low_stock_rows():
    from . import services
    from .models import GymSettings, Product
    rows = Product.objects.filter(active=True, stock__lte=GymSettings.load().low_stock_threshold).order_by("stock")[:8]
    return [{"p": p, "need": services.restock_need(p)[0]} for p in rows]


def people_panels(now, today):
    """Who deserves a personal word today: birthdays, and paying members who stopped coming (a nudge keeps them)."""
    from .models import User, Visit
    members = User.objects.filter(is_superuser=False, is_active=True)
    birthdays = list(members.filter(birth_date__month=today.month, birth_date__day=today.day).order_by("first_name")[:12])
    for u in birthdays:
        u.turns = today.year - u.birth_date.year
    recent = Visit.objects.filter(ts__gte=now - timedelta(days=14)).values("user")
    away = list(members.filter(memberships__starts__lte=now, memberships__expires__gt=now).exclude(pk__in=recent)
                .annotate(last=Max("visits__ts")).distinct().order_by("last")[:8])
    return {"birthdays": birthdays, "birthday_ids": ",".join(str(u.pk) for u in birthdays),
            "away": away, "away_ids": ",".join(str(u.pk) for u in away)}


def extra_stats(now, today, revenue_month):
    """Live part of the dashboard: who is in the gym, today's classes, the monthly goal, a feed and the setup checklist."""
    from django.conf import settings
    from django.urls import reverse
    from . import click, services, sms, telegram
    from .models import Booking, GymClass, GymSettings, Order, Payment, Review, User, Visit
    gs = GymSettings.load()
    goal = gs.revenue_goal or 0
    classes = []
    for c in GymClass.objects.filter(active=True, weekday=today.weekday()).select_related("trainer"):
        n = Booking.objects.filter(gym_class=c, date=today).count()
        classes.append({"c": c, "n": n, "w": min(100, round(n / c.capacity * 100)) if c.capacity else 0})
    feed = []
    for u in User.objects.filter(is_superuser=False).order_by("-created")[:6]:
        feed.append({"ts": u.created, "icon": "＋", "cls": "green", "text": f"Yangi a'zo: {u.first_name} {u.last_name}", "url": reverse("admin:member", args=[u.pk])})
    for p in Payment.objects.select_related("user").order_by("-created")[:6]:
        feed.append({"ts": p.created, "icon": {"paid": "✓", "pending": "…"}.get(p.status, "×"),
                     "cls": "gold" if p.status == "pending" else ("green" if p.status == "paid" else ""),
                     "text": f"To'lov #{p.pk}: {p.amount:,} so'm · {p.get_status_display()}".replace(",", " ") + (f" · {p.user.first_name}" if p.user else ""),
                     "url": reverse("admin:gym_payment_change", args=[p.pk])})
    for o in Order.objects.select_related("user").order_by("-created")[:5]:
        feed.append({"ts": o.created, "icon": "🛒", "cls": "", "text": f"Buyurtma #{o.pk}: {o.total:,} so'm".replace(",", " ") + (f" · {o.user.first_name}" if o.user else ""),
                     "url": reverse("admin:gym_order_change", args=[o.pk])})
    for v in Visit.objects.select_related("user").order_by("-ts")[:6]:
        feed.append({"ts": v.ts, "icon": "→", "cls": "dark", "text": f"Zalga keldi: {v.user.first_name} {v.user.last_name}", "url": reverse("admin:member", args=[v.user_id])})
    for r in Review.objects.select_related("user").order_by("-created")[:4]:
        feed.append({"ts": r.created, "icon": "★", "cls": "gold", "text": f"Fikr {r.rating}/5: {r.user.first_name}" + ("" if r.approved else " · tasdiq kutmoqda"),
                     "url": reverse("admin:gym_review_change", args=[r.pk])})
    feed.sort(key=lambda x: x["ts"], reverse=True)
    hour = timezone.localtime(now).hour
    setup = [
        {"ok": bool(services.current_card()), "name": "To'lov kartasi", "hint": "A'zolar pulni shu kartaga o'tkazadi", "url": reverse("admin:gym_paymentcard_changelist")},
        {"ok": bool(gs.google_id()), "name": "Google bilan kirish", "hint": "Client ID kiriting (yo'riqnoma sozlamalarda)", "url": reverse("admin:gym_gymsettings_change", args=[gs.pk])},
        {"ok": sms.real_backend(), "name": "Haqiqiy SMS (Eskiz)", "hint": "Hozir kodlar ekranda ko'rsatiladi" if settings.DEBUG else "SMS_BACKEND=eskiz kerak", "url": ""},
        {"ok": telegram.enabled(), "name": "Telegram bot", "hint": "TELEGRAM_BOT_TOKEN: eslatma va xabarlar uchun", "url": ""},
        {"ok": click.enabled(), "name": "Click to'lovlari", "hint": "Onlayn to'lov uchun Click shartnomasi", "url": ""},
        {"ok": bool(gs.hero_video), "name": "Bosh sahifa videosi", "hint": "Sozlamalarda video yuklang", "url": reverse("admin:gym_gymsettings_change", args=[gs.pk])},
        {"ok": bool(gs.map_embed()), "name": "Xaritada zal", "hint": "Yandex Xarita havolasini sozlamalarga qo'ying", "url": reverse("admin:gym_gymsettings_change", args=[gs.pk])},
    ]
    from .models import PTSession, Trainer
    coaches = []
    for tr in Trainer.objects.filter(active=True).select_related("user"):
        pt = PTSession.objects.filter(trainer=tr, status="confirmed", starts__year=today.year, starts__month=today.month).count()
        bk = Booking.objects.filter(gym_class__trainer=tr, date__year=today.year, date__month=today.month).count()
        coaches.append({"t": tr, "pt": pt, "bk": bk, "score": pt * 3 + bk, "linked": bool(tr.user_id)})
    coaches.sort(key=lambda c: -c["score"])
    top = max([c["score"] for c in coaches] + [1])
    for c in coaches:
        c["w"] = max(4, round(c["score"] / top * 100))
    return {
        **people_panels(now, today),
        "coaches": coaches,
        "greeting": "Xayrli tong" if 5 <= hour < 12 else ("Xayrli kun" if hour < 18 else "Xayrli kech"),
        "goal": goal, "goal_pct": min(100, round(revenue_month / goal * 100)) if goal else 0, "goal_left": max(0, goal - revenue_month),
        "in_gym": Visit.objects.filter(ts__gte=now - timedelta(hours=2)).values("user").distinct().count(),
        "today_classes": classes, "feed": feed[:12], "setup": setup, "setup_done": sum(1 for s in setup if s["ok"]),
        "unapproved_reviews": Review.objects.filter(approved=False).count(),
    }


def member_data(user):
    from django.db.models import Sum as S
    from . import services
    from .models import Booking, Membership, Order, Payment, PTSession, VipPass, Visit
    now = timezone.now()
    ms = Membership.objects.filter(user=user).select_related("plan")
    active = ms.filter(starts__lte=now, expires__gt=now).first()
    vip = VipPass.objects.filter(user=user, starts__lte=now, expires__gt=now).order_by("-expires").first()
    visits = Visit.objects.filter(user=user)
    month_ago = now - timedelta(days=30)
    weeks = []  # visits per week for the last 12 weeks, oldest first
    start = timezone.localdate() - timedelta(days=timezone.localdate().weekday() + 77)
    counts = {}
    for v in visits.filter(ts__date__gte=start).values_list("ts", flat=True):
        k = (timezone.localtime(v).date() - start).days // 7
        counts[k] = counts.get(k, 0) + 1
    for i in range(12):
        weeks.append({"label": f"{start + timedelta(days=i * 7):%d.%m}", "v": counts.get(i, 0)})
    return {
        "m": user, "active": active, "vip": vip, "is_vip": services.is_vip(user),
        "days_left": (active.expires - now).days if active else 0,
        "memberships": ms[:10], "payments": Payment.objects.filter(user=user).select_related("plan")[:10],
        "orders": Order.objects.filter(user=user).prefetch_related("items")[:8],
        "visits": visits[:10], "visits_total": visits.count(), "visits_30": visits.filter(ts__gte=month_ago).count(),
        "spent": Payment.objects.filter(user=user, status="paid").aggregate(s=S("amount"))["s"] or 0,
        "bookings": Booking.objects.filter(user=user, date__gte=timezone.localdate()).select_related("gym_class")[:6],
        "pts": PTSession.objects.filter(user=user).select_related("trainer").order_by("-starts")[:6],
        "weeks": _bars(weeks), "referrals": user.referrals.count(),
        "notes": user.notifications.order_by("-created")[:5], "records": user.records.order_by("-date", "-id")[:6],
    }


AUDIENCES = [("all", "Barcha a'zolar"), ("active", "Faol abonementi borlar"), ("vip", "VIP a'zolar"),
             ("expiring", "Abonementi 7 kunda tugaydiganlar"), ("lapsed", "Abonementi tugaganlar (60 kun ichida)")]


def audience_qs(key):
    from .models import User
    now = timezone.now()
    qs = User.objects.filter(is_superuser=False, is_active=True)
    if key == "active":
        return qs.filter(memberships__starts__lte=now, memberships__expires__gt=now).distinct()
    if key == "vip":
        return qs.filter(vip_passes__starts__lte=now, vip_passes__expires__gt=now).distinct()
    annotated = qs.annotate(until=Max("memberships__expires"))
    if key == "expiring":
        return annotated.filter(until__gt=now, until__lte=now + timedelta(days=7))
    if key == "lapsed":
        return annotated.filter(until__gte=now - timedelta(days=60), until__lt=now)
    return qs


def global_search(q):
    from django.db.models import Q
    from .models import Order, Payment, Product, User
    q = q.strip()[:60]
    if len(q) < 2:
        return {}
    digits = "".join(ch for ch in q if ch.isdigit())
    uq = Q(first_name__icontains=q) | Q(last_name__icontains=q) | Q(email__icontains=q)
    parts = q.split()
    if len(parts) >= 2:
        uq |= Q(first_name__icontains=parts[0], last_name__icontains=parts[1]) | Q(first_name__icontains=parts[1], last_name__icontains=parts[0])
    if len(digits) >= 3:
        uq |= Q(phone__contains=digits)
    if q.upper().startswith("FZ-") and digits:
        uq |= Q(pk=int(digits))
    out = {"users": list(User.objects.filter(uq).annotate(until=Max("memberships__expires")).order_by("-created")[:20]),
           "products": list(Product.objects.filter(name__icontains=q)[:8])}
    num = q.lstrip("#")
    if num.isdigit():
        out["payments"] = list(Payment.objects.filter(pk=int(num)).select_related("user"))
        out["orders"] = list(Order.objects.filter(pk=int(num)).select_related("user"))
    out["total"] = sum(len(v) for v in out.values())
    return out


def _bars(rows, key="v"):
    top = max([r[key] for r in rows] + [1])
    for r in rows:
        r["h"] = max(3, round(r[key] / top * 100)) if r[key] else 3
    return rows


def _months(n):
    """First day of each of the last n months, oldest first."""
    d = timezone.localdate().replace(day=1)
    out = []
    for _ in range(n):
        out.append(d)
        d = (d - timedelta(days=1)).replace(day=1)
    return out[::-1]


def report_data():
    from .models import Membership, OrderItem, Payment, User, Visit
    months = _months(12)
    first = months[0]
    rev = {r["m"].date() if hasattr(r["m"], "date") else r["m"]: r["s"] for r in
           Payment.objects.filter(status="paid", created__date__gte=first).annotate(m=TruncMonth("created")).values("m").annotate(s=Sum("amount"))}
    new = {r["m"].date() if hasattr(r["m"], "date") else r["m"]: r["c"] for r in
           User.objects.filter(is_superuser=False, created__date__gte=first).annotate(m=TruncMonth("created")).values("m").annotate(c=Count("id"))}
    revenue = _bars([{"label": f"{m:%m.%y}", "v": rev.get(m, 0)} for m in months])
    members = _bars([{"label": f"{m:%m.%y}", "v": new.get(m, 0)} for m in months])
    since = timezone.now() - timedelta(days=90)
    weekday_names = ["Du", "Se", "Ch", "Pa", "Ju", "Sh", "Ya"]
    wd = {r["d"]: r["c"] for r in Visit.objects.filter(ts__gte=since).annotate(d=ExtractWeekDay("ts")).values("d").annotate(c=Count("id"))}
    by_weekday = _bars([{"label": weekday_names[i], "v": wd.get(((i + 1) % 7) + 1, 0)} for i in range(7)])  # Django: 1=Sunday
    hr = {r["h"]: r["c"] for r in Visit.objects.filter(ts__gte=since).annotate(h=ExtractHour("ts")).values("h").annotate(c=Count("id"))}
    by_hour = _bars([{"label": f"{h:02d}", "v": hr.get(h, 0)} for h in range(5, 24)])
    amount = ExpressionWrapper(F("price") * F("qty"), output_field=BigIntegerField())
    products = list(OrderItem.objects.filter(order__created__gte=since).values("name").annotate(sold=Sum("qty"), total=Sum(amount)).order_by("-total")[:8])
    plans = list(Payment.objects.filter(status="paid", kind="plan").values("plan__name").annotate(c=Count("id"), total=Sum("amount")).order_by("-total"))
    now = timezone.now()
    lapsed = (User.objects.filter(is_superuser=False).annotate(until=Max("memberships__expires"))
              .filter(until__gte=now - timedelta(days=60), until__lt=now))
    ended = Membership.objects.filter(expires__gte=now - timedelta(days=60), expires__lt=now).values("user").distinct().count()
    renewed = ended - lapsed.count()
    this_m, prev_m = revenue[-1]["v"], revenue[-2]["v"]
    top_product = max([p["total"] or 0 for p in products] + [1])
    for p in products:
        p["w"] = max(4, round((p["total"] or 0) / top_product * 100))
    top_plan = max([p["total"] or 0 for p in plans] + [1])
    for p in plans:
        p["w"] = max(4, round((p["total"] or 0) / top_plan * 100))
    busiest_day = max(by_weekday, key=lambda r: r["v"]) if any(r["v"] for r in by_weekday) else None
    busiest_hour = max(by_hour, key=lambda r: r["v"]) if any(r["v"] for r in by_hour) else None
    return {"revenue": revenue, "members": members, "by_weekday": by_weekday, "by_hour": by_hour, "products": products, "plans": plans,
            "ended": ended, "renewed": max(0, renewed), "lapsed": list(lapsed.order_by("until")[:15]),
            "renewal_rate": round(max(0, renewed) / ended * 100) if ended else None,
            "kpi": {"rev_this": this_m, "rev_prev": prev_m, "rev_change": round((this_m - prev_m) / prev_m * 100) if prev_m else None,
                    "new_this": members[-1]["v"], "year_total": sum(r["v"] for r in revenue),
                    "busiest_day": busiest_day["label"] if busiest_day else "—", "busiest_hour": f"{busiest_hour['label']}:00" if busiest_hour else "—"}}


SECTIONS = [  # the sidebar groups the gym's many tables by job instead of one long alphabetical list
    ("A'zolar", ["user", "membership", "vippass", "guestpass", "visit", "bodylog", "personalrecord"]),
    ("Moliya", ["payment", "paymentcard", "plan", "promocode"]),
    ("Do'kon", ["order", "product", "category"]),
    ("Mashg'ulotlar", ["gymclass", "booking", "trainer", "ptsession", "workoutplan", "workouttype", "lesson"]),
    ("Muloqot", ["notification", "chatmessage", "chatreport", "announcement", "review"]),
    ("Sozlamalar", ["gymsettings"]),
]


class GymAdminSite(admin.AdminSite):
    site_header = "Fitnes Zal · Admin"
    site_title = "Fitnes Zal"
    index_title = "Boshqaruv paneli"
    index_template = "admin/dashboard.html"

    def get_app_list(self, request, app_label=None):
        apps = super().get_app_list(request, app_label)
        gym = next((a for a in apps if a["app_label"] == "gym"), None)
        if app_label is not None or not gym:
            return apps  # the per-app page keeps Django's own shape
        by_name = {m["object_name"].lower(): m for m in gym["models"]}
        out, used = [], set()
        for title, names in SECTIONS:
            models = [by_name[n] for n in names if n in by_name]
            used.update(n for n in names if n in by_name)
            if models:
                out.append({**gym, "name": title, "models": models})
        rest = [m for n, m in by_name.items() if n not in used]
        if rest:
            out.append({**gym, "name": "Boshqa", "models": rest})
        return out + [a for a in apps if a["app_label"] != "gym"]

    def index(self, request, extra_context=None):
        extra = dashboard_stats()
        extra.update(extra_context or {})
        return super().index(request, extra)

    def get_urls(self):
        return [path("reports/", self.admin_view(self.reports_view), name="reports"),
                path("reports/csv/", self.admin_view(self.reports_csv), name="reports_csv"),
                path("search/", self.admin_view(self.search_view), name="search"),
                path("member/<int:pk>/", self.admin_view(self.member_view), name="member"),
                path("broadcast/", self.admin_view(self.broadcast_view), name="broadcast"),
                path("message/", self.admin_view(self.message_view), name="message"),
                path("live/", self.admin_view(self.live_view), name="live"),
                path("schedule/", self.admin_view(self.schedule_view), name="schedule"),
                path("cash/", self.admin_view(self.cash_view), name="cash")] + super().get_urls()

    def schedule_view(self, request):
        """The week's group classes as a timetable, with how full each one is."""
        from .models import Booking, GymClass
        try:
            shift = max(-4, min(8, int(request.GET.get("w", 0))))
        except ValueError:
            shift = 0
        today = timezone.localdate()
        monday = today - timedelta(days=today.weekday()) + timedelta(weeks=shift)
        dates = [monday + timedelta(days=i) for i in range(7)]
        counts = {(r["gym_class"], r["date"]): r["n"] for r in Booking.objects.filter(date__range=(dates[0], dates[-1]))
                  .values("gym_class", "date").annotate(n=Count("id"))}
        cols = []
        for i, d in enumerate(dates):
            items = []
            for c in GymClass.objects.filter(active=True, weekday=i).select_related("trainer").order_by("start_time"):
                n = counts.get((c.pk, d), 0)
                items.append({"c": c, "n": n, "w": min(100, round(n / c.capacity * 100)) if c.capacity else 0})
            cols.append({"d": d, "name": GymClass.WEEKDAYS[i][1], "today": d == today, "items": items})
        ctx = {**self.each_context(request), "title": "Haftalik jadval", "cols": cols, "shift": shift, "monday": monday, "sunday": dates[-1],
               "total": sum(counts.values())}
        return TemplateResponse(request, "admin/schedule.html", ctx)

    def cash_view(self, request):
        """End-of-day cash-up: what was paid on a day, by method, plus what still waits for confirmation."""
        from django.utils.dateparse import parse_date
        from .models import Order, Payment
        try:
            day = parse_date(request.GET.get("d", "") or "") or timezone.localdate()
        except ValueError:  # e.g. ?d=2026-02-30: show today instead of crashing
            day = timezone.localdate()
        paid = Payment.objects.filter(status="paid", created__date=day).select_related("user", "plan")
        labels = {"cash": "Naqd", "card": "Karta o'tkazmasi", "click": "Click", "payme": "Payme", "uzum": "Uzum"}
        by_method = [{"m": labels.get(r["method"], r["method"]), "n": r["n"], "s": r["s"]}
                     for r in paid.values("method").annotate(n=Count("id"), s=Sum("amount")).order_by("-s")]
        kinds = {r["kind"]: r["s"] for r in paid.values("kind").annotate(s=Sum("amount"))}
        ctx = {**self.each_context(request), "title": "Kassa hisoboti", "day": day, "prev": day - timedelta(days=1), "next": day + timedelta(days=1),
               "is_today": day == timezone.localdate(), "total": sum(r["s"] for r in by_method), "count": paid.count(), "by_method": by_method,
               "kinds": [{"k": {"plan": "Abonementlar", "shop": "Do'kon", "vip": "VIP"}.get(k, k), "s": s} for k, s in kinds.items()],
               "payments": paid.order_by("-created")[:100], "pending": Payment.objects.filter(status="pending").count(),
               "handed": Order.objects.filter(status="done", done_at__date=day).count()}
        top = max([r["s"] for r in by_method] + [1])
        for r in by_method:
            r["w"] = max(4, round(r["s"] / top * 100))
        return TemplateResponse(request, "admin/cash.html", ctx)

    def live_view(self, request):
        """Small numbers the dashboard refreshes every 20 seconds without reloading the page."""
        from django.http import JsonResponse
        from .models import Order, Payment, Visit
        now, today = timezone.now(), timezone.localdate()
        paid = Payment.objects.filter(status="paid")
        return JsonResponse({
            "in_gym": Visit.objects.filter(ts__gte=now - timedelta(hours=2)).values("user").distinct().count(),
            "visits_today": Visit.objects.filter(ts__date=today).count(),
            "revenue_today": paid.filter(created__date=today).aggregate(s=Sum("amount"))["s"] or 0,
            "revenue_month": paid.filter(created__year=today.year, created__month=today.month).aggregate(s=Sum("amount"))["s"] or 0,
            "pending_payments": Payment.objects.filter(status="pending").count(),
            "new_orders": Order.objects.filter(status="new").count(),
            "time": timezone.localtime(now).strftime("%H:%M:%S"),
        })

    def search_view(self, request):
        q = request.GET.get("q", "")
        res = global_search(q)
        if res.get("total") == 1 and res["users"]:  # one exact hit: open the member card straight away
            from django.shortcuts import redirect
            return redirect("admin:member", res["users"][0].pk)
        ctx = {**self.each_context(request), "title": "Qidiruv", "q": q, "res": res, "now": timezone.now()}
        return TemplateResponse(request, "admin/search.html", ctx)

    def member_view(self, request, pk):
        from django.shortcuts import get_object_or_404
        from .models import User
        user = get_object_or_404(User, pk=pk)
        ctx = {**self.each_context(request), "title": f"{user.first_name} {user.last_name}", **member_data(user)}
        return TemplateResponse(request, "admin/member.html", ctx)

    def broadcast_view(self, request):
        from django.contrib import messages
        from django.shortcuts import redirect
        from . import telegram
        from .models import Announcement
        counts = {k: audience_qs(k).count() for k, _ in AUDIENCES}
        tg_counts = {k: audience_qs(k).exclude(telegram_chat_id=None).count() for k, _ in AUDIENCES}
        form = {"title": "", "body": "", "audience": "all", "announce": True, "tg": telegram.enabled()}
        error = None
        if request.method == "POST":
            form = {"title": request.POST.get("title", "").strip()[:100], "body": request.POST.get("body", "").strip()[:2000],
                    "audience": request.POST.get("audience", "all"), "announce": bool(request.POST.get("announce")), "tg": bool(request.POST.get("tg"))}
            if form["audience"] not in counts:
                form["audience"] = "all"
            if not form["title"] or not form["body"]:
                error = "Sarlavha va matnni yozing."
            elif not (form["announce"] or form["tg"]):
                error = "Kamida bitta kanalni tanlang: saytdagi e'lon yoki Telegram."
            else:
                done = []
                if form["announce"]:
                    Announcement.objects.create(title=form["title"], body=form["body"])
                    done.append("saytga e'lon qo'yildi")
                if form["tg"]:
                    if not telegram.enabled():
                        done.append("Telegram bot ulanmagani uchun Telegramga yuborilmadi")
                    else:
                        sent = 0
                        for u in audience_qs(form["audience"]).exclude(telegram_chat_id=None)[:2000]:
                            if telegram.send(u.telegram_chat_id, f"{form['title']}\n\n{form['body']}"):
                                sent += 1
                        done.append(f"Telegramda {sent} kishiga yuborildi")
                messages.success(request, "Tayyor: " + ", ".join(done) + ".")
                return redirect("admin:broadcast")
        ctx = {**self.each_context(request), "title": "Xabar yuborish", "form": form, "error": error, "tg_on": telegram.enabled(),
               "audiences": [{"key": k, "name": n, "n": counts[k], "tg": tg_counts[k]} for k, n in AUDIENCES],
               "recent": Announcement.objects.all()[:6]}
        return TemplateResponse(request, "admin/broadcast.html", ctx)

    def message_view(self, request):
        """A personal message to one member or a hand-picked few. It always lands in their inbox on the site (the bell),
        and optionally also goes by Telegram and SMS. {ism} in the text becomes each person's first name."""
        from django.contrib import messages
        from django.shortcuts import redirect
        from . import services, sms, telegram
        from .models import Notification, User
        raw = request.POST.getlist("ids") if request.method == "POST" else request.GET.get("ids", "").split(",")
        ids = {int(x) for x in raw if str(x).strip().isdigit()}
        aud = request.GET.get("aud", "")
        if aud in dict(AUDIENCES):  # "add a whole group" shortcut, still editable one by one afterwards
            ids |= set(audience_qs(aud).values_list("pk", flat=True)[:300])
        people = list(User.objects.filter(pk__in=ids, is_active=True).order_by("first_name", "last_name")[:300])
        ids = [u.pk for u in people]
        q = request.GET.get("q", "")
        found = [u for u in global_search(q).get("users", []) if u.pk not in ids and u.is_active][:12]
        form = {"title": "", "body": "", "tg": telegram.enabled(), "sms": False}
        error = None
        if request.method == "POST":
            form = {"title": request.POST.get("title", "").strip()[:120], "body": request.POST.get("body", "").strip()[:2000],
                    "tg": bool(request.POST.get("tg")), "sms": bool(request.POST.get("sms"))}
            if not people:
                error = "Kamida bitta qabul qiluvchini tanlang."
            elif not form["title"]:
                error = "Sarlavhani yozing."
            else:
                n = {"site": 0, "tg": 0, "sms": 0}
                for u in people:
                    def fill(s):
                        return s.replace("{ism}", u.first_name or "")
                    sent = services.notify(u, fill(form["title"]), fill(form["body"]), sender=request.user,
                                           telegram_too=form["tg"], sms_too=form["sms"])
                    for k in n:
                        n[k] += bool(sent.get(k))
                parts = [f"{n['site']} kishining xabarlar qutisiga tushdi"]
                if form["tg"]:
                    parts.append(f"Telegramda {n['tg']} ta")
                if form["sms"]:
                    parts.append(f"SMS {n['sms']} ta")
                messages.success(request, "Yuborildi: " + ", ".join(parts) + ".")
                if len(people) == 1:
                    return redirect("admin:member", people[0].pk)
                return redirect("admin:message")
        recent = (Notification.objects.filter(sender__isnull=False).select_related("user", "sender").order_by("-created")[:10])
        ctx = {**self.each_context(request), "title": "Shaxsiy xabar", "people": people, "ids": ids, "ids_csv": ",".join(map(str, ids)),
               "q": q, "found": found, "form": form, "error": error, "tg_on": telegram.enabled(), "sms_backend": sms.backend(),
               "audiences": AUDIENCES, "recent": recent,
               "tg_count": sum(1 for u in people if u.telegram_chat_id), "phone_count": sum(1 for u in people if u.phone)}
        return TemplateResponse(request, "admin/message.html", ctx)

    def reports_view(self, request):
        ctx = {**self.each_context(request), "title": "Hisobotlar", **report_data()}
        return TemplateResponse(request, "admin/reports.html", ctx)

    def reports_csv(self, request):
        data = report_data()
        resp = HttpResponse(content_type="text/csv; charset=utf-8")
        resp["Content-Disposition"] = 'attachment; filename="hisobot.csv"'
        resp.write("﻿")
        w = csv.writer(resp)
        w.writerow(["oy", "tushum (so'm)", "yangi a'zolar"])
        for a, b in zip(data["revenue"], data["members"]):
            w.writerow([a["label"], a["v"], b["v"]])
        return resp
