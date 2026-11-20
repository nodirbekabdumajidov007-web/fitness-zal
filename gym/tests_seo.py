import json
import re

from django.test import Client, TestCase

from .models import Category, GymSettings, Product


class SeoTests(TestCase):
    def test_robots_hides_private_pages_and_points_to_the_sitemap(self):
        r = Client().get("/robots.txt")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r["Content-Type"], "text/plain; charset=utf-8")
        body = r.content.decode()
        for p in ("/django-admin/", "/dashboard/", "/cart/", "/login/"):
            self.assertIn(f"Disallow: {p}", body)
        self.assertIn("Sitemap: http://testserver/sitemap.xml", body)

    def test_sitemap_lists_public_pages_and_active_products_only(self):
        cat = Category.objects.create(name="T", order=1)
        on = Product.objects.create(name="On", price=1, stock=1, category=cat)
        off = Product.objects.create(name="Off", price=1, stock=1, category=cat, active=False)
        r = Client().get("/sitemap.xml")
        self.assertEqual(r["Content-Type"], "application/xml; charset=utf-8")
        body = r.content.decode()
        for p in ("/", "/about/", "/plans/", "/shop/"):
            self.assertIn(f"<loc>http://testserver{p}</loc>", body)
        self.assertIn(f"/shop/{on.pk}/", body)
        self.assertNotIn(f"/shop/{off.pk}/", body)
        self.assertNotIn("/dashboard/", body)

    def test_every_page_has_description_canonical_and_share_tags(self):
        h = Client().get("/plans/").content.decode()
        self.assertIn('<meta name="description"', h)
        self.assertIn('<link rel="canonical" href="http://testserver/plans/">', h)
        self.assertIn('property="og:image" content="http://testserver/static/img/og-share.png', h)
        self.assertIn('name="twitter:card" content="summary_large_image"', h)

    def test_home_has_valid_structured_data_with_only_entered_facts(self):
        GymSettings.load()
        GymSettings.objects.filter(pk=1).update(address="Toshkent, Test 1", map_lat="41.293341", map_lng="69.222725")
        h = Client().get("/").content.decode()
        m = re.search(r'<script type="application/ld\+json">(.*?)</script>', h, re.S)
        data = json.loads(m.group(1))
        self.assertEqual(data["@type"], "HealthClub")
        self.assertEqual(data["address"]["streetAddress"], "Toshkent, Test 1")
        self.assertAlmostEqual(data["geo"]["latitude"], 41.293341)
        self.assertEqual(data["openingHoursSpecification"][0]["opens"], "06:00")

    def test_structured_data_has_no_address_when_none_is_set(self):
        GymSettings.load()
        GymSettings.objects.filter(pk=1).update(address="")
        data = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', Client().get("/").content.decode(), re.S).group(1))
        self.assertNotIn("address", data)

    def test_script_breaking_text_cannot_escape_the_json(self):
        GymSettings.load()
        GymSettings.objects.filter(pk=1).update(address="</script><b>x")
        h = Client().get("/").content.decode()
        m = re.search(r'<script type="application/ld\+json">(.*?)</script>', h, re.S)
        self.assertNotIn("<b>", m.group(1))


class ErrorPageTests(TestCase):
    def test_404_is_the_sites_own_page_not_djangos_bare_one(self):
        r = Client().get("/no-such-page-here/")
        self.assertEqual(r.status_code, 404)
        h = r.content.decode()
        self.assertIn("err-page", h)
        self.assertIn("Fitnes Zal", h)
        self.assertNotIn("The requested resource was not found", h)

    def test_500_and_400_pages_stand_alone(self):
        from django.template.loader import render_to_string
        for code in ("500", "400"):
            h = render_to_string(f"{code}.html")
            self.assertIn(code, h)
            self.assertNotIn("{%", h)

    def test_skip_link_points_at_the_main_area(self):
        h = Client().get("/").content.decode()
        self.assertIn('class="skip-link" href="#main"', h)
        self.assertIn('id="main"', h)
