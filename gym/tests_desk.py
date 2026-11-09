"""Qabulxona inside the admin panel (/django-admin/desk/): redirects from the old /staff/ addresses, who may open it, search,
check-in, selling a membership, quick registration, payment approval, guest passes, the shift summary and the CSRF rule."""
import copy
import json
from datetime import timedelta

from django.conf import settings
from django.core.cache import cache
from django.core.management import call_command
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from . import extras, services
from .models import Booking, EntryLog, GymClass, GymSettings, Membership, Order, Payment, Plan, Trainer, User, Visit

PW = "Kuchli-Parol-77"
TEMPLATES = copy.deepcopy(settings.TEMPLATES)
TEMPLATES[0]["OPTIONS"]["string_if_invalid"] = "@@INVALID[%s]@@"  # a typo in a template variable fails the test instead of printing nothing
D = "/django-admin/desk/"


def clean(html):
    """The admin top bar prints {{ q|default:'' }}: that one name is allowed to be missing (same rule as the whole-site audit)."""
    return html.replace("@@INVALID[q]@@", "")


def jpost(client, url, data=None):
    return client.post(url, json.dumps(data or {}), content_type="application/json")


class DeskBase(TestCase):
    def setUp(self):
        cache.clear()
        call_command("setup_gym", demo=True, verbosity=0)
        Plan.objects.filter(code="m1").update(guest_passes=3)
        self.plan = Plan.objects.get(code="m1")
        self.boss = User.objects.get(is_superuser=True)
        self.boss.first_name = "Boss"
        self.boss.save()
        self.staff_user = User.objects.create_user(username="qabul1", password="Xodim-Parol-1", first_name="Dilnoza", is_staff=True)
        self.desk = self.client_for(self.staff_user, admin_mode=True)
        self.m = User.objects.create_user(username="aziz", password=PW, first_name="Aziz", last_name="Karimov", phone="+998901112233")

    def client_for(self, user, admin_mode=False):
        c = Client()
        c.force_login(user)
        s = c.session
        s["admin_mode"] = admin_mode
        s.save()
        return c

    def membership(self, user, days=30, started=1):
        now = timezone.now()
        return Membership.objects.create(user=user, plan=self.plan, starts=now - timedelta(days=started), expires=now + timedelta(days=days))


class RedirectTests(DeskBase):
    def test_old_staff_urls_redirect_permanently(self):
        for old, new in (("/staff/", D), ("/staff/scan/", D + "scan/"), ("/staff/classes/", D + "classes/"), ("/staff/checkin/5/", D + "checkin/5/")):
            r = self.desk.get(old)
            self.assertEqual((r.status_code, r["Location"]), (301, new), old)
        self.assertEqual(self.desk.get("/staff/?q=Aziz")["Location"], D + "?q=Aziz")  # the search text survives

    def test_nav_has_desk_scan_and_attendance(self):
        html = self.desk.get(reverse("admin:index")).content.decode().split('id="fz-side"')[1].split("</aside>")[0]
        for url in (D, D + "scan/", D + "classes/"):
            self.assertIn(f'href="{url}"', html)
        self.assertNotIn("/staff/", html)

    def test_public_sidebar_has_one_admin_link_for_staff_only(self):
        html = self.desk.get("/").content.decode()
        self.assertIn('href="/django-admin/"', html)
        self.assertNotIn('href="/staff/"', html)
        self.assertNotIn(D, html)
        member = self.client_for(self.m).get("/").content.decode()
        self.assertNotIn("/django-admin/", member)

    def test_home_hero_has_no_duplicate_open_pill(self):
        html = Client().get("/").content.decode()
        self.assertNotIn("cine-eyebrow", html)
        self.assertNotIn("cine-badges", html)
        self.assertIn('class="pill ', html.split("</header>")[0])  # the top bar still shows the opening hours


class PermissionTests(DeskBase):
    PAGES = (D, D + "scan/", D + "classes/", D + "shift/", D + "search/?q=aziz", D + "today/", "MEMBER")
    POSTS = ("checkin", "sell", "freeze", "unfreeze", "block")

    def urls(self):
        return [self.m and (D + f"member/{self.m.pk}/" if p == "MEMBER" else p) for p in self.PAGES]

    def test_anonymous_goes_to_login(self):
        c = Client()
        for url in self.urls():
            self.assertEqual(c.get(url).status_code, 302, url)
        self.assertEqual(c.post(D + f"checkin/{self.m.pk}/").status_code, 302)

    def test_member_and_trainer_see_nothing(self):
        coach = User.objects.create_user(username="coach1", password=PW, first_name="Murabbiy")
        Trainer.objects.create(name="Murabbiy", specialty="Kuch", user=coach)
        for user in (self.m, coach):
            c = self.client_for(user)
            for url in self.urls():
                self.assertEqual(c.get(url).status_code, 404, url)
            for name in self.POSTS:
                self.assertEqual(jpost(c, D + f"{name}/{self.m.pk}/").status_code, 404, name)
            self.assertEqual(jpost(c, D + "new-member/", {"first_name": "X", "phone": "901234567"}).status_code, 404)
        self.assertEqual(User.objects.filter(phone="+998901234567").count(), 0)

    def test_staff_outside_admin_mode_is_sent_to_the_admin_login(self):
        c = self.client_for(self.staff_user, admin_mode=False)
        for url in self.urls():
            r = c.get(url)
            self.assertEqual((r.status_code, r["Location"]), (302, "/login/?need_admin=1"), url)
        self.assertEqual(jpost(c, D + f"checkin/{self.m.pk}/").status_code, 302)
        self.assertFalse(Visit.objects.exists())

    def test_staff_in_admin_mode_opens_every_page(self):
        for url in self.urls():
            self.assertEqual(self.desk.get(url).status_code, 200, url)

    def test_get_on_an_action_endpoint_is_a_json_405(self):
        r = self.desk.get(D + f"checkin/{self.m.pk}/")
        self.assertEqual((r.status_code, r.json()["ok"]), (405, False))

    def test_posts_need_a_csrf_token(self):
        c = Client(enforce_csrf_checks=True)
        c.force_login(self.staff_user)
        s = c.session
        s["admin_mode"] = True
        s.save()
        self.assertEqual(c.post(D + f"checkin/{self.m.pk}/", content_type="application/json", data="{}").status_code, 403)
        self.assertEqual(c.post(D + "scan/", content_type="application/json", data="{}").status_code, 403)
        self.assertFalse(EntryLog.objects.exists())


@override_settings(TEMPLATES=TEMPLATES)
class PageTests(DeskBase):
    def test_pages_render_without_missing_variables(self):
        self.membership(self.m)
        pay = Payment.objects.create(user=self.m, kind="plan", plan=self.plan, amount=self.plan.price, method="card", status="pending", card_last4="1111")
        for url in (D, D + "?q=Aziz", D + "scan/", D + "classes/", D + "shift/", D + f"card/{self.m.pk}/"):
            r = self.desk.get(url)
            self.assertEqual(r.status_code, 200, url)
            self.assertNotIn("@@INVALID", clean(r.content.decode()), url)
        r = self.desk.get(D + f"member/{self.m.pk}/")
        self.assertNotIn("@@INVALID", r.json()["html"])
        self.desk.post(D + f"confirm/{pay.pk}/", content_type="application/json")
        paid = Payment.objects.get(pk=pay.pk)
        r = self.desk.get(D + f"receipt/{paid.pk}/")
        self.assertContains(r, "To'lov cheki")
        self.assertNotIn("@@INVALID", clean(r.content.decode()))

    def test_desk_page_lists_the_queues(self):
        Payment.objects.create(user=self.m, kind="plan", plan=self.plan, amount=100000, method="card", status="pending", card_last4="1111",
                               sender_last4="9999", proof_at=timezone.now())
        html = self.desk.get(D).content.decode()
        self.assertIn("9999", html)
        self.assertIn('id="dk-q"', html)
        self.assertIn('data-tab="classes"', html)
        self.assertIn('data-tab="guests"', html)

    def test_classes_page_and_attendance(self):
        today = timezone.localdate()
        c = GymClass.objects.create(name="Yoga", weekday=today.weekday(), start_time=(timezone.localtime() - timedelta(hours=2)).time(), capacity=10, active=True)
        b = Booking.objects.create(user=self.m, gym_class=c, date=today)
        self.assertContains(self.desk.get(D + "classes/"), "Yoga")
        r = jpost(self.desk, D + f"booking/{b.pk}/came/")
        self.assertEqual((r.status_code, r.json()["ok"]), (200, True))
        b.refresh_from_db()
        self.assertIsNotNone(b.checked_in_at)
        jpost(self.desk, D + f"booking/{b.pk}/noshow/")
        b.refresh_from_db()
        self.assertTrue(b.no_show)
        self.assertEqual(jpost(self.desk, D + f"booking/{b.pk}/wrong/").status_code, 400)


class SearchTests(DeskBase):
    def find(self, q, client=None):
        r = (client or self.desk).get(D + "search/", {"q": q})
        self.assertEqual(r.status_code, 200, q)
        return r.json()

    def test_search_by_name_phone_code_and_qr_text(self):
        for q in ("Aziz", "azi kari", "901112233", "+998 90 111 22 33", self.m.member_code, f"fz{self.m.pk}", services.card_token(self.m)):
            rows = self.find(q)["results"]
            self.assertEqual([r["id"] for r in rows], [self.m.pk], q)
        row = self.find("Aziz")["results"][0]
        self.assertEqual((row["name"], row["code"], row["status"]), ("Aziz Karimov", self.m.member_code, "none"))

    def test_search_never_returns_the_owner_and_ignores_junk(self):
        self.assertEqual(self.find(services.card_token(self.boss))["results"], [])
        self.assertEqual(self.find("a")["results"] and self.find("zzzzzz")["results"], [])
        self.assertEqual(self.find("")["results"], [])

    def test_status_labels(self):
        cases = {}
        a = User.objects.create_user(username="act1", password=PW, first_name="Faol")
        self.membership(a, days=30)
        b = User.objects.create_user(username="exp1", password=PW, first_name="Tugayapti")
        self.membership(b, days=3)
        c = User.objects.create_user(username="old1", password=PW, first_name="Tugagan")
        now = timezone.now()
        Membership.objects.create(user=c, plan=self.plan, starts=now - timedelta(days=60), expires=now - timedelta(days=30))
        d = User.objects.create_user(username="blk1", password=PW, first_name="Bloklangan", is_active=False)
        e = User.objects.create_user(username="frz1", password=PW, first_name="Muzlagan")
        self.membership(e, days=40)
        extras.start_freeze(e, 7)
        for u in (a, b, c, d, e):
            cases[u.first_name] = self.find(u.first_name)["results"][0]["status"]
        self.assertEqual(cases, {"Faol": "active", "Tugayapti": "expiring", "Tugagan": "expired", "Bloklangan": "blocked", "Muzlagan": "frozen"})

    def test_search_is_rate_limited(self):
        codes = [self.desk.get(D + "search/", {"q": "Aziz"}).status_code for _ in range(45)]
        self.assertEqual(codes[:40], [200] * 40)
        self.assertEqual(codes[-1], 429)
        r = self.desk.get(D + "search/", {"q": "Aziz"})
        self.assertEqual((r.json()["ok"], r.status_code), (False, 429))

    def test_guest_code_in_the_search_box(self):
        self.membership(self.m, days=30)
        gp, err = extras.create_guest_pass(self.m, "Sardor", "", timezone.localdate())
        self.assertIsNone(err)
        g = self.find(extras.guest_code(gp))["guest"]
        self.assertEqual((g["guest"], g["state"], g["can"]), ("Sardor", "good", True))
        self.assertIsNone(self.find("GP-1-badbadbadbad")["guest"])


class EntryTests(DeskBase):
    def checkin(self, u=None):
        r = jpost(self.desk, D + f"checkin/{(u or self.m).pk}/")
        self.assertEqual(r.status_code, 200)
        return r.json()

    def test_checkin_ok_writes_visit_and_entry_with_the_staff_member(self):
        self.membership(self.m)
        d = self.checkin()
        self.assertTrue(d["entered"])
        self.assertEqual((d["banner"]["title"], d["banner"]["name"]), ("Kirishga ruxsat", "Aziz Karimov"))
        self.assertEqual(Visit.objects.filter(user=self.m).count(), 1)
        e = EntryLog.objects.get()
        self.assertEqual((e.method, e.result, e.staff), ("manual", "ok", self.staff_user))
        self.assertIn("Aziz Karimov", d["html"])

    def test_second_checkin_is_a_repeat_not_a_new_visit(self):
        self.membership(self.m)
        self.checkin()
        d = self.checkin()
        self.assertTrue(d["entered"])
        self.assertEqual(Visit.objects.filter(user=self.m).count(), 1)
        self.assertEqual(list(EntryLog.objects.order_by("id").values_list("result", flat=True)), ["ok", "repeat"])

    def test_expired_membership_is_refused_with_a_reason(self):
        now = timezone.now()
        Membership.objects.create(user=self.m, plan=self.plan, starts=now - timedelta(days=60), expires=now - timedelta(days=30))
        d = self.checkin()
        self.assertFalse(d["entered"])
        self.assertEqual((d["banner"]["title"], d["banner"]["reason"], d["banner"]["reason_label"]), ("Kirish taqiqlangan", "expired", "Abonement tugagan"))
        self.assertFalse(Visit.objects.exists())
        e = EntryLog.objects.get()
        self.assertEqual((e.result, e.reason, e.staff), ("rejected", "expired", self.staff_user))

    def test_no_membership_and_blocked_and_frozen(self):
        d = self.checkin()
        self.assertEqual(d["banner"]["reason"], "no_membership")
        blocked = User.objects.create_user(username="blk", password=PW, first_name="Blok", is_active=False)
        self.membership(blocked)
        self.assertEqual(self.checkin(blocked)["banner"]["reason"], "blocked")
        frozen = User.objects.create_user(username="frz", password=PW, first_name="Muz")
        self.membership(frozen, days=40)
        extras.start_freeze(frozen, 7)
        d = self.checkin(frozen)
        self.assertEqual((d["entered"], d["banner"]["reason"]), (False, "frozen"))
        self.assertIn("gacha", d["banner"]["reason_label"])
        self.assertFalse(Visit.objects.exists())

    def test_scan_returns_the_banner_and_the_member_id(self):
        self.membership(self.m)
        r = jpost(self.desk, D + "scan/", {"code": services.card_token(self.m)})
        d = r.json()
        self.assertEqual((r.status_code, d["entered"], d["member_id"], d["banner"]["title"]), (200, True, self.m.pk, "Kirishga ruxsat"))
        self.assertIn("tk", d["ticket"])
        r = jpost(self.desk, D + "scan/", {"code": "FZ:1:bad"})
        self.assertEqual((r.status_code, r.json()["ok"]), (404, False))
        self.assertEqual(EntryLog.objects.filter(reason="invalid", staff=self.staff_user).count(), 1)

    def test_freeze_and_unfreeze_from_the_panel(self):
        self.membership(self.m, days=40)
        r = jpost(self.desk, D + f"freeze/{self.m.pk}/", {"days": 7})
        self.assertEqual((r.status_code, r.json()["ok"]), (200, True))
        self.assertTrue(services.active_membership(self.m).is_frozen)
        self.assertEqual(jpost(self.desk, D + f"freeze/{self.m.pk}/", {"days": 7}).status_code, 409)  # already frozen
        self.assertEqual(jpost(self.desk, D + f"freeze/{self.m.pk}/", {"days": "x"}).status_code, 400)
        r = jpost(self.desk, D + f"unfreeze/{self.m.pk}/")
        self.assertTrue(r.json()["ok"])
        self.assertFalse(services.active_membership(self.m).is_frozen)
        self.assertEqual(jpost(self.desk, D + f"unfreeze/{self.m.pk}/").status_code, 409)

    def test_block_toggle(self):
        self.assertTrue(jpost(self.desk, D + f"block/{self.m.pk}/").json()["ok"])
        self.m.refresh_from_db()
        self.assertFalse(self.m.is_active)
        jpost(self.desk, D + f"block/{self.m.pk}/")
        self.m.refresh_from_db()
        self.assertTrue(self.m.is_active)

    def test_the_owner_account_is_not_handled_at_the_desk(self):
        self.assertEqual(jpost(self.desk, D + f"checkin/{self.boss.pk}/").status_code, 404)
        self.assertEqual(self.desk.get(D + f"member/{self.boss.pk}/").status_code, 404)


class SaleTests(DeskBase):
    def sell(self, **kw):
        data = {"plan": "m1", "method": "cash", "consent": True, **kw}
        return jpost(self.desk, D + f"sell/{self.m.pk}/", data)

    def test_sale_creates_a_confirmed_payment_and_membership_with_the_staff_member(self):
        r = self.sell()
        d = r.json()
        self.assertEqual((r.status_code, d["ok"]), (200, True))
        p = Payment.objects.get()
        self.assertEqual((p.status, p.method, p.kind, p.amount, p.user, p.plan, p.staff), ("paid", "cash", "plan", self.plan.price, self.m, self.plan, self.staff_user))
        self.assertIsNotNone(p.consent_at)
        self.m.refresh_from_db()
        self.assertIsNotNone(self.m.consent_at)
        m = services.active_membership(self.m)
        self.assertEqual(m.plan, self.plan)
        self.assertEqual(d["receipt"], D + f"receipt/{p.pk}/")
        self.assertIn("Faol", d["html"])

    def test_card_transfer_sale_records_the_receiving_card(self):
        self.sell(method="card")
        p = Payment.objects.get()
        self.assertEqual((p.method, p.status), ("card", "paid"))
        card = services.current_card()
        if card:
            self.assertEqual(p.card_last4, card.last4)

    def test_extending_stacks_on_the_current_membership(self):
        self.membership(self.m, days=10)
        before = services.paid_until(self.m)
        self.sell()
        self.assertEqual(services.paid_until(self.m), before + timedelta(days=30 * self.plan.months))
        self.assertEqual(Membership.objects.filter(user=self.m).count(), 2)

    def test_sale_validation(self):
        self.assertEqual(self.sell(plan="nope").status_code, 400)
        self.assertEqual(self.sell(method="gift").status_code, 400)
        self.assertEqual(self.sell(consent=False).status_code, 400)  # consent must be ticked the first time
        self.m.is_active = False
        self.m.save()
        self.assertEqual(self.sell().status_code, 409)
        self.assertFalse(Payment.objects.exists() or Membership.objects.exists())

    def test_consent_is_not_asked_again_once_given(self):
        self.sell()
        r = self.sell(consent=False)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(Payment.objects.count(), 2)

    def test_referral_reward_runs_on_a_desk_sale(self):
        friend = User.objects.create_user(username="friend", password=PW, first_name="Do'st", referred_by=self.m)
        jpost(self.desk, D + f"sell/{friend.pk}/", {"plan": "m1", "method": "cash", "consent": True})
        friend.refresh_from_db()
        self.assertTrue(friend.referral_rewarded)


class QuickMemberTests(DeskBase):
    def make(self, **kw):
        data = {"first_name": "Bobur", "last_name": "Aliyev", "phone": "93 555 66 77", **kw}
        return jpost(self.desk, D + "new-member/", data)

    def test_creates_a_member_with_a_random_password_and_a_card(self):
        r = self.make()
        d = r.json()
        self.assertEqual((r.status_code, d["ok"]), (200, True))
        u = User.objects.get(phone="+998935556677")
        self.assertEqual((u.first_name, u.last_name, u.is_staff, u.is_superuser, u.is_active), ("Bobur", "Aliyev", False, False, True))
        self.assertTrue(u.has_usable_password())
        self.assertFalse(u.check_password(""))
        self.assertIn("<svg", d["card"])
        self.assertEqual(d["card_url"], D + f"card/{u.pk}/")
        self.assertEqual(d["id"], u.pk)
        self.assertFalse(Payment.objects.exists())
        self.assertEqual(self.desk.get(d["card_url"]).status_code, 200)

    def test_phone_must_be_valid_and_unique(self):
        self.assertEqual(self.make(phone="123").status_code, 400)
        self.assertEqual(self.make(phone="").json()["field"], "phone")
        r = self.make(phone="90 111 22 33")  # already taken by Aziz
        self.assertEqual((r.status_code, r.json()["field"]), (409, "phone"))
        self.assertEqual(self.make(first_name="B").status_code, 400)
        self.assertEqual(User.objects.filter(is_superuser=False, is_staff=False).count(), 1)

    def test_optional_plan_sale(self):
        r = self.make(plan="m1", method="cash", consent=True)
        self.assertEqual(r.status_code, 200)
        p = Payment.objects.get()
        self.assertEqual((p.status, p.staff, p.user.phone), ("paid", self.staff_user, "+998935556677"))
        self.assertTrue(services.active_membership(p.user))
        self.assertEqual(r.json()["receipt"], D + f"receipt/{p.pk}/")

    def test_plan_sale_needs_consent_and_a_known_plan(self):
        self.assertEqual(self.make(plan="m1", method="cash").status_code, 400)
        self.assertEqual(self.make(plan="nope", consent=True).status_code, 400)
        self.assertFalse(User.objects.filter(phone="+998935556677").exists())


class QueueTests(DeskBase):
    def pending(self):
        return Payment.objects.create(user=self.m, kind="plan", plan=self.plan, amount=self.plan.price, method="card", status="pending", card_last4="1111")

    def test_approve_payment_gives_the_membership_and_records_the_staff_member(self):
        p = self.pending()
        r = jpost(self.desk, D + f"confirm/{p.pk}/")
        self.assertEqual((r.status_code, r.json()["ok"]), (200, True))
        p.refresh_from_db()
        self.assertEqual((p.status, p.staff), ("paid", self.staff_user))
        self.assertTrue(services.active_membership(self.m))
        self.assertEqual(jpost(self.desk, D + f"confirm/{p.pk}/").status_code, 409)  # not twice
        self.assertEqual(Membership.objects.filter(user=self.m).count(), 1)

    def test_reject_payment(self):
        p = self.pending()
        self.assertTrue(jpost(self.desk, D + f"reject/{p.pk}/").json()["ok"])
        p.refresh_from_db()
        self.assertEqual((p.status, p.staff), ("cancelled", self.staff_user))
        self.assertFalse(Membership.objects.exists())
        self.assertEqual(jpost(self.desk, D + f"reject/{p.pk}/").status_code, 409)

    def test_unknown_ids_are_404_json_free_of_side_effects(self):
        self.assertEqual(jpost(self.desk, D + "confirm/99999/").status_code, 404)
        self.assertEqual(jpost(self.desk, D + "handover/99999/").status_code, 404)

    def test_today_endpoint_counts_and_fragments(self):
        self.pending()
        self.membership(self.m)
        jpost(self.desk, D + f"checkin/{self.m.pk}/")
        d = self.desk.get(D + "today/").json()
        self.assertEqual(d["counts"]["pay"], 1)
        self.assertEqual(d["counts"]["visits"], 1)
        self.assertEqual(set(d["tabs"]), {"pay", "orders", "pt", "classes", "guests", "visits"})
        self.assertIn("Aziz Karimov", d["tabs"]["visits"]["html"])
        self.assertIn("Tasdiqlash", d["tabs"]["pay"]["html"])
        self.assertTrue(d["tabs"]["pay"]["hash"])
        self.assertIn("Bugungi tushum", d["shift"])
        again = self.desk.get(D + "today/").json()
        self.assertEqual(again["tabs"]["pay"]["hash"], d["tabs"]["pay"]["hash"])  # unchanged queue: the page does not redraw it

    def test_order_handover(self):
        o = Order.objects.create(user=self.m, total=50000, status="new")
        self.assertContains(self.desk.get(D), f"#{o.pk}")
        self.assertTrue(jpost(self.desk, D + f"handover/{o.pk}/").json()["ok"])
        o.refresh_from_db()
        self.assertEqual(o.status, "done")


class ShiftTests(DeskBase):
    def test_summary_numbers(self):
        self.membership(self.m)
        other = User.objects.create_user(username="qabul2", password="Xodim-Parol-2", first_name="Zafar", is_staff=True)
        jpost(self.desk, D + f"sell/{self.m.pk}/", {"plan": "m1", "method": "cash", "consent": True})
        jpost(self.desk, D + f"sell/{self.m.pk}/", {"plan": "m1", "method": "card", "consent": True})
        jpost(self.client_for(other, True), D + f"sell/{self.m.pk}/", {"plan": "m1", "method": "cash"})
        old = Payment.objects.create(user=self.m, kind="plan", plan=self.plan, amount=999, method="cash", status="paid")
        Payment.objects.filter(pk=old.pk).update(created=timezone.now() - timedelta(days=3))
        Payment.objects.create(user=self.m, kind="plan", plan=self.plan, amount=777, method="cash", status="pending")  # not collected yet
        jpost(self.desk, D + f"checkin/{self.m.pk}/")
        no = User.objects.create_user(username="nomem", password=PW, first_name="Yo'q")
        jpost(self.desk, D + f"checkin/{no.pk}/")
        gp, _ = extras.create_guest_pass(self.m, "Mehmon", "", timezone.localdate())
        jpost(self.desk, D + "guest/", {"id": gp.pk, "redeem": True})
        p = self.plan.price
        s = self.desk.get(D + "today/").json()
        self.assertEqual(s["counts"]["visits"], 1)
        from .desk import shift_summary
        s = shift_summary(timezone.localdate(), self.staff_user)
        self.assertEqual(s["total"], 3 * p)
        self.assertEqual(s["count"], 3)
        self.assertEqual(s["cash"], 2 * p)
        self.assertEqual({r["method"]: (r["n"], r["sum"]) for r in s["by_method"]}, {"cash": (2, 2 * p), "card": (1, p)})
        self.assertEqual((s["sold"], s["sold_sum"]), (3, 3 * p))
        self.assertEqual((s["entries"], s["rejected"], s["guest_entries"]), (1, 1, 1))
        self.assertEqual((s["mine"], s["mine_n"]), (2 * p, 2))
        self.assertEqual({r["name"]: r["sum"] for r in s["by_staff"]}, {"Dilnoza": 2 * p, "Zafar": p})

    def test_printable_report_shows_the_totals(self):
        jpost(self.desk, D + f"sell/{self.m.pk}/", {"plan": "m1", "method": "cash", "consent": True})
        r = self.desk.get(D + "shift/")
        self.assertContains(r, "Smena hisoboti")
        self.assertContains(r, f"{self.plan.price:,}".replace(",", " "))
        self.assertEqual(self.desk.get(D + "shift/?d=2999-01-01").status_code, 200)  # a future day falls back to today
        self.assertEqual(self.desk.get(D + "shift/?d=garbage").status_code, 200)


class GuestTests(DeskBase):
    def setUp(self):
        super().setUp()
        self.membership(self.m, days=30)
        self.gp, err = extras.create_guest_pass(self.m, "Sardor", "90 765 43 21", timezone.localdate())
        self.assertIsNone(err)

    def test_check_then_let_the_guest_in(self):
        code = extras.guest_code(self.gp)
        r = jpost(self.desk, D + "guest/", {"code": code})
        g = r.json()["guest"]
        self.assertEqual((g["guest"], g["owner"], g["state"], g["can"]), ("Sardor", "Aziz Karimov", "good", True))
        self.assertFalse(r.json().get("entered"))
        self.gp.refresh_from_db()
        self.assertIsNone(self.gp.used_at)  # checking does not use the pass
        r = jpost(self.desk, D + "guest/", {"code": code, "redeem": True})
        d = r.json()
        self.assertTrue(d["entered"])
        self.assertEqual(d["banner"]["title"], "Kirishga ruxsat")
        self.gp.refresh_from_db()
        self.assertEqual((self.gp.checked_by, bool(self.gp.used_at)), (self.staff_user, True))
        e = EntryLog.objects.get()
        self.assertEqual((e.method, e.result, e.guest_pass, e.staff), ("guest", "ok", self.gp, self.staff_user))
        r = jpost(self.desk, D + "guest/", {"code": code, "redeem": True})
        self.assertFalse(r.json()["entered"])
        self.assertEqual(r.json()["guest"]["state"], "bad")

    def test_wrong_day_and_unknown_code(self):
        tomorrow, _ = extras.create_guest_pass(self.m, "Ertaga", "", timezone.localdate() + timedelta(days=1))
        g = jpost(self.desk, D + "guest/", {"id": tomorrow.pk}).json()["guest"]
        self.assertEqual((g["state"], g["can"]), ("warn", False))
        self.assertFalse(jpost(self.desk, D + "guest/", {"id": tomorrow.pk, "redeem": True}).json()["entered"])
        self.assertEqual(jpost(self.desk, D + "guest/", {"code": "GP-1-badbadbadbad"}).status_code, 404)
        self.assertEqual(jpost(self.desk, D + "guest/", {"id": "abc"}).status_code, 404)

    def test_scanner_accepts_a_guest_qr_and_the_list_shows_today(self):
        r = jpost(self.desk, D + "scan/", {"code": extras.guest_code(self.gp)})
        d = r.json()
        self.assertEqual((r.status_code, d["entered"], d["banner"]["name"]), (200, True, "Sardor"))
        tab = self.desk.get(D + "today/").json()["tabs"]["guests"]["html"]
        self.assertIn("Sardor", tab)
        self.assertIn("Kirgan", tab)
