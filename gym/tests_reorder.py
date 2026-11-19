from django.test import Client, TestCase
from django.urls import reverse

from .models import Category, Order, OrderItem, Product, User


class ReorderTests(TestCase):
    def setUp(self):
        cat = Category.objects.create(name="T", order=1)
        self.a = Product.objects.create(name="A", price=1000, stock=10, category=cat)
        self.b = Product.objects.create(name="B", price=2000, stock=2, category=cat)
        self.gone = Product.objects.create(name="Gone", price=500, stock=0, category=cat)
        self.u = User.objects.create_user(username="ro1", password="x")
        self.o = Order.objects.create(user=self.u, total=1, method="cash")
        for p, q in ((self.a, 3), (self.b, 5), (self.gone, 1)):
            OrderItem.objects.create(order=self.o, product=p, name=p.name, price=p.price, qty=q)
        self.c = Client()
        self.c.force_login(self.u)

    def test_reorder_fills_the_cart_within_stock_and_skips_unavailable(self):
        r = self.c.post(reverse("order_reorder", args=[self.o.pk]))
        self.assertRedirects(r, reverse("cart"), fetch_redirect_response=False)
        cart = self.c.session["cart"]
        self.assertEqual(cart[str(self.a.pk)], 3)
        self.assertEqual(cart[str(self.b.pk)], 2)  # only 2 in stock
        self.assertNotIn(str(self.gone.pk), cart)

    def test_nothing_available_goes_back_to_orders(self):
        OrderItem.objects.filter(order=self.o).exclude(product=self.gone).delete()
        r = self.c.post(reverse("order_reorder", args=[self.o.pk]))
        self.assertRedirects(r, reverse("orders"), fetch_redirect_response=False)
        self.assertFalse(self.c.session.get("cart"))

    def test_only_the_owner_and_only_post(self):
        other = Client()
        other.force_login(User.objects.create_user(username="ro2", password="x"))
        self.assertEqual(other.post(reverse("order_reorder", args=[self.o.pk])).status_code, 404)
        self.assertEqual(self.c.get(reverse("order_reorder", args=[self.o.pk])).status_code, 405)
        self.assertEqual(Client().post(reverse("order_reorder", args=[self.o.pk])).status_code, 302)

    def test_orders_page_has_the_button(self):
        self.assertContains(self.c.get(reverse("orders")), reverse("order_reorder", args=[self.o.pk]))
