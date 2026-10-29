"""Whole-site audit: every page as a trainer too, every custom admin page, and the entry receipt in every state and language.
Templates run with string_if_invalid, so a typo in a variable name fails the test instead of printing nothing."""
import copy
import json
import re
from datetime import timedelta

from django.conf import settings
from django.core.cache import cache
from django.core.management import call_command
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from . import services
from .i18n import T
from .models import Membership, Notification, Plan, Product, Trainer, User, Visit
from .urls import urlpatterns

INVALID = "@@INVALID[%s]@@"
TEMPLATES = copy.deepcopy(settings.TEMPLATES)
TEMPLATES[0]["OPTIONS"]["string_if_invalid"] = INVALID
ALLOWED_INVALID = {"mine.comment", "mine.rating", "q", "next"}
PW = "Kuchli-Parol-77"


def invalid_vars(html):
    return set(re.findall(r"@@INVALID\[(.*?)\]@@", html)) - ALLOWED_INVALID


def raw_keys(html):
    """Translation keys that leaked to the page untranslated (the tag falls back to the key itself)."""
    words = set(re.findall(r"(?<![\w/.#-])([a-z]+_[a-z0-9_]+)(?![\w/.=-])", re.sub(r"<[^>]+>", " ", html)))
    return {w for w in words if w in T["uz"] and T["uz"][w] != w}


@override_settings(TEMPLATES=TEMPLATES, GOOGLE_CLIENT_ID="")
class AuditBase(TestCase):
    def setUp(self):
        cache.clear()
        call_command("setup_gym", demo=True, verbosity=0)
        self.admin = User.objects.get(is_superuser=True)
        self.admin.set_password("AdminPass1")
        self.admin.save()
        now = timezone.now()
        self.m = User.objects.create_user(phone="+998901112233", password=PW, first_name="Aziz", last_name="Karimov")
        Membership.objects.create(user=self.m, plan=Plan.objects.get(code="m1"), starts=now - timedelta(days=2), expires=now + timedelta(days=20))
        self.coach_user = User.objects.create_user(phone="+998935554433", password=PW, first_name="Sardor", last_name="R")
        self.t = Trainer.objects.filter(active=True).first()
        self.t.user = self.coach_user
        self.t.save()
        self.staff = Client()
        self.staff.post("/login/", {"login": "admin1", "password": "AdminPass1.admin"})
        self.coach = Client()
        self.coach.post("/login/", {"phone": "935554433", "password": PW, "role": "trainer"})

    def page_ok(self, client, url, who):
        r = client.get(url)
        self.assertLess(r.status_code, 500, f"{who} {url}")
        if r.status_code == 200 and "text/html" in r.get("Content-Type", ""):
            html = r.content.decode()
            self.assertEqual(invalid_vars(html), set(), f"{who} {url}: unknown template variables")
            self.assertEqual(raw_keys(html), set(), f"{who} {url}: untranslated keys on the page")
        return r


class RoleCrawlTests(AuditBase):
    def test_trainer_sees_every_page_without_errors(self):
        n = 0
        for p in urlpatterns:
            if p.pattern.converters or not p.name:
                continue
            self.page_ok(self.coach, reverse(p.name), "trainer")
            n += 1
        self.assertGreater(n, 30)
        self.assertEqual(self.coach.get("/coach/").status_code, 200)

    def test_pages_in_every_language(self):
        member = Client()
        member.post("/login/", {"phone": "901112233", "password": PW})
        for lang in ("uz", "ru", "en"):
            member.cookies["fz_lang"] = lang
            for url in ("/", "/dashboard/", "/profile/", "/inbox/", "/plans/", "/shop/", "/trainers/", "/records/", "/tools/", "/workouts/", "/card/"):
                self.page_ok(member, url, f"member[{lang}]")


class AdminCustomPagesTests(AuditBase):
    def test_every_custom_admin_page(self):
        services.notify(self.m, "Salom", "Matn", sender=self.admin, telegram_too=False)
        Product.objects.filter(pk=Product.objects.first().pk).update(stock=1)
        urls = ["/django-admin/", "/django-admin/reports/", "/django-admin/search/?q=Aziz", "/django-admin/search/?q=zz",
                f"/django-admin/member/{self.m.pk}/", "/django-admin/broadcast/", "/django-admin/message/",
                f"/django-admin/message/?ids={self.m.pk}", "/django-admin/message/?aud=active", "/django-admin/message/?q=Aziz",
                "/django-admin/live/", "/django-admin/schedule/", "/django-admin/schedule/?w=1", "/django-admin/cash/",
                "/django-admin/gym/product/?zaxira=low", "/django-admin/gym/product/?zaxira=out", "/django-admin/gym/notification/",
                "/django-admin/gym/personalrecord/", "/django-admin/gym/user/?goal__exact=lose"]
        for url in urls:
            r = self.staff.get(url)
            if url.endswith("q=Aziz") and "search" in url:  # a single hit opens the member card straight away
                self.assertEqual(r["Location"], f"/django-admin/member/{self.m.pk}/")
                continue
            self.assertEqual(r.status_code, 200, url)

    def test_bad_query_values_do_not_crash(self):
        for url in ("/django-admin/schedule/?w=abc", "/django-admin/cash/?d=2026-99-99", "/django-admin/message/?ids=1,abc,,9999999",
                    "/django-admin/message/?aud=nope", "/django-admin/member/999999/"):
            self.assertIn(self.staff.get(url).status_code, (200, 404), url)


class LoginAndAdminPolishTests(AuditBase):
    def test_owner_card_prints_a_receipt_and_blocked_member_is_refused(self):
        now = timezone.now()
        Membership.objects.create(user=self.admin, plan=Plan.objects.get(code="m1"), starts=now - timedelta(days=1), expires=now + timedelta(days=9))
        r = self.staff.post("/staff/scan/", json.dumps({"code": services.card_token(self.admin)}), content_type="application/json")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()["entered"])
        self.assertIn("V-", r.json()["ticket"])
        self.m.is_active = False
        self.m.save()
        r = self.staff.post("/staff/scan/", json.dumps({"code": services.card_token(self.m)}), content_type="application/json")
        self.assertFalse(r.json()["entered"])  # a paid membership does not let a blocked account in
        from django.utils.html import escape
        self.assertIn(escape(T["uz"]["err_blocked"]), r.json()["ticket"])
        self.assertIn(escape(T["uz"]["tk_help_blocked"]), r.json()["ticket"])  # not "renew at the desk"
        self.assertFalse(Visit.objects.filter(user=self.m).exists())

    def test_no_real_phone_in_placeholders(self):
        for url in ("/register/", "/forgot/"):
            html = Client().get(url).content.decode()
            phone_input = re.search(r'<input id="id_phone"[^>]*>', html).group(0)  # the gym's number in the footer is public on purpose
            self.assertNotIn("877", phone_input, url)
            self.assertIn('placeholder="XX XXX XX XX"', phone_input, url)

    def test_remember_me_and_previous_sign_in_note(self):
        c = Client()
        c.post("/login/", {"phone": "901112233", "password": PW})  # not ticked: ends with the browser
        self.assertTrue(c.session.get_expire_at_browser_close())
        c2 = Client()
        r = c2.post("/login/", {"phone": "901112233", "password": PW, "remember": "1"}, follow=True)
        self.assertFalse(c2.session.get_expire_at_browser_close())
        self.assertGreater(c2.session.get_expiry_age(), 20 * 86400)
        self.assertContains(r, T["uz"]["last_seen"].split("{")[0])  # the second sign-in shows when the first one was

    def test_login_page_has_the_new_parts(self):
        html = Client().get("/login/").content.decode()
        for part in ('name="remember"', "data-caps=", "auth-trust"):
            self.assertIn(part, html)
        self.assertNotIn("auth-hint", html)

    def test_admin_greets_by_name_and_shows_kpis_in_uzbek(self):
        r = self.staff.get("/django-admin/")
        self.assertContains(r, "fz-kpi-strip")
        self.assertContains(r, "Ketib qolish")
        self.assertNotContains(r, "+998908775505</strong>")
        r = self.staff.get("/django-admin/gym/user/")
        self.assertContains(r, "tanlang va tahrirlang")
        self.assertNotContains(r, "Select A")


class AdminResetOnDeployTests(AuditBase):
    def test_reset_only_when_asked(self):
        from unittest import mock
        with mock.patch.dict("os.environ", {"FZ_ADMIN_PASSWORD": "Yangi-Parol-2026"}):
            call_command("setup_gym", verbosity=0)
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.check_password("AdminPass1"))  # a normal deploy never touches the password
        with mock.patch.dict("os.environ", {"FZ_ADMIN_PASSWORD": "Yangi-Parol-2026", "FZ_ADMIN_RESET": "1"}):
            call_command("setup_gym", verbosity=0)
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.check_password("Yangi-Parol-2026"))
        r = Client().post("/login/", {"login": "admin1", "password": "Yangi-Parol-2026.admin"})
        self.assertEqual(r["Location"], "/django-admin/")

    def test_admin_suffix_in_env_is_not_part_of_the_password(self):
        from unittest import mock
        with mock.patch.dict("os.environ", {"FZ_ADMIN_PASSWORD": "2012.admin", "FZ_ADMIN_RESET": "1"}):
            call_command("setup_gym", verbosity=0)
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.check_password("2012"))
        r = Client().post("/login/", {"login": "admin1", "password": "2012.admin"})
        self.assertEqual(r["Location"], "/django-admin/")
        User.objects.filter(is_superuser=True).delete()  # a brand-new database (first deploy) gets the same treatment
        with mock.patch.dict("os.environ", {"FZ_ADMIN_PASSWORD": "2012.admin"}):
            call_command("setup_gym", verbosity=0)
        self.assertTrue(User.objects.get(is_superuser=True).check_password("2012"))


class ReceiptStatesTests(AuditBase):
    def scan(self, code, lang="uz"):
        self.staff.cookies["fz_lang"] = lang
        r = self.staff.post("/staff/scan/", json.dumps({"code": code}), content_type="application/json")
        return r, (r.json() if r.get("Content-Type", "").startswith("application/json") else {})

    def ticket_clean(self, d, label):
        html = d["ticket"]
        self.assertEqual(invalid_vars(html), set(), f"{label}: unknown variables in the receipt")
        self.assertEqual(raw_keys(html), set(), f"{label}: untranslated keys in the receipt")
        self.assertNotIn("None", re.sub(r"<[^>]+>", " ", html), f"{label}: 'None' printed on the receipt")
        return html

    def test_member_states_in_three_languages(self):
        for lang in ("uz", "ru", "en"):
            Visit.objects.all().delete()
            r, d = self.scan(services.card_token(self.m), lang)
            html = self.ticket_clean(d, f"ok[{lang}]")
            self.assertTrue(d["entered"])
            self.assertIn(T[lang]["tk_allowed"], html)
            self.assertIn("20 " + T[lang]["tk_days_left"], html)  # calendar days left
            r, d = self.scan(services.card_token(self.m) + " ", lang)  # same code again (different string, no client dedupe)
            html = self.ticket_clean(d, f"repeat[{lang}]")
            self.assertIn(T[lang]["tk_again"], html)
            self.assertEqual(Visit.objects.filter(user=self.m).count(), 1)

    def test_denied_states(self):
        nobody = User.objects.create_user(phone="+998977776655", password=PW, first_name="Begona", last_name="X")
        r, d = self.scan(services.card_token(nobody))
        html = self.ticket_clean(d, "no membership")
        self.assertFalse(d["entered"])
        self.assertIn(T["uz"]["err_member"], html)
        self.assertNotIn("tk-bar", html)
        self.assertNotIn("V-", html)
        # came in this morning, then the membership was frozen: the refusal must not reuse this morning's number
        Visit.objects.create(user=self.m)
        services.freeze(self.m, 7)
        r, d = self.scan(services.card_token(self.m))
        html = self.ticket_clean(d, "frozen")
        self.assertFalse(d["entered"])
        self.assertIn(T["uz"]["err_frozen"], html)
        self.assertNotIn("V-", html)

    def test_membership_ending_tomorrow_says_one_day(self):
        Membership.objects.filter(user=self.m).update(expires=timezone.now() + timedelta(hours=26))
        r, d = self.scan(services.card_token(self.m))
        exp = timezone.localtime(Membership.objects.get(user=self.m).expires).date()
        days = (exp - timezone.localdate()).days
        self.assertIn(f"{days} {T['uz']['tk_days_left']}", d["ticket"])
        self.assertGreaterEqual(days, 1)

    def test_impossible_dates_are_ignored_not_crashing(self):
        member = Client()
        member.post("/login/", {"phone": "901112233", "password": PW})
        r = member.post("/profile/", {"form": "goals", "goal": "keep", "birth_date": "1999-02-30"})
        self.assertEqual(r.status_code, 302)
        self.m.refresh_from_db()
        self.assertIsNone(self.m.birth_date)
        self.assertEqual(self.staff.get("/django-admin/cash/?d=2026-02-30").status_code, 200)

    def test_chat_send_with_odd_json(self):
        from . import chat
        other = User.objects.create_user(phone="+998977776655", password=PW, first_name="Begona", last_name="X")
        room = chat.direct_room(self.m, other)
        member = Client()
        member.post("/login/", {"phone": "901112233", "password": PW})
        for body in ("[1,2]", '{"body": 5}', "nope"):
            r = member.post(f"/chat/{room.pk}/send/", body, content_type="application/json", HTTP_ACCEPT="application/json")
            self.assertLess(r.status_code, 500, body)

    def test_bad_input(self):
        for body in ("", "{}", "[]", '{"code": null}', '{"code": 5}', '{"code": ["FZ:1:x"]}', "not json"):
            r = self.staff.post("/staff/scan/", body, content_type="application/json")
            self.assertIn(r.status_code, (404,), body)
        self.assertEqual(self.scan("FZ:1:bad")[0].status_code, 404)

    def test_scanner_page_is_clean(self):
        self.page_ok(self.staff, "/staff/scan/", "staff")
