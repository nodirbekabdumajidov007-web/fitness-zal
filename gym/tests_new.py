"""Username sign-up and sign-in, e-mail (SMTP) messages and password reset, the AI coach and AI plans (API mocked),
Cloudinary switches and the removal of VIP."""
from unittest import mock

from django.core import mail
from django.core.cache import cache
from django.core.management import call_command
from django.test import Client, TestCase, override_settings

from . import services
from .models import AIMessage, Lesson, Plan, User, WorkoutPlan

PW = "Kuchli-Parol-77"


@override_settings(GOOGLE_CLIENT_ID="", EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class Base(TestCase):
    def setUp(self):
        cache.clear()
        call_command("setup_gym", demo=True, verbosity=0)
        self.admin = User.objects.get(is_superuser=True)
        self.admin.set_password("AdminPass1")
        self.admin.save()

    def register(self, client=None, **over):
        data = {"username": "aziz_k", "email": "aziz@example.com", "password": PW, "password2": PW}
        data.update(over)
        return (client or Client()).post("/register/", data)


class RegistrationTests(Base):
    def test_username_email_password_is_enough(self):
        r = self.register()
        self.assertEqual(r.status_code, 302)
        u = User.objects.get(username="aziz_k")
        self.assertEqual((u.email, u.phone, u.full_name), ("aziz@example.com", None, "aziz_k"))
        self.assertTrue(u.check_password(PW))
        self.assertEqual(len(mail.outbox), 1)  # welcome e-mail
        self.assertIn("aziz_k", mail.outbox[0].body)

    def test_validation(self):
        self.register()
        cases = [
            ({"username": "AZIZ_K"}, "err_username_taken"),          # case-insensitive
            ({"username": "a b"}, "err_username"),
            ({"username": "new1", "email": "AZIZ@example.com"}, "err_email_taken"),
            ({"username": "new2", "email": "x@y.uz", "password2": "other"}, "err_pass_match"),
            ({"username": "new3", "email": "z@y.uz", "phone": "123"}, "err_phone"),
            ({"username": "new4", "email": "not-an-email"}, "err_email"),
        ]
        from .i18n import T
        for over, key in cases:
            r = self.register(**over)
            self.assertEqual(r.status_code, 200, over)
            self.assertContains(r, T["uz"][key].replace("'", "&#x27;"), msg_prefix=str(over))
        self.assertEqual(User.objects.filter(is_superuser=False).count(), 1)

    def test_optional_phone_and_name(self):
        self.register(username="vali", email="vali@x.uz", phone="93 555 44 33", first_name="Vali")
        u = User.objects.get(username="vali")
        self.assertEqual((u.phone, u.first_name), ("+998935554433", "Vali"))

    def test_sign_in_with_username_email_or_phone(self):
        self.register(phone="93 555 44 33")
        for login in ("aziz_k", "AZIZ_K", "aziz@example.com", "93 555 44 33", "+998935554433"):
            c = Client()
            r = c.post("/login/", {"login": login, "password": PW})
            self.assertEqual(r.status_code, 302, login)
            self.assertIn("_auth_user_id", c.session, login)
        self.assertContains(Client().post("/login/", {"login": "aziz_k", "password": "wrong"}), "field-err")

    def test_owner_signs_in_as_admin1(self):
        r = Client().post("/login/", {"login": "admin1", "password": "AdminPass1.admin"})
        self.assertEqual(r["Location"], "/django-admin/")
        self.assertEqual(self.admin.username, "admin1")

    def test_owner_cannot_sign_in_by_phone(self):
        for login in ("90 877 55 05", "+998908775505", "908775505"):
            r = Client().post("/login/", {"login": login, "password": "AdminPass1.admin"})
            self.assertEqual(r.status_code, 200, login)
            self.assertContains(r, "field-err")
        c = Client()
        c.post("/login/", {"login": "ADMIN1", "password": "AdminPass1"})  # case-insensitive, normal (non-admin) mode
        self.assertIn("_auth_user_id", c.session)

    def test_migration_renames_admin_to_admin1(self):
        import importlib
        from django.apps import apps as real_apps
        mig = importlib.import_module("gym.migrations.0023_rename_admin_to_admin1")
        User.objects.filter(pk=self.admin.pk).update(username="admin")
        mig.rename(real_apps, None)
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.username, "admin1")
        User.objects.filter(pk=self.admin.pk).update(username="admin")
        other = User.objects.create_user("admin1", PW, email="x1@example.com")
        mig.rename(real_apps, None)  # admin1 is taken: nothing changes
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.username, "admin")
        other.delete()


class EmailTests(Base):
    def test_password_reset_by_email(self):
        self.register()
        c = Client()
        r = c.post("/password/email/", {"email": "aziz@example.com"})
        self.assertRedirects(r, "/password/email/sent/")
        self.assertEqual(len(mail.outbox), 2)  # welcome + reset
        link = next(line for line in mail.outbox[1].body.splitlines() if "/password/email/" in line).strip()
        path = link.split("testserver")[-1]
        r = c.get(path, follow=True)
        r = c.post(r.redirect_chain[-1][0], {"new_password1": "Yangi-Parol-2026", "new_password2": "Yangi-Parol-2026"})
        self.assertRedirects(r, "/password/email/done/")
        self.assertTrue(User.objects.get(username="aziz_k").check_password("Yangi-Parol-2026"))

    def test_unknown_email_gives_same_answer(self):
        r = Client().post("/password/email/", {"email": "nobody@example.com"})
        self.assertRedirects(r, "/password/email/sent/")
        self.assertEqual(len(mail.outbox), 0)

    def test_admin_message_by_email(self):
        self.register()
        u = User.objects.get(username="aziz_k")
        staff = Client()
        staff.post("/login/", {"login": "admin1", "password": "AdminPass1.admin"})
        staff.post("/django-admin/message/", {"ids": [u.pk], "title": "Salom, {ism}!", "body": "Ertaga zal 10:00 da", "email": "on"})
        self.assertEqual(mail.outbox[-1].to, ["aziz@example.com"])
        self.assertIn("Salom, aziz_k!", mail.outbox[-1].subject)


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class AITests(Base):
    """The coach page runs on the offline assistant: no API key, no network."""
    def setUp(self):
        super().setUp()
        self.register()
        self.u = User.objects.get(username="aziz_k")
        self.c = Client()
        self.c.post("/login/", {"login": "aziz_k", "password": PW})

    def test_page_for_guests_and_members(self):
        self.assertContains(Client().get("/ai/"), 'data-ai-form')
        self.assertContains(Client().get("/ai/"), "/login/?next=/ai/")
        r = self.c.get("/ai/")
        self.assertContains(r, 'name="equipment"')
        self.assertNotContains(r, "ANTHROPIC")

    def test_chat_answers_locally_and_is_stored(self):
        r = self.c.post("/ai/ask/", {"q": "Kuniga qancha oqsil kerak?"}, HTTP_X_REQUESTED_WITH="fetch")
        d = r.json()
        self.assertTrue(d["ok"] and d["matched"])
        self.assertIn("1,6-2,2", d["answer"])
        self.assertEqual(list(AIMessage.objects.values_list("role", flat=True)), ["user", "assistant"])
        self.assertEqual(self.c.post("/ai/ask/", {"q": "  "}, HTTP_X_REQUESTED_WITH="fetch").status_code, 400)

    def test_guest_can_ask_but_nothing_is_stored(self):
        r = Client().post("/ai/ask/", {"q": "squat qanday qilinadi"}, HTTP_X_REQUESTED_WITH="fetch")
        self.assertTrue(r.json()["matched"])
        self.assertEqual(AIMessage.objects.count(), 0)

    def test_plan_is_saved_as_current_plan(self):
        r = self.c.post("/ai/plan/", {"goal": "muscle", "level": "beginner", "days": "3", "equipment": "gym"})
        self.assertEqual(r["Location"], "/workouts/")
        p = WorkoutPlan.objects.get(user=self.u, active=True)
        self.assertTrue(p.title.startswith("✦"))
        self.assertEqual(sorted({e.weekday for e in p.exercises.all()}), [0, 2, 4])

    def test_trainer_plan_is_never_replaced(self):
        from .models import Trainer
        WorkoutPlan.objects.create(user=self.u, trainer=Trainer.objects.first(), title="Murabbiy rejasi", active=True)
        self.c.post("/ai/plan/", {"goal": "muscle", "level": "beginner", "days": "3", "equipment": "gym"})
        self.assertEqual(WorkoutPlan.objects.get(user=self.u, active=True).title, "Murabbiy rejasi")


class StorageAndVipTests(Base):
    def test_local_storage_without_cloudinary(self):
        from django.conf import settings
        from .media import is_local, video_storage
        self.assertFalse(settings.CLOUDINARY_ON)
        lesson = Lesson.objects.first()
        self.assertTrue(is_local(lesson.video_file))
        self.assertEqual(type(video_storage()).__name__, "FileSystemStorage")

    def test_remote_files_are_redirected(self):
        from .models import Product
        p = Product.objects.first()
        p.image.name = "products/x.png"
        p.save()
        from .models import image_url  # the picture view, as image_src links it
        url = image_url("product", p)
        with mock.patch("gym.media.is_local", return_value=False), mock.patch("django.db.models.fields.files.FieldFile.url",
                                                                               new_callable=mock.PropertyMock, return_value="https://res.cloudinary.com/x.png"):
            r = Client().get(url)
        self.assertEqual((r.status_code, r["Location"]), (302, "https://res.cloudinary.com/x.png"))

    def test_vip_is_gone(self):
        for url in ("/vip/", "/vip/guest/"):
            self.assertEqual(Client().get(url).status_code, 404)
        self.assertFalse(Plan.objects.filter(code="vip", active=True).exists())
        self.assertNotIn("VIP", Client().get("/").content.decode().replace("aria-label", ""))
        self.assertFalse(hasattr(services, "is_vip"))


class AvatarTests(Base):
    def setUp(self):
        super().setUp()
        import shutil
        import tempfile
        self.media = tempfile.mkdtemp()
        self.ov = override_settings(MEDIA_ROOT=self.media)
        self.ov.enable()
        self.addCleanup(lambda: (self.ov.disable(), shutil.rmtree(self.media, ignore_errors=True)))
        self.register()
        self.c = Client()
        self.c.post("/login/", {"login": "aziz_k", "password": PW})

    def test_upload_show_and_remove(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
        self.assertContains(self.c.get("/profile/"), "data-avatar-form")
        self.c.post("/profile/", {"form": "avatar", "avatar": SimpleUploadedFile("me.html", b"<script>")})
        self.assertFalse(User.objects.get(username="aziz_k").avatar)  # not a picture: refused
        self.c.post("/profile/", {"form": "avatar", "avatar": SimpleUploadedFile("me.png", png)})
        u = User.objects.get(username="aziz_k")
        self.assertTrue(u.avatar)
        page = self.c.get("/dashboard/").content.decode()
        self.assertIn(f'<img src="{u.avatar_src}"', page)  # in the account menu
        r = Client().get(u.avatar_src)
        self.assertEqual((r.status_code, r["Content-Type"]), (200, "image/png"))
        r.close()  # Windows keeps a file locked while a response still holds it open
        self.c.post("/profile/", {"form": "avatar", "remove": "1"})
        self.assertFalse(User.objects.get(username="aziz_k").avatar)
        self.assertIn('class="um-ava"', self.c.get("/dashboard/").content.decode())


class AccountSettingsTests(Base):
    def setUp(self):
        super().setUp()
        self.register()
        self.c = Client()
        self.c.post("/login/", {"login": "aziz_k", "password": PW})

    def post(self, **over):
        data = {"username": "aziz_k", "email": "aziz@example.com", "first_name": "Aziz", "last_name": "K", "phone": ""}
        data.update(over)
        return self.c.post("/account/", data)

    def test_page_and_menu(self):
        r = self.c.get("/account/")
        self.assertContains(r, "acc-side")
        self.assertContains(r, 'aria-current="page"')
        self.assertContains(self.c.get("/dashboard/"), 'href="/account/"')
        self.assertEqual(Client().get("/account/").status_code, 302)

    def test_change_details_and_password(self):
        r = self.post(username="aziz2", first_name="Azizbek", phone="93 111 22 33")
        self.assertRedirects(r, "/account/")
        u = User.objects.get(pk=User.objects.get(username="aziz2").pk)
        self.assertEqual((u.first_name, u.phone), ("Azizbek", "+998931112233"))
        self.post(username="aziz2", current_password="wrong", new_password="Yangi-2026")
        self.assertTrue(User.objects.get(username="aziz2").check_password(PW))  # wrong current password: unchanged
        r = self.post(username="aziz2", current_password=PW, new_password="Yangi-2026")
        self.assertRedirects(r, "/account/")
        self.assertTrue(User.objects.get(username="aziz2").check_password("Yangi-2026"))
        self.assertEqual(self.c.get("/account/").status_code, 200)  # still signed in after the change

    def test_unique_username_and_email(self):
        self.register(Client(), username="vali", email="vali@x.uz")
        self.assertContains(self.post(username="VALI"), "field-err")
        self.assertContains(self.post(email="vali@x.uz"), "field-err")
        self.assertEqual(User.objects.filter(username="aziz_k").count(), 1)
