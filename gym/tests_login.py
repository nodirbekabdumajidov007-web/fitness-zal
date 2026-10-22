"""Sign-in hardening: SMS code after the password/Google step, and the Google-only switch."""
import io
import json
import re
import time
from unittest import mock

from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import Client, TestCase, override_settings
from django.utils.html import escape

from . import sms
from .i18n import T
from .models import GymSettings, User

PW = "Kuchli-Parol-77"
CID = "test-client.apps.googleusercontent.com"


class Base(TestCase):
    def setUp(self):
        cache.clear()
        call_command("setup_gym", demo=True, verbosity=0)
        self.admin = User.objects.get(is_superuser=True)
        self.admin.set_password("AdminPass1")
        self.admin.save()
        self.member = User.objects.create_user(phone="+998901112233", password=PW, first_name="Aziz", last_name="Karimov")
        self.sent = []
        p1 = mock.patch.object(sms, "send_sms", side_effect=lambda phone, text: self.sent.append((phone, text)) or True)
        p2 = mock.patch.object(sms, "real_backend", return_value=True)  # tests run with DEBUG=False, so pretend Eskiz is connected
        p1.start(), p2.start()
        self.addCleanup(p1.stop), self.addCleanup(p2.stop)

    def switch(self, **kw):
        GymSettings.objects.filter(pk=1).update(**kw)

    def last_code(self, phone):
        sent = [t for p, t in self.sent if p == phone]
        return re.search(r"(\d{6})", sent[-1]).group(1)

    def logged_in(self, c):
        return c.get("/dashboard/").status_code == 200

    def google(self, c, email="ali@gmail.com"):
        info = {"aud": CID, "email": email, "email_verified": "true", "given_name": "Ali", "family_name": "Valiyev"}
        with mock.patch("gym.views.urllib.request.urlopen", return_value=io.BytesIO(json.dumps(info).encode())):
            return c.post("/auth/google/", json.dumps({"credential": "x.y.z"}), content_type="application/json")


class SmsLoginTests(Base):
    def test_off_by_default_password_logs_in_directly(self):
        c = Client()
        r = c.post("/login/", {"phone": "901112233", "password": PW})
        self.assertRedirects(r, "/dashboard/", fetch_redirect_response=False)
        self.assertEqual(self.sent, [])

    def test_password_alone_is_not_enough(self):
        self.switch(login_sms_code=True)
        c = Client()
        r = c.post("/login/", {"phone": "901112233", "password": PW})
        self.assertRedirects(r, "/login/code/", fetch_redirect_response=False)
        self.assertFalse(self.logged_in(c))
        self.assertEqual(len(self.sent), 1)
        page = c.get("/login/code/")
        self.assertContains(page, "+998 90 *** ** 33")
        self.assertNotContains(page, "901112233")  # the number is masked on screen

        r = c.post("/login/code/", {"code": "000000" if self.last_code(self.member.phone) != "000000" else "111111"})
        self.assertContains(r, escape(T["uz"]["otp_bad"]))
        self.assertFalse(self.logged_in(c))

        c.post("/login/code/", {"action": "resend"})
        self.assertEqual(len(self.sent), 2)
        r = c.post("/login/code/", {"code": self.last_code(self.member.phone)})
        self.assertRedirects(r, "/dashboard/", fetch_redirect_response=False)
        self.assertTrue(self.logged_in(c))
        self.member.refresh_from_db()
        self.assertTrue(self.member.phone_verified)

    def test_wrong_password_sends_nothing(self):
        self.switch(login_sms_code=True)
        Client().post("/login/", {"phone": "901112233", "password": "wrong-one"})
        self.assertEqual(self.sent, [])

    def test_code_page_without_password_step(self):
        self.switch(login_sms_code=True)
        r = Client().get("/login/code/")
        self.assertRedirects(r, "/login/", fetch_redirect_response=False)

    def test_pending_login_expires(self):
        self.switch(login_sms_code=True)
        c = Client()
        c.post("/login/", {"phone": "901112233", "password": PW})
        code = self.last_code(self.member.phone)
        s = c.session
        s["pending_login"]["ts"] = int(time.time()) - 3600
        s.save()
        r = c.post("/login/code/", {"code": code})
        self.assertRedirects(r, "/login/", fetch_redirect_response=False)
        self.assertFalse(self.logged_in(c))

    def test_admin_also_needs_the_code_then_lands_in_panel(self):
        self.switch(login_sms_code=True)
        c = Client()
        r = c.post("/login/", {"phone": "908775505", "password": "AdminPass1.admin"})
        self.assertRedirects(r, "/login/code/", fetch_redirect_response=False)
        self.assertEqual(c.get("/django-admin/").status_code, 302)
        r = c.post("/login/code/", {"code": self.last_code(self.admin.phone)})
        self.assertRedirects(r, "/django-admin/", fetch_redirect_response=False)
        self.assertTrue(c.session["admin_mode"])
        self.assertEqual(c.get("/django-admin/").status_code, 200)

    def test_next_is_kept_and_checked(self):
        self.switch(login_sms_code=True)
        c = Client()
        c.post("/login/", {"phone": "901112233", "password": PW, "next": "/shop/"})
        r = c.post("/login/code/", {"code": self.last_code(self.member.phone)})
        self.assertRedirects(r, "/shop/", fetch_redirect_response=False)
        c2 = Client()
        c2.post("/login/", {"phone": "901112233", "password": PW, "next": "https://evil.example/"})
        r = c2.post("/login/code/", {"code": self.last_code(self.member.phone)})
        self.assertRedirects(r, "/dashboard/", fetch_redirect_response=False)

    def test_register_confirms_the_new_number(self):
        self.switch(login_sms_code=True)
        c = Client()
        r = c.post("/register/", {"first_name": "Vali", "last_name": "Aliyev", "phone": "935554433", "password": PW})
        self.assertRedirects(r, "/login/code/", fetch_redirect_response=False)
        self.assertFalse(self.logged_in(c))
        c.post("/login/code/", {"code": self.last_code("+998935554433")})
        self.assertTrue(self.logged_in(c))
        self.assertTrue(User.objects.get(phone="+998935554433").phone_verified)

    def test_switch_refused_without_sms_service(self):
        gs = GymSettings.load()
        gs.login_sms_code = True
        with mock.patch.object(sms, "real_backend", return_value=False):
            with self.assertRaises(ValidationError):
                gs.full_clean()
            self.switch(login_sms_code=True)  # even if forced into the DB, nobody gets locked out
            c = Client()
            r = c.post("/login/", {"phone": "901112233", "password": PW})
            self.assertRedirects(r, "/dashboard/", fetch_redirect_response=False)


@override_settings(GOOGLE_CLIENT_ID=CID)
class GoogleOnlyTests(Base):
    def test_members_cannot_use_password(self):
        self.switch(require_google=True)
        c = Client()
        r = c.post("/login/", {"phone": "901112233", "password": PW})
        self.assertContains(r, escape(T["uz"]["google_required"]))
        self.assertFalse(self.logged_in(c))

    def test_owner_keeps_password_door(self):
        self.switch(require_google=True)
        c = Client()
        r = c.post("/login/", {"phone": "908775505", "password": "AdminPass1.admin"})
        self.assertRedirects(r, "/django-admin/", fetch_redirect_response=False)

    def test_register_form_is_closed(self):
        self.switch(require_google=True)
        c = Client()
        page = c.get("/register/")
        self.assertContains(page, escape(T["uz"]["google_only_register"]))
        self.assertNotContains(page, 'name="password"')
        c.post("/register/", {"first_name": "Vali", "last_name": "Aliyev", "phone": "935554433", "password": PW})
        self.assertFalse(User.objects.filter(phone="+998935554433").exists())

    def test_google_then_phone_then_code(self):
        self.switch(require_google=True, login_sms_code=True)
        c = Client()
        r = self.google(c)
        self.assertEqual(r.json()["next"], "/login/phone/")
        self.assertFalse(self.logged_in(c))
        r = c.post("/login/phone/", {"phone": "901112233"})  # someone else's number
        self.assertContains(r, escape(T["uz"]["err_exists"]))
        r = c.post("/login/phone/", {"phone": "97 777 66 55"})
        self.assertRedirects(r, "/login/code/", fetch_redirect_response=False)
        c.post("/login/code/", {"code": self.last_code("+998977776655")})
        self.assertTrue(self.logged_in(c))
        u = User.objects.get(email="ali@gmail.com")
        self.assertEqual(u.phone, "+998977776655")
        self.assertTrue(u.phone_verified)

        c2 = Client()  # next time: Google, then straight to the code
        self.assertEqual(self.google(c2).json()["next"], "/login/code/")

    def test_google_without_sms_logs_in(self):
        self.switch(require_google=True)
        c = Client()
        self.assertEqual(self.google(c).json()["next"], "/dashboard/")
        self.assertTrue(self.logged_in(c))

    def test_switch_needs_client_id(self):
        gs = GymSettings.load()
        gs.require_google = True
        gs.full_clean()  # fine: GOOGLE_CLIENT_ID is set here
        with override_settings(GOOGLE_CLIENT_ID=""):
            with self.assertRaises(ValidationError):
                gs.full_clean()
            self.switch(require_google=True)  # forced into the DB anyway: passwords keep working instead of locking everyone out
            r = Client().post("/login/", {"phone": "901112233", "password": PW})
            self.assertRedirects(r, "/dashboard/", fetch_redirect_response=False)
