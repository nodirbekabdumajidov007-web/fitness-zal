from django.core import mail
from django.test import Client, TestCase, override_settings

from .models import User


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class EmailResetTests(TestCase):
    def test_login_link_goes_to_the_email_page(self):
        r = Client().get("/login/")
        self.assertContains(r, 'href="/password/email/"')

    def test_password_account_gets_the_link(self):
        User.objects.create_user(username="pe1", email="Ali@Gmail.com", password="x")
        r = Client().post("/password/email/", {"email": "ali@gmail.com"})
        self.assertRedirects(r, "/password/email/sent/", fetch_redirect_response=False)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["Ali@Gmail.com"])
        self.assertIn("/password/email/", mail.outbox[0].body)

    def test_google_only_account_can_set_a_password(self):
        u = User.objects.create_user(username="pe2", email="g@gmail.com")  # no password: signed up with Google
        self.assertFalse(u.has_usable_password())
        Client().post("/password/email/", {"email": "g@gmail.com"})
        self.assertEqual(len(mail.outbox), 1)

    def test_unknown_address_looks_the_same_and_sends_nothing(self):
        r = Client().post("/password/email/", {"email": "nobody@gmail.com"})
        self.assertRedirects(r, "/password/email/sent/", fetch_redirect_response=False)
        self.assertEqual(len(mail.outbox), 0)

    def test_inactive_account_gets_nothing(self):
        User.objects.create_user(username="pe3", email="off@gmail.com", password="x", is_active=False)
        Client().post("/password/email/", {"email": "off@gmail.com"})
        self.assertEqual(len(mail.outbox), 0)
