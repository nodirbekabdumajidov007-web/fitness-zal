"""Username sign-up and sign-in, e-mail (SMTP) messages and password reset, the AI coach and AI plans (API mocked),
Cloudinary switches and the removal of VIP."""
import json
from unittest import mock

from django.core import mail
from django.core.cache import cache
from django.core.management import call_command
from django.test import Client, TestCase, override_settings

from . import ai, services
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

    def test_owner_signs_in_as_admin(self):
        r = Client().post("/login/", {"login": "admin", "password": "AdminPass1.admin"})
        self.assertEqual(r["Location"], "/django-admin/")
        self.assertEqual(self.admin.username, "admin")


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
        staff.post("/login/", {"login": "admin", "password": "AdminPass1.admin"})
        staff.post("/django-admin/message/", {"ids": [u.pk], "title": "Salom, {ism}!", "body": "Ertaga zal 10:00 da", "email": "on"})
        self.assertEqual(mail.outbox[-1].to, ["aziz@example.com"])
        self.assertIn("Salom, aziz_k!", mail.outbox[-1].subject)


class FakeBlock:
    def __init__(self, text):
        self.type, self.text = "text", text


class FakeResponse:
    def __init__(self, text, stop="end_turn"):
        self.content, self.stop_reason = [FakeBlock(text)], stop


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class AITests(Base):
    def setUp(self):
        super().setUp()
        self.register()
        self.u = User.objects.get(username="aziz_k")
        self.c = Client()
        self.c.post("/login/", {"login": "aziz_k", "password": PW})
        self.env = mock.patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key", "FZ_AI_DAILY_LIMIT": "3"})
        self.env.start()
        self.addCleanup(self.env.stop)

    def fake(self, text, stop="end_turn"):
        create = mock.Mock(return_value=FakeResponse(text, stop))
        client = mock.Mock()
        client.beta.messages.create = create
        return mock.patch("anthropic.Anthropic", return_value=client), create

    def test_page_for_guests_and_members(self):
        self.assertContains(Client().get("/ai/"), "/login/?next=/ai/")
        self.assertContains(self.c.get("/ai/"), 'data-ai-form')

    def test_chat_knows_the_member_and_is_stored(self):
        self.u.goal, self.u.target_weight = "lose", 70
        self.u.save()
        patcher, create = self.fake("Kuniga 2 litr suv iching.")
        with patcher:
            r = self.c.post("/ai/ask/", {"q": "Qancha suv ichay?"}, HTTP_X_REQUESTED_WITH="fetch")
        self.assertEqual(r.json()["answer"], "Kuniga 2 litr suv iching.")
        kw = create.call_args.kwargs
        self.assertEqual(kw["model"], "claude-opus-5-5")
        self.assertIn("Ozish", kw["messages"][-1]["content"])      # goal in the profile
        self.assertIn("Target weight: 70", kw["messages"][-1]["content"])
        self.assertIn("Uzbek", kw["system"])
        self.assertEqual(list(AIMessage.objects.values_list("role", flat=True)), ["user", "assistant"])
        with patcher:  # the next question carries the earlier turns
            self.c.post("/ai/ask/", {"q": "Yana?"}, HTTP_X_REQUESTED_WITH="fetch")
        self.assertEqual([m["role"] for m in create.call_args.kwargs["messages"]], ["user", "assistant", "user"])

    def test_daily_limit_refusal_and_no_key(self):
        patcher, _ = self.fake("ok")
        with patcher:
            for _ in range(3):
                self.c.post("/ai/ask/", {"q": "savol"}, HTTP_X_REQUESTED_WITH="fetch")
            r = self.c.post("/ai/ask/", {"q": "savol"}, HTTP_X_REQUESTED_WITH="fetch")
        self.assertEqual(r.status_code, 400)
        cache.clear()
        patcher, _ = self.fake("", stop="refusal")
        with patcher:
            r = self.c.post("/ai/ask/", {"q": "savol"}, HTTP_X_REQUESTED_WITH="fetch")
        self.assertEqual(r.status_code, 400)
        with mock.patch.dict("os.environ", {"ANTHROPIC_API_KEY": ""}):
            self.assertFalse(ai.enabled())
            r = self.c.post("/ai/ask/", {"q": "savol"}, HTTP_X_REQUESTED_WITH="fetch")
        self.assertEqual(r.status_code, 400)

    def test_plan_is_saved_as_current_plan(self):
        plan = {"title": "Kuchli start", "notes": "Har hafta og'irlikni oshiring.", "exercises": [
            {"weekday": 0, "name": "O'tirib turish (Squat)", "sets": 3, "reps": "8-10", "note": "Orqa tekis"},
            {"weekday": 2, "name": "Tortilish (Pull-up)", "sets": 99, "reps": "max", "note": ""},
            {"weekday": 9, "name": "Noto'g'ri kun", "sets": 3, "reps": "10", "note": ""}]}
        patcher, create = self.fake(json.dumps(plan))
        with patcher:
            r = self.c.post("/ai/plan/", {"level": "beginner", "days": "3", "minutes": "60"})
        self.assertEqual(r["Location"], "/workouts/")
        self.assertEqual(create.call_args.kwargs["output_config"]["format"]["type"], "json_schema")
        p = WorkoutPlan.objects.get(user=self.u, active=True)
        self.assertEqual(p.title, "✦ Kuchli start")
        self.assertEqual([(e.weekday, e.sets) for e in p.exercises.all()], [(0, 3), (2, 10)])  # bad day dropped, sets capped

    def test_trainer_plan_is_never_replaced(self):
        from .models import Trainer
        WorkoutPlan.objects.create(user=self.u, trainer=Trainer.objects.first(), title="Murabbiy rejasi", active=True)
        patcher, create = self.fake("{}")
        with patcher:
            self.c.post("/ai/plan/", {"level": "beginner", "days": "3", "minutes": "60"})
        create.assert_not_called()
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
