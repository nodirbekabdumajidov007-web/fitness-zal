import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from .models import GymPhoto, GymSettings

PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 64


class AboutPageTests(TestCase):
    def setUp(self):  # uploads go to a throw-away folder, never into the real media directory
        self._tmp = tempfile.mkdtemp()
        self._ov = override_settings(MEDIA_ROOT=self._tmp)
        self._ov.enable()
        self.addCleanup(self._ov.disable)
        self.addCleanup(shutil.rmtree, self._tmp, True)

    def photo(self, **kw):
        return GymPhoto.objects.create(image=SimpleUploadedFile("z.png", PNG, content_type="image/png"), **kw)

    def test_empty_gym_shows_a_friendly_note_not_an_error(self):
        r = Client().get(reverse("about"))
        self.assertContains(r, "tez orada")
        self.assertNotContains(r, "gal-item")

    def test_text_photos_and_where_to_find(self):
        GymSettings.load()
        GymSettings.objects.filter(pk=1).update(about_text="Birinchi abzas.\n\nIkkinchi abzas.", address="Toshkent, Test ko'cha 1")
        self.photo(caption="Asosiy zal", order=1)
        hidden = self.photo(caption="Yashirin", active=False)
        r = Client().get(reverse("about"))
        self.assertContains(r, "Birinchi abzas.")
        self.assertContains(r, "Ikkinchi abzas.")
        self.assertContains(r, "Asosiy zal")
        self.assertNotContains(r, hidden.caption)
        self.assertContains(r, "Test ko&#x27;cha 1")

    def test_about_text_is_escaped(self):
        GymSettings.load()
        GymSettings.objects.filter(pk=1).update(about_text="<script>alert(1)</script>")
        self.assertNotContains(Client().get(reverse("about")), "<script>alert(1)</script>")

    def test_home_shows_a_photo_strip_only_when_there_are_photos(self):
        self.assertNotContains(Client().get("/"), "gal-strip")
        self.photo(caption="Zal")
        r = Client().get("/")
        self.assertContains(r, "gal-strip")
        self.assertContains(r, reverse("about"))

    def test_nav_links_to_the_page(self):
        r = Client().get("/")
        self.assertContains(r, 'href="%s"' % reverse("about"))

    def test_gallery_images_are_served_through_the_image_view(self):
        p = self.photo(caption="Zal")
        self.assertTrue(p.src.startswith(f"/img/gym/{p.pk}/"))
        r = Client().get(p.src)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r["Content-Type"], "image/png")
        self.assertContains(Client().get(reverse("about")), p.src)
