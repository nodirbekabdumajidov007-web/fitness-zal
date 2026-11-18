from django.test import Client, TestCase
from django.urls import reverse

from .models import Payment, Plan, User


class PaymentHistoryTests(TestCase):
    def setUp(self):
        self.u = User.objects.create_user(username="ph1", password="x")
        self.plan = Plan.objects.create(code="ph_m", name="Oylik", price=400000, days=30)
        Payment.objects.create(user=self.u, kind="plan", plan=self.plan, amount=400000, discount=40000, promo="YANGI10", method="cash", status="paid")
        Payment.objects.create(user=self.u, kind="plan", plan=self.plan, amount=50000, method="card", status="pending")
        Payment.objects.create(user=self.u, kind="plan", plan=self.plan, amount=999, method="cash", status="cancelled")
        self.c = Client()
        self.c.force_login(self.u)

    def test_summary_counts_only_paid(self):
        r = self.c.get(reverse("payments"))
        self.assertEqual(r.context["total"], 400000)
        self.assertEqual(r.context["paid_n"], 1)
        self.assertEqual(r.context["saved"], 40000)
        self.assertEqual(len(r.context["payments"]), 3)

    def test_status_filter(self):
        r = self.c.get(reverse("payments"), {"status": "pending"})
        self.assertEqual([p.amount for p in r.context["payments"]], [50000])
        self.assertEqual(len(self.c.get(reverse("payments"), {"status": "nonsense"}).context["payments"]), 3)

    def test_csv_export_is_own_and_safe(self):
        other = User.objects.create_user(username="ph2", password="x")
        Payment.objects.create(user=other, kind="plan", plan=self.plan, amount=777, method="cash", status="paid")
        Payment.objects.create(user=self.u, kind="plan", plan=self.plan, amount=1, promo="=HYPERLINK(1)", method="cash", status="paid")
        r = self.c.get(reverse("payments"), {"export": "csv"})
        self.assertEqual(r["Content-Type"], "text/csv; charset=utf-8")
        body = r.content.decode("utf-8-sig")
        self.assertIn("400000", body)
        self.assertNotIn("777", body)
        self.assertIn("'=HYPERLINK(1)", body)
        self.assertNotIn(",=HYPERLINK", body)

    def test_guest_is_sent_to_login(self):
        self.assertEqual(Client().get(reverse("payments")).status_code, 302)
        self.assertEqual(Client().get(reverse("payments"), {"export": "csv"}).status_code, 302)

    def test_page_renders_in_every_language(self):
        for lg in ("uz", "ru", "en", "tr", "ky", "tg"):
            self.c.cookies["fz_lang"] = lg
            self.assertContains(self.c.get(reverse("payments")), "400", status_code=200)
