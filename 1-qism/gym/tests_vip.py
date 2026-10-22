"""Training lessons (types, daily schedule, video, instructions) and the paid VIP add-on."""
from datetime import timedelta

from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import Client, TestCase
from django.utils import timezone
from django.utils.html import escape

from . import services
from .i18n import T
from .media import video_embed
from .models import Lesson, Membership, Order, Payment, Plan, PaymentCard, Product, PromoCode, User, VipPass, WorkoutType

TEST_CARD = "4111111111111111"


class VipBase(TestCase):
    def setUp(self):
        cache.clear()
        call_command("setup_gym", demo=True, verbosity=0)
        self.admin = User.objects.get(is_superuser=True)
        self.admin.set_password("AdminPass1")
        self.admin.save()
        PaymentCard.objects.create(bank="Uzcard", number=TEST_CARD, holder="TEST OWNER", is_primary=True)

    def member(self, phone="+998901112233", first="Aziz"):
        c = Client()
        c.post("/register/", {"first_name": first, "last_name": "Karimov", "phone": phone[4:], "password": "secret12"})
        return c, User.objects.get(phone=phone)

    def staff(self):
        c = Client()
        c.post("/login/", {"phone": "908775505", "password": "AdminPass1.admin"})
        return c

    def buy_vip_by_card(self, client, user):
        client.post("/vip/buy/", {"method": "card"})
        pay = Payment.objects.filter(user=user, kind="vip").order_by("-pk").first()
        services.confirm_payment(pay)
        return pay


class VideoEmbedTests(TestCase):
    def test_supported_links(self):
        yt = "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"
        self.assertEqual(video_embed("https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=5s"), {"kind": "iframe", "src": yt})
        self.assertEqual(video_embed("https://youtu.be/dQw4w9WgXcQ?si=abc"), {"kind": "iframe", "src": yt})
        self.assertEqual(video_embed("https://youtube.com/shorts/dQw4w9WgXcQ"), {"kind": "iframe", "src": yt})
        self.assertEqual(video_embed("https://vimeo.com/123456789"), {"kind": "iframe", "src": "https://player.vimeo.com/video/123456789"})
        self.assertEqual(video_embed("https://cdn.example.com/a/b.mp4"), {"kind": "video", "src": "https://cdn.example.com/a/b.mp4"})
        self.assertEqual(video_embed("https://example.com/page")["kind"], "link")

    def test_unsafe_or_empty_links_are_never_embedded(self):
        for bad in ("", None, "javascript:alert(1)", "http://youtu.be/dQw4w9WgXcQ", "data:text/html,x", "https://", "//evil.com/x.mp4"):
            self.assertIsNone(video_embed(bad), bad)
        self.assertEqual(video_embed("https://www.youtube.com/watch?v=short")["kind"], "link")  # not a valid video id: never put in an iframe
        self.assertEqual(video_embed('https://youtu.be/"><script>')["kind"], "link")

    def test_model_rejects_non_https(self):
        with self.assertRaises(ValidationError):
            Lesson(title="x", video_url="http://example.com/v.mp4").full_clean()


class TrainingPageTests(VipBase):
    def test_every_day_has_lessons_and_daily_ones_show_everywhere(self):
        c = Client()
        daily = Lesson.objects.get(weekday=None, title__startswith="Qizdirish")
        for day in range(7):
            r = c.get(f"/training/?day={day}")
            self.assertEqual(r.status_code, 200)
            self.assertContains(r, escape(daily.title))  # titles contain apostrophes, which HTML-escape
        self.assertContains(c.get("/training/?day=0"), "Skvat")
        self.assertNotContains(c.get("/training/?day=1"), "Skvat: to&#x27;g&#x27;ri texnika")
        self.assertEqual(c.get("/training/?day=banana").status_code, 200)  # junk input falls back to today
        self.assertEqual(c.get("/training/?day=99").status_code, 200)

    def test_type_and_level_filters(self):
        c = Client()
        yoga = WorkoutType.objects.get(name="Yoga va cho'zilish")
        r = c.get(f"/training/?day=5&type={yoga.pk}")
        self.assertContains(r, "Ertalabki yoga")
        self.assertNotContains(r, "Funksional aylana")
        r = c.get("/training/?day=0&level=advanced")
        self.assertContains(r, "haftalik massa")
        self.assertNotContains(r, "Skvat: to&#x27;g&#x27;ri texnika")

    def test_lesson_content_and_video(self):
        lesson = Lesson.objects.get(title__startswith="Skvat")
        lesson.video_url = "https://youtu.be/dQw4w9WgXcQ"
        lesson.save()
        r = Client().get(f"/training/{lesson.pk}/")
        self.assertContains(r, "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ")
        self.assertContains(r, "Tovonni yerdan uzmang")  # the instructions and tips are shown
        self.assertIn("youtube-nocookie.com", r["Content-Security-Policy"])  # the CSP allows exactly this player
        lesson.video_url = "https://example.com/watch"
        lesson.save()
        r = Client().get(f"/training/{lesson.pk}/")
        self.assertContains(r, 'rel="noopener noreferrer"')
        self.assertNotContains(r, "<iframe")
        lesson.video_url = ""
        lesson.save()
        self.assertContains(Client().get(f"/training/{lesson.pk}/"), "note")  # friendly "no video yet" notice

    def test_inactive_lessons_are_hidden(self):
        lesson = Lesson.objects.get(title__startswith="Skvat")
        lesson.active = False
        lesson.save()
        self.assertEqual(Client().get(f"/training/{lesson.pk}/").status_code, 404)
        self.assertNotContains(Client().get("/training/?day=0"), "Skvat: to&#x27;g&#x27;ri")

    def test_vip_lessons_are_locked_until_vip(self):
        lesson = Lesson.objects.get(is_vip=True, title__contains="ovqatlanish")
        step = "Oqsil: tana vazningizning"
        anon = Client().get(f"/training/{lesson.pk}/")
        self.assertContains(anon, lesson.title)
        self.assertNotContains(anon, step)  # the content is not sent at all
        self.assertContains(anon, "/vip/")
        c, u = self.member()
        self.assertNotContains(c.get(f"/training/{lesson.pk}/"), step)
        self.assertContains(c.get("/training/?day=0"), "VIP")  # listed, marked as VIP
        self.buy_vip_by_card(c, u)
        self.assertContains(c.get(f"/training/{lesson.pk}/"), step)

    def test_locked_lesson_hides_the_video_too(self):
        lesson = Lesson.objects.get(is_vip=True, title__contains="ovqatlanish")
        lesson.video_url = "https://youtu.be/dQw4w9WgXcQ"
        lesson.save()
        self.assertNotContains(Client().get(f"/training/{lesson.pk}/"), "youtube")


class VipPurchaseTests(VipBase):
    def test_price_and_card_flow(self):
        c, u = self.member()
        self.assertContains(c.get("/vip/"), "50 000")
        r = c.post("/vip/buy/", {"method": "card", "amount": "1", "price": "1"})  # the browser cannot choose the price
        pay = Payment.objects.get()
        self.assertEqual((pay.kind, pay.amount, pay.status, r["Location"]), ("vip", 50000, "pending", f"/pay/{pay.pk}/"))
        self.assertFalse(VipPass.objects.exists())  # nothing before the money is confirmed
        self.assertContains(c.get(f"/pay/{pay.pk}/"), "VIP obuna")
        self.assertFalse(services.is_vip(u))
        self.assertTrue(services.confirm_payment(pay))
        vp = VipPass.objects.get()
        self.assertEqual((vp.expires - vp.starts).days, 30)
        self.assertTrue(services.is_vip(u))
        self.assertContains(c.get("/dashboard/"), "VIP")
        self.assertEqual(c.get(f"/receipt/{pay.pk}/").status_code, 200)

    def test_passes_stack_and_expire(self):
        c, u = self.member()
        self.buy_vip_by_card(c, u)
        first_end = services.vip_until(u)
        self.buy_vip_by_card(c, u)
        self.assertEqual(services.vip_until(u), first_end + timedelta(days=30))
        VipPass.objects.all().update(starts=timezone.now() - timedelta(days=90), expires=timezone.now() - timedelta(days=1))
        self.assertFalse(services.is_vip(u))

    def test_reject_leaves_no_vip_and_promo_discount(self):
        c, u = self.member()
        c.post("/vip/buy/", {"method": "card", "promo": "YANGI10"})
        pay = Payment.objects.get()
        self.assertEqual((pay.amount, pay.discount), (45000, 5000))
        services.cancel_payment(pay)
        self.assertFalse(VipPass.objects.exists())
        self.assertEqual(PromoCode.objects.get(code="YANGI10").used, 0)
        self.assertFalse(services.confirm_payment(pay))
        self.assertFalse(VipPass.objects.exists())

    def test_login_needed_and_vip_plan_includes_perks(self):
        r = Client().post("/vip/buy/", {"method": "card"})
        self.assertTrue(r["Location"].startswith("/login/"))
        c, u = self.member()
        now = timezone.now()
        Membership.objects.create(user=u, plan=Plan.objects.get(code="vip"), starts=now - timedelta(days=1), expires=now + timedelta(days=29))
        self.assertTrue(services.is_vip(u))  # the 600 000 VIP plan already includes the VIP perks
        self.assertContains(c.get("/vip/"), "VIP")

    def test_double_points_and_shop_discount(self):
        c, u = self.member()
        suv = Product.objects.get(name="Suv 0.5 l")
        c.post(f"/cart/add/{suv.pk}/")
        c.post(f"/cart/update/{suv.pk}/", {"qty": 10})
        c.post("/checkout/", {"method": "card"})  # not VIP yet: full price
        self.assertEqual(Order.objects.get().total, 50000)
        base = services.points(u)
        self.buy_vip_by_card(c, u)
        self.assertEqual(services.points(u), base * 2)
        c.post(f"/cart/add/{suv.pk}/")
        c.post(f"/cart/update/{suv.pk}/", {"qty": 10})
        c.post("/checkout/", {"method": "card"})
        order = Order.objects.order_by("-pk").first()
        pay = order.payments.get()
        self.assertEqual((order.total, pay.amount, pay.discount, pay.promo), (45000, 45000, 5000, "VIP"))
        PromoCode.objects.create(code="VIP", percent=5)  # a promo that happens to share the label must not be touched
        services.cancel_payment(pay)
        self.assertEqual(PromoCode.objects.get(code="VIP").used, 0)
        self.assertEqual(c.get(f"/receipt/{pay.pk}/").status_code, 200)

    def test_no_vip_without_confirmed_money(self):
        """Every way to get VIP perks: none may work before a payment is confirmed."""
        from django.test import override_settings
        from .models import GymSettings
        c, u = self.member()
        GymSettings.objects.filter(pk=1).update(demo_payments=True)
        with override_settings(ALLOW_DEMO_PAYMENTS=True):  # even with the demo buttons switched on for development
            for m in ("Payme", "Click", "Uzum"):
                c.post("/vip/buy/", {"method": m})
                c.post("/plans/vip/buy/", {"method": m})  # the VIP plan also unlocks VIP perks
            self.assertNotIn('value="Payme"', c.get("/vip/").content.decode())
        self.assertFalse(Payment.objects.exists())
        for m in ("cash", "card"):
            c.post("/vip/buy/", {"method": m})
        c.post("/plans/vip/buy/", {"method": "cash"})
        c.post(f"/pay/{Payment.objects.filter(method='card').get().pk}/report/", {"sender_last4": "1234"})  # "I've paid" is not proof
        self.assertTrue(Payment.objects.exists() and not Payment.objects.exclude(status="pending").exists())
        self.assertFalse(VipPass.objects.exists())
        self.assertFalse(services.is_vip(u))
        self.assertEqual(c.get(f"/training/{Lesson.objects.filter(is_vip=True).first().pk}/").status_code, 200)
        self.assertNotContains(c.get(f"/training/{Lesson.objects.filter(is_vip=True, title__contains='ovqatlanish').get().pk}/"), "Oqsil: tana")
        pay = Payment.objects.filter(kind="vip", method="cash").get()
        self.assertTrue(services.confirm_payment(pay))  # only now
        self.assertTrue(services.is_vip(u))
        self.assertEqual(VipPass.objects.get().payment, pay)  # every pass points to the payment that bought it

    def test_admin_tools(self):
        c, u = self.member()
        a = self.staff()
        self.assertNotContains(a.get("/django-admin/gym/user/"), "grant_vip")  # no "free VIP" button
        self.assertEqual(a.get("/django-admin/gym/vippass/add/").status_code, 403)  # passes cannot be typed in by hand
        services.add_vip(u)
        for url in ("/django-admin/", "/django-admin/gym/lesson/", "/django-admin/gym/lesson/add/", "/django-admin/gym/workouttype/", "/django-admin/gym/vippass/",
                    "/django-admin/gym/gymsettings/1/change/"):
            self.assertEqual(a.get(url).status_code, 200, url)
        self.assertContains(a.get("/django-admin/"), "Faol VIP")


class TranslationTests(TestCase):
    def test_new_keys_exist_in_all_languages(self):
        need = ["nav_training", "training", "vip_get", "vip_locked", "kind_vip", "safety_note", "every_day",
                *(f"level_{x}" for x in ("beginner", "intermediate", "advanced"))]
        for lang in T:
            self.assertEqual([k for k in need if k not in T[lang]], [], lang)
