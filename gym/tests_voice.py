import json

from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from .models import GymSettings, Plan, User


class VoiceTests(TestCase):
    def setUp(self):
        cache.clear()
        gs = GymSettings.load()
        gs.address = "Toshkent, Test ko'chasi 1"
        gs.save()
        gs.refresh_from_db()
        Plan.objects.create(code="vtest", name="Maxsus", months=2, price=250000)
        self.u = User.objects.create_user(username="ovoz", email="ovoz@x.uz", password="pw12345678", first_name="Ovoz", phone="+998901112233")

    def _cfg(self, html):
        start = html.index('id="voice-i18n"')
        body = html[html.index(">", start) + 1:html.index("</script>", start)]
        return json.loads(body)

    def test_info_content_and_no_private_data(self):
        self.client.force_login(self.u)
        r = self.client.get(reverse("voice_info"))
        self.assertEqual(r.status_code, 200)
        d = r.json()
        for k in ("open", "close", "phone", "address", "instagram", "telegram", "crowd", "plans", "is_open"):
            self.assertIn(k, d)
        self.assertEqual(d["address"], "Toshkent, Test ko'chasi 1")
        self.assertTrue(any(p["code"] == "vtest" and p["price"] == 250000 for p in d["plans"]))
        raw = r.content.decode()
        for private in ("ovoz@x.uz", "901112233", "ovoz", "pw12345678"):
            self.assertNotIn(private, raw)

    def test_info_is_public(self):
        self.assertEqual(self.client.get(reverse("voice_info")).status_code, 200)

    def test_template_has_button_and_json_config(self):
        r = self.client.get(reverse("home"))
        self.assertContains(r, 'id="vmic"')
        self.assertContains(r, "js/voice.js")
        cfg = self._cfg(r.content.decode())
        self.assertEqual(cfg["speechLang"], "uz-UZ")
        self.assertFalse(cfg["auth"])
        self.assertEqual(cfg["urls"]["info"], reverse("voice_info"))
        self.assertIn("vc-title", cfg["t"])
        self.assertEqual(cfg["pages"]["shop"]["url"], reverse("shop"))

    def test_language_follows_site(self):
        self.client.cookies["fz_lang"] = "ru"
        cfg = self._cfg(self.client.get(reverse("home")).content.decode())
        self.assertEqual(cfg["speechLang"], "ru-RU")
        self.assertEqual(cfg["t"]["vc-close"], "Закрыть")
        self.client.cookies["fz_lang"] = "en"
        self.assertEqual(self._cfg(self.client.get(reverse("home")).content.decode())["speechLang"], "en-US")

    def test_no_ai_in_config(self):
        cfg = self._cfg(self.client.get(reverse("home")).content.decode())
        self.assertNotIn("ai", cfg)
        self.assertNotIn("ask", cfg["urls"])
        self.assertNotIn("calAi", cfg["urls"])
        self.assertEqual(cfg["urls"]["assistant"], "/assistant/ask/")

    def test_auth_flag(self):
        self.client.force_login(self.u)
        self.assertTrue(self._cfg(self.client.get(reverse("home")).content.decode())["auth"])

    def test_permissions_policy_allows_microphone(self):
        r = self.client.get(reverse("home"))
        self.assertIn("microphone=(self)", r["Permissions-Policy"])

    def test_csp_has_no_inline_script_for_voice(self):
        r = self.client.get(reverse("home"))
        self.assertNotIn("unsafe-inline' https", r["Content-Security-Policy"].split("script-src")[1].split(";")[0])

    def test_all_voice_keys_translated(self):
        from .i18n import T
        from .voice import UI_KEYS
        for lang in ("uz", "ru", "en"):
            for k in UI_KEYS:
                self.assertIn(k, T[lang], (lang, k))
