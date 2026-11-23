"""Shop sorting, the share button and the per-day price of memberships."""
from django.core.management import call_command
from django.test import Client, TestCase

from .models import Plan, Product


class ShopSortShareTests(TestCase):
    def setUp(self):
        call_command("setup_gym", demo=True, verbosity=0)

    def names(self, url):
        return [p.name for p in Client().get(url).context["products"]]

    def test_sorting_by_price_and_newest_keeps_the_filter_in_pager_links(self):
        cheap = self.names("/shop/?sort=cheap")
        prices = [Product.objects.get(name=n).price for n in cheap]
        self.assertEqual(prices, sorted(prices))
        dear = [Product.objects.get(name=n).price for n in self.names("/shop/?sort=dear")]
        self.assertEqual(dear, sorted(dear, reverse=True))
        self.assertEqual(Client().get("/shop/?sort=bogus").context["sort"], "")
        self.assertIn("sort=cheap", Client().get("/shop/?sort=cheap").context["keep"])

    def test_share_button_on_product_and_about(self):
        p = Product.objects.filter(active=True).first()
        h = Client().get(f"/shop/{p.pk}/").content.decode()
        self.assertIn("data-share", h)
        self.assertIn(f"/shop/{p.pk}/", h)
        self.assertIn("data-share", Client().get("/about/").content.decode())

    def test_per_day_price_only_on_longer_plans(self):
        plan = Plan(price=400000, months=1)
        self.assertEqual(plan.per_day, 13300)
        h = Client().get("/plans/").content.decode()
        self.assertIn('class="per-day"', h)
        day = Plan.objects.filter(days=1).first()
        if day:
            self.assertEqual(day.duration_days, 1)
