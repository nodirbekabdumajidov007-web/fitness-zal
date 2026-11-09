"""Mobile regression guard: every key template keeps a proper viewport meta tag and the mobile CSS blocks stay in the stylesheets.

Why: a missing `width=device-width` makes phones render the desktop layout zoomed out, and the "Mobile pass 2" blocks restore
44px tap targets / 14px text / dvh dialogs that the earlier "compact sizing" pass had shrunk - deleting them silently breaks phones."""
import re
from pathlib import Path

from django.core.cache import cache
from django.core.management import call_command
from django.test import Client, TestCase, override_settings

from .models import User

STATIC = Path(__file__).resolve().parent / "static" / "css"
VIEWPORT = re.compile(r'<meta\s+name="viewport"\s+content="[^"]*width=device-width[^"]*initial-scale=1(?:\.0)?[^"]*"', re.I)

PUBLIC = ["/", "/plans/", "/shop/", "/classes/", "/trainers/", "/tools/", "/ai/", "/reviews/", "/faq/", "/oferta/", "/privacy/",
          "/refund/", "/login/", "/register/", "/password/email/"]
MEMBER = ["/dashboard/", "/account/", "/profile/", "/card/", "/membership/", "/calories/", "/workouts/", "/achievements/",
          "/payments/", "/orders/", "/cart/", "/chat/", "/inbox/", "/gift/"]
STAFF = ["/staff/", "/staff/scan/", "/staff/classes/", "/django-admin/", "/django-admin/reports/", "/django-admin/gym/user/",
         "/django-admin/gym/payment/", "/django-admin/gym/product/", "/django-admin/gym/user/1/change/"]


@override_settings(GOOGLE_CLIENT_ID="")
class MobileTemplates(TestCase):
    def setUp(self):
        cache.clear()
        call_command("setup_gym", demo=True, verbosity=0)
        self.boss = User.objects.filter(is_superuser=True).first()
        self.member = User.objects.create_user(phone="+998901234567", username="mobile_t", password="secret12", first_name="Mob", last_name="Ile")

    def _check(self, client, urls):
        for url in urls:
            r = client.get(url, follow=True)
            self.assertEqual(r.status_code, 200, url)
            html = r.content.decode()
            self.assertRegex(html, VIEWPORT, f"{url}: viewport meta (width=device-width, initial-scale=1) is missing")

    def test_public_pages_have_viewport(self):
        self._check(Client(), PUBLIC)

    def test_member_pages_have_viewport(self):
        c = Client()
        c.force_login(self.member)
        self._check(c, MEMBER)

    def test_staff_and_admin_pages_have_viewport(self):
        c = Client()
        c.force_login(self.boss)
        s = c.session
        s["admin_mode"] = True
        s.save()
        self._check(c, STAFF)

    def test_site_uses_safe_area_viewport(self):
        """The public shell covers the notch (viewport-fit=cover) and the fixed bars add env(safe-area-inset-*)."""
        html = Client().get("/").content.decode()
        self.assertIn("viewport-fit=cover", html)
        css = (STATIC / "app.css").read_text(encoding="utf-8")
        self.assertIn("env(safe-area-inset-bottom", css)

    def test_mobile_css_block_exists(self):
        app = (STATIC / "app.css").read_text(encoding="utf-8")
        admin = (STATIC / "admin.css").read_text(encoding="utf-8")
        self.assertIn("/* === Mobile pass 2 ===", app)
        self.assertIn("/* === Mobile pass 2 (admin) ===", admin)
        # the guarantees the block exists for
        block = app[app.index("/* === Mobile pass 2 ==="):]
        self.assertIn("min-height:44px", block)
        self.assertIn("100dvh", block)
        self.assertIn("max(14px", block)
        ablock = admin[admin.index("/* === Mobile pass 2 (admin) ==="):]
        self.assertIn("font-size:16px", ablock)
        self.assertIn("min-height:44px", ablock)

    def test_form_controls_are_16px_on_phones(self):
        """iOS Safari zooms the page when a focused input is smaller than 16px."""
        app = (STATIC / "app.css").read_text(encoding="utf-8")
        self.assertRegex(app, r"input,select,textarea\{font-size:16px!important")
