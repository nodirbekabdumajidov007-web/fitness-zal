from django.test import Client, TestCase
from django.urls import reverse

from .models import Category, Favorite, Product, User


class FavoriteTests(TestCase):
    def setUp(self):
        cat = Category.objects.create(name="Test", order=1)
        self.p = Product.objects.create(name="Whey", price=100000, stock=5, category=cat)
        self.p2 = Product.objects.create(name="Hidden", price=1000, stock=5, category=cat, active=False)
        self.u = User.objects.create_user(username="fav1", password="x")
        self.c = Client()
        self.c.force_login(self.u)

    def toggle(self, pk, **kw):
        return self.c.post(reverse("favorite_toggle", args=[pk]), HTTP_X_REQUESTED_WITH="fetch", **kw)

    def test_toggle_adds_then_removes(self):
        r = self.toggle(self.p.pk).json()
        self.assertTrue(r["ok"] and r["on"] and r["count"] == 1)
        self.assertEqual(Favorite.objects.filter(user=self.u).count(), 1)
        r = self.toggle(self.p.pk).json()
        self.assertFalse(r["on"])
        self.assertEqual(Favorite.objects.count(), 0)

    def test_guests_are_sent_to_login_and_nothing_is_saved(self):
        r = Client().post(reverse("favorite_toggle", args=[self.p.pk]))
        self.assertEqual(r.status_code, 302)
        self.assertIn("/login/", r["Location"])
        self.assertEqual(Favorite.objects.count(), 0)

    def test_inactive_product_cannot_be_favourited(self):
        self.assertEqual(self.toggle(self.p2.pk).status_code, 404)

    def test_get_is_not_allowed(self):
        self.assertEqual(self.c.get(reverse("favorite_toggle", args=[self.p.pk])).status_code, 405)

    def test_redirect_only_to_own_host(self):
        r = self.c.post(reverse("favorite_toggle", args=[self.p.pk]), {"next": "https://evil.example/x"})
        self.assertEqual(r.status_code, 302)
        self.assertNotIn("evil", r["Location"])
        r = self.c.post(reverse("favorite_toggle", args=[self.p.pk]), {"next": "/shop/?cat=1"})
        self.assertEqual(r["Location"], "/shop/?cat=1")

    def test_pages_show_the_heart_and_the_list(self):
        shop = self.c.get(reverse("shop"))
        self.assertContains(shop, "fav-form")
        self.assertContains(self.c.get(reverse("favorites")), "Whey", count=0)  # nothing yet
        self.toggle(self.p.pk)
        page = self.c.get(reverse("favorites"))
        self.assertContains(page, "Whey")
        self.assertContains(self.c.get(reverse("shop")), 'aria-pressed="true"')

    def test_favourites_are_private(self):
        self.toggle(self.p.pk)
        other = Client()
        other.force_login(User.objects.create_user(username="fav2", password="x"))
        self.assertNotContains(other.get(reverse("favorites")), "Whey")
        self.assertEqual(Client().get(reverse("favorites")).status_code, 302)
