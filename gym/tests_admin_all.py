"""Walks the whole custom admin as a superuser in admin mode: every registered model's changelist (plain, searched, sorted),
add form and change form, plus every custom admin view and the redesigned shell (sidebar, top bar, user menu)."""
import datetime
import decimal
from html import unescape

from django.contrib import admin
from django.core.cache import cache
from django.core.management import call_command
from django.db import models as dj
from django.test import Client, TestCase, override_settings
from django.urls import NoReverseMatch, reverse
from django.utils import timezone

from .models import User

CUSTOM_VIEWS = ["admin:index", "admin:reports", "admin:reports_csv", "admin:search", "admin:broadcast", "admin:message",
                "admin:live", "admin:schedule", "admin:cash", "admin:password_change"]


def sample(field, make):
    """A throw-away value for one required field, so any model can get a row without a hand-written factory per model."""
    if field.choices:
        return field.choices[0][0]
    if isinstance(field, dj.ForeignKey | dj.OneToOneField):
        return make(field.related_model)
    if isinstance(field, dj.BooleanField):
        return True
    if isinstance(field, dj.DateTimeField):
        return timezone.now()
    if isinstance(field, dj.DateField):
        return datetime.date.today()
    if isinstance(field, dj.TimeField):
        return datetime.time(10, 0)
    if isinstance(field, dj.DecimalField):
        return decimal.Decimal("1")
    if isinstance(field, dj.IntegerField | dj.FloatField):
        return 1
    if isinstance(field, dj.JSONField):
        return {}
    if isinstance(field, dj.EmailField):
        return "a@b.uz"
    return "x"


@override_settings(GOOGLE_CLIENT_ID="")
class AdminWalk(TestCase):
    def setUp(self):
        cache.clear()
        call_command("setup_gym", demo=True, verbosity=0)
        self.boss = User.objects.filter(is_superuser=True).first()
        self.c = Client()
        self.c.force_login(self.boss)
        s = self.c.session
        s["admin_mode"] = True
        s.save()

    def make(self, model):
        obj = model.objects.first()
        if obj:
            return obj
        kw = {}
        for f in model._meta.concrete_fields:
            if f.primary_key or f.has_default() or f.null or f.blank or isinstance(f, dj.AutoField) or f.auto_created:
                continue
            if getattr(f, "auto_now_add", False) or getattr(f, "auto_now", False):
                continue
            kw[f.name] = sample(f, self.make)
        return model.objects.create(**kw)

    def test_custom_views(self):
        for name in CUSTOM_VIEWS:
            r = self.c.get(reverse(name))
            self.assertEqual(r.status_code, 200, name)
        u = self.make(User)
        self.assertEqual(self.c.get(reverse("admin:member", args=[u.pk])).status_code, 200)
        self.assertEqual(self.c.get(reverse("admin:search") + "?q=zzzz-nothing").status_code, 200)
        self.assertEqual(self.c.get(reverse("admin:schedule") + "?w=2").status_code, 200)
        self.assertEqual(self.c.get(reverse("admin:cash") + "?d=2026-02-30").status_code, 200)
        self.assertEqual(self.c.get(reverse("admin:message") + "?aud=active").status_code, 200)
        self.assertEqual(self.c.get("/django-admin/gym/").status_code, 200)  # the app page

    def test_every_model(self):
        checked = 0
        for model, ma in admin.site._registry.items():
            info = model._meta.app_label, model._meta.model_name
            url = reverse("admin:%s_%s_changelist" % info)
            self.make(model)
            self.assertEqual(self.c.get(url).status_code, 200, url)
            if ma.search_fields:
                self.assertEqual(self.c.get(url + "?q=a").status_code, 200, url + "?q=a")
            self.assertEqual(self.c.get(url + "?o=1").status_code, 200, url + "?o=1")
            for flt in ma.list_filter:  # every filter's own querystring must render too
                name = flt if isinstance(flt, str) else getattr(flt, "parameter_name", None)
                if isinstance(name, str) and "__" not in name and name in {f.name for f in model._meta.fields if isinstance(f, dj.BooleanField)}:
                    self.assertEqual(self.c.get(f"{url}?{name}__exact=1").status_code, 200, url)
            if ma.has_add_permission(self.rf_request()):
                self.assertEqual(self.c.get(reverse("admin:%s_%s_add" % info)).status_code, 200, "add " + url)
            obj = model.objects.first()
            if obj is not None:
                ch = reverse("admin:%s_%s_change" % info, args=[obj.pk])
                self.assertEqual(self.c.get(ch).status_code, 200, ch)
                self.assertEqual(self.c.get(reverse("admin:%s_%s_history" % info, args=[obj.pk])).status_code, 200, ch + " history")
                if ma.has_delete_permission(self.rf_request(), obj):
                    self.assertEqual(self.c.get(reverse("admin:%s_%s_delete" % info, args=[obj.pk])).status_code, 200, ch + " delete")
            checked += 1
        self.assertGreater(checked, 20)

    def rf_request(self):
        from django.test import RequestFactory
        r = RequestFactory().get("/")
        r.user = self.boss
        return r

    def test_shell(self):
        """The new layout: grouped sidebar with real links only, top bar with search, theme toggle, site button and user menu."""
        r = self.c.get(reverse("admin:index"))
        html = unescape(r.content.decode())
        for needle in ('id="fz-side"', 'id="fz-q"', 'class="fz-user"', reverse("admin:password_change"), reverse("admin:logout"),
                       reverse("admin:cash"), reverse("admin:gym_payment_changelist"), "Moliya", "A'zolar", "Do'kon"):
            self.assertIn(needle, html, needle)
        for emoji in ("👤", "🎫", "🛒", "💳", "✉"):
            self.assertNotIn(emoji, html, "emoji left in the admin shell")
        # the active entry is highlighted on a model page
        r = self.c.get(reverse("admin:gym_payment_changelist"))
        self.assertRegex(r.content.decode(), r'class="fz-nav-a on"[^>]*href="%s"|href="%s"[^>]*class="fz-nav-a on"' % (
            reverse("admin:gym_payment_changelist"), reverse("admin:gym_payment_changelist")))

    def test_sidebar_respects_permissions(self):
        staff = User.objects.create_user(username="desk1", password="Xodim-Parol-1", is_staff=True)
        c = Client()
        c.force_login(staff)
        s = c.session
        s["admin_mode"] = True
        s.save()
        r = c.get(reverse("admin:index"))
        self.assertEqual(r.status_code, 200)
        self.assertNotIn(reverse("admin:gym_payment_changelist"), r.content.decode())
        self.assertNotIn(reverse("admin:cash"), r.content.decode().split('id="fz-side"')[1].split("</aside>")[0])

    def test_login_page_renders(self):
        r = Client().get("/django-admin/login/")
        self.assertIn(r.status_code, (200, 302))
        try:
            reverse("admin:login")
        except NoReverseMatch:
            self.fail("admin:login missing")

    def test_summary_pages_need_permission(self):
        """Staff without payment/member rights get the plain index, and 403 on takings and member pages (not the whole business)."""
        staff = User.objects.create_user(username="desk2", password="Xodim-Parol-2", is_staff=True)
        c = Client()
        c.force_login(staff)
        s = c.session
        s["admin_mode"] = True
        s.save()
        for name in ("admin:cash", "admin:reports", "admin:reports_csv", "admin:live", "admin:search", "admin:message", "admin:broadcast", "admin:schedule"):
            self.assertEqual(c.get(reverse(name)).status_code, 403, name)
        r = c.get(reverse("admin:index"))
        self.assertEqual(r.status_code, 200)
        self.assertNotIn("Bugungi tushum", r.content.decode())

    def test_filtered_nav_entry_and_app_page(self):
        r = self.c.get(reverse("admin:gym_user_changelist") + "?is_active__exact=0")
        html = unescape(r.content.decode())
        self.assertRegex(html, r'class="fz-nav-a on"[^>]*href="[^"]*is_active__exact=0"')
        r = self.c.get("/django-admin/gym/")
        self.assertContains(r, "fz-side")
