from datetime import timedelta
from unittest import mock

from django.core.cache import cache
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from . import route
from .models import GymSettings, Order, User

GYM = (41.293341, 69.222725)
HOME = (41.31, 69.28)


def staff_client():
    u = User.objects.create_user(username="trk_staff", password="x", is_staff=True)
    c = Client()
    c.force_login(u)
    s = c.session
    s["admin_mode"] = True
    s.save()
    return c


class RouteTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_falls_back_to_a_straight_line(self):
        with mock.patch("gym.route.urllib.request.urlopen", side_effect=OSError("down")):
            r = route.road(GYM, HOME)
        self.assertEqual(r["source"], "line")
        self.assertEqual(len(r["coords"]), 2)
        self.assertGreater(r["km"], 0)

    def test_road_answer_is_parsed_and_cached(self):
        body = b'{"routes":[{"distance":6200,"duration":780,"geometry":{"coordinates":[[69.22,41.29],[69.25,41.30],[69.28,41.31]]}}]}'
        fake = mock.MagicMock()
        fake.__enter__.return_value.read.return_value = body
        with mock.patch("gym.route.urllib.request.urlopen", return_value=fake) as op:
            a = route.road(GYM, HOME)
            b = route.road(GYM, HOME)
        self.assertEqual((a["source"], a["km"], a["min"]), ("road", 6.2, 13))
        self.assertEqual(a["coords"][0], [41.29, 69.22])  # GeoJSON [lng, lat] turned into [lat, lng]
        self.assertEqual(b, a)
        self.assertEqual(op.call_count, 1)

    def test_far_points_are_not_sent_out(self):
        with mock.patch("gym.route.urllib.request.urlopen") as op:
            r = route.road(GYM, (42.45, 59.61))  # Nukus
        op.assert_not_called()
        self.assertEqual(r["source"], "line")


class TrackingTests(TestCase):
    def setUp(self):
        cache.clear()
        GymSettings.load()
        GymSettings.objects.filter(pk=1).update(delivery_lat=GYM[0], delivery_lng=GYM[1])
        self.u = User.objects.create_user(username="trk1", password="x")
        self.o = Order.objects.create(user=self.u, total=50000, method="cash", delivery="courier", address="Chilonzor",
                                      delivery_lat=HOME[0], delivery_lng=HOME[1])
        self.c = Client()
        self.c.force_login(self.u)

    def test_route_endpoint(self):
        with mock.patch("gym.route.urllib.request.urlopen", side_effect=OSError):
            r = self.c.get(reverse("delivery_route"), {"lat": HOME[0], "lng": HOME[1]}).json()
        self.assertTrue(r["ok"])
        self.assertEqual(r["gym"], list(GYM))
        self.assertEqual(self.c.get(reverse("delivery_route"), {"lat": 10, "lng": 10}).status_code, 400)  # outside Uzbekistan

    def test_courier_ping_is_staff_only_and_moves_the_order(self):
        url = reverse("courier_ping", args=[self.o.pk])
        self.assertIn(self.c.post(url, {"lat": 41.3, "lng": 69.25}).status_code, (302, 404))  # a member is turned away
        sc = staff_client()
        self.assertEqual(sc.post(url, {"lat": "abc", "lng": "1"}).status_code, 400)
        self.assertEqual(sc.post(url, {"lat": 41.3, "lng": 69.25}).json(), {"ok": True})
        self.o.refresh_from_db()
        self.assertEqual((self.o.courier_lat, self.o.status), (41.3, "shipping"))

    def test_owner_sees_the_courier_only_while_on_the_way(self):
        url = reverse("order_track", args=[self.o.pk])
        self.assertIsNone(self.c.get(url).json()["courier"])
        Order.objects.filter(pk=self.o.pk).update(status="shipping", courier_lat=41.3, courier_lng=69.25, courier_at=timezone.now())
        d = self.c.get(url).json()
        self.assertEqual(d["courier"]["lat"], 41.3)
        self.assertGreaterEqual(d["eta_min"], 1)
        Order.objects.filter(pk=self.o.pk).update(courier_at=timezone.now() - timedelta(minutes=30))
        self.assertIsNone(self.c.get(url).json()["courier"])  # stale position: offline
        Order.objects.filter(pk=self.o.pk).update(courier_at=timezone.now(), status="done")
        self.assertIsNone(self.c.get(url).json()["courier"])  # delivered: nothing is shown any more

    def test_other_members_cannot_track_it(self):
        other = Client()
        other.force_login(User.objects.create_user(username="trk2", password="x"))
        self.assertEqual(other.get(reverse("order_track", args=[self.o.pk])).status_code, 404)
        self.assertEqual(Client().get(reverse("order_track", args=[self.o.pk])).status_code, 302)

    def test_pages_render(self):
        self.assertContains(self.c.get(reverse("orders")), "data-track")
        sc = staff_client()
        r = sc.get(reverse("courier", args=[self.o.pk]))
        self.assertContains(r, "courier-map")
        self.assertIn(self.c.get(reverse("courier", args=[self.o.pk])).status_code, (302, 404))
