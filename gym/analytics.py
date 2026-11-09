"""AI Analitika: the numbers behind /django-admin/analytics/ and the offline assistant (analytics_ai.py).

Everything here is one or two aggregate queries per block (TruncDate / TruncHour / TruncMonth + Sum / Count), never a query per row,
and every block is cached for 60 seconds per period. A period is always a closed range of local dates; the "previous period" is the
equally long range right before it, which is what every delta on the page compares against."""
import csv
import math
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from django.core.cache import cache
from django.db.models import Count, Exists, ExpressionWrapper, F, Max, OuterRef, Q, Subquery, Sum
from django.db.models.fields import BigIntegerField
from django.db.models.functions import ExtractHour, ExtractWeekDay, TruncDate, TruncHour, TruncMonth
from django.urls import reverse
from django.utils import timezone

CACHE_TTL = 60
MAX_DAYS = 800
PRESETS = [("today", "Bugun", 1), ("7d", "7 kun", 7), ("30d", "30 kun", 30), ("3m", "3 oy", 90), ("12m", "12 oy", 365)]
PRESET_DAYS = {k: d for k, _, d in PRESETS}
WEEKDAYS = ["Du", "Se", "Ch", "Pa", "Ju", "Sh", "Ya"]
WEEKDAYS_LONG = ["Dushanba", "Seshanba", "Chorshanba", "Payshanba", "Juma", "Shanba", "Yakshanba"]
MONTHS_UZ = ["yanvar", "fevral", "mart", "aprel", "may", "iyun", "iyul", "avgust", "sentabr", "oktyabr", "noyabr", "dekabr"]
METHOD_LABELS = {"cash": "Naqd", "card": "Karta o'tkazmasi", "click": "Click", "payme": "Payme", "uzum": "Uzum", "gift": "Sertifikat"}
KIND_LABELS = {"plan": "Abonement", "shop": "Do'kon", "gift": "Sertifikat"}
REMINDER_TITLE = "Abonementingiz tez orada tugaydi"


def money(n):
    return f"{int(n or 0):,}".replace(",", " ")


def _start_of(d):
    return timezone.make_aware(datetime.combine(d, time.min))


@dataclass(frozen=True)
class Period:
    key: str
    start: date
    end: date

    @property
    def days(self):
        return (self.end - self.start).days + 1

    @property
    def start_dt(self):
        return _start_of(self.start)

    @property
    def end_dt(self):  # exclusive: the first instant after the last day
        return _start_of(self.end + timedelta(days=1))

    @property
    def prev(self):
        n = self.days
        return Period("prev", self.start - timedelta(days=n), self.start - timedelta(days=1))

    @property
    def gran(self):
        return "hour" if self.days == 1 else ("day" if self.days <= 92 else "month")

    @property
    def label(self):
        if self.days == 1:
            return "Bugun" if self.end == timezone.localdate() else f"{self.end:%d.%m.%Y}"
        return f"{self.start:%d.%m.%Y} – {self.end:%d.%m.%Y}"

    def as_dict(self):
        pv = self.prev
        return {"key": self.key, "start": self.start.isoformat(), "end": self.end.isoformat(), "days": self.days, "gran": self.gran,
                "label": self.label, "prev_start": pv.start.isoformat(), "prev_end": pv.end.isoformat(),
                "presets": [{"key": k, "label": lab} for k, lab, _ in PRESETS]}


def parse_period(key=None, frm=None, to=None, today=None):
    """A preset key (bugun, 7d, ...) or a custom from/to pair (ISO dates). Anything unreadable falls back to the last 30 days."""
    today = today or timezone.localdate()
    key = (key or "").strip().lower()
    if key in PRESET_DAYS:
        n = PRESET_DAYS[key]
        return Period(key, today - timedelta(days=n - 1), today)
    if frm or to:
        try:
            a = date.fromisoformat(str(frm)[:10]) if frm else None
            b = date.fromisoformat(str(to)[:10]) if to else None
        except ValueError:
            a = b = None
        if a or b:
            a, b = a or b, b or a
            if a > b:
                a, b = b, a
            b = min(b, today)
            a = max(min(a, b), b - timedelta(days=MAX_DAYS - 1))
            return Period("custom", a, b)
    return Period("30d", today - timedelta(days=29), today)


def period_from_request(params):
    return parse_period(params.get("period"), params.get("from"), params.get("to"))


# ---------- bucket helpers ----------
def _bucket_key(v, gran):
    if gran == "day":
        return v
    v = timezone.localtime(v) if timezone.is_aware(v) else v
    return v.hour if gran == "hour" else v.date().replace(day=1)


def buckets(p):
    """[(key, label, instant_after_bucket)] in order; the instant is capped at now, so a snapshot never looks into the future."""
    now = timezone.now()
    out = []
    if p.gran == "hour":
        for h in range(24):
            out.append((h, f"{h:02d}", min(now, p.start_dt + timedelta(hours=h + 1))))
    elif p.gran == "day":
        for i in range(p.days):
            d = p.start + timedelta(days=i)
            out.append((d, f"{d:%d.%m}", min(now, _start_of(d + timedelta(days=1)))))
    else:
        d = p.start.replace(day=1)
        while d <= p.end:
            nxt = (d.replace(day=28) + timedelta(days=4)).replace(day=1)
            out.append((d, f"{d:%m.%y}", min(now, _start_of(min(nxt, p.end + timedelta(days=1))))))
            d = nxt
    return out


def _grouped(qs, field, gran, *extra, **aggs):
    fn = {"hour": TruncHour, "day": TruncDate, "month": TruncMonth}[gran]
    for r in qs.annotate(b=fn(field)).values("b", *extra).annotate(**aggs):
        r["k"] = _bucket_key(r["b"], gran)
        yield r


def _cached(name, p, fn):
    ck = f"fz_an:{name}:{p.start}:{p.end}"
    got = cache.get(ck)
    if got is None:
        got = fn(p)
        cache.set(ck, got, CACHE_TTL)
    return got


# ---------- base querysets ----------
def paid_in(p):
    from .models import Payment
    return Payment.objects.filter(status="paid", created__gte=p.start_dt, created__lt=p.end_dt)


def members_qs():
    from .models import User
    return User.objects.filter(is_superuser=False)


def totals(p):
    """Revenue, shop revenue, paid count, new members and visits of one period: four cheap aggregates."""
    from .models import Visit
    a = paid_in(p).aggregate(rev=Sum("amount"), n=Count("id"), shop=Sum("amount", filter=Q(kind="shop")))
    rev, n, shop = a["rev"] or 0, a["n"], a["shop"] or 0
    return {"revenue": rev, "paid_n": n, "shop": shop, "avg_check": rev // n if n else 0,
            "new_members": members_qs().filter(created__gte=p.start_dt, created__lt=p.end_dt).count(),
            "visits": Visit.objects.filter(ts__gte=p.start_dt, ts__lt=p.end_dt).count()}


def active_at(instant):
    from .models import Membership
    return (Membership.objects.filter(user__is_superuser=False, starts__lte=instant, expires__gt=instant).values("user").distinct().count())


def frozen_rows(p):
    from .models_extra import MembershipFreeze
    return list(MembershipFreeze.objects.filter(start_date__lte=p.end, end_date__gt=p.start - timedelta(days=1))
                .values_list("membership__user_id", "start_date", "end_date")[:20000])


def frozen_at(rows, d):
    return len({u for u, s, e in rows if s <= d < e})


def renewal(p):
    """(ended, renewed): people whose membership ran out inside the period, and how many of them hold one that reaches past it."""
    from .models import Membership
    cut = min(p.end_dt, timezone.now())
    window = Membership.objects.filter(user__is_superuser=False, expires__gte=p.start_dt, expires__lt=cut)
    lasts = Membership.objects.filter(user__in=window.values("user")).values("user").annotate(m=Max("expires")).values_list("m", flat=True)
    ended = renewed = 0
    for m in lasts:
        ended += 1
        renewed += m >= cut
    return ended, renewed


# ---------- series (revenue / members / visits per bucket) ----------
def _series(p):
    from .models import Visit
    keys = [b[0] for b in buckets(p)]
    rev = {k: {"plan": 0, "shop": 0, "n": 0} for k in keys}
    for r in _grouped(paid_in(p), "created", p.gran, "kind", s=Sum("amount"), c=Count("id")):
        slot = rev.get(r["k"])
        if slot is not None:
            slot["shop" if r["kind"] == "shop" else "plan"] += r["s"] or 0
            slot["n"] += r["c"]
    mem = {k: 0 for k in keys}
    for r in _grouped(members_qs().filter(created__gte=p.start_dt, created__lt=p.end_dt), "created", p.gran, c=Count("id")):
        if r["k"] in mem:
            mem[r["k"]] += r["c"]
    vis = {k: 0 for k in keys}
    for r in _grouped(Visit.objects.filter(ts__gte=p.start_dt, ts__lt=p.end_dt), "ts", p.gran, c=Count("id")):
        if r["k"] in vis:
            vis[r["k"]] += r["c"]
    return {"keys": keys, "rev": rev, "mem": mem, "vis": vis}


def series(p):
    return _cached("series", p, _series)


# ---------- sections ----------
def _delta(cur, prev):
    """Percent change, or None when there is nothing to compare with."""
    if cur is None or prev is None or not prev:
        return None
    return round((cur - prev) / prev * 100, 1)


def kpis(p):
    return _cached("kpis", p, _kpis)


def _kpis(p):
    pv = p.prev
    cur, old = totals(p), totals(pv)
    bs = buckets(p)
    s = series(p)
    now = timezone.now()
    ended, renewed = renewal(p)
    p_ended, p_renewed = renewal(pv)
    rate = round(renewed / ended * 100) if ended else None
    p_rate = round(p_renewed / p_ended * 100) if p_ended else None
    today = timezone.localdate()
    frows = frozen_rows(p)
    def sample(seq):  # long ranges: 24 evenly spaced points instead of one query per day
        if len(seq) <= 24:
            return list(seq)
        step = len(seq) / 24
        return [seq[min(len(seq) - 1, int((i + 1) * step) - 1)] for i in range(24)]

    actives = [active_at(inst) for _, _, inst in sample(bs)]
    act_now = active_at(min(now, p.end_dt))
    act_prev = active_at(min(now, pv.end_dt))
    fro_now = frozen_at(frows, min(today, p.end))
    fro_prev = frozen_at(frows, pv.end)
    frozen_spark = [frozen_at(frows, min(today, timezone.localtime(inst - timedelta(microseconds=1)).date())) for _, _, inst in bs]
    frozen_spark = sample(frozen_spark)
    rev_s = [s["rev"][k]["plan"] + s["rev"][k]["shop"] for k in s["keys"]]
    defs = [
        ("revenue", "Tushum", "money", "so'm", True, cur["revenue"], old["revenue"], rev_s, "Davrdagi barcha to'langan to'lovlar yig'indisi."),
        ("new_members", "Yangi a'zolar", "int", "", True, cur["new_members"], old["new_members"], [s["mem"][k] for k in s["keys"]], "Ro'yxatdan o'tgan yangi a'zolar."),
        ("active", "Faol abonementlar", "int", "", True, act_now, act_prev, actives, "Davr oxirida amal qilayotgan abonementi bor odamlar."),
        ("visits", "Tashriflar", "int", "", True, cur["visits"], old["visits"], [s["vis"][k] for k in s["keys"]], "Zalga kirishlar soni."),
        ("avg_check", "O'rtacha chek", "money", "so'm", True, cur["avg_check"], old["avg_check"],
         [(s["rev"][k]["plan"] + s["rev"][k]["shop"]) // s["rev"][k]["n"] if s["rev"][k]["n"] else 0 for k in s["keys"]], "Tushum bo'lingan to'lovlar soniga."),
        ("shop", "Do'kon savdosi", "money", "so'm", True, cur["shop"], old["shop"], [s["rev"][k]["shop"] for k in s["keys"]], "Mahsulot sotuvidan tushum."),
        ("renewal", "Uzaytirish ulushi", "pct", "%", True, rate, p_rate, None,
         f"Davrda abonementi tugaganlarning {ended} nafaridan {renewed} nafari uzaytirgan."),
        ("frozen", "Muzlatilganlar", "int", "", None, fro_now, fro_prev, frozen_spark, "Davr oxirida muzlatilgan abonementlar."),
    ]
    out = []
    for key, label, fmt, unit, good, val, prev, spark, hint in defs:
        d = (round(val - prev, 1) if (val is not None and prev is not None) else None) if fmt == "pct" else _delta(val, prev)
        out.append({"key": key, "label": label, "fmt": fmt, "unit": unit, "value": val, "prev": prev, "delta": d, "delta_kind": "pp" if fmt == "pct" else "pct",
                    "up_is_good": good, "spark": spark, "hint": hint,
                    "display": "—" if val is None else (money(val) if fmt == "money" else f"{val}%" if fmt == "pct" else str(val))})
    return {"cards": out, "churn": max(0, ended - renewed), "ended": ended, "renewed": renewed}


def revenue_section(p):
    def build(p):
        s = series(p)
        rows = []
        for k, lab, _ in buckets(p):
            r = s["rev"][k]
            rows.append({"label": lab, "membership": r["plan"], "shop": r["shop"], "total": r["plan"] + r["shop"]})
        tot = sum(r["total"] for r in rows)
        return {"gran": p.gran, "rows": rows, "total": tot, "membership": sum(r["membership"] for r in rows), "shop": sum(r["shop"] for r in rows)}
    return _cached("revenue", p, build)


def members_section(p):
    def build(p):
        s = series(p)
        rows = [{"label": lab, "value": s["mem"][k]} for k, lab, _ in buckets(p)]
        return {"gran": p.gran, "rows": rows, "total": sum(r["value"] for r in rows)}
    return _cached("members", p, build)


def plans_section(p):
    def build(p):
        from .models import Membership
        sold = {r["plan__name"]: r["c"] for r in Membership.objects.filter(user__is_superuser=False, starts__gte=p.start_dt, starts__lt=p.end_dt)
                .values("plan__name").annotate(c=Count("id"))}
        paid = {r["plan__name"]: r["s"] for r in paid_in(p).filter(kind="plan").values("plan__name").annotate(s=Sum("amount"))}
        rows = [{"label": n or "—", "value": c, "revenue": paid.get(n, 0)} for n, c in sorted(sold.items(), key=lambda x: (-x[1], x[0] or ""))]
        return {"rows": rows, "total": sum(r["value"] for r in rows)}
    return _cached("plans", p, build)


def methods_section(p):
    def build(p):
        rows = [{"key": r["method"], "label": METHOD_LABELS.get(r["method"], r["method"] or "—"), "value": r["s"] or 0, "count": r["c"]}
                for r in paid_in(p).values("method").annotate(s=Sum("amount"), c=Count("id")).order_by("-s")]
        return {"rows": rows, "total": sum(r["value"] for r in rows)}
    return _cached("methods", p, build)


def heatmap(p):
    from .models import Visit
    matrix = [[0] * 24 for _ in range(7)]
    qs = Visit.objects.filter(ts__gte=p.start_dt, ts__lt=p.end_dt).annotate(wd=ExtractWeekDay("ts"), h=ExtractHour("ts"))
    for r in qs.values("wd", "h").annotate(c=Count("id")):
        matrix[(r["wd"] + 5) % 7][r["h"]] += r["c"]  # Django: 1 = Sunday; we want 0 = Monday
    return matrix


def visits_section(p):
    def build(p):
        m = heatmap(p)
        day = [sum(row) for row in m]
        hour = [sum(m[d][h] for d in range(7)) for h in range(24)]
        used = [h for h in range(24) if hour[h]]
        lo, hi = (min(used), max(used)) if used else (6, 22)
        lo, hi = min(lo, 6), max(hi, 22)
        return {"weekday": [{"label": WEEKDAYS[i], "full": WEEKDAYS_LONG[i], "value": day[i]} for i in range(7)],
                "hours": [{"label": f"{h:02d}", "value": hour[h]} for h in range(lo, hi + 1)],
                "heatmap": {"hours": [f"{h:02d}" for h in range(lo, hi + 1)], "days": WEEKDAYS, "matrix": [row[lo:hi + 1] for row in m],
                            "max": max([max(row) for row in m] + [0])},
                "total": sum(day), "peak_hour": (max(range(24), key=lambda h: hour[h]) if used else None),
                "peak_day": (max(range(7), key=lambda d: day[d]) if sum(day) else None)}
    return _cached("visits", p, build)


def products_section(p):
    def build(p):
        from .models import OrderItem
        amount = ExpressionWrapper(F("price") * F("qty"), output_field=BigIntegerField())
        qs = OrderItem.objects.filter(order__created__gte=p.start_dt, order__created__lt=p.end_dt).exclude(order__status="cancelled")
        rows = [{"label": r["name"], "value": r["sold"] or 0, "revenue": r["total"] or 0, "id": r["pid"]}
                for r in qs.values("name").annotate(sold=Sum("qty"), total=Sum(amount), pid=Max("product_id")).order_by("-total")[:8]]
        for r in rows:
            r["url"] = reverse("admin:gym_product_change", args=[r["id"]]) if r["id"] else ""
        return {"rows": rows, "total": sum(r["revenue"] for r in rows)}
    return _cached("products", p, build)


def stock_section(p=None):
    """Active products at or under the alert threshold, with how many to bring (same formula as services.restock_need, one query for all)."""
    def build(_):
        from .models import GymSettings, OrderItem, Product
        gs = GymSettings.load()
        prods = list(Product.objects.filter(active=True, stock__lte=gs.low_stock_threshold).order_by("stock", "name")[:12])
        since = timezone.now() - timedelta(days=30)
        sold = {r["product"]: r["s"] for r in OrderItem.objects.filter(product__in=[x.pk for x in prods], order__created__gte=since)
                .exclude(order__status="cancelled").values("product").annotate(s=Sum("qty"))}
        rows = []
        for x in prods:
            target = max(gs.low_stock_threshold * 4, math.ceil(sold.get(x.pk, 0) / 30 * 14))
            rows.append({"id": x.pk, "label": x.name, "stock": x.stock, "need": max(1, target - x.stock),
                         "url": reverse("admin:gym_product_change", args=[x.pk])})
        return {"rows": rows, "total": len(rows), "threshold": gs.low_stock_threshold}
    return _cached("stock", Period("x", date(2000, 1, 1), date(2000, 1, 1)), build)


def expiring_qs(days=7, now=None):
    now = now or timezone.now()
    return (members_qs().filter(is_active=True).annotate(until=Max("memberships__expires"))
            .filter(until__gt=now, until__lte=now + timedelta(days=days)))


def expiring_section(p=None):
    def build(_):
        now = timezone.now()
        qs = expiring_qs(7, now)
        rows = []
        for u in qs.order_by("until")[:40]:
            rows.append({"id": u.pk, "label": f"{u.first_name} {u.last_name}".strip() or u.username, "phone": u.phone or "",
                         "until": timezone.localtime(u.until).strftime("%d.%m.%Y"), "days": max(0, (u.until - now).days),
                         "url": reverse("admin:member", args=[u.pk])})
        return {"rows": rows, "total": qs.count()}
    return _cached("expiring", Period("x", date(2000, 1, 1), date(2000, 1, 1)), build)


def at_risk_qs(days=14, now=None):
    """Members whose membership is running but who have not come for `days` days (and are not on a freeze)."""
    from .models import Membership, Visit
    from .models_extra import MembershipFreeze
    now = now or timezone.now()
    today = timezone.localdate()
    live = Membership.objects.filter(user=OuterRef("pk"), starts__lte=now, expires__gt=now)
    recent = Visit.objects.filter(user=OuterRef("pk"), ts__gte=now - timedelta(days=days))
    frozen = MembershipFreeze.objects.filter(membership__user=OuterRef("pk"), start_date__lte=today, end_date__gt=today)
    last = Visit.objects.filter(user=OuterRef("pk")).order_by("-ts").values("ts")[:1]
    return (members_qs().filter(is_active=True).filter(Exists(live)).exclude(Exists(recent)).exclude(Exists(frozen))
            .annotate(last=Subquery(last)))


# ---------- insights ----------
def _ins(iid, tone, icon, title, text, cta=None, action=None):
    return {"id": iid, "tone": tone, "icon": icon, "title": title, "text": text, "cta": cta, "action": action}


def _change_insight(iid, name, delta, cur, prev, unit, icon, url, label):
    if delta is None or abs(delta) < 10:
        return None
    up = delta > 0
    return _ins(iid, "good" if up else "bad", "trend" if up else "alert", f"{name} {abs(delta):g}% {'oshdi' if up else 'kamaydi'}",
                f"{money(cur)}{unit} — oldingi davrda {money(prev)}{unit} edi.", {"label": label, "url": url})


def insights(p):
    return _cached("insights", p, _insights)


def _insights(p):
    from .models import ChatReport, Order, Payment, PTSession, Review
    out = []
    k = {c["key"]: c for c in kpis(p)["cards"]}
    for key, name, unit, icon, url, label in [
        ("revenue", "Tushum", " so'm", "wallet", reverse("admin:reports"), "Hisobotlar"),
        ("new_members", "Yangi a'zolar", "", "user-plus", reverse("admin:gym_user_changelist"), "A'zolar"),
        ("visits", "Tashriflar", "", "login", reverse("admin:gym_visit_changelist"), "Tashriflar"),
    ]:
        c = k[key]
        got = _change_insight(f"chg-{key}", name, c["delta"], c["value"], c["prev"], unit, icon, url, label)
        if got:
            out.append(got)
    rev = revenue_section(p)
    active_days = [r for r in rev["rows"] if r["total"]]
    if len(active_days) >= 3:
        best, worst = max(active_days, key=lambda r: r["total"]), min(active_days, key=lambda r: r["total"])
        unit = "kun" if rev["gran"] == "day" else ("oy" if rev["gran"] == "month" else "soat")
        out.append(_ins("best", "good", "star", f"Eng yaxshi {unit}: {best['label']}", f"{money(best['total'])} so'm tushum tushgan.", {"label": "Kassa", "url": reverse("admin:cash")}))
        if worst["label"] != best["label"]:
            out.append(_ins("worst", "warn", "clock", f"Eng sust {unit}: {worst['label']}", f"Faqat {money(worst['total'])} so'm. Shu kunga aksiya o'ylab ko'ring.", {"label": "E'lon yuborish", "url": reverse("admin:broadcast")}))
    v = visits_section(p)
    if v["total"] and v["peak_hour"] is not None:
        out.append(_ins("peak", "info", "dumbbell", f"Eng gavjum soat: {v['peak_hour']:02d}:00",
                        f"Eng gavjum kun: {WEEKDAYS_LONG[v['peak_day']]}. Murabbiylar jadvalini shunga moslang.", {"label": "Haftalik jadval", "url": reverse("admin:schedule")}))
    st = stock_section()
    if st["rows"]:
        names = ", ".join(r["label"] for r in st["rows"][:3])
        out.append(_ins("stock", "warn", "package", f"{st['total']} ta mahsulot tugayapti", f"{names}{' va boshqalar' if st['total'] > 3 else ''} — buyurtma bering.",
                        {"label": "Mahsulotlar", "url": reverse("admin:gym_product_changelist")}))
    risk = at_risk_qs()
    n_risk = risk.count()
    if n_risk:
        ids = ",".join(str(i) for i in risk.order_by("last").values_list("pk", flat=True)[:40])
        out.append(_ins("risk", "bad", "shield-x", f"{n_risk} a'zo xavf ostida", "Abonementi bor, lekin 14 kundan beri kelmagan. Shaxsiy xabar yozing.",
                        {"label": "Xabar yozish", "url": reverse("admin:message") + f"?ids={ids}"}))
    ex = expiring_section()
    if ex["total"]:
        out.append(_ins("expiring", "warn", "bell", f"{ex['total']} ta abonement 7 kunda tugaydi", "Eslatma yuboring: uzaytirish ehtimoli oshadi.", None, {"label": "Eslatma yuborish", "name": "remind"}))
    if k["renewal"]["value"] is not None and kpis(p)["churn"]:
        out.append(_ins("churn", "bad", "alert", f"{kpis(p)['churn']} kishi uzaytirmadi", f"Uzaytirish ulushi {k['renewal']['value']}%. Ularga qo'ng'iroq qiling.",
                        {"label": "Foydalanuvchilar", "url": reverse("admin:gym_user_changelist")}))
    pending = Payment.objects.filter(status="pending").count()
    if pending:
        out.append(_ins("pending", "warn", "clock", f"{pending} ta to'lov tasdiq kutmoqda", "A'zolar kutib turibdi — qabulxonada tasdiqlang.", {"label": "To'lovlar", "url": reverse("admin:gym_payment_changelist") + "?status__exact=pending"}))
    new_orders = Order.objects.filter(status="new").count()
    if new_orders:
        out.append(_ins("orders", "warn", "bag", f"{new_orders} ta yangi buyurtma", "Hali topshirilmagan buyurtmalar bor.", {"label": "Buyurtmalar", "url": reverse("admin:gym_order_changelist") + "?status__exact=new"}))
    pt = PTSession.objects.filter(status="requested", starts__gte=timezone.now()).count()
    if pt:
        out.append(_ins("pt", "info", "user-check", f"{pt} ta shaxsiy mashg'ulot so'rovi", "Murabbiy tasdig'ini kutmoqda.", {"label": "So'rovlar", "url": reverse("admin:gym_ptsession_changelist")}))
    reports = ChatReport.objects.filter(resolved=False).count()
    if reports:
        out.append(_ins("reports", "bad", "flag", f"{reports} ta chat shikoyati javobsiz", "Ko'rib chiqing.", {"label": "Shikoyatlar", "url": reverse("admin:gym_chatreport_changelist")}))
    rv = Review.objects.filter(approved=False).count()
    if rv:
        out.append(_ins("reviews", "info", "star", f"{rv} ta fikr tasdiq kutmoqda", "Saytda ko'rinishi uchun tasdiqlang.", {"label": "Fikrlar", "url": reverse("admin:gym_review_changelist")}))
    if not out:
        out.append(_ins("calm", "good", "check", "Hammasi joyida", "Hozircha e'tibor talab qiladigan narsa yo'q.", None))
    return {"rows": out}


# ---------- sections registry / bundle ----------
SECTIONS = {"kpis": kpis, "revenue": revenue_section, "members": members_section, "plans": plans_section, "methods": methods_section,
            "visits": visits_section, "products": products_section, "stock": stock_section, "expiring": expiring_section, "insights": insights}


def bundle(p):
    return {"period": p.as_dict(), **{name: fn(p) for name, fn in SECTIONS.items()}}


# ---------- reminders ----------
def send_expiry_reminders(ids, sender):
    """In-app notification (+ Telegram when linked, + e-mail when enabled in settings) to members whose membership ends within 7 days.
    Only people really in that group can be reached, whatever ids the browser sent, and nobody gets it twice in one day."""
    from . import services
    from .models import GymSettings, Notification
    now, today = timezone.now(), timezone.localdate()
    qs = expiring_qs(7, now)
    if ids is not None:
        qs = qs.filter(pk__in=ids)
    users = list(qs.order_by("until")[:200])
    done = set(Notification.objects.filter(user__in=[u.pk for u in users], title=REMINDER_TITLE, created__gte=_start_of(today)).values_list("user_id", flat=True))
    email = GymSettings.load().reminder_email
    sent = skipped = 0
    for u in users:
        if u.pk in done:
            skipped += 1
            continue
        when = timezone.localtime(u.until).strftime("%d.%m.%Y")
        services.notify(u, REMINDER_TITLE, f"Hurmatli {u.first_name or u.username}, abonementingiz {when} da tugaydi. Uzaytirish uchun saytdagi Abonementlar bo'limiga kiring yoki qabulxonaga keling.",
                        sender=sender, telegram_too=True, email_too=email)
        sent += 1
    return {"sent": sent, "skipped": skipped, "found": len(users)}


# ---------- CSV ----------
def _safe(v):
    s = str(v)
    return "'" + s if s[:1] in ("=", "+", "-", "@", "\t", "\r") else s


def write_csv(resp, p):
    resp.write("﻿")
    w = csv.writer(resp)
    d = bundle(p)
    w.writerow(["AI Analitika", p.label, f"oldingi davr: {p.prev.label}"])
    w.writerow([])
    w.writerow(["Ko'rsatkich", "Qiymat", "Oldingi davr", "O'zgarish"])
    for c in d["kpis"]["cards"]:
        w.writerow([c["label"], c["display"], "" if c["prev"] is None else c["prev"], "" if c["delta"] is None else f"{c['delta']}{'%' if c['delta_kind'] == 'pct' else ' punkt'}"])
    w.writerow([])
    w.writerow(["Sana", "Abonement (so'm)", "Do'kon (so'm)", "Jami (so'm)"])
    for r in d["revenue"]["rows"]:
        w.writerow([r["label"], r["membership"], r["shop"], r["total"]])
    w.writerow([])
    w.writerow(["Yangi a'zolar", "Soni"])
    for r in d["members"]["rows"]:
        w.writerow([r["label"], r["value"]])
    w.writerow([])
    w.writerow(["Abonement turi", "Sotilgan", "Tushum (so'm)"])
    for r in d["plans"]["rows"]:
        w.writerow([_safe(r["label"]), r["value"], r["revenue"]])
    w.writerow([])
    w.writerow(["To'lov usuli", "To'lovlar", "Summa (so'm)"])
    for r in d["methods"]["rows"]:
        w.writerow([_safe(r["label"]), r["count"], r["value"]])
    w.writerow([])
    w.writerow(["Hafta kuni", "Tashriflar"])
    for r in d["visits"]["weekday"]:
        w.writerow([r["full"], r["value"]])
    w.writerow([])
    w.writerow(["Mahsulot", "Sotilgan (dona)", "Tushum (so'm)"])
    for r in d["products"]["rows"]:
        w.writerow([_safe(r["label"]), r["value"], r["revenue"]])
    w.writerow([])
    w.writerow(["Tugayotgan abonement (7 kun)", "Telefon", "Tugash sanasi"])
    for r in d["expiring"]["rows"]:
        w.writerow([_safe(r["label"]), _safe(r["phone"]), r["until"]])
    return resp
