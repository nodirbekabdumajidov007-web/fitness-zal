"""Pictures for products and trainers, product and trainer pages, and the new VIP perks: reserved class spots, a free monthly
consultation and guest passes."""
import json
import shutil
import tempfile
from datetime import timedelta

from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import Client, TestCase, override_settings
from django.utils import timezone

from . import services
from .media import validate_image
from .models import Booking, GuestPass, GymClass, Membership, Plan, Product, PTSession, Trainer, User

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
JPG = b"\xff\xd8\xff\xe0" + b"\x00" * 64
WEBP = b"RIFF\x00\x00\x00\x00WEBPVP8 " + b"\x00" * 64


class Base(TestCase):
    def setUp(self):
        cache.clear()
        call_command("setup_gym", demo=True, verbosity=0)
        self.media = tempfile.mkdtemp()
        o = override_settings(MEDIA_ROOT=self.media)
        o.enable()
        self.addCleanup(lambda: (o.disable(), shutil.rmtree(self.media, ignore_errors=True)))
        self.admin = User.objects.get(is_superuser=True)
        self.admin.set_password("AdminPass1")
        self.admin.save()

    def member(self, phone="+998901112233", first="Aziz", membership=True):
        c = Client()
        c.post("/register/", {"first_name": first, "last_name": "Karimov", "phone": phone[4:], "password": "secret12"})
        u = User.objects.get(phone=phone)
        if membership:
            now = timezone.now()
            Membership.objects.create(user=u, plan=Plan.objects.get(code="m1"), starts=now - timedelta(days=1), expires=now + timedelta(days=29))
        return c, u

    def staff(self):
        c = Client()
        c.post("/login/", {"phone": "908775505", "password": "AdminPass1.admin"})
        return c


class ImageTests(Base):
    def test_validation_reads_the_bytes_not_the_name(self):
        for name, data in (("a.png", PNG), ("a.jpg", JPG), ("a.webp", WEBP)):
            validate_image(SimpleUploadedFile(name, data))
        for name, data in (("evil.svg", b"<svg onload=alert(1)>"), ("fake.png", b"<html><script>alert(1)</script>"),
                           ("doc.pdf", b"%PDF-1.4"), ("a.png.html", PNG)):
            with self.assertRaises(ValidationError, msg=name):
                validate_image(SimpleUploadedFile(name, data))
        with override_settings(MAX_IMAGE_MB=0):
            with self.assertRaises(ValidationError):
                validate_image(SimpleUploadedFile("big.png", PNG))

    def test_uploaded_picture_is_served_safely_and_shown(self):
        p = Product.objects.get(name="Suv 0.5 l")
        self.assertEqual(p.image_src, "")
        self.assertContains(Client().get("/shop/"), "img/products/bottle")  # drawn illustration until a photo exists
        p.image.save("water.png", SimpleUploadedFile("water.png", PNG), save=True)
        r = Client().get(p.image_src)
        self.assertEqual((r.status_code, r["Content-Type"], r["X-Content-Type-Options"]), (200, "image/png", "nosniff"))
        self.assertIn("sandbox", r["Content-Security-Policy"])
        self.assertIn("max-age", r["Cache-Control"])
        self.assertEqual(b"".join(r.streaming_content), PNG)
        self.assertContains(Client().get("/shop/"), p.image_src)
        self.assertContains(Client().get(f"/shop/{p.pk}/"), p.image_src)

    def test_product_image_link(self):
        p = Product.objects.get(name="Suv 0.5 l")
        p.image_url = "https://example.com/water.jpg"
        p.full_clean()
        p.save()
        page = Client().get("/shop/").content.decode()
        self.assertIn('src="https://example.com/water.jpg"', page)
        self.assertIn('referrerpolicy="no-referrer" data-fallback="/static/img/products/bottle.svg"', page)  # no referrer, and a drawing if the link breaks
        p.image.save("w.png", SimpleUploadedFile("w.png", PNG), save=True)
        self.assertTrue(p.image_src.startswith(f"/img/product/{p.pk}/"))  # an uploaded file wins over the link
        for bad in ("http://example.com/a.jpg", "javascript:alert(1)"):
            p.image_url = bad
            with self.assertRaises(ValidationError):
                p.full_clean()

    def test_trainer_photo_and_fallbacks(self):
        tr = Trainer.objects.first()
        self.assertContains(Client().get("/trainers/"), "img/trainer.svg")
        tr.photo.save("t.jpg", SimpleUploadedFile("t.jpg", JPG), save=True)
        self.assertEqual(Client().get(tr.image_src)["Content-Type"], "image/jpeg")
        self.assertContains(Client().get("/trainers/"), tr.image_src)
        self.assertContains(Client().get("/"), tr.image_src)

    def test_bad_requests(self):
        p = Product.objects.first()
        self.assertEqual(Client().get(f"/img/product/{p.pk}/").status_code, 404)  # no picture uploaded
        self.assertEqual(Client().get(f"/img/user/{p.pk}/").status_code, 404)
        self.assertEqual(Client().get("/img/product/99999/").status_code, 404)
        p.image.save("x.png", SimpleUploadedFile("x.png", PNG), save=True)
        with open(p.image.path, "wb") as fh:
            fh.write(b"<script>alert(1)</script>")  # replaced on disk with something that is not an image
        self.assertEqual(Client().get(f"/img/product/{p.pk}/").status_code, 404)

    def test_illustration_matches_the_product(self):
        names = {"Suv 1.5 l": "bottle", "Whey protein 900 g": "tub", "Energetik ichimlik": "can", "Proteinli batonchik": "bar",
                 "Shaker": "shaker", "Protein kokteyl": "shaker", "Kreatin 300 g": "tub"}
        for name, pic in names.items():
            self.assertEqual(Product.objects.get(name=name).illustration, f"img/products/{pic}.svg", name)
        self.assertEqual(Product(name="Sochiq").illustration, "img/products/box.svg")


class ShopPageTests(Base):
    def test_product_page_badges_and_vip_price(self):
        p = Product.objects.get(name="Whey protein 900 g")
        r = Client().get(f"/shop/{p.pk}/")
        self.assertContains(r, "450 000")
        self.assertContains(r, "/vip/")  # non-VIP sees the VIP hint
        c, u = self.member()
        services.add_vip(u)
        self.assertContains(c.get(f"/shop/{p.pk}/"), "405 000")  # 10% off for VIP
        self.assertContains(c.get("/shop/"), "VIP: 405 000")
        Product.objects.filter(pk=p.pk).update(stock=3)
        self.assertContains(Client().get("/shop/"), "Kam qoldi")
        self.assertEqual(Client().get("/shop/99999/").status_code, 404)
        Product.objects.filter(pk=p.pk).update(active=False)
        self.assertEqual(Client().get(f"/shop/{p.pk}/").status_code, 404)

    def test_popular_badge_follows_sales(self):
        c, u = self.member()
        suv = Product.objects.get(name="Suv 0.5 l")
        self.assertNotContains(Client().get(f"/shop/{suv.pk}/"), "Ommabop")
        c.post(f"/cart/add/{suv.pk}/")
        c.post("/checkout/", {"method": "cash"})
        self.assertContains(Client().get(f"/shop/{suv.pk}/"), "Ommabop")


class TrainerPageTests(Base):
    def test_trainer_page(self):
        tr = GymClass.objects.first().trainer
        r = Client().get(f"/trainers/{tr.pk}/")
        self.assertContains(r, tr.name)
        self.assertContains(r, GymClass.objects.filter(trainer=tr).first().name)
        self.assertContains(r, "/login/")  # guests are asked to sign in before requesting
        c, u = self.member()
        self.assertContains(c.get(f"/trainers/{tr.pk}/"), f"/trainers/{tr.pk}/pt/")
        Trainer.objects.filter(pk=tr.pk).update(active=False)
        self.assertEqual(Client().get(f"/trainers/{tr.pk}/").status_code, 404)


class ReservedSeatsTests(Base):
    def test_vip_spots_are_held_back(self):
        cls = GymClass.objects.filter(capacity__gte=8).first()
        cls.capacity = 6
        cls.save()
        self.assertEqual(services.reserved_seats(cls), 2)
        regulars = [self.member(f"+99890000{i:04d}", f"A{i}") for i in range(5)]
        for c, u in regulars:
            c.post(f"/classes/{cls.pk}/book/")
        self.assertEqual(Booking.objects.filter(gym_class=cls).count(), 4)  # 6 seats - 2 held for VIP
        self.assertEqual(services.seats_left(cls, cls.next_date(), vip=False), 0)
        self.assertEqual(services.seats_left(cls, cls.next_date(), vip=True), 2)
        vc, vu = self.member("+998977777777", "Vip")
        services.add_vip(vu)
        self.assertContains(vc.get("/classes/"), "★ VIP")
        vc.post(f"/classes/{cls.pk}/book/")
        self.assertEqual(Booking.objects.filter(gym_class=cls).count(), 5)

    def test_small_classes_keep_at_least_half_public(self):
        cls = GymClass.objects.first()
        for cap, held in ((1, 0), (2, 1), (3, 1), (20, 2)):
            cls.capacity = cap
            self.assertEqual(services.reserved_seats(cls), held, cap)


class FreeConsultationTests(Base):
    def slot(self, days):
        return (timezone.localtime() + timedelta(days=days)).replace(hour=12, minute=0).strftime("%Y-%m-%dT%H:%M")

    def test_one_free_per_month_for_vip_only(self):
        tr = Trainer.objects.first()
        c, u = self.member()
        c.post(f"/trainers/{tr.pk}/pt/", {"starts": self.slot(2)})
        self.assertFalse(PTSession.objects.get().is_free)  # not VIP: paid as usual
        PTSession.objects.all().delete()
        services.add_vip(u)
        self.assertEqual(services.free_pt_left(u), 1)
        self.assertContains(c.get("/trainers/"), "bepul")
        c.post(f"/trainers/{tr.pk}/pt/", {"starts": self.slot(2)})
        c.post(f"/trainers/{tr.pk}/pt/", {"starts": self.slot(3)})
        self.assertEqual(list(PTSession.objects.order_by("pk").values_list("is_free", flat=True)), [True, False])
        first = PTSession.objects.order_by("pk").first()
        c.post(f"/pt/{first.pk}/cancel/")
        self.assertEqual(services.free_pt_left(u), 1)  # a cancelled free session gives the perk back
        self.assertContains(self.staff().get("/staff/"), "VIP")


class GuestPassTests(Base):
    def test_create_limits_and_page(self):
        c, u = self.member()
        self.assertEqual(c.post("/vip/guest/", {"guest_name": "Do'st", "date": timezone.localdate().isoformat()})["Location"], "/vip/#guest")
        self.assertFalse(GuestPass.objects.exists())  # not VIP
        services.add_vip(u)
        for bad in ({"guest_name": "", "date": timezone.localdate().isoformat()},
                    {"guest_name": "Do'st", "date": (timezone.localdate() - timedelta(days=1)).isoformat()},
                    {"guest_name": "Do'st", "date": (timezone.localdate() + timedelta(days=40)).isoformat()},
                    {"guest_name": "Do'st", "date": "garbage"}):
            c.post("/vip/guest/", bad)
        self.assertFalse(GuestPass.objects.exists())
        r = c.post("/vip/guest/", {"guest_name": "Sardor", "date": timezone.localdate().isoformat()})
        gp = GuestPass.objects.get()
        self.assertEqual(r["Location"], f"/vip/guest/{gp.code}/")
        page = c.get(r["Location"])
        self.assertContains(page, "<svg")
        self.assertContains(page, gp.code)
        c.post("/vip/guest/", {"guest_name": "Ikkinchi", "date": timezone.localdate().isoformat()})
        self.assertEqual(GuestPass.objects.count(), 1)  # one per month
        other, _ = self.member("+998935556677", "Bek")
        self.assertEqual(other.get(f"/vip/guest/{gp.code}/").status_code, 404)
        self.assertEqual(self.staff().get(f"/vip/guest/{gp.code}/").status_code, 200)
        self.assertContains(c.get("/vip/"), "Sardor")

    def test_desk_and_scanner(self):
        c, u = self.member()
        services.add_vip(u)
        today = timezone.localdate()
        gp, _ = services.create_guest_pass(u, "Sardor", today)
        a = self.staff()
        self.assertContains(a.get(f"/staff/?q={gp.code.lower()}"), "Sardor")
        self.assertContains(a.get("/staff/"), "Sardor")  # listed among today's guests
        scan = lambda code: a.post("/staff/scan/", json.dumps({"code": code}), content_type="application/json")
        r = scan(f"FZG:{gp.code}")
        self.assertEqual((r.status_code, r.json()["entered"]), (200, True))
        r = scan(f"FZG:{gp.code}")
        self.assertFalse(r.json()["entered"])  # works once
        self.assertEqual(scan("FZG:00000000").status_code, 404)
        self.assertEqual(c.post("/staff/scan/", json.dumps({"code": f"FZG:{gp.code}"}), content_type="application/json").status_code, 404)  # members cannot scan
        later, err = services.create_guest_pass(u, "Ertaga", today + timedelta(days=1))
        self.assertEqual((later, err), (None, "guest_limit"))  # the used pass still counts for this month

    def test_wrong_day_and_desk_button(self):
        c, u = self.member()
        services.add_vip(u)
        gp = GuestPass.objects.create(user=u, guest_name="Ertangi", date=timezone.localdate() + timedelta(days=1), code="ABCDEF12")
        gp2, err = services.use_guest_pass("abcdef12")
        self.assertEqual(err, "guest_wrong_day")
        GuestPass.objects.filter(pk=gp.pk).update(date=timezone.localdate())
        a = self.staff()
        a.post(f"/staff/guest/{gp.code}/")
        gp.refresh_from_db()
        self.assertIsNotNone(gp.used_at)
        self.assertEqual(services.use_guest_pass(gp.code)[1], "guest_used")


class VipPageTests(Base):
    def test_page_for_everyone_and_for_vip(self):
        r = Client().get("/vip/")
        for needle in ("VIP", "50 000", 'id="perks"', 'id="buy"'):
            self.assertContains(r, needle)
        self.assertNotContains(r, 'id="guest"')
        c, u = self.member()
        services.add_vip(u)
        r = c.get("/vip/")
        self.assertContains(r, 'id="guest"')
        self.assertContains(r, "1 / 1")  # guest passes and free consultations left this month
        self.assertContains(r, u.member_code)
