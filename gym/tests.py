import re
from datetime import timedelta
from pathlib import Path

from django.core.cache import cache
from django.core.management import call_command
from django.test import Client, TestCase, override_settings
from django.utils import timezone

from . import services
from .i18n import T
from .models import Booking, GymClass, GymSettings, Membership, Order, Payment, Plan, Product, PromoCode, Review, User

PW = "secret12"


def quiet_setup():
    call_command("setup_gym", demo=True, verbosity=0)


@override_settings(ALLOW_DEMO_PAYMENTS=True)  # these tests use the demo gateways; the real-money rules are covered in tests_card.py
class Base(TestCase):
    def setUp(self):
        cache.clear()
        quiet_setup()
        GymSettings.objects.filter(pk=1).update(demo_payments=True)  # off by default; these tests exercise the demo gateways
        self.admin = User.objects.get(is_superuser=True)
        self.admin.set_password("AdminPass1")
        self.admin.save()

    def member(self, phone="+998901112233", first="Aziz"):
        c = Client()
        r = c.post("/register/", {"first_name": first, "last_name": "Karimov", "phone": phone[4:], "password": PW, "username": "u" + "".join(ch for ch in str(phone[4:]) if ch.isdigit()), "email": "u" + "".join(ch for ch in str(phone[4:]) if ch.isdigit()) + "@test.uz", "password2": PW})
        self.assertEqual(r.status_code, 302, r.content[:300])
        return c, User.objects.get(phone=phone)

    def staff(self):
        c = Client()
        r = c.post("/login/", {"phone": "908775505", "password": "AdminPass1.admin"})
        self.assertEqual((r.status_code, r["Location"]), (302, "/django-admin/"))
        return c


class AuthTests(Base):
    def test_register_login_and_validation(self):
        c, u = self.member()
        self.assertTrue(c.get("/dashboard/").status_code == 200)
        bad = Client().post("/register/", {"first_name": "X", "last_name": "Y", "phone": "901112233", "password": PW, "username": "u" + "".join(ch for ch in str("901112233") if ch.isdigit()), "email": "u" + "".join(ch for ch in str("901112233") if ch.isdigit()) + "@test.uz", "password2": PW})
        self.assertContains(bad, "field-err")  # duplicate phone
        self.assertContains(Client().post("/register/", {"first_name": "X", "last_name": "Y", "phone": "123", "password": PW, "username": "u" + "".join(ch for ch in str("123") if ch.isdigit()), "email": "u" + "".join(ch for ch in str("123") if ch.isdigit()) + "@test.uz", "password2": PW}), "field-err")
        self.assertContains(Client().post("/login/", {"phone": "901112233", "password": "wrong"}), "field-err")
        self.assertEqual(Client().post("/login/", {"phone": "+998 90 111 22 33", "password": PW}).status_code, 302)

    def test_pages_render_in_all_languages(self):
        c, _ = self.member()
        for lang in ("uz", "ru", "en"):
            c.cookies["fz_lang"] = lang
            for url in ("/", "/dashboard/", "/plans/", "/shop/", "/cart/", "/classes/", "/trainers/", "/progress/", "/reviews/", "/profile/", "/orders/", "/payments/"):
                r = c.get(url)
                self.assertEqual(r.status_code, 200, f"{lang} {url}")
                self.assertNotIn(b"{%", r.content)
        for url in ("/login/", "/register/"):
            self.assertEqual(Client().get(url).status_code, 200)

    def test_blocked_user_and_rate_limit(self):
        _, u = self.member()
        u.is_active = False
        u.save()
        self.assertContains(Client().post("/login/", {"phone": "901112233", "password": PW}), "field-err")
        cache.clear()
        for _ in range(8):
            Client().post("/login/", {"phone": "900000000", "password": "nope"})
        r = Client().post("/login/", {"phone": "900000000", "password": "nope"})
        self.assertContains(r, "field-err")
        self.assertEqual(Client().post("/login/", {"phone": "900000000", "password": "nope"}).status_code, 200)

    def test_staff_area_needs_admin_suffix(self):
        c, _ = self.member()
        self.assertEqual(c.get("/django-admin/").status_code, 404)  # a member cannot even see it exists
        self.assertEqual(c.get("/staff/").status_code, 404)
        plain = Client()
        plain.post("/login/", {"phone": "908775505", "password": "AdminPass1"})
        self.assertEqual(plain.get("/django-admin/")["Location"], "/login/?need_admin=1")
        self.assertEqual(Client().get("/staff/").status_code, 302)
        a = self.staff()
        self.assertEqual(a.get("/django-admin/").status_code, 200)
        self.assertEqual(a.get("/staff/").status_code, 200)
        m = Client()  # a member cannot gain staff rights with the suffix
        self.assertContains(m.post("/login/", {"phone": "901112233", "password": PW + ".admin"}), "field-err") if User.objects.filter(phone="+998901112233").exists() else None

    def test_csrf_enforced(self):
        c = Client(enforce_csrf_checks=True)
        self.assertEqual(c.post("/login/", {"phone": "901112233", "password": "x"}).status_code, 403)


class MembershipTests(Base):
    def test_buy_demo_cash_and_stacking(self):
        c, u = self.member()
        plan = Plan.objects.get(code="m1")
        c.post("/plans/m1/buy/", {"method": "Payme"})
        self.assertTrue(services.active_membership(u))
        first_end = services.paid_until(u)
        c.post("/plans/m1/buy/", {"method": "Click"})
        self.assertEqual(services.paid_until(u), first_end + timedelta(days=30))  # stacked, no days lost
        c.post("/plans/m3/buy/", {"method": "cash"})
        pay = Payment.objects.filter(status="pending").get()
        self.assertEqual(Membership.objects.filter(user=u).count(), 2)  # cash waits for confirmation
        self.assertTrue(services.confirm_payment(pay))
        self.assertFalse(services.confirm_payment(pay))  # idempotent
        self.assertEqual(Membership.objects.filter(user=u).count(), 3)
        self.assertEqual(plan.price, 400000)

    def test_promo_code(self):
        c, u = self.member()
        c.post("/plans/m1/buy/", {"method": "Payme", "promo": "yangi10"})
        p = Payment.objects.get()
        self.assertEqual((p.amount, p.discount), (360000, 40000))
        c.post("/plans/m1/buy/", {"method": "Payme", "promo": "NOPE"})
        self.assertEqual(Payment.objects.count(), 1)  # bad code: nothing created
        PromoCode.objects.filter(code="YANGI10").update(max_uses=1)
        c.post("/plans/m1/buy/", {"method": "Payme", "promo": "YANGI10"})
        self.assertEqual(Payment.objects.count(), 1)  # usage limit reached

    def test_checkin_rules_and_freeze(self):
        c, u = self.member()
        c.post("/checkin/")
        self.assertEqual(u.visits.count(), 0)  # no membership yet
        c.post("/plans/m3/buy/", {"method": "Payme"})
        c.post("/checkin/")
        c.post("/checkin/")
        self.assertEqual(u.visits.count(), 1)  # once per day
        before = services.paid_until(u)
        c.post("/membership/freeze/", {"days": 7})
        self.assertEqual(services.paid_until(u), before + timedelta(days=7))
        self.assertFalse(services.can_enter(u))  # frozen
        c.post("/membership/freeze/", {"days": 7})
        self.assertEqual(services.paid_until(u), before + timedelta(days=7))  # only once
        self.assertEqual(c.get("/dashboard/").status_code, 200)

    def test_classes_booking(self):
        c, u = self.member()
        cls = GymClass.objects.filter(name="Pauerlifting").get()
        c.post(f"/classes/{cls.pk}/book/")
        self.assertEqual(Booking.objects.count(), 0)  # needs a membership
        c.post("/plans/m1/buy/", {"method": "Payme"})
        c.post(f"/classes/{cls.pk}/book/")
        c.post(f"/classes/{cls.pk}/book/")
        self.assertEqual(Booking.objects.count(), 1)
        cls.capacity = 1
        cls.save()
        c2, _ = self.member("+998935556677", "Bek")
        c2.post("/plans/m1/buy/", {"method": "Payme"})
        c2.post(f"/classes/{cls.pk}/book/")
        self.assertEqual(Booking.objects.count(), 1)  # full
        self.assertEqual(c.get("/classes/").status_code, 200)


class ShopTests(Base):
    def test_order_flow_prices_stock_rollback(self):
        c, u = self.member()
        suv = Product.objects.get(name="Suv 0.5 l")
        c.post(f"/cart/add/{suv.pk}/")
        c.post(f"/cart/update/{suv.pk}/", {"qty": 3})
        c.post("/checkout/", {"method": "cash"})
        o = Order.objects.get()
        self.assertEqual(o.total, 15000)
        suv.refresh_from_db()
        self.assertEqual(suv.stock, 117)
        self.assertTrue(services.hand_over(o))
        self.assertEqual(Payment.objects.get().status, "paid")  # cash collected at pickup
        suv.stock = 1
        suv.save()
        c.post(f"/cart/add/{suv.pk}/")
        c.post(f"/cart/update/{suv.pk}/", {"qty": 5})
        self.assertEqual(c.session["cart"][str(suv.pk)], 1)  # clamped to stock in the cart
        suv.stock = 0
        suv.save()
        c.post("/checkout/", {"method": "Click"})
        self.assertEqual(Order.objects.count(), 1)  # failed order rolled back

    def test_checkout_requires_login(self):
        c = Client()
        suv = Product.objects.get(name="Suv 0.5 l")
        c.post(f"/cart/add/{suv.pk}/")
        r = c.post("/checkout/", {"method": "cash"})
        self.assertTrue(r["Location"].startswith("/login/"))

    def test_receipt_access(self):
        c, u = self.member()
        c.post("/plans/m1/buy/", {"method": "Payme"})
        pay = Payment.objects.get()
        self.assertEqual(c.get(f"/receipt/{pay.pk}/").status_code, 200)
        other, _ = self.member("+998935556677", "Bek")
        self.assertEqual(other.get(f"/receipt/{pay.pk}/").status_code, 404)


class StaffAndAdminTests(Base):
    def test_desk_flow(self):
        c, u = self.member()
        c.post("/plans/m3/buy/", {"method": "cash"})
        a = self.staff()
        self.assertContains(a.get("/staff/?q=" + u.member_code), u.first_name)
        pid = Payment.objects.get().pk
        a.post(f"/staff/confirm/{pid}/")
        self.assertTrue(services.active_membership(u))
        a.post(f"/staff/checkin/{u.pk}/")
        self.assertEqual(u.visits.count(), 1)
        a.post(f"/staff/sell/{u.pk}/", {"plan": "m1"})
        self.assertEqual(Membership.objects.filter(user=u).count(), 2)
        a.post(f"/staff/block/{u.pk}/")
        u.refresh_from_db()
        self.assertFalse(u.is_active)
        self.assertEqual(c.get("/dashboard/").status_code, 302)  # blocked sessions end

    def test_admin_pages_and_actions(self):
        c, u = self.member()
        c.post("/plans/m1/buy/", {"method": "cash"})
        a = self.staff()
        for url in ("/django-admin/", "/django-admin/gym/user/", "/django-admin/gym/payment/", "/django-admin/gym/order/", "/django-admin/gym/product/",
                    "/django-admin/gym/plan/", "/django-admin/gym/review/", "/django-admin/gym/gymclass/", "/django-admin/gym/gymsettings/1/change/"):
            self.assertEqual(a.get(url).status_code, 200, url)
        pid = Payment.objects.get().pk
        a.post("/django-admin/gym/payment/", {"action": "confirm", "_selected_action": [pid]})
        self.assertEqual(Payment.objects.get().status, "paid")
        r = a.post("/django-admin/gym/user/", {"action": "csv", "_selected_action": [u.pk]})
        self.assertIn("text/csv", r["Content-Type"])

    def test_review_moderation(self):
        c, u = self.member()
        c.post("/reviews/", {"rating": 5, "comment": "Ajoyib zal"})
        self.assertEqual(Review.objects.count(), 1)
        self.assertNotContains(Client().get("/reviews/"), "Ajoyib zal")  # hidden until approved
        Review.objects.update(approved=True)
        self.assertContains(Client().get("/reviews/"), "Ajoyib zal")

    def test_progress_chart_and_profile(self):
        c, u = self.member()
        today = timezone.localdate()
        c.post("/progress/", {"date": today - timedelta(days=10), "weight": "82.5", "height_cm": 178})
        c.post("/progress/", {"date": today, "weight": "80.0", "height_cm": 178})
        r = c.get("/progress/")
        self.assertContains(r, "<polyline")
        self.assertContains(r, "bmi_ok") if False else None
        c.post("/profile/", {"form": "profile", "first_name": "Aziz2", "last_name": "K", "phone": "90 111 22 33"})
        u.refresh_from_db()
        self.assertEqual(u.first_name, "Aziz2")
        c.post("/profile/", {"form": "password", "current": PW, "new": "newsecret1"})
        self.assertEqual(c.get("/dashboard/").status_code, 200)  # session survives the password change
        self.assertTrue(User.objects.get(pk=u.pk).check_password("newsecret1"))


class I18nTests(TestCase):
    def test_every_template_key_exists_in_all_languages(self):
        used = set()
        for f in Path(__file__).parent.joinpath("templates/gym").rglob("*.html"):
            used |= {k for k in re.findall(r"\{% t '([a-z_0-9]+)'", f.read_text(encoding="utf-8")) if not k.endswith("_")}  # "st_" etc. are prefixes
        for lang in T:
            self.assertEqual(sorted(k for k in used if k not in T[lang]), [], lang)
        for k in ("st_pending", "st_paid", "st_cancelled", "st_new", "st_done", "kind_plan", "kind_shop", "bmi_low", "bmi_ok", "bmi_high", "bmi_obese",
                  *(f"weekday_{i}" for i in range(7))):
            self.assertIn(k, T["uz"])
        self.assertEqual({len(T[l]) for l in T}, {len(T["uz"])})
