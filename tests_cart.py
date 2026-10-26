"""The shop's + / − controls (instant JSON answers) and the safe "back" redirects."""
from django.core.cache import cache
from django.core.management import call_command
from django.test import Client, TestCase

from .models import Product

FETCH = {"HTTP_X_REQUESTED_WITH": "fetch"}


class CartControlTests(TestCase):
    def setUp(self):
        cache.clear()
        call_command("setup_gym", demo=True, verbosity=0)
        self.p = Product.objects.get(name="Suv 0.5 l")
        self.c = Client()

    def test_plus_minus_and_totals(self):
        j = self.c.post(f"/cart/add/{self.p.pk}/", **FETCH).json()
        self.assertEqual((j["ok"], j["qty"], j["count"], j["total"], j["line"]), (True, 1, 1, 5000, 5000))
        j = self.c.post(f"/cart/update/{self.p.pk}/", {"qty": 3}, **FETCH).json()
        self.assertEqual((j["qty"], j["count"], j["total"]), (3, 3, 15000))
        j = self.c.post(f"/cart/update/{self.p.pk}/", {"qty": 2}, **FETCH).json()
        self.assertEqual(j["qty"], 2)
        j = self.c.post(f"/cart/update/{self.p.pk}/", {"qty": 0}, **FETCH).json()
        self.assertEqual((j["qty"], j["count"], j["total"]), (0, 0, 0))  # minus at 1 removes it

    def test_stock_limit(self):
        Product.objects.filter(pk=self.p.pk).update(stock=2)
        for _ in range(2):
            self.c.post(f"/cart/add/{self.p.pk}/", **FETCH)
        j = self.c.post(f"/cart/add/{self.p.pk}/", **FETCH).json()
        self.assertEqual((j["ok"], j["qty"], j["max"]), (False, 2, 2))
        self.assertTrue(j["error"])
        j = self.c.post(f"/cart/update/{self.p.pk}/", {"qty": 99}, **FETCH).json()
        self.assertEqual((j["ok"], j["qty"]), (False, 2))  # clamped, with a message
        Product.objects.filter(pk=self.p.pk).update(stock=0)
        self.assertFalse(self.c.post(f"/cart/add/{self.p.pk}/", **FETCH).json()["ok"])

    def test_pages_show_the_control_and_bar(self):
        page = self.c.get("/shop/").content.decode()
        self.assertIn('class="qty-ctl"', page)
        self.assertIn('id="cart-bar"', page)
        self.c.post(f"/cart/update/{self.p.pk}/", {"qty": 2})
        page = self.c.get("/shop/").content.decode()
        self.assertIn(f'data-pid="{self.p.pk}" data-qty="2"', page)  # server renders the current quantity
        self.assertIn("10 000", page)  # cart bar total
        self.assertIn(f'data-line="{self.p.pk}"', self.c.get("/cart/").content.decode())
        self.assertIn('class="qty-ctl big"', self.c.get(f"/shop/{self.p.pk}/").content.decode())

    def test_without_javascript_forms_still_work(self):
        r = self.c.post(f"/cart/add/{self.p.pk}/", {"back": "/shop/?cat=1"})
        self.assertEqual(r["Location"], "/shop/?cat=1")
        r = self.c.post(f"/cart/update/{self.p.pk}/", {"qty": 3, "back": "/shop/"})
        self.assertEqual(r["Location"], "/shop/")
        self.assertEqual(self.c.session["cart"][str(self.p.pk)], 3)

    def test_back_cannot_send_people_to_another_site(self):
        for evil in ("//evil.example/phish", "https://evil.example/", "/\\evil.example"):
            r = self.c.post(f"/cart/add/{self.p.pk}/", {"back": evil})
            self.assertEqual(r["Location"], "/shop/", evil)
            r = self.c.post(f"/cart/update/{self.p.pk}/", {"qty": 1, "back": evil})
            self.assertEqual(r["Location"], "/cart/", evil)
