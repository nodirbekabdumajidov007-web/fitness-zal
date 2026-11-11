"""Confetti is a reward, not a decoration: only flash messages tagged "celebrate" may fire it; ordinary "saved/sent" toasts never do."""
from django.contrib import messages
from django.test import Client, TestCase
from django.urls import reverse

from .models import GymSettings, User


class CelebrateTests(TestCase):
    def setUp(self):
        GymSettings.load()
        self.u = User.objects.create_user(username="cel", email="c@x.uz", password="pw12345678", first_name="C")
        self.c = Client()
        self.c.force_login(self.u)

    def test_review_toast_has_no_celebrate_tag(self):
        r = self.c.post(reverse("reviews"), {"rating": 5, "comment": "Juda yaxshi zal"}, follow=True)
        self.assertContains(r, "msg success")
        self.assertNotContains(r, "msg success celebrate")

    def test_profile_save_is_specific_and_quiet(self):
        r = self.c.post(reverse("profile"), {"form": "profile", "first_name": "Ali", "last_name": "V", "phone": self.u.phone or "901234567"}, follow=True)
        self.assertNotContains(r, "success celebrate")

    def test_new_record_celebrates_but_a_lower_one_does_not(self):
        r = self.c.post(reverse("records"), {"lift": "bench", "weight": "100", "reps": "5"}, follow=True)
        self.assertContains(r, "msg success celebrate")
        r = self.c.post(reverse("records"), {"lift": "bench", "weight": "50", "reps": "5"}, follow=True)
        self.assertNotContains(r, "celebrate")

    def test_flash_helper_sets_the_tag(self):
        from .views import flash
        from django.contrib.messages.storage.fallback import FallbackStorage
        from django.test import RequestFactory
        req = RequestFactory().get("/")
        req.session = {}
        req._messages = FallbackStorage(req)
        req.lang = "uz"
        flash(req, messages.SUCCESS, "saved")
        flash(req, messages.SUCCESS, "record_new", celebrate=True)
        tags = [m.extra_tags for m in req._messages]
        self.assertEqual(tags, ["", "celebrate"])

    def test_js_only_fires_on_the_celebrate_class(self):
        import pathlib
        js = (pathlib.Path(__file__).parent / "static" / "js" / "app.js").read_text(encoding="utf-8")
        self.assertIn(".msg.success.celebrate", js)
        self.assertNotIn("querySelector('.msg.success')", js)

    def test_distinct_actions_have_distinct_toasts(self):
        from .i18n import T
        keys = ["cancel_ok", "pt_cancel_ok", "pt_confirmed_ok", "pt_declined_ok", "profile_saved", "pw_changed", "body_saved", "weight_saved",
                "goal_saved", "report_sent", "chat_report_sent", "review_ok", "cal_added"]
        for lang in ("uz", "ru", "en"):
            texts = [T[lang][k] for k in keys]
            self.assertEqual(len(set(texts)), len(texts), lang)
        self.assertIn("yuborildi", T["uz"]["chat_report_sent"])
