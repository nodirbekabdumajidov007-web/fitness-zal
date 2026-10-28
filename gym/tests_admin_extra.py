"""Admin extras (dashboard feed, search, member card, broadcast), the cinematic home page and the Google Client ID from settings."""
from datetime import timedelta
from unittest import mock

from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import Client, TestCase, override_settings
from django.utils import timezone

from . import telegram
from .models import Announcement, GymSettings, Membership, Payment, Plan, User, Visit

PW = "Kuchli-Parol-77"
CID = "123-abc.apps.googleusercontent.com"


@override_settings(GOOGLE_CLIENT_ID="")
class Base(TestCase):
    def setUp(self):
        cache.clear()
        call_command("setup_gym", demo=True, verbosity=0)
        self.admin = User.objects.get(is_superuser=True)
        self.admin.set_password("AdminPass1")
        self.admin.save()
        self.m = User.objects.create_user(phone="+998901112233", password=PW, first_name="Aziz", last_name="Karimov")
        now = timezone.now()
        Membership.objects.create(user=self.m, plan=Plan.objects.get(code="m1"), starts=now - timedelta(days=3), expires=now + timedelta(days=5))
        Visit.objects.create(user=self.m)
        Payment.objects.create(user=self.m, kind="plan", amount=400000, method="cash", status="paid")
        self.staff = Client()
        self.staff.post("/login/", {"phone": "908775505", "password": "AdminPass1.admin"})


class DashboardTests(Base):
    def test_dashboard_has_live_parts(self):
        r = self.staff.get("/django-admin/")
        self.assertEqual(r.status_code, 200)
        for text in ("Jonli lenta", "Sozlash holati", "Zalga keldi: Aziz Karimov", "maqsad", "Bugungi guruh"):
            self.assertContains(r, text)
        self.assertEqual(r.context["in_gym"], 1)
        self.assertEqual(r.context["goal_pct"], 2)  # 400 000 of the default 20 000 000

    def test_member_pages_need_admin_mode(self):
        c = Client()
        c.post("/login/", {"phone": "901112233", "password": PW})
        for url in ("/django-admin/search/?q=Aziz", f"/django-admin/member/{self.m.pk}/", "/django-admin/broadcast/"):
            self.assertIn(c.get(url).status_code, (302, 404), url)


class SearchTests(Base):
    def test_one_hit_opens_member_card(self):
        r = self.staff.get("/django-admin/search/?q=11 22")  # spaces are ignored: digits 1122 are in 90 111 22 33
        self.assertRedirects(r, f"/django-admin/member/{self.m.pk}/", fetch_redirect_response=False)
        r = self.staff.get(f"/django-admin/search/?q=FZ-{self.m.pk:04d}")
        self.assertRedirects(r, f"/django-admin/member/{self.m.pk}/", fetch_redirect_response=False)
        r = self.staff.get("/django-admin/search/?q=karimov aziz")
        self.assertRedirects(r, f"/django-admin/member/{self.m.pk}/", fetch_redirect_response=False)

    def test_many_and_none(self):
        User.objects.create_user(phone="+998901112244", password=PW, first_name="Aziza", last_name="Olimova")
        r = self.staff.get("/django-admin/search/?q=aziz")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Aziza Olimova")
        self.assertContains(self.staff.get("/django-admin/search/?q=qwertyzz"), "hech narsa topilmadi")

    def test_member_card(self):
        r = self.staff.get(f"/django-admin/member/{self.m.pk}/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.context["visits_total"], 1)
        self.assertEqual(r.context["spent"], 400000)
        self.assertContains(r, "kun qoldi")
        self.assertContains(self.staff.get("/django-admin/gym/user/"), f"/django-admin/member/{self.m.pk}/")


class BroadcastTests(Base):
    def test_announcement_only(self):
        r = self.staff.post("/django-admin/broadcast/", {"title": "Yakshanba", "body": "10:00 da ochilamiz", "audience": "all", "announce": "on"})
        self.assertRedirects(r, "/django-admin/broadcast/", fetch_redirect_response=False)
        self.assertTrue(Announcement.objects.filter(title="Yakshanba").exists())
        self.assertEqual(Client().get("/").status_code, 200)  # announcements are no longer shown on the home page

    def test_needs_text_and_channel(self):
        r = self.staff.post("/django-admin/broadcast/", {"title": "", "body": "x", "announce": "on"})
        self.assertContains(r, "Sarlavha va matnni yozing")
        r = self.staff.post("/django-admin/broadcast/", {"title": "a", "body": "b"})
        self.assertContains(r, "Kamida bitta kanalni")
        self.assertFalse(Announcement.objects.filter(title="a").exists())

    def test_telegram_goes_to_chosen_audience_only(self):
        User.objects.filter(pk=self.m.pk).update(telegram_chat_id=111)
        other = User.objects.create_user(phone="+998935554433", password=PW, first_name="Vali", last_name="A")  # no membership
        User.objects.filter(pk=other.pk).update(telegram_chat_id=222)
        sent = []
        with mock.patch.object(telegram, "enabled", return_value=True), \
                mock.patch.object(telegram, "send", side_effect=lambda chat, text: sent.append(chat) or {"ok": True}):
            self.staff.post("/django-admin/broadcast/", {"title": "Eslatma", "body": "Abonement", "audience": "expiring", "tg": "on"})
        self.assertEqual(sent, [111])


class HomeAndGoogleTests(Base):
    def test_home_is_cinematic(self):
        r = Client().get("/")
        self.assertContains(r, 'class="cine"')
        self.assertContains(r, "KUCH")
        self.assertContains(r, "js/home.js")
        self.assertNotContains(r, "<video")  # no clip uploaded: animated photo instead
        self.assertEqual(Client().get("/hero/video/").status_code, 404)

    def test_client_id_from_settings_page(self):
        gs = GymSettings.load()
        gs.require_google = True
        with self.assertRaises(ValidationError):
            gs.full_clean()
        gs.google_client_id = "not-an-id"
        with self.assertRaises(ValidationError):
            gs.full_clean()
        gs.google_client_id = CID
        gs.full_clean()
        gs.save()
        r = Client().get("/login/")
        self.assertContains(r, f'data-client="{CID}"')
        r = Client().post("/login/", {"phone": "901112233", "password": PW})
        self.assertContains(r, "Google")  # members are sent to the Google button
        self.assertFalse(Client().get("/dashboard/").status_code == 200)

    def test_auth_pages_have_parallax_scene(self):
        for url in ("/login/", "/register/"):
            r = Client().get(url)
            self.assertContains(r, "data-scene")
            self.assertContains(r, "data-warp")
            self.assertContains(r, "js/scene.js")
            self.assertContains(r, 'class="scene gymroom"')  # the gym room with lamps, a punching bag and a neon sign
            self.assertContains(r, "FITNES ZAL")

    def test_delete_buttons_use_bin_animation(self):
        from .models import BodyLog
        BodyLog.objects.create(user=self.m, weight=80)
        c = Client()
        c.post("/login/", {"phone": "901112233", "password": PW})
        self.assertContains(c.get("/progress/"), "data-bin data-confirm")

    def test_live_numbers_and_bento(self):
        r = self.staff.get("/django-admin/live/")
        self.assertEqual(r.status_code, 200)
        d = r.json()
        self.assertEqual((d["in_gym"], d["visits_today"], d["revenue_month"]), (1, 1, 400000))
        page = self.staff.get("/django-admin/")
        self.assertContains(page, 'class="bento"')
        self.assertContains(page, "data-live-url")
        self.assertIn(Client().get("/django-admin/live/").status_code, (302, 404))  # not for visitors

    def test_member_edit_page_hides_password_hash(self):
        r = self.staff.get(f"/django-admin/gym/user/{self.m.pk}/change/")
        self.assertEqual(r.status_code, 200)
        self.assertNotContains(r, "pbkdf2_")
        self.assertContains(r, "A'zo kartochkasi")
        self.assertContains(r, "Bosh admin")

    def test_reviews_page_and_language_flags(self):
        from .models import Review
        Review.objects.create(user=self.m, rating=5, comment="Zo'r zal", approved=True)
        Review.objects.create(user=self.admin, rating=3, comment="Yaxshi", approved=True)
        r = Client().get("/reviews/")
        self.assertContains(r, "star-pick")
        self.assertEqual([d["n"] for d in r.context["dist"]], [1, 0, 1, 0, 0])
        self.assertEqual(r.context["dist"][0]["pct"], 50)
        self.assertContains(r, 'class="flag"')
        self.assertContains(r, "/lang/ru/?next=")

    def test_checkout_page_card_and_steps(self):
        from .models import PaymentCard
        PaymentCard.objects.create(bank="Humo", number="4111111111111111", holder="TEST", is_primary=True)
        c = Client()
        c.post("/login/", {"phone": "901112233", "password": PW})
        c.post("/plans/m1/buy/", {"method": "card"})
        p = Payment.objects.filter(user=self.m, status="pending").latest("id")
        r = c.get(f"/pay/{p.pk}/")
        self.assertContains(r, 'class="bankcard humo"')
        self.assertContains(r, "4111 1111 1111 1111")
        self.assertContains(r, "co-steps")
        self.assertContains(r, "js/pay.js")
        self.assertNotContains(r, 'name="cvc"')  # only the last 4 digits are ever asked for
        c.post(f"/pay/{p.pk}/report/", {"sender_last4": "1234"})
        self.assertContains(c.get(f"/pay/{p.pk}/"), "co-wait")

    def test_trainer_portraits_marked_for_pixels(self):
        from .models import Trainer
        tr = Trainer.objects.filter(active=True).first()
        self.assertContains(Client().get(f"/trainers/{tr.pk}/"), 'data-px="22"')
        self.assertContains(Client().get("/trainers/"), 'data-px="14"')

    def test_settings_admin_page_shows_google_help(self):
        r = self.staff.get("/django-admin/gym/gymsettings/1/change/")
        self.assertContains(r, "console.cloud.google.com")
        self.assertContains(r, "Google Client ID")
