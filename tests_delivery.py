"""Shop delivery (courier vs pickup), order tracking, the route button, the crowd meter, the 3D QR view and Sign in with Apple."""
import base64
import hashlib
import json
import random
import time
from datetime import timedelta
from unittest import mock

from django.core.cache import cache
from django.core.management import call_command
from django.test import Client, TestCase

from . import apple, services
from .models import GymSettings, Order, Payment, Product, User, Visit

PW = "Kuchli-Parol-77"


class Base(TestCase):
    def setUp(self):
        cache.clear()
        call_command("setup_gym", demo=True, verbosity=0)
        self.admin = User.objects.get(is_superuser=True)
        self.admin.set_password("AdminPass1")
        self.admin.save()
        self.m = User.objects.create_user(phone="+998901112233", password=PW, first_name="Aziz", last_name="Karimov")
        self.c = Client()
        self.c.post("/login/", {"phone": "901112233", "password": PW})
        self.p = Product.objects.filter(active=True, stock__gte=5).order_by("price").first()

    def add(self, qty=1, product=None):
        for _ in range(qty):
            self.c.post(f"/cart/add/{(product or self.p).pk}/")


class DeliveryTests(Base):
    def test_pickup_is_free_and_unchanged(self):
        self.add(2)
        self.c.post("/checkout/", {"method": "cash", "delivery": "pickup"})
        o = Order.objects.get(user=self.m)
        self.assertEqual((o.delivery, o.delivery_fee, o.total), ("pickup", 0, self.p.price * 2))

    def test_courier_adds_fee_and_needs_address(self):
        gs = GymSettings.load()
        self.add(1)
        r = self.c.post("/checkout/", {"method": "cash", "delivery": "courier", "address": "kalta"})
        self.assertFalse(Order.objects.exists())  # too short: nothing is placed, stock untouched
        self.assertEqual(Product.objects.get(pk=self.p.pk).stock, self.p.stock)
        self.c.post("/checkout/", {"method": "cash", "delivery": "courier", "address": "Chilonzor 5-kvartal, 12-uy", "delivery_phone": "93 555 44 33", "delivery_note": "3-qavat"})
        o = Order.objects.get(user=self.m)
        self.assertEqual(o.delivery, "courier")
        self.assertEqual(o.delivery_fee, gs.delivery_fee)
        self.assertEqual(o.total, self.p.price + gs.delivery_fee)
        self.assertEqual(o.delivery_phone, "+998935554433")
        self.assertEqual(Payment.objects.get(order=o).amount, o.total)

    def test_free_delivery_above_threshold(self):
        GymSettings.objects.filter(pk=1).update(free_delivery_from=self.p.price * 3)
        self.add(3)
        self.c.post("/checkout/", {"method": "cash", "delivery": "courier", "address": "Yunusobod 4, 17-uy"})
        self.assertEqual(Order.objects.get(user=self.m).delivery_fee, 0)
        self.add(2)  # below the threshold: the fee applies
        self.c.post("/checkout/", {"method": "cash", "delivery": "courier", "address": "Yunusobod 4, 17-uy"})
        self.assertEqual(Order.objects.filter(user=self.m).latest("id").delivery_fee, GymSettings.load().delivery_fee)

    def test_delivery_switched_off(self):
        GymSettings.objects.filter(pk=1).update(delivery_on=False)
        self.add(1)
        self.c.post("/checkout/", {"method": "cash", "delivery": "courier", "address": "Chilonzor 5-kvartal, 12-uy"})
        self.assertFalse(Order.objects.exists())
        self.assertNotContains(self.c.get("/cart/"), 'value="courier"')

    def test_ship_then_deliver_and_tracking(self):
        self.add(1)
        self.c.post("/checkout/", {"method": "cash", "delivery": "courier", "address": "Chilonzor 5-kvartal, 12-uy"})
        o = Order.objects.get(user=self.m)
        staff = Client()
        staff.post("/login/", {"phone": "908775505", "password": "AdminPass1.admin"})
        self.assertContains(staff.get("/staff/"), "Chilonzor")
        staff.post(f"/staff/ship/{o.pk}/")
        o.refresh_from_db()
        self.assertEqual(o.status, "shipping")
        self.assertIsNotNone(o.shipped_at)
        page = self.c.get("/orders/")
        self.assertContains(page, "track courier st-shipping")
        staff.post(f"/staff/handover/{o.pk}/")
        o.refresh_from_db()
        self.assertEqual(o.status, "done")
        self.assertEqual(Payment.objects.get(order=o).status, "paid")  # cash collected by the courier

    def test_pickup_order_cannot_be_shipped(self):
        self.add(1)
        self.c.post("/checkout/", {"method": "cash"})
        o = Order.objects.get(user=self.m)
        self.assertFalse(services.ship_order(o))


class RouteCrowdQrTests(Base):
    def test_route_button_needs_a_place(self):
        self.assertNotContains(Client().get("/"), "route-btn")
        GymSettings.objects.filter(pk=1).update(map_lat="41.311081", map_lng="69.240562")
        r = Client().get("/")
        self.assertContains(r, "route-btn")
        self.assertContains(r, "rtext=~41.311081,69.240562")
        self.assertContains(r, "destination=41.311081,69.240562")

    def test_crowd_meter(self):
        GymSettings.objects.filter(pk=1).update(gym_capacity=2, open_time="00:00", close_time="23:59")
        Visit.objects.create(user=self.m)
        r = Client().get("/")
        self.assertEqual(r.context["crowd"]["level"], "mid")  # 1 of 2 = 50%

    def test_card_has_3d_view_data(self):
        r = self.c.get("/card/")
        self.assertContains(r, 'id="qr3d"')
        mods = r.context["modules"].split(",")
        self.assertTrue(len(mods) >= 21 and all(len(row) == len(mods) for row in mods))


def timezone_now():
    from django.utils import timezone
    return timezone.now()


# ---- a tiny RSA signer so the Apple check can be tested end to end without any crypto package
def _prime(bits, rnd):
    while True:
        n = rnd.getrandbits(bits) | (1 << bits - 1) | 1
        if all(pow(a, n - 1, n) == 1 for a in (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37)):
            return n


def _keypair():
    rnd = random.Random(7)
    e = 65537
    while True:
        p, q = _prime(512, rnd), _prime(512, rnd)
        phi = (p - 1) * (q - 1)
        if p != q and phi % e:
            return p * q, e, pow(e, -1, phi)


N, E, D = _keypair()


def _b64(b):
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def sign(claims, kid="k1", d=D):
    head = _b64(json.dumps({"alg": "RS256", "kid": kid}).encode())
    body = _b64(json.dumps(claims).encode())
    k = (N.bit_length() + 7) // 8
    digest = apple.SHA256_PREFIX + hashlib.sha256(f"{head}.{body}".encode()).digest()
    em = b"\x00\x01" + b"\xff" * (k - len(digest) - 3) + b"\x00" + digest
    sig = pow(int.from_bytes(em, "big"), d, N).to_bytes(k, "big")
    return f"{head}.{body}.{_b64(sig)}"


KEYS = [{"kty": "RSA", "kid": "k1", "n": _b64(N.to_bytes((N.bit_length() + 7) // 8, "big")), "e": _b64(E.to_bytes(3, "big"))}]
CID = "uz.fitneszal.web"


class AppleTests(Base):
    def claims(self, **kw):
        c = {"iss": apple.ISSUER, "aud": CID, "exp": time.time() + 600, "sub": "001.abc", "email": "ali@icloud.com", "email_verified": "true"}
        c.update(kw)
        return c

    def test_verify(self):
        self.assertEqual(apple.verify(sign(self.claims()), CID, keys=KEYS)["email"], "ali@icloud.com")
        self.assertIsNone(apple.verify(sign(self.claims(aud="other")), CID, keys=KEYS))
        self.assertIsNone(apple.verify(sign(self.claims(exp=time.time() - 5)), CID, keys=KEYS))
        self.assertIsNone(apple.verify(sign(self.claims(iss="https://evil")), CID, keys=KEYS))
        tok = sign(self.claims())
        h, b, s = tok.split(".")
        forged = _b64(json.dumps(self.claims(email="boss@icloud.com")).encode())
        self.assertIsNone(apple.verify(f"{h}.{forged}.{s}", CID, keys=KEYS))  # body changed, signature no longer matches
        self.assertIsNone(apple.verify(sign(self.claims(), kid="nope"), CID, keys=KEYS))
        self.assertIsNone(apple.verify("garbage", CID, keys=KEYS))

    def test_login_endpoint(self):
        c = Client()
        post = lambda tok: c.post("/auth/apple/", json.dumps({"id_token": tok, "name": {"firstName": "Ali", "lastName": "Valiyev"}}), content_type="application/json")
        self.assertEqual(post(sign(self.claims())).status_code, 501)  # not set up yet
        GymSettings.objects.filter(pk=1).update(apple_client_id=CID)
        with mock.patch.object(apple, "_keys", return_value=KEYS):
            self.assertEqual(post(sign(self.claims(aud="x"))).status_code, 401)
            r = post(sign(self.claims()))
        self.assertTrue(r.json()["ok"])
        u = User.objects.get(email="ali@icloud.com")
        self.assertEqual((u.first_name, u.last_name), ("Ali", "Valiyev"))
        self.assertEqual(c.get("/dashboard/").status_code, 200)

    def test_buttons(self):
        r = Client().get("/login/")
        self.assertContains(r, 'id="abtn"')
        self.assertContains(r, "Apple")
        GymSettings.objects.filter(pk=1).update(apple_client_id=CID)
        self.assertContains(Client().get("/login/"), f'data-client="{CID}"')
