"""Pictures for products and trainers, product and trainer pages, and class capacity."""
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
from .models import Booking, GymClass, Membership, Plan, Product, Trainer, User

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
        c.post("/register/", {"first_name": first, "last_name": "Karimov", "phone": phone[4:], "password": "secret12", "username": "u" + "".join(ch for ch in str(phone[4:]) if ch.isdigit()), "email": "u" + "".join(ch for ch in str(phone[4:]) if ch.isdigit()) + "@test.uz", "password2": "secret12"})
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
    def test_product_page_badges_and_price(self):
        p = Product.objects.get(name="Whey protein 900 g")
        r = Client().get(f"/shop/{p.pk}/")
        self.assertContains(r, "450 000")
        self.assertNotContains(r, "/vip/")
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


class ClassCapacityTests(Base):
    def test_every_seat_is_bookable(self):
        cls = GymClass.objects.filter(capacity__gte=8).first()
        cls.capacity = 3
        cls.save()
        for i in range(4):
            c, u = self.member(f"+99890000{i:04d}", f"A{i}")
            c.post(f"/classes/{cls.pk}/book/")
        self.assertEqual(Booking.objects.filter(gym_class=cls).count(), 3)  # the whole class, nothing held back
        self.assertEqual(services.seats_left(cls, cls.next_date()), 0)
