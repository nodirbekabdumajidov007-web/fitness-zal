"""Regression tests for the visual / console audit: small things a browser pass found. The CSS ones read the stylesheet text (a layout bug cannot
be seen by the test client), so they only pin the rules that fixed each bug."""
from pathlib import Path

from django.contrib.staticfiles import finders
from django.core.cache import cache
from django.test import Client, TestCase
from django.urls import reverse

from .models import GymSettings, User


def css(name):
    return Path(finders.find(name)).read_text(encoding="utf-8")


class AuditFixTests(TestCase):
    def setUp(self):
        cache.clear()
        GymSettings.load()
        GymSettings.objects.get(pk=1).save()

    def test_calories_text_result_uses_the_translated_unit(self):
        """The recognised-foods list said "kcal" in every language: the unit now comes from the page (kkal / ккал / kcal)."""
        u = User.objects.create_user(username="kal2", email="kal2@x.uz", password="pw12345678")
        self.client.force_login(u)
        r = self.client.get(reverse("calories"))
        self.assertContains(r, 'data-kcal="kkal"')
        self.assertIn("data-kcal", Path(finders.find("js/calories.js")).read_text(encoding="utf-8"))

    def test_hidden_radios_are_not_page_wide(self):
        """`input{width:100%}` made the invisible meal radios 985px wide, so /calories/ scrolled sideways: they are 1px boxes now."""
        sheet = css("css/app.css")
        self.assertIn(".cal-meals input,.role-pick input,.star-pick input,.dlv-opt input,.tl-sex input,.tl-goal input,.ptile input{width:1px;height:1px", sheet)

    def test_receipt_keeps_light_colours_in_the_dark_theme(self):
        """The white member card / receipt had light-green and light-grey text in the dark theme (contrast 2.2 - 2.5)."""
        self.assertIn(".receipt{--muted:#5b6370;--good:#1d9a52", css("css/app.css"))

    def test_admin_light_theme_tokens_beat_djangos(self):
        """Django sets its variables on html[data-theme=light], which is more specific than :root, so the hand-picked light theme showed red text
        on a red delete button: our tokens are set on both selectors now."""
        sheet = css("css/admin.css")
        self.assertIn(':root,html[data-theme="light"]{', sheet)
        self.assertIn("--delete-button-bg:#fff", sheet)

    def test_admin_chart_tooltips_cannot_widen_the_page(self):
        sheet = css("css/admin.css")
        self.assertIn(".nb-chart{overflow-x:clip}", sheet)
        self.assertIn(".nb-col:nth-last-child(-n+2)::after", sheet)

    def test_admin_report_buttons_readable_outside_the_hero(self):
        self.assertIn(".fz-wrap>.fz-actions a:not(.red){", css("css/admin.css"))

    def test_admin_pages_have_a_favicon_link(self):
        """The admin shell had no <link rel=icon>, so every admin page made the browser ask for /favicon.ico (a 404)."""
        boss = User.objects.create_superuser(username="bossy", email="bossy@x.uz", password="pw12345678")
        c = Client()
        c.force_login(boss)
        s = c.session
        s["admin_mode"] = True
        s.save()
        r = c.get("/django-admin/")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'rel="icon"')
        self.assertContains(r, "img/icon-192.png")


class VoiceScriptTests(TestCase):
    """voice.js cannot run here; the rules that decide where an utterance goes are pinned by their source text."""

    def test_ambiguous_verbs_do_not_turn_questions_into_food(self):
        src = Path(finders.find("js/voice.js")).read_text(encoding="utf-8")
        self.assertIn("var STRONG_EAT", src)
        self.assertIn("if (!STRONG_EAT.test(n + ' ')) return fallback(raw);", src)
        self.assertIn("var QUESTION", src)
        self.assertIn("pg && !NAV_VERB.test(n) && QUESTION.test(n)", src)

    def test_text_box_appears_when_the_microphone_is_blocked(self):
        """With speech recognition present but the mic denied, the message said "or type the question" while the text box stayed hidden."""
        src = Path(finders.find("js/voice.js")).read_text(encoding="utf-8")
        self.assertIn("panel.classList.add('typing')", src)
        self.assertIn(".vpanel.nomic .vp-form,.vpanel.typing .vp-form{display:flex}", css("css/app.css"))
