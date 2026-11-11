"""Sign in by e-mailed code, the optional e-mail 2-step check, and Google ID-token verification."""
import base64
import hashlib
import json
import re
import time
from unittest import mock

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from django.core import mail
from django.core.cache import cache
from django.core.management import call_command
from django.test import Client, TestCase

from . import emailcode, google_auth
from .models import GymSettings, User

PW = "Kuchli-Parol-77"
CID = "test-client.apps.googleusercontent.com"


def code_from_outbox(i=-1):
    return re.search(r"\b(\d{6})\b", mail.outbox[i].body).group(1)


class EmailLoginBase(TestCase):
    def setUp(self):
        cache.clear()
        call_command("setup_gym", demo=True, verbosity=0)
        self.user = User.objects.create_user("aziz", PW, email="aziz@example.com", first_name="Aziz")
        self.staff = User.objects.create_user("coach1", PW, email="staff@example.com", is_staff=True)
        self.owner = User.objects.get(is_superuser=True)
        self.owner.email = "owner@example.com"
        self.owner.set_password("AdminPass1")
        self.owner.save()

    def ask(self, c, login="aziz@example.com", **extra):
        return c.post("/login/email/", {"login": login, **extra})

    def enter(self, c, code):
        return c.post("/login/email/code/", {"code": code})

    def in_(self, c):
        return c.get("/dashboard/").status_code == 200


class CodeLoginTests(EmailLoginBase):
    def test_same_answer_for_known_and_unknown(self):
        a, b = self.ask(Client()), self.ask(Client(), "nobody@example.com")
        self.assertEqual((a.status_code, a.url), (b.status_code, b.url))
        self.assertEqual(len(mail.outbox), 1)  # only the real account got a message
        pa, pb = Client(), Client()
        self.ask(pa, "aziz2@example.com")
        self.ask(pb, "nobody@example.com")
        self.assertEqual(pa.get("/login/email/code/").content.decode().count("ec_"), pb.get("/login/email/code/").content.decode().count("ec_"))

    def test_mail_has_code_and_html(self):
        self.ask(Client())
        m = mail.outbox[0]
        self.assertEqual(m.to, ["aziz@example.com"])
        code = code_from_outbox()
        self.assertIn(code, m.subject)
        self.assertEqual(m.alternatives[0][1], "text/html")
        self.assertIn(code, m.alternatives[0][0])
        self.assertIn("Fitnes Zal", m.body)

    def test_login_by_username_uses_account_email(self):
        self.ask(Client(), "aziz")
        self.assertEqual(mail.outbox[0].to, ["aziz@example.com"])

    def test_good_code_logs_in_and_is_single_use(self):
        c = Client()
        self.ask(c)
        code = code_from_outbox()
        r = self.enter(c, code)
        self.assertRedirects(r, "/dashboard/", fetch_redirect_response=False)
        self.assertTrue(self.in_(c))
        c2 = Client()
        self.ask(c2)  # cooldown: no new mail, the burnt code must not work
        self.assertFalse(emailcode.check(self.user, "login", code))

    def test_wrong_code_attempt_limit_burns_code(self):
        c = Client()
        self.ask(c)
        good = code_from_outbox()
        bad = "000000" if good != "000000" else "111111"
        for _ in range(4):
            self.assertContains(self.enter(c, bad), "field-err")
        r = self.enter(c, bad)  # 5th miss
        self.assertRedirects(r, "/login/", fetch_redirect_response=False)
        c2 = Client()
        self.ask(c2)
        self.assertFalse(self.in_(c))
        self.assertFalse(emailcode.check(self.user, "login", good))

    def test_expiry(self):
        c = Client()
        self.ask(c)
        code = code_from_outbox()
        cache.delete(f"ec:login:{self.user.pk}")  # what the 10-minute cache TTL does
        r = self.enter(c, code)
        self.assertEqual(r.status_code, 200)
        self.assertFalse(self.in_(c))
        self.assertEqual(emailcode.TTL, 600)

    def test_resend_cooldown(self):
        c = Client()
        self.ask(c)
        r = c.post("/login/email/code/", {"action": "resend"})
        self.assertEqual(r.status_code, 200)  # still cooling down: an error, no second mail
        self.assertEqual(len(mail.outbox), 1)
        s = c.session["pending_email"]
        s["sent"] -= 61
        sess = c.session
        sess["pending_email"] = s
        sess.save()
        cache.delete(f"ec:cool:{self.user.pk}")
        r = c.post("/login/email/code/", {"action": "resend"})
        self.assertRedirects(r, "/login/email/code/", fetch_redirect_response=False)
        self.assertEqual(len(mail.outbox), 2)

    def test_per_account_cooldown_and_hourly_cap(self):
        for _ in range(3):
            self.ask(Client())
        self.assertEqual(len(mail.outbox), 1)  # 60 s cooldown per account, even from other browsers
        for _ in range(10):
            cache.delete(f"ec:cool:{self.user.pk}")
            self.ask(Client())
        self.assertEqual(len(mail.outbox), emailcode.PER_ACCOUNT_HOUR)

    def test_per_ip_rate_limit(self):
        c = Client()
        for i in range(8):
            self.ask(c, f"x{i}@example.com")
        r = self.ask(c, "x9@example.com")
        self.assertContains(r, "field-err")
        self.assertEqual(r.status_code, 200)

    def test_code_check_ip_rate_limit(self):
        c = Client()
        self.ask(c)
        for _ in range(4):
            self.enter(c, "000000")
        # new sessions from the same IP keep counting against the same limiter
        for _ in range(4):
            c2 = Client()
            self.ask(c2, "nobody@example.com")
            self.enter(c2, "000000")
        c3 = Client()
        self.ask(c3, "nobody@example.com")
        r = self.enter(c3, "000000")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "field-err")

    def test_next_redirect_and_open_redirect_blocked(self):
        c = Client()
        self.ask(c, next="/plans/")
        self.assertRedirects(self.enter(c, code_from_outbox()), "/plans/", fetch_redirect_response=False)
        cache.clear()
        c = Client()
        self.ask(c, next="https://evil.example/")
        self.assertRedirects(self.enter(c, code_from_outbox()), "/dashboard/", fetch_redirect_response=False)

    def test_staff_never_gets_admin_mode(self):
        for who, email in ((self.staff, "staff@example.com"), (self.owner, "owner@example.com")):
            cache.clear()
            c = Client()
            self.ask(c, email)
            r = self.enter(c, code_from_outbox())
            self.assertRedirects(r, "/dashboard/", fetch_redirect_response=False)
            self.assertFalse(c.session.get("admin_mode"))
            self.assertEqual(c.get("/django-admin/").status_code, 302)  # not in admin mode: sent to the admin login, not the panel

    def test_blocked_and_no_email_accounts_get_nothing(self):
        User.objects.filter(pk=self.user.pk).update(is_active=False)
        self.ask(Client())
        u = User.objects.create_user("noemail", PW, phone="+998901234567")
        self.ask(Client(), "noemail")
        self.assertEqual(len(mail.outbox), 0)

    def test_login_page_has_link(self):
        self.assertContains(Client().get("/login/"), "/login/email/")


class TwoStepTests(EmailLoginBase):
    def setUp(self):
        super().setUp()
        User.objects.filter(pk__in=[self.user.pk, self.staff.pk]).update(email_2fa=True)

    def test_password_alone_is_not_enough(self):
        c = Client()
        r = c.post("/login/", {"login": "aziz", "password": PW})
        self.assertRedirects(r, "/login/email/code/", fetch_redirect_response=False)
        self.assertFalse(self.in_(c))
        self.assertEqual(len(mail.outbox), 1)
        self.assertRedirects(self.enter(c, code_from_outbox()), "/dashboard/", fetch_redirect_response=False)
        self.assertTrue(self.in_(c))

    def test_wrong_password_sends_nothing(self):
        Client().post("/login/", {"login": "aziz", "password": "nope-nope"})
        self.assertEqual(len(mail.outbox), 0)

    def test_wrong_code_keeps_out(self):
        c = Client()
        c.post("/login/", {"login": "aziz", "password": PW})
        good = code_from_outbox()
        self.enter(c, "000000" if good != "000000" else "111111")
        self.assertFalse(self.in_(c))

    def test_staff_admin_mode_kept_after_password_and_code(self):
        c = Client()
        r = c.post("/login/", {"login": "coach1", "password": PW + ".admin"})
        self.assertRedirects(r, "/login/email/code/", fetch_redirect_response=False)
        r = self.enter(c, code_from_outbox())
        self.assertRedirects(r, "/django-admin/", fetch_redirect_response=False)
        self.assertTrue(c.session["admin_mode"])

    def test_code_login_still_requires_nothing_extra(self):
        c = Client()
        self.ask(c)
        self.assertRedirects(self.enter(c, code_from_outbox()), "/dashboard/", fetch_redirect_response=False)  # the code is the proof, no 2nd code

    def test_google_still_needs_code(self):
        GymSettings.objects.filter(pk=1).update(google_client_id=CID)
        info = {"aud": CID, "email": "aziz@example.com", "email_verified": "true"}
        c = Client()
        with mock.patch("gym.views.google_auth.verify", return_value=info):
            r = c.post("/auth/google/", json.dumps({"credential": "x.y.z"}), content_type="application/json")
        self.assertEqual(r.json()["next"], "/login/email/code/")
        self.assertFalse(self.in_(c))
        self.enter(c, code_from_outbox())
        self.assertTrue(self.in_(c))

    def test_setting_in_account_page(self):
        User.objects.filter(pk=self.user.pk).update(email_2fa=False)
        c = Client()
        c.force_login(self.user)
        page = c.get("/account/")
        self.assertContains(page, "email_2fa")
        data = {"username": "aziz", "email": "aziz@example.com", "first_name": "Aziz", "last_name": "", "phone": "", "email_2fa": "1"}
        c.post("/account/", data)
        self.user.refresh_from_db()
        self.assertTrue(self.user.email_2fa)
        data.pop("email_2fa")
        c.post("/account/", data)
        self.user.refresh_from_db()
        self.assertFalse(self.user.email_2fa)

    def test_staff_sees_recommendation(self):
        User.objects.filter(pk=self.staff.pk).update(email_2fa=False)
        c = Client()
        c.force_login(self.staff)
        self.assertContains(c.get("/account/"), "Xodimlar uchun tavsiya")


def _b64(b):
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


class GoogleTokenTests(TestCase):
    """The ID token is verified locally: a real RS256 signature against a (test) JWKS."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        nums = cls.key.public_key().public_numbers()
        cls.jwks = [{"kty": "RSA", "kid": "k1", "alg": "RS256", "n": _b64(nums.n.to_bytes(256, "big")), "e": _b64(nums.e.to_bytes(3, "big"))}]

    def token(self, **over):
        claims = {"iss": "https://accounts.google.com", "aud": CID, "exp": time.time() + 600, "email": "a@gmail.com", "email_verified": True, **over}
        head, body = _b64(json.dumps({"alg": "RS256", "kid": "k1"}).encode()), _b64(json.dumps(claims).encode())
        sig = self.key.sign(f"{head}.{body}".encode(), padding.PKCS1v15(), hashes.SHA256())
        return f"{head}.{body}.{_b64(sig)}"

    def test_valid_token(self):
        self.assertEqual(google_auth.verify(self.token(), CID, keys=self.jwks)["email"], "a@gmail.com")
        self.assertTrue(google_auth.verify(self.token(iss="accounts.google.com"), CID, keys=self.jwks))

    def test_rejections(self):
        v = lambda t: google_auth.verify(t, CID, keys=self.jwks)
        self.assertIsNone(v(self.token(aud="other.apps.googleusercontent.com")))
        self.assertIsNone(v(self.token(exp=time.time() - 5)))
        self.assertIsNone(v(self.token(email_verified=False)))
        self.assertIsNone(v(self.token(iss="https://evil.example")))
        h, b, s = self.token().split(".")
        forged = _b64(json.dumps({"iss": "https://accounts.google.com", "aud": CID, "exp": time.time() + 600, "email": "victim@gmail.com",
                                  "email_verified": True}).encode())
        self.assertIsNone(v(f"{h}.{forged}.{s}"))  # body changed, signature no longer matches
        self.assertIsNone(v("garbage"))

    def test_endpoint_uses_verifier(self):
        call_command("setup_gym", demo=True, verbosity=0)
        GymSettings.objects.filter(pk=1).update(google_client_id=CID)
        c = Client()
        with mock.patch("gym.google_auth._keys", return_value=self.jwks):
            r = c.post("/auth/google/", json.dumps({"credential": self.token(email="new@gmail.com")}), content_type="application/json")
            self.assertEqual(r.json()["next"], "/dashboard/")
            bad = Client().post("/auth/google/", json.dumps({"credential": "a.b.c"}), content_type="application/json")
        self.assertEqual(bad.status_code, 401)
        self.assertTrue(User.objects.filter(email="new@gmail.com").exists())

    def test_button_hidden_without_client_id(self):
        call_command("setup_gym", demo=True, verbosity=0)
        with self.settings(GOOGLE_CLIENT_ID=""):
            GymSettings.objects.filter(pk=1).update(google_client_id="")
            page = Client().get("/login/").content.decode()
            self.assertNotIn('id="gbtn"', page)
            GymSettings.objects.filter(pk=1).update(google_client_id=CID)
            self.assertIn('id="gbtn"', Client().get("/login/").content.decode())
