"""Delivery by distance across Uzbekistan (gym/geo.py): where is the customer, how far, what does it cost, when does it arrive;
the quote API, the checkout that stores the place, the order page and the admin."""
from datetime import datetime

from django.test import Client
from django.test import TestCase
from django.utils import timezone

from . import geo
from .models import GymSettings, Order, Payment, Product
from .tests_delivery import Base

TASHKENT = (41.2995, 69.2401)     # a street in Tashkent
CHILONZOR = (41.2750, 69.2040)
SAMARKAND = (39.6542, 66.9597)
NUKUS = (42.4531, 59.6103)
MOSCOW = (55.7558, 37.6173)
ALMATY = (43.2389, 76.8897)


def gym(**kw):
    """The gym starts from Tashkent unless told otherwise; the free thresholds are off so prices are easy to compare."""
    GymSettings.load()  # make sure the row exists before it is updated
    GymSettings.objects.filter(pk=1).update(**{"delivery_origin": "tashkent", "free_delivery_from": 0, "free_region_from": 0, **kw})
    return GymSettings.load()


class GeoMathTests(TestCase):
    def test_distance_between_known_cities(self):
        d = geo.haversine_km(geo.place_point("tashkent"), geo.place_point("samarqand"))
        self.assertAlmostEqual(d, 268, delta=8)
        self.assertEqual(geo.haversine_km(TASHKENT, TASHKENT), 0)

    def test_nearest_place(self):
        self.assertEqual(geo.nearest_place(*TASHKENT)[0], "tashkent")
        self.assertEqual(geo.nearest_place(39.70, 66.90)[0], "samarqand")
        self.assertEqual(geo.nearest_place(*NUKUS)[0], "nukus")

    def test_only_uzbekistan(self):
        gs = gym()
        for pt in (MOSCOW, ALMATY, (0, 0)):
            q = geo.quote(gs, *pt, 100000)
            self.assertFalse(q["ok"], pt)
            self.assertEqual(q["error"], "err_geo_out")
        self.assertTrue(geo.quote(gs, *SAMARKAND, 100000)["ok"])

    def test_garbage_positions_are_refused(self):
        gs = gym()
        for bad in (("abc", "1"), (None, None), ("nan", "nan"), ("91", "0"), ("41.3", "inf")):
            self.assertFalse(geo.quote(gs, *bad, 1000)["ok"], bad)

    def test_place_names_follow_the_language(self):
        self.assertEqual(geo.place_name("samarqand", "uz"), "Samarqand")
        self.assertEqual(geo.place_name("samarqand", "ru"), "Самарканд")
        self.assertEqual(geo.place_name("samarqand", "en"), "Samarkand")
        self.assertEqual(geo.place_name("samarqand", "tr"), "Samarkand")  # Turkish -> English
        self.assertEqual(geo.place_name("samarqand", "ky"), "Самарканд")  # Kyrgyz -> Russian
        self.assertEqual(geo.place_name("nope"), "")
        self.assertEqual(len(geo.place_choices("ru")), len(geo.PLACES))


class QuoteTests(TestCase):
    def test_without_a_starting_point_the_flat_fee_stays(self):
        GymSettings.objects.filter(pk=1).update(delivery_origin="", map_lat=None, map_lng=None, free_delivery_from=0)
        gs = GymSettings.load()
        q = geo.quote(gs, *SAMARKAND, 50000)
        self.assertTrue(q["ok"])
        self.assertFalse(q["priced"])
        self.assertEqual(q["fee"], gs.delivery_fee)
        self.assertIsNone(q["eta"])

    def test_city_courier_price_and_minutes(self):
        gs = gym()
        q = geo.quote(gs, *CHILONZOR, 100000)
        self.assertEqual(q["mode"], "city")
        self.assertLess(q["km"], gs.delivery_city_km)
        self.assertEqual(q["fee"], geo.city_fee(gs, q["km"]))
        self.assertGreaterEqual(q["fee"], gs.delivery_fee)
        self.assertEqual(q["eta"]["kind"], "minutes")
        self.assertEqual(q["eta"]["b"] - q["eta"]["a"], 15)
        self.assertGreaterEqual(q["eta"]["a"], gs.delivery_prep_min)

    def test_region_is_priced_in_days(self):
        gs = gym()
        sam, nuk = geo.quote(gs, *SAMARKAND, 100000), geo.quote(gs, *NUKUS, 100000)
        for q in (sam, nuk):
            self.assertEqual(q["mode"], "region")
            self.assertEqual(q["eta"]["kind"], "days")
            self.assertEqual(q["eta"]["b"], q["eta"]["a"] + 1)
        self.assertEqual(sam["eta"]["a"], 1)           # ~350 km of road: the next day
        self.assertEqual(nuk["eta"]["a"], 3)           # ~1400 km: three days on the road
        self.assertGreater(nuk["fee"], sam["fee"])
        self.assertGreater(sam["fee"], geo.city_fee(gs, gs.delivery_city_km))  # never cheaper than the edge of the city zone

    def test_a_farther_place_is_never_cheaper(self):
        gs = gym()
        rows = sorted(((geo.quote(gs, *geo.place_point(k), 100000), k) for k in geo.PLACES), key=lambda r: r[0]["km"])
        fees = [q["fee"] for q, _k in rows]
        self.assertEqual(fees, sorted(fees))
        self.assertGreater(fees[-1], fees[0])

    def test_free_delivery_and_the_amount_still_missing(self):
        gs = gym(free_delivery_from=200000)
        short = geo.quote(gs, *CHILONZOR, 150000)
        self.assertFalse(short["free"])
        self.assertEqual(short["left_for_free"], 50000)
        enough = geo.quote(gs, *CHILONZOR, 200000)
        self.assertTrue(enough["free"])
        self.assertEqual((enough["fee"], enough["left_for_free"]), (0, 0))
        far = geo.quote(gs, *SAMARKAND, 900000)
        self.assertFalse(far["free"])  # the city threshold does not apply to intercity delivery
        gs = gym(free_region_from=900000)
        self.assertTrue(geo.quote(gs, *SAMARKAND, 900000)["free"])

    def test_intercity_can_be_switched_off(self):
        gs = gym(region_delivery_on=False)
        q = geo.quote(gs, *SAMARKAND, 100000)
        self.assertEqual((q["ok"], q["error"]), (False, "err_geo_far"))
        self.assertTrue(geo.quote(gs, *CHILONZOR, 100000)["ok"])

    def test_gym_coordinates_win_over_the_chosen_city(self):
        gs = gym(map_lat="39.654200", map_lng="66.959700")  # the gym is in Samarkand
        self.assertEqual(geo.quote(gs, *SAMARKAND, 1000)["km"], 0)
        self.assertEqual(geo.quote(gs, *SAMARKAND, 1000)["mode"], "city")
        self.assertEqual(geo.quote(gs, *TASHKENT, 1000)["mode"], "region")

    def test_closed_gym_delays_the_courier_and_intercity_by_a_day(self):
        gs = gym()
        night = timezone.make_aware(datetime(2026, 11, 17, 3, 0))
        noon = timezone.make_aware(datetime(2026, 11, 17, 12, 0))
        late = timezone.make_aware(datetime(2026, 11, 17, 22, 50))  # too late to finish before closing
        self.assertTrue(geo.quote(gs, *CHILONZOR, 1000, now=night)["eta"]["delayed"])
        self.assertTrue(geo.quote(gs, *CHILONZOR, 1000, now=late)["eta"]["delayed"])
        self.assertFalse(geo.quote(gs, *CHILONZOR, 1000, now=noon)["eta"]["delayed"])
        start, delayed = geo.dispatch_time(gs, night)
        self.assertEqual((start.hour, start.minute, delayed), (6, 0, True))
        start, delayed = geo.dispatch_time(gs, late)
        self.assertEqual((start.day, start.hour, delayed), (18, 6, True))
        self.assertEqual(geo.quote(gs, *SAMARKAND, 1000, now=noon)["eta"]["a"], 1)
        self.assertEqual(geo.quote(gs, *SAMARKAND, 1000, now=night)["eta"]["a"], 2)


class CheckoutGeoTests(Base):
    def order_for(self, **post):
        data = {"method": "cash", "delivery": "courier", "address": "Chilonzor 5-kvartal, 12-uy", "delivery_phone": "93 555 44 33", **post}
        return self.c.post("/checkout/", data)

    def test_position_sets_price_distance_and_time_on_the_order(self):
        gs = gym()
        self.add(1)
        self.order_for(geo_lat=str(SAMARKAND[0]), geo_lng=str(SAMARKAND[1]))
        o = Order.objects.get(user=self.m)
        q = geo.quote(gs, *SAMARKAND, self.p.price)
        self.assertEqual(o.delivery_fee, q["fee"])
        self.assertEqual(o.total, self.p.price + q["fee"])
        self.assertEqual((o.delivery_place, o.delivery_region), ("samarqand", True))
        self.assertEqual(float(o.delivery_km), q["km"])
        self.assertIsNotNone(o.delivery_eta_from)
        self.assertLess(o.delivery_eta_from, o.delivery_eta_to)
        self.assertEqual(Payment.objects.get(order=o).amount, o.total)
        self.assertIn("yandex.uz/maps/?pt=", o.map_links["yandex"])

    def test_a_chosen_city_works_without_gps(self):
        gym()
        self.add(1)
        self.order_for(geo_place="nukus")
        o = Order.objects.get(user=self.m)
        self.assertEqual(o.delivery_place, "nukus")
        self.assertTrue(o.delivery_region)
        self.assertGreater(o.delivery_fee, 0)

    def test_the_browser_cannot_name_its_own_price(self):
        gym()
        self.add(1)
        self.order_for(geo_lat=str(SAMARKAND[0]), geo_lng=str(SAMARKAND[1]), delivery_fee="0", fee="0", total="1")
        o = Order.objects.get(user=self.m)
        self.assertGreater(o.delivery_fee, 0)
        self.assertEqual(o.total, self.p.price + o.delivery_fee)

    def test_position_is_required_when_the_price_depends_on_it(self):
        gym()
        self.add(1)
        self.order_for()
        self.assertFalse(Order.objects.exists())
        self.assertEqual(Product.objects.get(pk=self.p.pk).stock, self.p.stock)

    def test_outside_uzbekistan_is_refused_and_stock_untouched(self):
        gym()
        self.add(1)
        self.order_for(geo_lat=str(MOSCOW[0]), geo_lng=str(MOSCOW[1]))
        self.assertFalse(Order.objects.exists())
        self.assertEqual(Product.objects.get(pk=self.p.pk).stock, self.p.stock)

    def test_without_a_starting_point_the_old_flat_fee_still_works(self):
        GymSettings.objects.filter(pk=1).update(delivery_origin="", map_lat=None, map_lng=None, free_delivery_from=0)
        self.add(1)
        self.order_for(geo_lat=str(SAMARKAND[0]), geo_lng=str(SAMARKAND[1]))
        o = Order.objects.get(user=self.m)
        self.assertEqual(o.delivery_fee, GymSettings.load().delivery_fee)
        self.assertEqual(o.delivery_place, "samarqand")  # the place is still kept for the courier
        self.assertIsNone(o.delivery_eta_from)

    def test_pickup_ignores_any_position(self):
        gym()
        self.add(1)
        self.c.post("/checkout/", {"method": "cash", "delivery": "pickup", "geo_lat": "41.3", "geo_lng": "69.2"})
        o = Order.objects.get(user=self.m)
        self.assertEqual((o.delivery, o.delivery_fee, o.delivery_lat), ("pickup", 0, None))

    def test_failed_order_gives_back_the_stock_of_earlier_items(self):
        a, b = Product.objects.filter(active=True, stock__gte=5).order_by("id")[:2]
        self.add(1, a)
        self.add(1, b)
        Product.objects.filter(pk=b.pk).update(stock=0)  # sold out between "add to cart" and "pay"
        self.c.post("/checkout/", {"method": "cash", "delivery": "pickup"})
        self.assertFalse(Order.objects.exists())
        self.assertEqual(Product.objects.get(pk=a.pk).stock, a.stock)  # was 1 lower before the fix: stock leaked

    def test_order_page_shows_the_window_the_distance_and_the_map(self):
        gym()
        self.add(1)
        self.order_for(geo_lat=str(SAMARKAND[0]), geo_lng=str(SAMARKAND[1]))
        page = self.c.get("/orders/").content.decode()
        self.assertIn("ord-eta", page)
        self.assertIn("Samarqand", page)
        self.assertIn("yandex.uz/maps/?pt=", page)
        self.assertIn("tel:+998", page)

    def test_staff_see_the_distance_and_a_map_link(self):
        gym()
        self.add(1)
        self.order_for(geo_lat=str(SAMARKAND[0]), geo_lng=str(SAMARKAND[1]))
        o = Order.objects.get(user=self.m)
        staff = Client()
        staff.post("/login/", {"login": "admin1", "password": "AdminPass1.admin"})
        self.assertContains(staff.get("/django-admin/desk/"), "Samarqand")
        self.assertContains(staff.get(f"/django-admin/gym/order/{o.pk}/change/"), "yandex.uz/maps/?pt=")


class QuoteApiTests(Base):
    def test_quote_for_a_city_and_for_a_position(self):
        gym()
        self.add(1)
        r = self.c.get("/delivery/quote/", {"place": "samarqand"}).json()
        self.assertTrue(r["ok"])
        self.assertEqual((r["place"], r["mode"], r["eta"]["kind"]), ("Samarqand", "region", "days"))
        self.assertEqual(r["total"], self.p.price + r["fee"])
        self.assertIn("yandex.uz/maps/?pt=", r["map"])
        r = self.c.get("/delivery/quote/", {"lat": CHILONZOR[0], "lng": CHILONZOR[1]}).json()
        self.assertEqual((r["ok"], r["mode"], r["eta"]["kind"]), (True, "city", "minutes"))

    def test_quote_errors_are_translated_and_nothing_is_stored(self):
        gym()
        self.add(1)
        r = self.c.get("/delivery/quote/", {"lat": MOSCOW[0], "lng": MOSCOW[1]}).json()
        self.assertFalse(r["ok"])
        self.assertIn("O'zbekiston", r["error"])
        bad = self.c.get("/delivery/quote/", {"lat": "x", "lng": "y"})
        self.assertEqual(bad.status_code, 400)
        self.assertEqual(self.c.get("/delivery/quote/").status_code, 400)
        self.assertFalse(Order.objects.exists())

    def test_quote_follows_the_cart_total_for_free_delivery(self):
        gym(free_delivery_from=self.p.price * 3)
        self.add(1)
        self.assertEqual(self.c.get("/delivery/quote/", {"place": "tashkent"}).json()["left"], self.p.price * 2)
        self.add(2)
        r = self.c.get("/delivery/quote/", {"place": "tashkent"}).json()
        self.assertTrue(r["free"])
        self.assertEqual(r["fee"], 0)

    def test_quote_in_another_language(self):
        gym()
        self.add(1)
        self.c.cookies["fz_lang"] = "ru"
        r = self.c.get("/delivery/quote/", {"place": "samarqand"}).json()
        self.assertEqual(r["place"], "Самарканд")

    def test_quote_is_off_when_delivery_is_off(self):
        gym(delivery_on=False)
        self.assertEqual(self.c.get("/delivery/quote/", {"place": "tashkent"}).status_code, 400)

    def test_cart_page_has_the_location_controls(self):
        gym()
        self.add(1)
        page = self.c.get("/cart/").content.decode()
        self.assertIn('id="dg-detect"', page)
        self.assertIn('data-priced="1"', page)
        self.assertIn('value="samarqand"', page)
        self.assertIn("Butun O&#x27;zbekiston", page)
        GymSettings.objects.filter(pk=1).update(delivery_origin="", map_lat=None, map_lng=None)
        self.assertNotIn('data-priced="1"', self.c.get("/cart/").content.decode())

    def test_last_place_is_offered_again(self):
        gym()
        self.add(1)
        self.c.post("/checkout/", {"method": "cash", "delivery": "courier", "address": "Registon ko'chasi, 5", "delivery_phone": "93 555 44 33",
                                   "geo_lat": str(SAMARKAND[0]), "geo_lng": str(SAMARKAND[1])})
        self.add(1)
        page = self.c.get("/cart/").content.decode()
        self.assertIn('id="dg-last"', page)
        self.assertIn("Registon", page)


class AssistantDeliveryAnswerTests(TestCase):
    def ask(self, q, lang="uz"):
        import json
        return Client().post("/assistant/ask/", data=json.dumps({"q": q, "lang": lang}), content_type="application/json").json()["answer"]

    def test_price_is_called_a_starting_price_once_it_depends_on_distance(self):
        gym()
        self.assertIn("dan (masofaga qarab)", self.ask("yetkazib berish narxi qancha?"))
        self.assertIn("depends on distance", self.ask("how much does delivery cost?", "en"))
        GymSettings.objects.filter(pk=1).update(delivery_origin="", map_lat=None, map_lng=None)
        self.assertNotIn("masofaga qarab", self.ask("yetkazib berish narxi qancha?"))
