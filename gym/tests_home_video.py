"""Home promo video: URL parsing (YouTube variants, shorts, Instagram, mp4, junk), the click-to-load section, hiding when empty,
the admin field and the CSP allow-list (only the two new frame hosts + the YouTube thumbnail host were added)."""
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import Client, TestCase

from .models import GymSettings, User
from .promo_video import parse_promo

YT = "dQw4w9WgXcQ"


class ParseTests(TestCase):
    def test_youtube_variants(self):
        for url in (f"https://www.youtube.com/watch?v={YT}", f"https://youtube.com/watch?v={YT}&t=10s", f"https://m.youtube.com/watch?v={YT}",
                    f"https://youtu.be/{YT}", f"https://youtu.be/{YT}?si=abc", f"https://www.youtube.com/embed/{YT}", f"https://www.youtube.com/live/{YT}",
                    f"https://www.youtube-nocookie.com/embed/{YT}"):
            p = parse_promo(url)
            self.assertEqual(p["kind"], "youtube", url)
            self.assertTrue(p["src"].startswith(f"https://www.youtube-nocookie.com/embed/{YT}?"), url)  # privacy-enhanced mode
            self.assertFalse(p["vertical"], url)
            self.assertEqual(p["thumb"], f"https://i.ytimg.com/vi/{YT}/hqdefault.jpg")

    def test_youtube_shorts_is_vertical(self):
        p = parse_promo(f"https://www.youtube.com/shorts/{YT}")
        self.assertEqual(p["kind"], "youtube")
        self.assertTrue(p["vertical"])

    def test_instagram(self):
        p = parse_promo("https://www.instagram.com/reel/Cabc123_-XY/?igsh=zzz")
        self.assertEqual(p, {"kind": "instagram", "src": "https://www.instagram.com/reel/Cabc123_-XY/embed", "vertical": True, "thumb": ""})
        p = parse_promo("https://instagram.com/p/Cabc123_-XY/")
        self.assertEqual((p["src"], p["vertical"]), ("https://www.instagram.com/p/Cabc123_-XY/embed", False))
        self.assertEqual(parse_promo("https://www.instagram.com/reels/Cabc123_-XY/")["src"], "https://www.instagram.com/reel/Cabc123_-XY/embed")

    def test_direct_mp4(self):
        p = parse_promo("https://cdn.example.uz/videos/zal.mp4?v=3")
        self.assertEqual((p["kind"], p["src"]), ("file", "https://cdn.example.uz/videos/zal.mp4?v=3"))
        self.assertEqual(parse_promo("https://cdn.example.uz/a.webm")["kind"], "file")

    def test_invalid_is_hidden(self):
        for url in ("", "   ", None, "not a url", "http://youtu.be/" + YT, f"https://evil.com/watch?v={YT}", "https://www.youtube.com/watch?v=short",
                    "https://www.youtube.com/", "https://youtube.com.evil.com/watch?v=" + YT, "https://www.instagram.com/someuser/", "https://www.instagram.com/reel/",
                    "https://example.com/page.html", "javascript:alert(1)", "https://example.com/x.mp4.exe"):
            self.assertIsNone(parse_promo(url), url)


class SectionTests(TestCase):
    def setUp(self):
        cache.clear()
        call_command("setup_gym", demo=True, verbosity=0)

    def home(self):
        return Client().get("/").content.decode()

    def set(self, url="", **kw):
        GymSettings.objects.filter(pk=1).update(promo_video_url=url, **kw)

    def test_hidden_when_empty_or_invalid(self):
        for url in ("", "https://example.com/nothing"):
            self.set(url)
            html = self.home()
            self.assertNotIn("data-promo", html)
            self.assertNotIn("js/promo.js", html)

    def test_youtube_facade_loads_nothing_before_click(self):
        self.set(f"https://youtu.be/{YT}")
        html = self.home()
        self.assertIn("data-promo", html)
        self.assertIn('data-kind="youtube"', html)
        self.assertIn("js/promo.js", html)
        self.assertIn(f"https://i.ytimg.com/vi/{YT}/hqdefault.jpg", html)
        self.assertNotIn("<iframe", html)  # no third-party frame until the visitor presses play
        self.assertIn('class="promo-play"', html)

    def test_vertical_class_for_shorts_and_reels(self):
        self.set(f"https://www.youtube.com/shorts/{YT}")
        self.assertIn("promo-box tall", self.home())
        self.set("https://www.instagram.com/reel/Cabc123_-XY/")
        html = self.home()
        self.assertIn("promo-box tall", html)
        self.assertIn('data-src="https://www.instagram.com/reel/Cabc123_-XY/embed"', html)
        self.set("https://cdn.example.uz/zal.mp4")
        html = self.home()
        self.assertNotIn("promo-box tall", html)
        self.assertIn('data-kind="file"', html)

    def test_uploaded_poster_wins_over_youtube_thumb(self):
        self.set(f"https://youtu.be/{YT}", promo_video_poster="promo/cover.png")
        html = self.home()
        self.assertIn("/img/promo/1/?v=", html)
        self.assertNotIn("i.ytimg.com", html)

    def test_poster_view_404_without_file(self):
        self.assertEqual(Client().get("/img/promo/1/").status_code, 404)

    def test_js_builds_the_player_only_on_click(self):
        js = open("gym/static/js/promo.js", encoding="utf-8").read()
        for needle in ("createElement('iframe')", "createElement('video')", "node.muted = true", "playsinline", "addEventListener('click'", "indexOf('https://')"):
            self.assertIn(needle, js)

    def test_admin_field_with_help_text(self):
        admin = User.objects.get(is_superuser=True)
        admin.set_password("AdminPass1")
        admin.save()
        c = Client()
        c.post("/login/", {"login": "admin1", "password": "AdminPass1.admin"})
        html = c.get("/django-admin/gym/gymsettings/1/change/").content.decode()
        self.assertIn('name="promo_video_url"', html)
        self.assertIn('name="promo_video_poster"', html)
        self.assertIn("YouTube", html)
        f = GymSettings._meta.get_field("promo_video_url")  # a non-https link is refused by the field validator
        with self.assertRaises(ValidationError):
            f.clean("http://youtu.be/" + YT, None)


class CspTests(TestCase):
    def csp(self, path="/"):
        out = {}
        for d in Client().get(path)["Content-Security-Policy"].split(";"):
            bits = d.strip().split(" ")
            out[bits[0]] = bits[1:]
        return out

    def test_frame_src_has_only_the_expected_hosts(self):
        fs = self.csp()["frame-src"]
        self.assertEqual(set(fs), {"https://accounts.google.com", "https://appleid.apple.com", "https://www.youtube-nocookie.com", "https://www.instagram.com",
                                   "https://player.vimeo.com", "https://yandex.uz", "https://yandex.ru"})
        self.assertNotIn("*", fs)
        self.assertNotIn("https:", fs)

    def test_img_src_allows_youtube_thumbnails(self):
        self.assertIn("https://i.ytimg.com", self.csp()["img-src"])

    def test_everything_else_stays_strict(self):
        d = self.csp()
        self.assertEqual(d["default-src"], ["'self'"])
        self.assertEqual(set(d["script-src"]), {"'self'", "https://accounts.google.com", "https://appleid.cdn-apple.com"})
        self.assertEqual(d["frame-ancestors"], ["'none'"])
        self.assertEqual(d["base-uri"], ["'none'"])
        self.assertEqual(d["form-action"], ["'self'"])
