"""AI Analitika: permissions, KPI numbers and deltas on a small hand-made data set, every JSON endpoint's shape, the CSV export,
the insight rules, the bulk reminder, period parsing and the offline assistant (70+ questions in Uzbek Latin/Cyrillic, Russian and English)."""
import json
from datetime import date, datetime, time, timedelta

from django.core.cache import cache
from django.core.management import call_command
from django.db import connection
from django.test import Client, TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from . import analytics as an
from . import analytics_ai as ai
from .models import Booking, GymClass, GymSettings, Membership, Notification, Order, OrderItem, Payment, Plan, Product, PTSession, Trainer, User, Visit
from .models_extra import AdminQuery, GuestPass, MembershipFreeze, TrainerReview

PW = "Kuchli-Parol-77"
A = "/django-admin/analytics/"


def at(days_ago, hour=12):
    d = timezone.localdate() - timedelta(days=days_ago)
    return timezone.make_aware(datetime.combine(d, time(hour)))


def jpost(c, url, data=None):
    return c.post(url, json.dumps(data if data is not None else {}), content_type="application/json")


def client_for(user, admin_mode=True, **kw):
    c = Client(**kw)
    c.force_login(user)
    s = c.session
    s["admin_mode"] = admin_mode
    s.save()
    return c


class Base(TestCase):
    """Today = D. Current period (7 days): D-6..D; previous: D-13..D-7. All money in so'm."""

    def setUp(self):
        cache.clear()
        call_command("setup_gym", demo=True, verbosity=0)
        self.boss = User.objects.get(is_superuser=True)
        self.plan1, self.plan3 = Plan.objects.get(code="m1"), Plan.objects.get(code="m3")
        self.today = timezone.localdate()

        def mk(name, days_old=100, phone=None):
            u = User.objects.create_user(username=name, password=PW, first_name=name.capitalize(), last_name="Test", phone=phone)
            User.objects.filter(pk=u.pk).update(created=at(days_old))
            return u
        self.a, self.b, self.c, self.d, self.e = (mk("anvar", phone="+998901112233"), mk("bobur"), mk("charos"), mk("dilya"), mk("eldor"))
        for i, days in enumerate((0, 1, 3)):
            mk(f"new{i}", days)
        mk("oldnew", 9)
        now = timezone.now()
        Membership.objects.create(user=self.a, plan=self.plan1, starts=now - timedelta(days=27), expires=now + timedelta(days=3))
        self.mb = Membership.objects.create(user=self.b, plan=self.plan3, starts=now - timedelta(days=30), expires=now + timedelta(days=20))
        Membership.objects.create(user=self.c, plan=self.plan1, starts=now - timedelta(days=33), expires=now - timedelta(days=3))
        Membership.objects.create(user=self.d, plan=self.plan1, starts=now - timedelta(days=40), expires=now - timedelta(days=10))
        Membership.objects.create(user=self.d, plan=self.plan3, starts=now - timedelta(days=9), expires=now + timedelta(days=30))
        Membership.objects.create(user=self.e, plan=self.plan1, starts=now - timedelta(days=5), expires=now + timedelta(days=40))
        MembershipFreeze.objects.create(membership=self.mb, start_date=self.today - timedelta(days=2), end_date=self.today + timedelta(days=5), planned_days=7)

        def pay(user, amount, kind, method, days, status="paid", plan=None):
            p = Payment.objects.create(user=user, kind=kind, plan=plan, amount=amount, method=method, status=status)
            Payment.objects.filter(pk=p.pk).update(created=at(days))
            return p
        pay(self.a, 400000, "plan", "cash", 0, plan=self.plan1)
        pay(self.b, 1000000, "plan", "card", 2, plan=self.plan3)
        pay(self.a, 50000, "shop", "cash", 1)
        self.pending = pay(self.a, 70000, "shop", "cash", 0, status="pending")
        pay(self.c, 400000, "plan", "cash", 10, plan=self.plan1)
        pay(self.c, 100000, "shop", "click", 8)
        for u, days, hour in ((self.a, 0, 10), (self.a, 1, 18), (self.d, 2, 18), (self.d, 3, 18), (self.a, 4, 10), (self.a, 8, 10), (self.a, 9, 10)):
            v = Visit.objects.create(user=u)
            Visit.objects.filter(pk=v.pk).update(ts=at(days, hour))
        self.whey = Product.objects.get(name__startswith="Whey")
        order = Order.objects.create(user=self.a, total=1350000, method="cash", status="done")
        Order.objects.filter(pk=order.pk).update(created=at(1))
        OrderItem.objects.create(order=order, product=self.whey, name=self.whey.name, price=450000, qty=3)
        Product.objects.filter(name__startswith="BCAA").update(stock=2)

    def boss_client(self):
        return client_for(self.boss)


# ---------- permissions ----------
class PermissionTests(Base):
    def setUp(self):
        super().setUp()
        self.plain = User.objects.create_user(username="plain", password=PW, is_staff=True)
        self.viewer = User.objects.create_user(username="viewer", password=PW, is_staff=True)
        from django.contrib.auth.models import Permission
        self.viewer.user_permissions.add(Permission.objects.get(codename="view_payment"))

    def test_anonymous_redirected_everywhere(self):
        c = Client()
        for url in (A, A + "api/all/", A + "csv/", A + "api/ask/"):
            self.assertEqual(c.get(url).status_code, 302, url)

    def test_member_gets_404(self):
        c = client_for(self.a, admin_mode=False)
        self.assertEqual(c.get(A).status_code, 404)

    def test_staff_without_admin_mode_redirected(self):
        self.assertEqual(client_for(self.viewer, admin_mode=False).get(A).status_code, 302)

    def test_staff_without_permission_forbidden_page_and_json(self):
        c = client_for(self.plain)
        self.assertEqual(c.get(A).status_code, 403)
        self.assertEqual(c.get(A + "csv/").status_code, 403)
        r = c.get(A + "api/kpis/")
        self.assertEqual(r.status_code, 403)
        self.assertEqual(r.json()["ok"], False)
        r = jpost(c, A + "api/ask/", {"q": "tushum"})
        self.assertEqual((r.status_code, r.json()["ok"]), (403, False))
        r = jpost(c, A + "api/remind/", {})
        self.assertEqual((r.status_code, r.json()["ok"]), (403, False))

    def test_staff_with_permission_and_superuser_allowed(self):
        for u in (self.viewer, self.boss):
            c = client_for(u)
            self.assertEqual(c.get(A).status_code, 200)
            self.assertTrue(c.get(A + "api/kpis/").json()["ok"])

    def test_nav_entry_and_floating_button_follow_permission(self):
        html = self.boss_client().get("/django-admin/").content.decode()
        self.assertIn('href="/django-admin/analytics/"', html)
        self.assertIn("fz-ai-fab", html)
        html = client_for(self.plain).get("/django-admin/").content.decode()
        self.assertNotIn("/django-admin/analytics/", html)
        self.assertNotIn("fz-ai-fab", html)
        html = client_for(self.viewer).get("/django-admin/").content.decode()
        self.assertIn("fz-ai-fab", html)

    def test_nav_item_sits_in_asosiy_group(self):
        from .admin_site import NAV
        labels = [e[0] for e in dict(NAV)["Asosiy"]]
        self.assertEqual(labels.index("AI Analitika"), labels.index("Qabulxona") + 1)

    def test_post_needs_csrf_and_answers_json(self):
        c = client_for(self.boss, enforce_csrf_checks=True)
        r = jpost(c, A + "api/ask/", {"q": "tushum"})
        self.assertEqual(r.status_code, 403)
        self.assertEqual(r.json()["ok"], False)
        r = jpost(c, A + "api/remind/", {})
        self.assertEqual((r.status_code, r.json()["ok"]), (403, False))

    def test_wrong_method_and_bad_body(self):
        c = self.boss_client()
        r = c.post(A + "api/kpis/")
        self.assertEqual((r.status_code, r.json()["ok"]), (405, False))
        r = c.get(A + "api/remind/")
        self.assertEqual(r.status_code, 405)
        r = c.post(A + "api/ask/", "not json", content_type="application/json")
        self.assertEqual((r.status_code, r.json()["ok"]), (400, False))
        r = jpost(c, A + "api/ask/", {"q": "   "})
        self.assertEqual((r.status_code, r.json()["ok"]), (400, False))
        r = jpost(c, A + "api/ask/", {"q": "x" * 600})
        self.assertEqual(r.status_code, 400)
        r = jpost(c, A + "api/remind/", {"ids": "all"})
        self.assertEqual((r.status_code, r.json()["ok"]), (400, False))
        r = jpost(c, A + "api/remind/", {"ids": [True]})
        self.assertEqual(r.status_code, 400)
        r = c.get(A + "api/nope/")
        self.assertEqual((r.status_code, r.json()["ok"]), (404, False))


# ---------- periods ----------
class PeriodTests(TestCase):
    TODAY = date(2026, 11, 9)

    def test_presets(self):
        for key, days in (("today", 1), ("7d", 7), ("30d", 30), ("3m", 90), ("12m", 365)):
            p = an.parse_period(key, today=self.TODAY)
            self.assertEqual((p.days, p.end, p.key), (days, self.TODAY, key))
        self.assertEqual(an.parse_period("7d", today=self.TODAY).start, date(2026, 11, 3))

    def test_previous_period_is_equally_long_and_adjacent(self):
        p = an.parse_period("7d", today=self.TODAY)
        self.assertEqual((p.prev.start, p.prev.end), (date(2026, 10, 27), date(2026, 11, 2)))
        t = an.parse_period("today", today=self.TODAY)
        self.assertEqual(t.prev.start, date(2026, 11, 8))

    def test_granularity(self):
        self.assertEqual(an.parse_period("today", today=self.TODAY).gran, "hour")
        self.assertEqual(an.parse_period("30d", today=self.TODAY).gran, "day")
        self.assertEqual(an.parse_period("3m", today=self.TODAY).gran, "day")
        self.assertEqual(an.parse_period("12m", today=self.TODAY).gran, "month")

    def test_custom_range_swapped_clamped_and_bad_input(self):
        p = an.parse_period(None, "2026-11-05", "2026-11-01", today=self.TODAY)
        self.assertEqual((p.key, p.start, p.end), ("custom", date(2026, 11, 1), date(2026, 11, 5)))
        p = an.parse_period("custom", "2026-11-05", "2030-01-01", today=self.TODAY)
        self.assertEqual(p.end, self.TODAY)
        p = an.parse_period(None, "2000-01-01", "2026-11-09", today=self.TODAY)
        self.assertEqual(p.days, an.MAX_DAYS)
        for bad in (("garbage", None, None), (None, "x", "y"), (None, None, None), ("", "", "")):
            p = an.parse_period(*bad, today=self.TODAY)
            self.assertEqual((p.key, p.days), ("30d", 30))

    def test_buckets_cover_the_range(self):
        self.assertEqual(len(an.buckets(an.parse_period("today"))), 24)
        self.assertEqual(len(an.buckets(an.parse_period("7d"))), 7)
        self.assertGreaterEqual(len(an.buckets(an.parse_period("12m"))), 12)


# ---------- KPI numbers ----------
class KpiTests(Base):
    def cards(self, key="7d"):
        return {c["key"]: c for c in an.kpis(an.parse_period(key))["cards"]}

    def test_eight_cards_in_order(self):
        keys = [c["key"] for c in an.kpis(an.parse_period("7d"))["cards"]]
        self.assertEqual(keys, ["revenue", "new_members", "active", "visits", "avg_check", "shop", "renewal", "frozen"])

    def test_money_numbers_and_deltas(self):
        k = self.cards()
        self.assertEqual((k["revenue"]["value"], k["revenue"]["prev"], k["revenue"]["delta"]), (1450000, 500000, 190.0))
        self.assertEqual((k["shop"]["value"], k["shop"]["prev"], k["shop"]["delta"]), (50000, 100000, -50.0))
        self.assertEqual((k["avg_check"]["value"], k["avg_check"]["prev"], k["avg_check"]["delta"]), (483333, 250000, 93.3))
        self.assertEqual(k["revenue"]["display"], "1 450 000")

    def test_pending_payments_are_not_revenue(self):
        self.assertEqual(an.totals(an.parse_period("today"))["revenue"], 400000)

    def test_members_visits_active_frozen(self):
        k = self.cards()
        self.assertEqual((k["new_members"]["value"], k["new_members"]["prev"], k["new_members"]["delta"]), (3, 1, 200.0))
        self.assertEqual((k["visits"]["value"], k["visits"]["prev"], k["visits"]["delta"]), (5, 2, 150.0))
        self.assertEqual(k["active"]["value"], 4)
        self.assertEqual(k["frozen"]["value"], 1)
        self.assertIsNone(k["frozen"]["up_is_good"])

    def test_renewal_rate_and_churn(self):
        k = an.kpis(an.parse_period("7d"))
        card = {c["key"]: c for c in k["cards"]}["renewal"]
        self.assertEqual((card["value"], card["prev"], card["delta"], card["delta_kind"]), (0, 100, -100, "pp"))
        self.assertEqual((k["ended"], k["renewed"], k["churn"]), (1, 0, 1))

    def test_delta_is_none_without_a_base(self):
        k = self.cards("today")  # yesterday had one 50 000 shop sale and nothing else
        self.assertEqual(k["revenue"]["prev"], 50000)
        k = {c["key"]: c for c in an.kpis(an.parse_period(None, (self.today - timedelta(days=200)).isoformat(), (self.today - timedelta(days=190)).isoformat()))["cards"]}
        self.assertEqual(k["revenue"]["value"], 0)
        self.assertIsNone(k["revenue"]["delta"])
        self.assertIsNone(k["renewal"]["value"])
        self.assertEqual(k["renewal"]["display"], "—")

    def test_sparkline_lengths_match_buckets(self):
        k = self.cards()
        for key in ("revenue", "new_members", "visits", "avg_check", "shop", "active", "frozen"):
            self.assertEqual(len(k[key]["spark"]), 7, key)
        self.assertIsNone(k["renewal"]["spark"])
        self.assertEqual(sum(k["revenue"]["spark"]), 1450000)
        self.assertEqual(len(self.cards("today")["revenue"]["spark"]), 24)

    def test_long_period_samples_the_active_sparkline(self):
        self.assertLessEqual(len(self.cards("12m")["active"]["spark"]), 24)


# ---------- endpoints ----------
class EndpointTests(Base):
    def get(self, name, **params):
        r = self.boss_client().get(A + f"api/{name}/", params)
        self.assertEqual(r.status_code, 200, name)
        j = r.json()
        self.assertTrue(j["ok"])
        self.assertEqual(j["section"], name)
        self.assertEqual(j["period"]["key"], params.get("period", "30d"))
        return j["data"]

    def test_kpis(self):
        d = self.get("kpis", period="7d")
        self.assertEqual(len(d["cards"]), 8)
        for c in d["cards"]:
            for key in ("key", "label", "fmt", "value", "prev", "delta", "spark", "display", "hint", "up_is_good"):
                self.assertIn(key, c)
        self.assertEqual({"churn", "ended", "renewed"} - set(d), set())

    def test_revenue_stacked_by_day(self):
        d = self.get("revenue", period="7d")
        self.assertEqual((d["gran"], len(d["rows"]), d["total"], d["membership"], d["shop"]), ("day", 7, 1450000, 1400000, 50000))
        self.assertEqual({"label", "membership", "shop", "total"}, set(d["rows"][0]))
        self.assertEqual(d["rows"][-1]["membership"], 400000)
        self.assertEqual(d["rows"][-2]["shop"], 50000)

    def test_revenue_by_hour_and_month(self):
        self.assertEqual(len(self.get("revenue", period="today")["rows"]), 24)
        d = self.get("revenue", period="12m")
        self.assertEqual(d["gran"], "month")
        self.assertEqual(d["total"], 1450000 + 500000)

    def test_members_series(self):
        d = self.get("members", period="7d")
        self.assertEqual((d["total"], len(d["rows"])), (3, 7))

    def test_plans_donut(self):
        d = self.get("plans", period="30d")
        by = {r["label"]: r for r in d["rows"]}
        self.assertEqual(by["3 oylik"]["revenue"], 1000000)
        self.assertEqual(d["total"], sum(r["value"] for r in d["rows"]))
        self.assertTrue(all({"label", "value", "revenue"} == set(r) for r in d["rows"]))

    def test_methods_donut(self):
        d = self.get("methods", period="7d")
        by = {r["key"]: r for r in d["rows"]}
        self.assertEqual((by["card"]["value"], by["cash"]["value"], by["cash"]["count"]), (1000000, 450000, 2))
        self.assertEqual(d["rows"][0]["label"], "Karta o'tkazmasi")
        self.assertEqual(d["total"], 1450000)

    def test_visits_weekday_and_heatmap(self):
        d = self.get("visits", period="7d")
        self.assertEqual(d["total"], 5)
        self.assertEqual(len(d["weekday"]), 7)
        self.assertEqual(sum(r["value"] for r in d["weekday"]), 5)
        hm = d["heatmap"]
        self.assertEqual(len(hm["matrix"]), 7)
        self.assertTrue(all(len(row) == len(hm["hours"]) for row in hm["matrix"]))
        self.assertEqual(sum(sum(row) for row in hm["matrix"]), 5)
        self.assertEqual(d["peak_hour"], 18)
        self.assertEqual(hm["max"], max(max(row) for row in hm["matrix"]))
        wd = (self.today - timedelta(days=2)).weekday()
        self.assertEqual(hm["matrix"][wd][hm["hours"].index("18")], 1)

    def test_products_top(self):
        d = self.get("products", period="7d")
        self.assertEqual(d["rows"][0]["label"], self.whey.name)
        self.assertEqual((d["rows"][0]["value"], d["rows"][0]["revenue"]), (3, 1350000))
        self.assertIn(f"/product/{self.whey.pk}/change/", d["rows"][0]["url"])

    def test_stock_low_list(self):
        d = self.get("stock", period="30d")
        row = next(r for r in d["rows"] if r["label"].startswith("BCAA"))
        self.assertEqual(row["stock"], 2)
        self.assertGreaterEqual(row["need"], 1)
        self.assertEqual(d["threshold"], GymSettings.load().low_stock_threshold)

    def test_expiring_next_7_days(self):
        d = self.get("expiring", period="30d")
        self.assertEqual((d["total"], len(d["rows"])), (1, 1))
        r = d["rows"][0]
        self.assertEqual((r["id"], r["phone"]), (self.a.pk, "+998901112233"))
        self.assertIn(r["days"], (2, 3))

    def test_insights_and_all(self):
        self.assertTrue(self.get("insights", period="7d")["rows"])
        r = self.boss_client().get(A + "api/all/", {"period": "7d"}).json()
        self.assertEqual(set(r["data"]), {"period", *an.SECTIONS})
        self.assertEqual(r["data"]["period"]["days"], 7)

    def test_custom_range_through_the_endpoint(self):
        f, t = (self.today - timedelta(days=2)).isoformat(), self.today.isoformat()
        r = self.boss_client().get(A + "api/revenue/", {"from": f, "to": t}).json()
        self.assertEqual((r["period"]["key"], r["data"]["total"]), ("custom", 1450000 - 0))
        self.assertEqual(len(r["data"]["rows"]), 3)

    def test_bad_period_falls_back_to_30_days(self):
        r = self.boss_client().get(A + "api/kpis/", {"period": "xx", "from": "bad"}).json()
        self.assertEqual(r["period"]["days"], 30)

    def test_page_renders_with_embedded_data(self):
        r = self.boss_client().get(A, {"period": "7d"})
        self.assertEqual(r.status_code, 200)
        html = r.content.decode()
        for needle in ('id="an-data"', 'id="an-period"', "CSV eksport", "AI yordamchi", 'data-period="3m"', "js/analytics.js", "fz-ai-fab", "prefers-reduced-motion" if False else "an-kpis"):
            self.assertIn(needle, html)
        self.assertEqual(r.context["period"]["key"], "7d")
        self.assertEqual(r.context["data"]["kpis"]["cards"][0]["value"], 1450000)

    def test_page_with_custom_range_and_light_failure(self):
        r = self.boss_client().get(A, {"from": "2026-01-01", "to": "2026-01-31"})
        self.assertEqual((r.status_code, r.context["period"]["key"]), (200, "custom"))
        self.assertEqual(self.boss_client().get(A, {"from": "garbage"}).status_code, 200)


# ---------- performance ----------
class PerformanceTests(Base):
    def count(self):
        cache.clear()
        with CaptureQueriesContext(connection) as q:
            an.bundle(an.parse_period("30d"))
        return len(q)

    def test_bundle_is_cached_for_a_minute(self):
        an.bundle(an.parse_period("30d"))
        with CaptureQueriesContext(connection) as q:
            an.bundle(an.parse_period("30d"))
        self.assertEqual(len(q), 0)

    def test_queries_do_not_grow_with_data(self):
        before = self.count()
        self.assertLess(before, 60)
        users = list(User.objects.filter(is_superuser=False)[:5])
        Payment.objects.bulk_create([Payment(user=users[i % 5], kind="shop", amount=1000, method="cash", status="paid") for i in range(1500)])
        Visit.objects.bulk_create([Visit(user=users[i % 5]) for i in range(1500)])
        User.objects.bulk_create([User(username=f"bulk{i}", first_name="B") for i in range(300)])
        self.assertLessEqual(self.count(), before)  # one fewer when the extra visits cleared the «at risk» member

    def test_indexes_exist(self):
        names = {i.name for m in (Payment, Visit, Membership, Order) for i in m._meta.indexes}
        self.assertTrue({"pay_status_created_idx", "visit_ts_idx", "visit_user_ts_idx", "mem_expires_idx", "order_created_idx"} <= names)


# ---------- CSV ----------
class CsvTests(Base):
    def test_csv_export(self):
        r = self.boss_client().get(A + "csv/", {"period": "7d"})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r["Content-Type"].startswith("text/csv"))
        self.assertIn("attachment", r["Content-Disposition"])
        text = r.content.decode("utf-8")
        self.assertTrue(text.startswith("﻿"))
        for needle in ("Tushum", "1 450 000", "To'lov usuli", "Karta o'tkazmasi", "Hafta kuni", "Mahsulot", self.whey.name, "1350000"):
            self.assertIn(needle, text)

    def test_formula_injection_is_defused(self):
        evil = Product.objects.create(name="=SUM(A1)", price=1000, stock=50)
        o = Order.objects.create(user=self.a, total=1000, method="cash", status="done")
        OrderItem.objects.create(order=o, product=evil, name=evil.name, price=1000, qty=1)
        text = self.boss_client().get(A + "csv/", {"period": "7d"}).content.decode("utf-8")
        self.assertIn("'=SUM(A1)", text)
        self.assertNotIn(",=SUM(A1)", text.replace("\n", ","))

    def test_custom_range_filename(self):
        r = self.boss_client().get(A + "csv/", {"from": "2026-01-01", "to": "2026-01-31"})
        self.assertIn("analitika-20260101-20260131.csv", r["Content-Disposition"])


# ---------- insights ----------
class InsightTests(Base):
    def ids(self, key="7d"):
        return {r["id"]: r for r in an.insights(an.parse_period(key))["rows"]}

    def test_significant_changes_are_reported(self):
        got = self.ids()
        self.assertEqual(got["chg-revenue"]["tone"], "good")
        self.assertIn("190", got["chg-revenue"]["title"])
        self.assertIn("oshdi", got["chg-revenue"]["title"])
        self.assertIn("chg-new_members", got)
        self.assertIn("chg-visits", got)

    def test_a_drop_is_bad_news(self):
        Payment.objects.filter(kind="plan", amount=400000, created__lt=at(8)).update(amount=4000000)
        got = self.ids()
        self.assertEqual(got["chg-revenue"]["tone"], "bad")
        self.assertIn("kamaydi", got["chg-revenue"]["title"])

    def test_small_changes_are_ignored(self):
        p = an.parse_period("7d")
        c = {"delta": 9.9, "value": 1, "prev": 1}
        self.assertIsNone(an._change_insight("x", "X", c["delta"], 1, 1, "", "trend", "/", "x"))
        self.assertIsNone(an._change_insight("x", "X", None, 1, 1, "", "trend", "/", "x"))
        self.assertIsNotNone(an._change_insight("x", "X", -10, 1, 1, "", "trend", "/", "x"))

    def test_best_and_worst_day(self):
        got = self.ids()
        self.assertIn("1 000 000", got["best"]["text"])
        self.assertIn("50 000", got["worst"]["text"])
        self.assertEqual(got["best"]["tone"], "good")

    def test_peak_hour(self):
        self.assertIn("18:00", self.ids()["peak"]["title"])

    def test_stock_risk_expiring_churn_pending(self):
        got = self.ids()
        self.assertIn("BCAA", got["stock"]["text"])
        self.assertIn("1 a'zo", got["risk"]["title"])
        self.assertIn(f"ids={self.e.pk}", got["risk"]["cta"]["url"])
        self.assertEqual(got["expiring"]["action"]["name"], "remind")
        self.assertIn("1 kishi", got["churn"]["title"])
        self.assertIn("1 ta to'lov", got["pending"]["title"])
        self.assertIn("status__exact=pending", got["pending"]["cta"]["url"])

    def test_frozen_member_is_not_at_risk(self):
        ids = list(an.at_risk_qs().values_list("pk", flat=True))
        self.assertEqual(ids, [self.e.pk])

    def test_every_insight_has_a_way_to_act_or_is_calm(self):
        for r in an.insights(an.parse_period("7d"))["rows"]:
            self.assertTrue(r["cta"] or r["action"] or r["id"] == "calm", r["id"])
            self.assertIn(r["tone"], ("good", "bad", "warn", "info"))

    def test_quiet_gym_is_calm(self):
        for m in (Payment, Visit, Membership, Order):
            m.objects.all().delete()
        User.objects.filter(is_superuser=False).delete()
        Product.objects.update(stock=100)
        MembershipFreeze.objects.all().delete()
        cache.clear()
        self.assertEqual([r["id"] for r in an.insights(an.parse_period("7d"))["rows"]], ["calm"])


# ---------- reminders ----------
class ReminderTests(Base):
    def test_bulk_reminder_goes_only_to_members_who_expire_within_7_days(self):
        c = self.boss_client()
        r = jpost(c, A + "api/remind/", {"ids": None}).json()
        self.assertEqual((r["ok"], r["sent"], r["found"]), (True, 1, 1))
        n = Notification.objects.get(user=self.a, title=an.REMINDER_TITLE)
        self.assertEqual(n.sender, self.boss)
        self.assertIn("Anvar", n.body)

    def test_not_twice_in_one_day(self):
        c = self.boss_client()
        jpost(c, A + "api/remind/", {})
        r = jpost(c, A + "api/remind/", {}).json()
        self.assertEqual((r["sent"], r["skipped"]), (0, 1))
        self.assertEqual(Notification.objects.filter(title=an.REMINDER_TITLE).count(), 1)

    def test_ids_outside_the_group_are_ignored(self):
        r = jpost(self.boss_client(), A + "api/remind/", {"ids": [self.e.pk, self.c.pk, 999999]}).json()
        self.assertEqual((r["ok"], r["sent"], r["found"]), (True, 0, 0))
        self.assertFalse(Notification.objects.filter(title=an.REMINDER_TITLE).exists())

    def test_selected_ids_only(self):
        r = jpost(self.boss_client(), A + "api/remind/", {"ids": [self.a.pk]}).json()
        self.assertEqual(r["sent"], 1)


# ---------- assistant: understanding ----------
TODAY = date(2026, 11, 9)

QUESTIONS = [
    # revenue
    ("Bugun tushum qancha?", "revenue_total"), ("Bu oy daromad qancha", "revenue_total"), ("бугун тушум қанча", "revenue_total"),
    ("Какая выручка за этот месяц?", "revenue_total"), ("What is the revenue today?", "revenue_total"), ("Kecha qancha pul tushdi", "revenue_total"),
    ("Oxirgi 30 kun tushum", "revenue_total"), ("Total sales last week", "revenue_total"), ("Тушум 2026 октябр", "revenue_total"),
    ("To'lov usullari bo'yicha tushum", "revenue_by_method"), ("Naqd va karta tushum bu oy", "revenue_by_method"),
    ("Выручка по способам оплаты", "revenue_by_method"), ("Revenue by payment method", "revenue_by_method"), ("Click orqali qancha tushum", "revenue_by_method"),
    ("Abonement turi bo'yicha tushum", "revenue_by_plan"), ("Revenue by plan", "revenue_by_plan"), ("Выручка по тарифам", "revenue_by_plan"),
    ("3 oylik abonement tushumi", "revenue_by_plan"),
    ("Do'kon savdosi bu oy", "shop_sales"), ("Shop sales this month", "shop_sales"), ("Продажи магазина за неделю", "shop_sales"),
    ("Tushum o'tgan oyga nisbatan", "compare"), ("Revenue compared to last month", "compare"), ("Выручка по сравнению с прошлым месяцем", "compare"),
    ("Yangi a'zolar o'tgan oyga nisbatan", "compare"), ("Visits vs last week", "compare"), ("O'rtacha chek oldingi oyga nisbatan", "compare"),
    # members
    ("Bu oy nechta yangi a'zo qo'shildi?", "new_members"), ("Сколько новых клиентов за неделю?", "new_members"), ("How many new members this month?", "new_members"),
    ("янги аъзолар бугун", "new_members"), ("Yangi mijozlar 3 oy", "new_members"),
    ("Faol abonementlar soni", "active_members"), ("Сколько активных клиентов", "active_members"), ("How many active members?", "active_members"),
    ("Jami a'zolar soni", "members_total"), ("Сколько всего клиентов?", "members_total"),
    # visits
    ("Bugun nechta odam keldi?", "visits_total"), ("Сколько человек пришло сегодня?", "visits_total"), ("How many visits this week?", "visits_total"),
    ("Kecha tashriflar soni", "visits_total"), ("бугун неча киши келди", "visits_total"),
    ("Eng gavjum soat qaysi?", "peak_hours"), ("Peak hours", "peak_hours"), ("Какой час пик?", "peak_hours"),
    ("Qaysi kun eng gavjum?", "peak_days"), ("Busiest day of the week", "peak_days"),
    # expiring / inactive / churn
    ("Bu hafta kimning abonementi tugaydi?", "expiring_members"), ("Bugun kim tugaydi", "expiring_members"), ("Who expires this week?", "expiring_members"),
    ("У кого заканчивается абонемент на этой неделе?", "expiring_members"), ("Ertaga abonementi tugaydiganlar", "expiring_members"),
    ("14 kundan beri kelmaganlar", "inactive_members"), ("Who hasn't visited in 30 days?", "inactive_members"), ("Кто не приходил 10 дней", "inactive_members"),
    ("кимлар келмаган 21 кундан бери", "inactive_members"),
    ("Bu oy abonementi tugaganlar", "churn"), ("Churn this month", "churn"), ("Сколько клиентов ушло", "churn"),
    ("Uzaytirish ulushi", "renewal_rate"), ("Renewal rate last month", "renewal_rate"),
    # shop
    ("Eng ko'p sotilgan mahsulotlar", "top_products"), ("Top 3 products", "top_products"), ("Самые продаваемые товары", "top_products"),
    ("Eng kam sotilgan mahsulotlar", "least_products"), ("Least sold products", "least_products"),
    ("Qaysi mahsulot tugayapti?", "low_stock"), ("Low stock", "low_stock"), ("Какие товары заканчиваются?", "low_stock"), ("Mahsulotlar qoldig'i", "low_stock"),
    ("Whey protein qancha qoldi", "product_info"), ("Kreatin necha dona sotildi", "product_info"),
    # money details
    ("Kutilayotgan to'lovlar", "pending_items"), ("Pending payments", "pending_items"), ("Ожидающие платежи", "pending_items"), ("Yangi buyurtmalar", "pending_items"),
    ("O'rtacha chek qancha?", "avg_check"), ("Average check this month", "avg_check"), ("Средний чек", "avg_check"),
    # people / classes
    ("Eng yaxshi murabbiy kim?", "best_trainer"), ("Best trainer", "best_trainer"), ("Лучший тренер", "best_trainer"),
    ("Mashg'ulotlar davomati", "class_attendance"), ("Class attendance", "class_attendance"), ("Посещаемость занятий", "class_attendance"),
    ("Mehmon taklifnomalari", "guest_passes"), ("Guest passes used", "guest_passes"), ("Гостевые приглашения", "guest_passes"),
    ("Muzlatilgan abonementlar", "freezes"), ("Frozen memberships", "freezes"), ("Заморозки абонементов", "freezes"),
    ("Taklif qilish statistikasi", "referrals"), ("Referral stats", "referrals"), ("Рефералы", "referrals"),
    # chit-chat
    ("Salom", "help"), ("Nima qila olasan?", "help"), ("Привет", "help"),
    ("asdfgh qwerty", "unknown"), ("Ob-havo qanday bo'ladi?", "unknown"), ("Bugun futbol kim yutdi", "unknown"), ("???", "unknown"),
]


class IntentTests(Base):
    def test_at_least_sixty_questions_in_all_languages(self):
        self.assertGreaterEqual(len(QUESTIONS), 60)
        self.assertTrue(any(ord(ch) > 1024 for q, _ in QUESTIONS for ch in q))  # Cyrillic is covered

    def test_every_question_maps_to_its_intent(self):
        bad = []
        for q, want in QUESTIONS:
            got = ai.understand(q, today=TODAY).intent
            if got != want:
                bad.append(f"{q!r}: expected {want}, got {got}")
        self.assertEqual(bad, [])

    def test_every_question_runs_and_returns_the_answer_shape(self):
        for q, want in QUESTIONS:
            a = ai.answer(q)
            self.assertTrue(a["ok"], q)
            self.assertEqual(a["intent"], want, q)
            self.assertTrue(a["text"], q)
            for key in ("table", "chart", "links", "entities", "suggestions"):
                self.assertIn(key, a, q)
            json.dumps(a)  # the answer must be JSON-ready
            for link in a["links"]:
                self.assertTrue(link["url"].startswith("/"), q)

    def test_entities(self):
        u = ai.understand("Top 3 products", today=TODAY)
        self.assertEqual(u.ent["top"], 3)
        self.assertEqual(ai.understand("eng ko'p sotilgan 7 ta mahsulot", today=TODAY).ent["top"], 7)
        self.assertEqual(ai.understand("топ 5 товаров", today=TODAY).ent["top"], 5)
        self.assertEqual(ai.understand("14 kundan beri kelmaganlar", today=TODAY).ent["days"], 14)
        self.assertEqual(ai.understand("Who hasn't visited in 30 days?", today=TODAY).ent["days"], 30)
        self.assertEqual(ai.understand("kelmaganlar 2 hafta", today=TODAY).ent["days"], 14)
        self.assertEqual(ai.understand("Click orqali tushum", today=TODAY).ent["method"], "click")
        u = ai.understand("3 oylik abonement tushumi", today=TODAY)
        self.assertEqual((u.ent["plan"], u.ent["plan_id"]), ("3 oylik", self.plan3.pk))
        self.assertIsNone(u.when)  # «3 oylik» is a plan name, not "3 months"
        u = ai.understand("Whey protein qancha qoldi", today=TODAY)
        self.assertEqual(u.ent["product_ids"], [self.whey.pk])
        self.assertTrue(ai.understand("Tushum o'tgan oyga nisbatan", today=TODAY).ent["compare"])
        self.assertEqual(ai.understand("Tushum o'tgan oyga nisbatan", today=TODAY).ent["metric"], "revenue")
        self.assertEqual(ai.understand("Visits vs last week", today=TODAY).ent["metric"], "visits")

    def test_follow_up_reuses_the_last_intent(self):
        a = ai.answer("o'tgan oy?", last="revenue_total", today=TODAY)
        self.assertEqual(a["intent"], "revenue_total")
        self.assertEqual(a["entities"]["period"]["start"], "2026-10-01")
        self.assertEqual(ai.answer("o'tgan oy?", today=TODAY)["intent"], "unknown")

    def test_unknown_is_honest_and_helpful(self):
        a = ai.answer("asdfgh qwerty")
        self.assertEqual(a["intent"], "unknown")
        self.assertTrue(a["text"].startswith("Tushunmadim"))
        self.assertGreaterEqual(len(a["suggestions"]), 5)
        self.assertEqual(ai.answer("tushim qancha")["suggestions"][0], "Bugun tushum qancha?")  # a typo gets a closest-match suggestion first
        self.assertEqual(ai.answer("   ")["ok"], False)

    def test_script_and_apostrophe_variants_agree(self):
        for q in ("O'rtacha chek", "Oʻrtacha chek", "O`rtacha chek", "O‘rtacha chek", "ўртача чек", "ORTACHA CHEK"):
            self.assertEqual(ai.understand(q, today=TODAY).intent, "avg_check", q)

    def test_mask_hides_long_digit_runs(self):
        self.assertEqual(ai.mask("tel 998901234567 qancha"), "tel # qancha")
        self.assertEqual(ai.mask("14 kun"), "14 kun")


class WhenTests(TestCase):
    def w(self, q):
        hay, _ = ai.prepare(q)
        return ai.parse_whens(hay, TODAY)

    def one(self, q):
        got = self.w(q)
        self.assertEqual(len(got), 1, (q, got))
        return got[0].start, got[0].end

    def test_days_of_the_week_and_month(self):
        monday = TODAY - timedelta(days=TODAY.weekday())
        self.assertEqual(self.one("bugun"), (TODAY, TODAY))
        self.assertEqual(self.one("Kecha tushum"), (TODAY - timedelta(days=1),) * 2)
        self.assertEqual(self.one("shu hafta"), (monday, TODAY))
        self.assertEqual(self.one("o'tgan hafta"), (monday - timedelta(days=7), monday - timedelta(days=1)))
        self.assertEqual(self.one("bu oy"), (date(2026, 11, 1), TODAY))
        self.assertEqual(self.one("o'tgan oy"), (date(2026, 10, 1), date(2026, 10, 31)))
        self.assertEqual(self.one("bu yil"), (date(2026, 1, 1), TODAY))
        self.assertEqual(self.one("o'tgan yil"), (date(2025, 1, 1), date(2025, 12, 31)))

    def test_languages(self):
        self.assertEqual(self.one("this month"), (date(2026, 11, 1), TODAY))
        self.assertEqual(self.one("last month"), (date(2026, 10, 1), date(2026, 10, 31)))
        self.assertEqual(self.one("за этот месяц"), (date(2026, 11, 1), TODAY))
        self.assertEqual(self.one("прошлый месяц"), (date(2026, 10, 1), date(2026, 10, 31)))
        self.assertEqual(self.one("вчера"), (TODAY - timedelta(days=1),) * 2)
        self.assertEqual(self.one("бугун"), (TODAY, TODAY))
        self.assertEqual(self.one("ўтган ой"), (date(2026, 10, 1), date(2026, 10, 31)))

    def test_trailing_windows(self):
        self.assertEqual(self.one("oxirgi 14 kun"), (TODAY - timedelta(days=13), TODAY))
        self.assertEqual(self.one("last 7 days"), (TODAY - timedelta(days=6), TODAY))
        self.assertEqual(self.one("за 10 дней"), (TODAY - timedelta(days=9), TODAY))
        self.assertEqual(self.one("2 hafta"), (TODAY - timedelta(days=13), TODAY))
        self.assertEqual(self.one("3 oy"), (date(2026, 8, 10), TODAY))
        self.assertEqual(self.one("oxirgi hafta"), (TODAY - timedelta(days=6), TODAY))

    def test_named_months(self):
        self.assertEqual(self.one("2026 oktyabr"), (date(2026, 10, 1), date(2026, 10, 31)))
        self.assertEqual(self.one("oktyabr 2026"), (date(2026, 10, 1), date(2026, 10, 31)))
        self.assertEqual(self.one("october 2025"), (date(2025, 10, 1), date(2025, 10, 31)))
        self.assertEqual(self.one("октябрь 2026"), (date(2026, 10, 1), date(2026, 10, 31)))
        self.assertEqual(self.one("oktyabrda"), (date(2026, 10, 1), date(2026, 10, 31)))
        self.assertEqual(self.one("в марте"), (date(2026, 3, 1), date(2026, 3, 31)))
        self.assertEqual(self.one("dekabr"), (date(2025, 12, 1), date(2025, 12, 31)))  # a month still ahead means last year's
        self.assertEqual(self.one("fevral 2024"), (date(2024, 2, 1), date(2024, 2, 29)))

    def test_single_dates_and_ranges(self):
        self.assertEqual(self.one("12 oktyabr"), (date(2026, 10, 12),) * 2)
        self.assertEqual(self.one("2026-10-05"), (date(2026, 10, 5),) * 2)
        self.assertEqual(self.one("05.10.2026"), (date(2026, 10, 5),) * 2)
        self.assertEqual(self.one("2026-10-05 dan 2026-10-20 gacha"), (date(2026, 10, 5), date(2026, 10, 20)))
        self.assertEqual(self.one("2025 yil"), (date(2025, 1, 1), date(2025, 12, 31)))

    def test_two_periods_for_a_comparison(self):
        got = self.w("bu oy o'tgan oyga nisbatan")
        self.assertEqual({(w.start, w.end) for w in got}, {(date(2026, 11, 1), TODAY), (date(2026, 10, 1), date(2026, 10, 31))})

    def test_nothing_found(self):
        self.assertEqual(self.w("tushum qancha"), [])

    def test_previous_span_rules(self):
        self.assertEqual(ai.prev_span(ai.When_(date(2026, 11, 1), TODAY, "month")), (date(2026, 10, 1), date(2026, 10, 9)))
        self.assertEqual(ai.prev_span(ai.When_(date(2026, 10, 1), date(2026, 10, 31), "last_month")), (date(2026, 9, 1), date(2026, 9, 30)))
        self.assertEqual(ai.prev_span(ai.When_(date(2026, 11, 3), TODAY, "days")), (date(2026, 10, 27), date(2026, 11, 2)))


# ---------- assistant: real numbers ----------
class AnswerTests(Base):
    def ask(self, q):
        return ai.answer(q)

    def test_revenue_numbers(self):
        self.assertIn("400 000 so'm", self.ask("Bugun tushum qancha?")["text"])
        self.assertIn("50 000 so'm", self.ask("Kecha tushum")["text"])
        a = self.ask("Oxirgi 7 kun tushum")
        self.assertIn("1 450 000 so'm", a["text"])
        self.assertIn("3 ta to'lov", a["text"])
        self.assertEqual({i["label"]: i["value"] for i in a["chart"]["items"]}, {"Abonement": 1400000, "Do'kon": 50000})

    def test_revenue_by_method_and_plan(self):
        a = self.ask("Oxirgi 7 kun to'lov usullari bo'yicha tushum")
        self.assertEqual(a["table"]["rows"][0][0], "Karta o'tkazmasi")
        self.assertIn("1 000 000", a["table"]["rows"][0][2])
        self.assertIn("Naqd: 450 000", self.ask("Oxirgi 7 kun naqd tushum usul")["text"])
        a = self.ask("Oxirgi 7 kun abonement turi bo'yicha tushum")
        self.assertEqual(a["table"]["rows"][0][0], "3 oylik")
        a = self.ask("30 kun 3 oylik abonement tushumi")
        self.assertIn("1 000 000", a["text"])
        self.assertIn("«3 oylik»", a["text"])

    def test_shop_and_compare(self):
        self.assertIn("50 000 so'm", self.ask("Do'kon savdosi oxirgi 7 kun")["text"])
        a = self.ask("Oxirgi 7 kun tushum oldingi davrga nisbatan")
        self.assertEqual(a["intent"], "compare")
        self.assertIn("+190%", a["text"])
        self.assertIn("500 000", a["text"])
        self.assertEqual(a["entities"]["delta"], 190.0)
        a = self.ask("Oxirgi 7 kun yangi a'zolar oldingi davrga nisbatan")
        self.assertIn("+200%", a["text"])
        a = self.ask("Oxirgi 7 kun o'rtacha chek")
        self.assertIn("483 333 so'm", a["text"])
        self.assertIn("250 000", a["text"])

    def test_members_and_visits(self):
        self.assertIn("3 ta yangi", self.ask("Oxirgi 7 kun yangi a'zolar")["text"])
        self.assertIn("4 ta faol", self.ask("Faol abonementlar soni")["text"])
        a = self.ask("Oxirgi 7 kun tashriflar")
        self.assertIn("5 ta tashrif", a["text"])
        self.assertIn("18:00", a["text"])
        self.assertIn("(18:00", self.ask("Eng gavjum soat 30 kun")["text"] + "(18:00" )
        self.assertEqual(self.ask("Eng gavjum soat 30 kun")["chart"]["items"][-1]["label"][-3:], ":00")
        self.assertEqual(self.ask("Jami a'zolar soni")["entities"]["total"], User.objects.filter(is_superuser=False).count())

    def test_expiring_and_inactive_lists(self):
        a = self.ask("7 kun ichida kimning abonementi tugaydi?")
        self.assertIn("1 ta", a["text"])
        self.assertEqual(a["table"]["rows"][0][0], "Anvar Test")
        self.assertTrue(any("analytics" in link["url"] for link in a["links"]))
        self.assertIn("ids=", next(link["url"] for link in a["links"] if "message" in link["url"]))
        self.assertIn("yo'q", self.ask("Bugun abonementi tugaydigan a'zolar")["text"])
        a = self.ask("14 kundan beri kelmaganlar")
        self.assertIn("1 ta faol a'zo", a["text"])
        self.assertEqual(a["table"]["rows"][0][0], "Eldor Test")
        self.assertEqual(a["table"]["rows"][0][2], "hech kelmagan")
        self.assertIn("churn", ai.answer("Oxirgi 7 kun abonementi tugaganlar")["intent"])
        self.assertIn("1 kishining", ai.answer("Oxirgi 7 kun abonementi tugaganlar")["text"])

    def test_products_and_stock(self):
        a = self.ask("Eng ko'p sotilgan mahsulotlar 30 kun")
        self.assertEqual(a["table"]["rows"][0][:2], [self.whey.name, 3])
        a = self.ask("Top 2 products 30 kun")
        self.assertEqual(len(a["table"]["rows"]), 2)
        a = self.ask("Eng kam sotilgan mahsulotlar")
        self.assertEqual(a["table"]["rows"][0][1], 0)
        a = self.ask("Qaysi mahsulot tugayapti?")
        self.assertIn("BCAA 200 g", [r[0] for r in a["table"]["rows"]])
        a = self.ask("Whey protein qancha qoldi")
        self.assertIn(f"omborda {self.whey.stock} dona", a["text"])
        self.assertIn("3 dona sotilgan", a["text"])

    def test_pending(self):
        a = self.ask("Kutilayotgan to'lovlar")
        self.assertIn("1 ta to'lov", a["text"])
        self.assertEqual(a["table"]["rows"][0][2], "70 000")

    def test_trainers_classes_guests_freezes_referrals(self):
        t1, t2 = Trainer.objects.order_by("id")[:2]
        for _ in range(2):
            PTSession.objects.create(user=self.a, trainer=t1, starts=at(0, 9), status="confirmed")
        PTSession.objects.create(user=self.b, trainer=t2, starts=at(0, 9), status="confirmed")
        TrainerReview.objects.create(trainer=t2, user=self.a, rating=5)
        a = self.ask("Eng yaxshi murabbiy kim?")
        self.assertIn(t1.name, a["text"].split("—")[1])
        self.assertIn(f"{t2.name} (5.0/5", a["text"])
        gc = GymClass.objects.first()
        Booking.objects.create(user=self.a, gym_class=gc, date=self.today, checked_in_at=timezone.now())
        Booking.objects.create(user=self.b, gym_class=gc, date=self.today, no_show=True)
        a = self.ask("Mashg'ulotlar davomati")
        self.assertIn("2 ta bron", a["text"])
        self.assertIn("1 ta kelmadi", a["text"])
        GuestPass.objects.create(owner=self.a, guest_name="Do'st", date=self.today, used_at=timezone.now())
        GuestPass.objects.create(owner=self.a, guest_name="Do'st2", date=self.today)
        a = self.ask("Mehmon taklifnomalari")
        self.assertIn("2 ta mehmon taklifnomasi", a["text"])
        self.assertIn("1 tasi ishlatilgan", a["text"])
        a = self.ask("Muzlatilgan abonementlar")
        self.assertIn("Hozir 1 ta abonement muzlatilgan", a["text"])
        self.assertEqual(a["table"]["rows"][0][0], "Bobur Test")
        User.objects.filter(username="new0").update(referred_by=self.a)
        a = self.ask("Taklif qilish statistikasi")
        self.assertIn("1 ta do'st", a["text"])
        self.assertEqual(a["table"]["rows"][0], ["Anvar Test", 1])

    def test_nothing_in_the_future(self):
        a = self.ask("Ertaga tushum")
        self.assertEqual(a["entities"]["period"]["start"], self.today.replace(day=1).isoformat())


class AskEndpointTests(Base):
    def test_conversation_is_kept_in_the_session(self):
        c = self.boss_client()
        r = jpost(c, A + "api/ask/", {"q": "Bugun tushum qancha?"}).json()
        self.assertEqual((r["ok"], r["intent"]), (True, "revenue_total"))
        jpost(c, A + "api/ask/", {"q": "asdf qwer"})
        h = c.get(A + "api/ask/").json()
        self.assertTrue(h["ok"])
        self.assertEqual([m["role"] for m in h["history"]], ["user", "bot", "user", "bot"])
        self.assertEqual(h["history"][0]["text"], "Bugun tushum qancha?")
        self.assertEqual(h["history"][3]["answer"]["intent"], "unknown")
        self.assertTrue(h["suggestions"])
        self.assertEqual(jpost(c, A + "api/ask/", {"clear": True}).json()["history"], [])
        self.assertEqual(c.get(A + "api/ask/").json()["history"], [])

    def test_follow_up_uses_the_session(self):
        c = self.boss_client()
        jpost(c, A + "api/ask/", {"q": "Bu oy tushum"})
        r = jpost(c, A + "api/ask/", {"q": "o'tgan oy?"}).json()
        self.assertEqual(r["intent"], "revenue_total")

    def test_history_is_capped(self):
        c = self.boss_client()
        for _ in range(16):
            jpost(c, A + "api/ask/", {"q": "Salom"})
        self.assertEqual(len(c.get(A + "api/ask/").json()["history"]), 24)

    def test_log_keeps_text_and_intent_without_numbers(self):
        c = self.boss_client()
        jpost(c, A + "api/ask/", {"q": "Bugun tushum qancha?"})
        jpost(c, A + "api/ask/", {"q": "qwerty 998901234567"})
        rows = list(AdminQuery.objects.order_by("id"))
        self.assertEqual([(r.intent, r.matched) for r in rows], [("revenue_total", True), ("unknown", False)])
        self.assertEqual(rows[1].text, "qwerty #")
        self.assertEqual(rows[0].user, self.boss)

    def test_one_failing_log_does_not_break_the_answer(self):
        from unittest import mock
        with mock.patch("gym.models_extra.AdminQuery.objects.create", side_effect=RuntimeError("db")):
            r = jpost(self.boss_client(), A + "api/ask/", {"q": "Salom"})
        self.assertEqual((r.status_code, r.json()["intent"]), (200, "help"))

    def test_server_error_is_json(self):
        from unittest import mock
        with mock.patch("gym.analytics_ai.answer", side_effect=RuntimeError("boom")):
            with self.assertLogs("gym.analytics_views", level="ERROR"):
                r = jpost(self.boss_client(), A + "api/ask/", {"q": "Salom"})
        self.assertEqual((r.status_code, r.json()["ok"]), (500, False))

    def test_panel_is_on_every_admin_page(self):
        c = self.boss_client()
        for url in ("/django-admin/", "/django-admin/reports/", "/django-admin/gym/user/", A):
            html = c.get(url).content.decode()
            self.assertIn('id="fz-ai"', html, url)
            self.assertIn("js/ai_panel.js", html, url)
        self.assertIn(reverse("admin:analytics_ask"), c.get("/django-admin/").content.decode())
