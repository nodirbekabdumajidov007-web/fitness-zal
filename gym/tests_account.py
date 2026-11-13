"""Account settings page (/account/): every field and control on it, including the cases the 2026-11-13 check found
(users without an e-mail could not save anything) and the ones that must stay locked (account type, other people's data)."""
import io
import shutil
import tempfile

from django.test import Client, TestCase, override_settings
from PIL import Image

from .models import User

MEDIA = tempfile.mkdtemp()


def png_bytes():
    buf = io.BytesIO()
    Image.new("RGB", (64, 64), (200, 40, 30)).save(buf, "PNG")
    buf.seek(0)
    buf.name = "a.png"
    return buf


@override_settings(MEDIA_ROOT=MEDIA)
class AccountSettingsTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA, ignore_errors=True)

    def setUp(self):
        self.u = User.objects.create_user(username="ali_v", password="eski-parol-1", first_name="Ali", last_name="V")
        self.u.email = None
        self.u.save()
        self.c = Client()
        self.c.force_login(self.u)

    def post(self, **over):
        data = {"username": "ali_v", "email": "", "first_name": "Ali", "last_name": "V", "phone": ""}
        data.update(over)
        return self.c.post("/account/", data)

    def test_user_without_email_can_save_name(self):
        r = self.post(first_name="Alisher")
        self.assertRedirects(r, "/account/")
        self.u.refresh_from_db()
        self.assertEqual(self.u.first_name, "Alisher")
        self.assertIsNone(self.u.email)  # stored as NULL, not "": the column is unique

    def test_two_users_without_email_do_not_clash(self):
        other = User.objects.create_user(username="vali_b", password="x-parol-12")
        other.email = None
        other.save()
        self.assertRedirects(self.post(last_name="Valiyev"), "/account/")

    def test_email_is_validated_and_unique_when_given(self):
        User.objects.create_user(username="band", password="x-parol-12", email="band@x.uz")
        self.assertContains(self.post(email="yaroqsiz"), "field-err")
        self.assertContains(self.post(email="BAND@x.uz"), "field-err")
        self.assertRedirects(self.post(email="Ali@X.uz"), "/account/")
        self.u.refresh_from_db()
        self.assertEqual(self.u.email, "ali@x.uz")

    def test_username_rules(self):
        User.objects.create_user(username="olingan", password="x-parol-12")
        self.assertContains(self.post(username="ab"), "field-err")
        self.assertContains(self.post(username="bo'sh joy"), "field-err")
        self.assertContains(self.post(username="OLINGAN"), "field-err")
        self.assertRedirects(self.post(username="ali.valiyev"), "/account/")

    def test_phone_change_needs_verification_again(self):
        self.u.phone, self.u.phone_verified = "+998901112233", True
        self.u.save()
        self.assertRedirects(self.post(phone="90 444 55 66"), "/account/")
        self.u.refresh_from_db()
        self.assertEqual(self.u.phone, "+998904445566")
        self.assertFalse(self.u.phone_verified)

    def test_password_change(self):
        self.assertContains(self.post(current_password="notogri", new_password="yangi-parol-2"), "field-err")
        self.assertContains(self.post(current_password="eski-parol-1", new_password="123"), "field-err")
        self.assertRedirects(self.post(current_password="eski-parol-1", new_password="yangi-parol-2"), "/account/")
        self.u.refresh_from_db()
        self.assertTrue(self.u.check_password("yangi-parol-2"))
        self.assertEqual(self.c.get("/account/").status_code, 200)  # still signed in

    def test_empty_password_fields_keep_the_password(self):
        self.assertRedirects(self.post(first_name="Ali"), "/account/")
        self.u.refresh_from_db()
        self.assertTrue(self.u.check_password("eski-parol-1"))

    def test_avatar_upload_clear_and_reject(self):
        self.assertRedirects(self.post(avatar=png_bytes()), "/account/")
        self.u.refresh_from_db()
        self.assertTrue(self.u.avatar)
        bad = io.BytesIO(b"bu rasm emas")
        bad.name = "x.png"
        self.assertContains(self.post(avatar=bad), "field-err")
        self.assertRedirects(self.post(avatar_clear="1"), "/account/")
        self.u.refresh_from_db()
        self.assertFalse(self.u.avatar)

    def test_account_type_cannot_be_raised(self):
        self.post(is_superuser="on", is_staff="on", role="admin", first_name="Ali")
        self.u.refresh_from_db()
        self.assertFalse(self.u.is_superuser)
        self.assertFalse(self.u.is_staff)
