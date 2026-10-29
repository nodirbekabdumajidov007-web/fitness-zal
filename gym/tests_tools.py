from datetime import date
from decimal import Decimal

from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

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

    def test_i18n_keys_resolve(self):
        html = self.client.get("/tools/").content.decode()
        self.assertEqual(raw_keys(html), set())
        self.assertEqual(invalid_vars(html), set())
        self.assertIn("Tana yog&#x27;i", html)
