"""Every URL of gym/urls.py as guest, member, trainer and staff: no 500, no raw i18n keys in visible text, no missing template variables."""
import re

from django.test import Client

from .i18n import T
from .models import Trainer, User
from .tests_smoke import INVALID, SmokeTests

TAG = re.compile(r"<(script|style)\b.*?</\1>|<!--.*?-->", re.S | re.I)
TEXT = re.compile(r">([^<>]+)<")
ALLOWED_INVALID = {"mine.comment", "mine.rating", "q", "next"}


class FullSmokeTests(SmokeTests):
    """Re-uses the fixtures of SmokeTests; its own tests are switched off here (they already run in tests_smoke)."""
    test_every_site_url = test_admin_shortcuts = test_every_admin_page = None

    def setUp(self):
        super().setUp()
        self.coach = User.objects.create_user(phone="+998909998877", password="secret12", first_name="Coach", last_name="Z")
        tr = Trainer.objects.filter(user__isnull=True).first()
        if tr is not None:
            tr.user = self.coach
            tr.save()
        self.trainer_client = Client()
        self.trainer_client.post("/login/", {"login": "+998909998877", "password": "secret12"})

    def leaks(self, html):
        out = set()
        for m in TEXT.finditer(TAG.sub("", html)):
            s = m.group(1).strip()
            if re.fullmatch(r"[a-z][a-z0-9]*(_[a-z0-9]+)+", s) and s in T["uz"]:
                out.add(s)
        return out

    def check(self, client, url, who):
        r = client.get(url)
        self.assertLess(r.status_code, 500, f"{who} {url}")
        if r.status_code == 200 and "text/html" in r.get("Content-Type", ""):
            html = r.content.decode()
            self.assertEqual(set(re.findall(r"@@INVALID\[(.*?)\]@@", html)) - ALLOWED_INVALID, set(), f"{who} {url}: missing variables")
            self.assertEqual(self.leaks(html), set(), f"{who} {url}: raw i18n keys")

    def test_every_site_url_all_roles(self):
        from django.urls import reverse
        from .urls import urlpatterns
        clients = {"guest": Client(), "member": self.member, "trainer": self.trainer_client, "staff": self.staff}
        for p in urlpatterns:
            url = reverse(p.name, kwargs=self.args_for(p.name, p.pattern.converters) or None) if p.name else "/" + str(p.pattern)
            for who, client in clients.items():
                self.check(client, url, who)
        for lang in ("uz", "ru", "en"):
            for client in clients.values():
                client.get(f"/lang/{lang}/")
                for url in ("/", "/plans/", "/shop/", "/classes/", "/trainers/", "/tools/", "/ai/", "/reviews/", "/login/", "/register/",
                            "/workouts/", "/calories/", "/dashboard/"):
                    self.check(client, url, f"{lang}")

    def test_new_endpoints_guard(self):
        guest = Client()
        for url in ("/calories/add/", "/calories/parse/", "/workouts/program/beginner/"):
            r = guest.post(url)
            self.assertEqual(r.status_code, 302, url)
            self.assertIn("/login/", r["Location"])
        self.assertEqual(self.member.post("/workouts/program/nope/").status_code, 302)
        r = self.member.post("/calories/add/", {"food": "0", "grams": "0"}, HTTP_X_REQUESTED_WITH="fetch")
        self.assertEqual(r.status_code, 400)
        self.assertFalse(r.json()["ok"])
        r = self.member.post("/calories/add/", {"food": "0", "grams": "100"}, HTTP_X_REQUESTED_WITH="fetch")
        self.assertTrue(r.json()["ok"])
        self.assertEqual(guest.get("/assistant/ask/").status_code, 405)
        self.assertEqual(guest.post("/assistant/ask/", {"q": "x" * 50000}).status_code, 200)
        self.assertEqual(guest.post("/assistant/ask/", {"q": "  "}).status_code, 400)
        data = guest.get("/voice/info/").content.decode()
        self.assertNotIn("+998901112233", data)
        csrf = Client(enforce_csrf_checks=True)
        self.assertEqual(csrf.post("/assistant/ask/", {"q": "salom"}).status_code, 403)
