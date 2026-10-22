"""Card-transfer payments: the gym's card receives the money, staff confirm after seeing it in the bank app."""
from datetime import timedelta

from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import Client, TestCase, override_settings
from django.utils import timezone

from . import services
from .models import Membership, Order, Payment, PaymentCard, Product, PromoCode, User

TEST_CARD = "4111111111111111"   # a public test number that passes the Luhn check
OTHER_CARD = "5555555555554444"


class CardBase(TestCase):
    def setUp(self):
        cache.clear()
        call_command("setup_gym", demo=True, verbosity=0)
        self.admin = User.objects.get(is_superuser=True)
        self.admin.set_password("AdminPass1")
        self.admin.save()

    def card(self, number=TEST_CARD, holder="TEST OWNER", primary=True):
        return PaymentCard.objects.create(bank="Uzcard", number=number, holder=holder, is_primary=primary)

    def member(self, phone="+998901112233", first="Aziz"):
        c = Client()
        c.post("/register/", {"first_name": first, "last_name": "Karimov", "phone": phone[4:], "password": "secret12"})
        return c, User.objects.get(phone=phone)

    def staff(self):
        c = Client()
        c.post("/login/", {"phone": "908775505", "password": "AdminPass1.admin"})
        return c


class CardModelTests(CardBase):
    def test_validation_and_formatting(self):
        with self.assertRaises(ValidationError):
            PaymentCard(number="1234 5678 9012 3456", holder="X").full_clean()  # fails the Luhn check
        with self.assertRaises(ValidationError):
            PaymentCard(number="4111", holder="X").full_clean()
        c = self.card("4111 1111 1111 1111")
        self.assertEqual((c.number, c.spaced, c.last4), (TEST_CARD, "4111 1111 1111 1111", "1111"))

    def test_only_one_primary(self):
        a = self.card()
        b = self.card(OTHER_CARD, "NEW OWNER", primary=True)
        a.refresh_from_db()
        self.assertEqual((a.is_primary, b.is_primary), (False, True))
        self.assertEqual(services.current_card(), b)
        b.active = False
        b.save()
        self.assertEqual(services.current_card(), a)  # falls back to another active card


class CardPaymentFlowTests(CardBase):
    def test_no_card_means_no_card_option(self):
        c, u = self.member()
        self.assertNotIn('value="card"', c.get("/plans/").content.decode())
        r = c.post("/plans/m1/buy/", {"method": "card"})
        self.assertEqual(Payment.objects.count(), 0)
        self.assertEqual(r["Location"], "/plans/")

    def test_plan_purchase_waits_for_staff(self):
        card = self.card()
        c, u = self.member()
        self.assertIn('value="card"', c.get("/plans/").content.decode())
        r = c.post("/plans/m1/buy/", {"method": "card"})
        pay = Payment.objects.get()
        self.assertEqual(r["Location"], f"/pay/{pay.pk}/")
        self.assertEqual((pay.status, pay.method, pay.pay_card, pay.card_last4), ("pending", "card", card, "1111"))
        self.assertFalse(Membership.objects.exists())  # nothing is activated before the money is confirmed
        page = c.get(f"/pay/{pay.pk}/")
        for needle in ("4111 1111 1111 1111", "TEST OWNER", str(pay.amount), f"P{pay.pk}"):
            self.assertContains(page, needle)
        # the member reports the transfer; this still does not activate anything
        c.post(f"/pay/{pay.pk}/report/", {"sender_last4": "9999"})
        pay.refresh_from_db()
        self.assertEqual((pay.sender_last4, bool(pay.proof_at), pay.status), ("9999", True, "pending"))
        self.assertFalse(Membership.objects.exists())
        a = self.staff()
        self.assertContains(a.get("/staff/"), "9999")  # staff see the sender card and the reference
        a.post(f"/staff/confirm/{pay.pk}/")
        pay.refresh_from_db()
        self.assertEqual(pay.status, "paid")
        self.assertTrue(services.active_membership(u))
        self.assertEqual(c.get(f"/pay/{pay.pk}/")["Location"], f"/receipt/{pay.pk}/")  # paid: go to the receipt

    def test_report_validation_and_ownership(self):
        self.card()
        c, u = self.member()
        c.post("/plans/m1/buy/", {"method": "card"})
        pay = Payment.objects.get()
        for bad in ("", "12", "12345", "abcd", "12 4"):
            c.post(f"/pay/{pay.pk}/report/", {"sender_last4": bad})
        pay.refresh_from_db()
        self.assertIsNone(pay.proof_at)
        other, _ = self.member("+998935556677", "Bek")
        self.assertEqual(other.get(f"/pay/{pay.pk}/").status_code, 404)
        self.assertEqual(other.post(f"/pay/{pay.pk}/report/", {"sender_last4": "1234"}).status_code, 404)
        self.assertEqual(other.post(f"/pay/{pay.pk}/cancel/").status_code, 404)
        self.assertEqual(Client().get(f"/pay/{pay.pk}/").status_code, 302)  # sign-in required

    def test_old_payment_keeps_its_card_after_switching(self):
        old = self.card()
        c, u = self.member()
        c.post("/plans/m1/buy/", {"method": "card"})
        pay = Payment.objects.get()
        self.card(OTHER_CARD, "NEW OWNER", primary=True)
        page = c.get(f"/pay/{pay.pk}/")
        self.assertContains(page, "4111 1111 1111 1111")  # still the card it was created for
        self.assertNotContains(page, "5555 5555 5555 4444")
        c.post("/plans/m1/buy/", {"method": "card"})
        newest = Payment.objects.order_by("-pk").first()
        self.assertEqual(newest.card_last4, "4444")
        self.assertEqual(old.last4, "1111")

    def test_member_can_cancel_until_reporting(self):
        self.card()
        c, u = self.member()
        c.post("/plans/m1/buy/", {"method": "card"})
        pay = Payment.objects.get()
        c.post(f"/pay/{pay.pk}/cancel/")
        pay.refresh_from_db()
        self.assertEqual(pay.status, "cancelled")
        c.post("/plans/m1/buy/", {"method": "card"})
        pay2 = Payment.objects.order_by("-pk").first()
        c.post(f"/pay/{pay2.pk}/report/", {"sender_last4": "4321"})
        c.post(f"/pay/{pay2.pk}/cancel/")
        pay2.refresh_from_db()
        self.assertEqual(pay2.status, "pending")  # once reported, only staff decide

    def test_promo_applies_and_is_released_on_cancel(self):
        self.card()
        c, u = self.member()
        c.post("/plans/m1/buy/", {"method": "card", "promo": "YANGI10"})
        pay = Payment.objects.get()
        self.assertEqual((pay.amount, pay.discount), (360000, 40000))
        self.assertEqual(PromoCode.objects.get(code="YANGI10").used, 1)
        services.cancel_payment(pay)
        self.assertEqual(PromoCode.objects.get(code="YANGI10").used, 0)


class CardShopTests(CardBase):
    def test_order_reserves_stock_and_reject_returns_it(self):
        self.card()
        c, u = self.member()
        suv = Product.objects.get(name="Suv 0.5 l")
        before = suv.stock
        c.post(f"/cart/add/{suv.pk}/")
        c.post(f"/cart/update/{suv.pk}/", {"qty": 4})
        r = c.post("/checkout/", {"method": "card"})
        pay = Payment.objects.get()
        self.assertEqual((r["Location"], pay.amount), (f"/pay/{pay.pk}/", 20000))
        suv.refresh_from_db()
        self.assertEqual(suv.stock, before - 4)
        a = self.staff()
        a.post(f"/staff/reject/{pay.pk}/")
        pay.refresh_from_db()
        suv.refresh_from_db()
        self.assertEqual((pay.status, suv.stock, Order.objects.get().status), ("cancelled", before, "cancelled"))
        self.assertFalse(services.confirm_payment(pay))  # a rejected payment cannot be confirmed afterwards

    def test_paid_order_still_needs_handover(self):
        self.card()
        c, u = self.member()
        suv = Product.objects.get(name="Suv 0.5 l")
        c.post(f"/cart/add/{suv.pk}/")
        c.post("/checkout/", {"method": "card"})
        pay = Payment.objects.get()
        services.confirm_payment(pay)
        self.assertEqual(Order.objects.get().status, "new")
        self.assertTrue(services.hand_over(Order.objects.get()))


class ExpiryAndSafetyTests(CardBase):
    def test_unreported_transfers_expire_reported_ones_do_not(self):
        self.card()
        c, u = self.member()
        suv = Product.objects.get(name="Suv 0.5 l")
        stock = suv.stock
        c.post("/plans/m1/buy/", {"method": "card"})
        c.post(f"/cart/add/{suv.pk}/")
        c.post("/checkout/", {"method": "card"})
        plan_pay, shop_pay = Payment.objects.order_by("pk")
        c.post(f"/pay/{plan_pay.pk}/report/", {"sender_last4": "1111"})
        Payment.objects.update(created=timezone.now() - timedelta(hours=30))
        self.assertEqual(services.expire_pending(), 1)
        plan_pay.refresh_from_db()
        shop_pay.refresh_from_db()
        self.assertEqual((plan_pay.status, shop_pay.status), ("pending", "cancelled"))
        suv.refresh_from_db()
        self.assertEqual(suv.stock, stock)  # stock released
        call_command("expire_pending", verbosity=0)

    def test_demo_payments_are_blocked_without_the_dev_flag(self):
        c, u = self.member()
        with override_settings(ALLOW_DEMO_PAYMENTS=False):
            self.assertNotIn('value="Payme"', c.get("/plans/").content.decode())
            c.post("/plans/m1/buy/", {"method": "Payme"})
            self.assertFalse(Payment.objects.exists())  # no free membership through the demo button
            self.assertFalse(Membership.objects.exists())
        with override_settings(ALLOW_DEMO_PAYMENTS=True):
            self.assertNotIn('value="Payme"', c.get("/plans/").content.decode())  # the gym switch is off by default too

    def test_admin_card_page_and_no_delete(self):
        self.card()
        a = self.staff()
        self.assertEqual(a.get("/django-admin/gym/paymentcard/").status_code, 200)
        self.assertContains(a.get("/django-admin/gym/paymentcard/add/"), "Karta raqami")
        card = PaymentCard.objects.get()
        self.assertEqual(a.get(f"/django-admin/gym/paymentcard/{card.pk}/delete/").status_code, 403)
        r = a.post("/django-admin/gym/paymentcard/add/", {"bank": "Humo", "number": "1234 5678 9012 3456", "holder": "X", "active": "on"})
        self.assertEqual(PaymentCard.objects.count(), 1)  # an invalid number is refused
        self.assertContains(r, "tekshiruv raqami")
