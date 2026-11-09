from datetime import date, timedelta
from decimal import Decimal

from django.core.cache import cache
from django.core.management import call_command
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from .models import BodyLog, User
from .tests_audit import invalid_vars, raw_keys


class ToolsPageTests(TestCase):
    def setUp(self):
        cache.clear()
        call_command("setup_gym", demo=True, verbosity=0)

    def test_anonymous_page_renders_with_defaults(self):
        r = self.client.get("/tools/")
        self.assertEqual(r.status_code, 200)
        html = r.content.decode()
        for name in ("age", "w", "h", "act", "neck", "waist", "hip", "lw", "lr", "tm", "rhr"):
            self.assertIn(f'name="{name}"', html)
        self.assertIn('value="70"', html)
        self.assertIn('data-birth=""', html)
        self.assertIn(reverse("calories"), html)
        self.assertNotIn("🥗", html)
        # five activity options with the standard multipliers
        for k in ("1.2", "1.375", "1.55", "1.725", "1.9"):
            self.assertIn(f'<option value="{k}"', html)

    def test_member_is_prefilled_from_profile(self):
        u = User.objects.create_user(username="calcuser", password="x12345678", birth_date=date(1995, 5, 5), goal="lose")
        BodyLog.objects.create(user=u, weight=Decimal("82.5"), height_cm=181)
        self.client.force_login(u)
        html = self.client.get("/tools/").content.decode()
        self.assertIn('value="82.5"', html)
        self.assertIn('value="181"', html)
        self.assertIn('data-birth="1995-05-05"', html)
        self.assertIn('data-goal="lose"', html)
        self.assertIn('data-profile-w="82.5"', html)

    def test_three_tabs_disclaimers_and_formulas(self):
        html = self.client.get("/tools/").content.decode()
        self.assertIn('role="tablist"', html)
        self.assertEqual(html.count('role="tab"'), 3)
        self.assertEqual(html.count('role="tabpanel"'), 3)
        for k in ("tana", "ovqat", "mashq"):
            self.assertIn(f'id="tl-tab-{k}"', html)
            self.assertIn(f'id="tl-panel-{k}"', html)
        self.assertIn("Tana tahlili", html)
        self.assertIn("Ovqatlanish", html)
        self.assertEqual(html.count('class="tl-disc muted"'), 3)
        for name in ("Devine", "Mifflin", "Epley", "Tanaka", "Karvonen", "US Navy"):
            self.assertIn(name, html)
        self.assertEqual(html.count('class="tl-how"'), 8)
        self.assertIn("Qanday hisoblanadi?", html)
        # shared inputs card with the mobile summary toggle; chart mounts for the SVG charts
        self.assertIn('class="tl-me-toggle"', html)
        for c in ("bmi", "bf", "cal", "macro", "cups", "orm", "zones"):
            self.assertIn(f'data-chart="{c}"', html)

    def test_tabs_in_every_language(self):
        for lang in ("uz", "ru", "en"):
            self.client.cookies["fz_lang"] = lang
            html = self.client.get("/tools/").content.decode()
            self.assertEqual(raw_keys(html), set(), lang)
            self.assertEqual(invalid_vars(html), set(), lang)
            self.assertEqual(html.count('role="tab"'), 3)
        self.client.cookies["fz_lang"] = "en"
        self.assertIn("Body analysis", self.client.get("/tools/").content.decode())

    def test_script_has_tabs_and_charts(self):
        js = open("gym/static/js/tools.js", encoding="utf-8").read()
        for needle in ("hashchange", "fz_tools_tab", "aria-selected", "FZTools", "viewBox"):
            self.assertIn(needle, js)

    def test_i18n_keys_resolve(self):
        html = self.client.get("/tools/").content.decode()
        self.assertEqual(raw_keys(html), set())
        self.assertEqual(invalid_vars(html), set())
        self.assertIn("Tana yog&#x27;i", html)


class ToolsSaveTests(TestCase):
    """"Natijani saqlash": the calculators' weight / height become today's BodyLog row, the goal becomes the profile goal."""

    def setUp(self):
        cache.clear()
        call_command("setup_gym", demo=True, verbosity=0)
        self.u = User.objects.create_user(username="saver", password="x12345678", goal="strength")
        self.client.force_login(self.u)
        self.url = reverse("tools_save")

    def save(self, **data):
        return self.client.post(self.url, data, headers={"X-Requested-With": "fetch"})

    def test_anonymous_sees_a_sign_in_link_not_the_button(self):
        self.client.logout()
        html = self.client.get("/tools/").content.decode()
        self.assertNotIn("data-save", html)
        self.assertIn(f'href="{reverse("login")}?next={reverse("tools")}"', html)
        self.assertIn("Saqlash uchun kiring", html)
        r = self.client.post(self.url, {"weight": "80", "height": "180"})
        self.assertEqual(r.status_code, 302)
        self.assertIn("/login/", r["Location"])
        self.assertFalse(BodyLog.objects.exists())

    def test_member_sees_the_button_and_toast(self):
        html = self.client.get("/tools/").content.decode()
        self.assertIn("data-save", html)
        self.assertIn(f'data-url="{reverse("tools_save")}"', html)
        self.assertIn("csrfmiddlewaretoken", html)
        self.assertIn('id="tl-toast"', html)
        self.assertIn("Natijani saqlash", html)
        self.assertNotIn("Saqlash uchun kiring", html)

    def test_saves_weight_height_and_goal(self):
        r = self.save(weight="82.5", height="181", goal="lose")
        self.assertEqual(r.status_code, 200)
        j = r.json()
        self.assertTrue(j["ok"] and j["created"])
        self.assertIn("Saqlandi", j["message"])
        log = BodyLog.objects.get(user=self.u)
        self.assertEqual((log.weight, log.height_cm, log.date), (Decimal("82.5"), 181, timezone.localdate()))
        self.u.refresh_from_db()
        self.assertEqual(self.u.goal, "lose")
        # the calculators now start from the saved numbers
        html = self.client.get("/tools/").content.decode()
        self.assertIn('data-profile-w="82.5"', html)
        self.assertIn('data-goal="lose"', html)

    def test_second_save_the_same_day_updates_the_row(self):
        self.save(weight="82.5", height="181", goal="lose")
        BodyLog.objects.filter(user=self.u).update(note="morning")
        r = self.save(weight="81,2", height="182", goal="gain")  # a decimal comma is accepted
        self.assertTrue(r.json()["ok"])
        self.assertFalse(r.json()["created"])
        self.assertIn("Yangilandi", r.json()["message"])
        log = BodyLog.objects.get(user=self.u)
        self.assertEqual((log.weight, log.height_cm, log.note), (Decimal("81.2"), 182, "morning"))
        self.u.refresh_from_db()
        self.assertEqual(self.u.goal, "gain")

    def test_earlier_days_and_other_members_are_untouched(self):
        other = User.objects.create_user(username="other", password="x12345678")
        old = BodyLog.objects.create(user=self.u, weight=Decimal("90"), height_cm=180, date=timezone.localdate() - timedelta(days=3))
        theirs = BodyLog.objects.create(user=other, weight=Decimal("60"), height_cm=165)
        self.save(weight="85", height="180")
        self.assertEqual(BodyLog.objects.filter(user=self.u).count(), 2)  # a new row for today, the old one stays
        old.refresh_from_db()
        theirs.refresh_from_db()
        self.assertEqual((old.weight, theirs.weight), (Decimal("90.0"), Decimal("60.0")))

    def test_goal_is_optional_and_validated(self):
        self.save(weight="85", height="180")
        self.u.refresh_from_db()
        self.assertEqual(self.u.goal, "strength")  # not sent: the profile goal stays
        r = self.save(weight="85", height="180", goal="bulk-up-now")
        self.assertEqual(r.status_code, 400)
        self.u.refresh_from_db()
        self.assertEqual(self.u.goal, "strength")

    def test_out_of_range_and_garbage_are_rejected(self):
        bad = [dict(weight="29.9", height="180"), dict(weight="250.1", height="180"), dict(weight="80", height="119"), dict(weight="80", height="231"),
               dict(weight="abc", height="180"), dict(weight="80", height="x"), dict(weight="80", height="175.5"), dict(weight="nan", height="180"),
               dict(weight="inf", height="180"), dict(weight="-70", height="180"), dict(weight="", height=""), dict(height="180"), dict(weight="80")]
        for data in bad:
            r = self.save(**data)
            self.assertEqual(r.status_code, 400, data)
            self.assertFalse(r.json()["ok"])
            self.assertIn("30–250", r.json()["error"])
        self.assertFalse(BodyLog.objects.exists())
        for data in (dict(weight="30", height="120"), dict(weight="250", height="230")):  # the limits themselves are fine
            self.assertEqual(self.save(**data).status_code, 200, data)

    def test_post_only_and_csrf(self):
        self.assertEqual(self.client.get(self.url).status_code, 405)
        strict = Client(enforce_csrf_checks=True)
        strict.force_login(self.u)
        self.assertEqual(strict.post(self.url, {"weight": "80", "height": "180"}).status_code, 403)
        strict.get("/tools/")  # sets the CSRF cookie
        token = strict.cookies["csrftoken"].value
        self.assertEqual(strict.post(self.url, {"weight": "80", "height": "180"}, headers={"X-CSRFToken": token}).status_code, 200)

    def test_messages_and_page_in_every_language(self):
        for lang, word in (("ru", "Сохранено"), ("en", "Saved")):
            BodyLog.objects.all().delete()
            self.client.cookies["fz_lang"] = lang
            self.assertIn(word, self.save(weight="80", height="180").json()["message"])
        for lang in ("uz", "ru", "en"):
            self.client.cookies["fz_lang"] = lang
            html = self.client.get("/tools/").content.decode()
            self.assertEqual(raw_keys(html), set(), lang)
            self.assertEqual(invalid_vars(html), set(), lang)
            self.assertIn("data-save", html)

    def test_script_posts_to_the_endpoint_with_csrf(self):
        js = open("gym/static/js/tools.js", encoding="utf-8").read()
        for needle in ("[data-save]", "X-CSRFToken", "X-Requested-With", "tl-toast", "URLSearchParams", "goalTouched"):
            self.assertIn(needle, js)
