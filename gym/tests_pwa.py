"""PWA: manifest, service worker, offline page, Android asset links, Web Push (subscribe/unsubscribe, notify hook, dead-subscription cleanup)."""
import json
import re
from io import StringIO
from unittest import mock

from django.contrib.staticfiles import finders
from django.core.management import call_command
from django.test import Client, TestCase, override_settings
from PIL import Image

from . import pwa, services
from .models import Notification, PushSubscription, User

KEYS = {"VAPID_PUBLIC_KEY": "BPublicKeyForTests", "VAPID_PRIVATE_KEY": "privateKeyForTests", "VAPID_SUBJECT": "mailto:t@example.com"}
ENDPOINT = "https://fcm.googleapis.com/fcm/send/abc123"


class GymTestCase(TestCase):
    """Pages need the gym's settings row (opening hours...), which setup_gym creates."""
    def setUp(self):
        call_command("setup_gym", demo=True, verbosity=0, stdout=StringIO())
        super().setUp()


def static_file(url):
    return finders.find(url.split("?")[0].replace("/static/", "", 1))


class ManifestTests(GymTestCase):
    def setUp(self):
        super().setUp()
        self.data = Client().get("/manifest.webmanifest").json()

    def test_fields(self):
        d = self.data
        self.assertEqual((d["id"], d["start_url"], d["scope"], d["display"], d["orientation"]), ("/", "/?source=pwa", "/", "standalone", "portrait"))
        self.assertEqual(d["display_override"], ["window-controls-overlay", "standalone"])
        self.assertEqual((d["name"], d["lang"], d["dir"]), ("Fitnes Zal", "uz", "ltr"))
        self.assertEqual(d["categories"], ["health", "fitness", "lifestyle"])
        self.assertTrue(d["short_name"] and d["description"])
        self.assertEqual((d["theme_color"], d["background_color"]), ("#101318", "#101318"))

    def test_content_type(self):
        self.assertEqual(Client().get("/manifest.webmanifest")["Content-Type"], "application/manifest+json")

    def test_icons_exist_with_declared_sizes(self):
        sizes = {i["sizes"] for i in self.data["icons"] if i["purpose"] == "any"}
        self.assertEqual(sizes, {f"{s}x{s}" for s in (48, 72, 96, 128, 144, 152, 192, 256, 384, 512)})
        purposes = {(i["sizes"], i["purpose"]) for i in self.data["icons"]}
        self.assertIn(("192x192", "maskable"), purposes)
        self.assertIn(("512x512", "maskable"), purposes)
        self.assertIn(("512x512", "monochrome"), purposes)
        for icon in self.data["icons"]:
            path = static_file(icon["src"])
            self.assertTrue(path, icon["src"])
            w, h = Image.open(path).size
            self.assertEqual(f"{w}x{h}", icon["sizes"], icon["src"])

    def test_shortcuts_and_screenshots(self):
        names = [s["name"] for s in self.data["shortcuts"]]
        self.assertEqual(names, ["Kabinet", "A'zo kartasi", "Mashg'ulotlar", "Kaloriya"])
        for s in self.data["shortcuts"]:
            self.assertTrue(s["url"].startswith("/"))
            for icon in s["icons"]:
                self.assertEqual(Image.open(static_file(icon["src"])).size, (96, 96))
        self.assertTrue(any(s["form_factor"] == "narrow" for s in self.data["screenshots"]))
        for s in self.data["screenshots"]:
            w, h = Image.open(static_file(s["src"])).size
            self.assertEqual(s["sizes"], f"{w}x{h}")

    def test_page_head_has_pwa_tags(self):
        html = Client().get("/").content.decode()
        for needle in ('rel="manifest"', 'name="apple-mobile-web-app-capable"', "black-translucent", 'media="(prefers-color-scheme: dark)"',
                       "apple-touch-icon", "favicon-32.png", "js/pwa.js"):
            self.assertIn(needle, html)
        self.assertEqual(Image.open(finders.find("img/apple-touch-icon.png")).size, (180, 180))
        self.assertEqual(Image.open(finders.find("img/favicon-32.png")).size, (32, 32))

    def test_launch_from_icon_goes_to_dashboard_when_signed_in(self):
        u = User.objects.create_user(username="pwauser", password="secret12", phone="+998901234500", first_name="A")
        c = Client()
        self.assertEqual(c.get("/?source=pwa").status_code, 200)  # guests see the home page
        c.force_login(u)
        self.assertRedirects(c.get("/?source=pwa"), "/dashboard/", fetch_redirect_response=False)


class ServiceWorkerTests(GymTestCase):
    def test_headers(self):
        r = Client().get("/sw.js")
        self.assertEqual(r.status_code, 200)
        self.assertEqual((r["Content-Type"], r["Service-Worker-Allowed"], r["Cache-Control"]), ("application/javascript", "/", "no-cache"))

    def test_version_is_stamped_and_stable(self):
        a, b = Client().get("/sw.js").content.decode(), Client().get("/sw.js").content.decode()
        self.assertNotIn("__SW_VERSION__", a)
        self.assertEqual(a, b)
        self.assertRegex(a, r"var VERSION = '[0-9a-f]{10}';")

    def test_never_caches_private_things(self):
        src = open(finders.find("js/sw.js"), encoding="utf-8").read()
        self.assertIn("req.method !== 'GET'", src)  # POSTs are never touched
        self.assertIn("X-FZ-Offline", src)  # the card is the one page it keeps, and only when the server marks it
        self.assertIn("CLEAR_PRIVATE", src)
        self.assertIn("SKIP_WAITING", src)
        self.assertNotIn("skipWaiting();\n});", src.split("self.addEventListener('install'")[1].split("self.addEventListener('activate'")[0])  # install waits for the toast

    def test_pwa_js_registers_and_handles_logout(self):
        src = open(finders.find("js/pwa.js"), encoding="utf-8").read()
        self.assertIn("register('/sw.js'", src)
        self.assertIn("beforeinstallprompt", src)
        self.assertIn("form[data-pwa-logout]", src)
        self.assertIn("navigator.onLine", src)

    def test_every_page_registers_the_worker(self):
        for url in ("/", "/plans/", "/login/", "/faq/"):
            self.assertIn("js/pwa.js", Client().get(url).content.decode(), url)


class OfflinePageTests(GymTestCase):
    def test_branded_and_three_languages(self):
        r = Client().get("/offline/")
        self.assertEqual(r.status_code, 200)
        html = r.content.decode()
        self.assertIn("<main", html)
        for text in ("Internet yo'q", "Нет интернета", "offline"):
            self.assertIn(text, html if text != "offline" else html.lower())
        self.assertIn("img/icon-192.png", html)
        self.assertNotIn("csrfmiddlewaretoken", html)  # safe to keep in a cache

    def test_start_url_is_covered(self):
        # the service worker answers every navigation with /offline/ when the network is gone, including /?source=pwa
        src = open(finders.find("js/sw.js"), encoding="utf-8").read()
        self.assertIn("caches.match('/offline/')", src)
        self.assertIn("req.mode === 'navigate'", src)


class CardOfflineTests(GymTestCase):
    def test_card_is_marked_for_the_service_worker(self):
        u = User.objects.create_user(username="cardman", password="secret12", phone="+998901234501", first_name="C")
        c = Client()
        c.force_login(u)
        r = c.get("/card/")
        self.assertEqual(r["X-FZ-Offline"], "card")
        self.assertIn("private", r["Cache-Control"])
        self.assertContains(r, "<svg")  # the QR is inline, so the cached page carries it
        self.assertContains(r, "data-pwa-logout")
        other = c.get("/dashboard/")
        self.assertNotIn("X-FZ-Offline", other)  # no other page is marked


class AssetLinksTests(TestCase):
    def test_empty_when_not_configured(self):
        with override_settings(ANDROID_PACKAGE_NAME="", ANDROID_SHA256_FINGERPRINTS=""):
            r = Client().get("/.well-known/assetlinks.json")
        self.assertEqual((r.status_code, r["Content-Type"], r.json()), (200, "application/json", []))

    def test_needs_both_values(self):
        with override_settings(ANDROID_PACKAGE_NAME="uz.fitneszal.app", ANDROID_SHA256_FINGERPRINTS=""):
            self.assertEqual(Client().get("/.well-known/assetlinks.json").json(), [])

    def test_configured(self):
        fp1, fp2 = "AA:BB:CC", "11:22:33"
        with override_settings(ANDROID_PACKAGE_NAME="uz.fitneszal.app", ANDROID_SHA256_FINGERPRINTS=f"{fp1.lower()}, {fp2}"):
            r = Client().get("/.well-known/assetlinks.json")
        self.assertEqual(r["Content-Type"], "application/json")
        d = r.json()
        self.assertEqual(len(d), 1)
        self.assertEqual(d[0]["relation"], ["delegate_permission/common.handle_all_urls"])
        self.assertEqual(d[0]["target"], {"namespace": "android_app", "package_name": "uz.fitneszal.app", "sha256_cert_fingerprints": [fp1, fp2]})


class VapidCommandTests(TestCase):
    def test_pair_is_valid(self):
        from py_vapid import Vapid
        out = StringIO()
        call_command("generate_vapid", stdout=out)
        text = out.getvalue()
        pub, priv = re.search(r"VAPID_PUBLIC_KEY=(\S+)", text).group(1), re.search(r"VAPID_PRIVATE_KEY=(\S+)", text).group(1)
        self.assertEqual(len(pub), 87)  # 65-byte uncompressed point, base64url without padding
        v = Vapid.from_string(priv)  # pywebpush accepts the private key as printed
        from .management.commands.generate_vapid import b64url
        from cryptography.hazmat.primitives import serialization
        self.assertEqual(b64url(v.public_key.public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)), pub)


@override_settings(**KEYS)
class PushEndpointTests(GymTestCase):
    def setUp(self):
        super().setUp()
        self.u = User.objects.create_user(username="pusher", password="secret12", phone="+998901234502", first_name="P")
        self.c = Client(enforce_csrf_checks=True)
        self.c.force_login(self.u)

    def post(self, url, data, client=None, token=True):
        client = client or self.c
        client.get("/account/")  # sets the CSRF cookie
        headers = {"HTTP_X_CSRFTOKEN": client.cookies["csrftoken"].value} if token else {}
        return client.post(url, json.dumps(data), content_type="application/json", **headers)

    def sub(self, endpoint=ENDPOINT):
        return {"endpoint": endpoint, "keys": {"p256dh": "p256-key", "auth": "auth-key"}}

    def test_login_and_csrf_required(self):
        anon = Client(enforce_csrf_checks=True)
        r = anon.post("/push/subscribe/", json.dumps(self.sub()), content_type="application/json")
        self.assertIn(r.status_code, (302, 403))
        self.assertEqual(PushSubscription.objects.count(), 0)
        self.assertEqual(self.post("/push/subscribe/", self.sub(), token=False).status_code, 403)

    def test_subscribe_and_update(self):
        self.assertEqual(self.post("/push/subscribe/", self.sub()).json(), {"ok": True})
        s = PushSubscription.objects.get()
        self.assertEqual((s.user, s.p256dh, s.auth), (self.u, "p256-key", "auth-key"))
        d = self.sub()
        d["keys"]["auth"] = "new-auth"
        self.post("/push/subscribe/", d)
        self.assertEqual(PushSubscription.objects.count(), 1)  # same endpoint: updated, not duplicated
        self.assertEqual(PushSubscription.objects.get().auth, "new-auth")

    def test_shared_device_changes_owner(self):
        other = User.objects.create_user(username="other1", password="secret12", phone="+998901234503", first_name="O")
        self.post("/push/subscribe/", self.sub())
        c2 = Client(enforce_csrf_checks=True)
        c2.force_login(other)
        self.post("/push/subscribe/", self.sub(), client=c2)
        self.assertEqual(PushSubscription.objects.get().user, other)

    def test_rejects_bad_input_and_foreign_hosts(self):
        for bad in ({}, {"endpoint": ENDPOINT}, {"endpoint": ENDPOINT, "keys": {"p256dh": "x"}},
                    self.sub("http://fcm.googleapis.com/x"), self.sub("https://evil.example.com/x"),
                    self.sub("https://127.0.0.1/x"), self.sub("https://fcm.googleapis.com.evil.com/x"), self.sub("https://x.googleapis.com/" + "a" * 700)):
            self.assertEqual(self.post("/push/subscribe/", bad).status_code, 400, bad)
        self.assertEqual(PushSubscription.objects.count(), 0)

    def test_per_user_cap(self):
        for i in range(pwa.MAX_SUBS_PER_USER + 3):
            self.post("/push/subscribe/", self.sub(f"https://fcm.googleapis.com/fcm/send/{i}"))
        self.assertEqual(PushSubscription.objects.filter(user=self.u).count(), pwa.MAX_SUBS_PER_USER)

    def test_unsubscribe_only_own(self):
        other = User.objects.create_user(username="other2", password="secret12", phone="+998901234504", first_name="O")
        PushSubscription.objects.create(user=other, endpoint="https://fcm.googleapis.com/fcm/send/theirs", p256dh="a", auth="b")
        self.post("/push/subscribe/", self.sub())
        self.assertEqual(self.post("/push/unsubscribe/", {"endpoint": "https://fcm.googleapis.com/fcm/send/theirs"}).json()["removed"], 0)
        self.assertEqual(self.post("/push/unsubscribe/", {"endpoint": ENDPOINT}).json()["removed"], 1)
        self.assertEqual(PushSubscription.objects.count(), 1)

    def test_off_without_vapid(self):
        with override_settings(VAPID_PUBLIC_KEY="", VAPID_PRIVATE_KEY=""):
            self.assertEqual(self.post("/push/subscribe/", self.sub()).status_code, 503)


class PushUiTests(GymTestCase):
    def setUp(self):
        super().setUp()
        self.u = User.objects.create_user(username="pushui", password="secret12", phone="+998901234505", first_name="U")
        self.c = Client()
        self.c.force_login(self.u)

    def test_account_shows_toggle_only_with_keys(self):
        with override_settings(**KEYS):
            html = self.c.get("/account/").content.decode()
        self.assertIn("data-push-btn", html)
        self.assertIn(KEYS["VAPID_PUBLIC_KEY"], html)
        self.assertNotIn(KEYS["VAPID_PRIVATE_KEY"], html)
        with override_settings(VAPID_PUBLIC_KEY="", VAPID_PRIVATE_KEY=""):
            self.assertNotIn("data-push-btn", self.c.get("/account/").content.decode())

    def test_dashboard_has_install_banner_and_sidebar_button(self):
        html = self.c.get("/dashboard/").content.decode()
        self.assertIn("data-pwa-banner", html)
        self.assertGreaterEqual(html.count("data-pwa-install-btn"), 3)  # banner, account menu, sidebar
        self.assertIn("data-pwa-ios", html)


@override_settings(**KEYS)
class PushSendTests(TestCase):
    def setUp(self):
        self.u = User.objects.create_user(username="sendme", password="secret12", phone="+998901234506", first_name="S", telegram_chat_id=None)
        PushSubscription.objects.create(user=self.u, endpoint=ENDPOINT, p256dh="p", auth="a")

    def test_notify_sends_push(self):
        with mock.patch("gym.pwa.webpush") as wp:
            sent = services.notify(self.u, "Abonement tugaydi", "3 kundan keyin", telegram_too=False)
        self.assertTrue(sent["push"] and sent["site"])
        self.assertEqual(wp.call_count, 1)
        kw = wp.call_args.kwargs
        self.assertEqual(kw["subscription_info"], {"endpoint": ENDPOINT, "keys": {"p256dh": "p", "auth": "a"}})
        self.assertEqual(kw["vapid_private_key"], KEYS["VAPID_PRIVATE_KEY"])
        self.assertEqual(kw["vapid_claims"], {"sub": KEYS["VAPID_SUBJECT"]})
        payload = json.loads(kw["data"])
        self.assertEqual((payload["title"], payload["body"], payload["url"]), ("Abonement tugaydi", "3 kundan keyin", "/inbox/"))
        self.assertTrue(payload["icon"] and payload["badge"])
        self.assertEqual(Notification.objects.filter(user=self.u).count(), 1)

    def test_push_too_false_and_no_subscriptions(self):
        with mock.patch("gym.pwa.webpush") as wp:
            services.notify(self.u, "x", push_too=False, telegram_too=False)
            other = User.objects.create_user(username="nosub", password="secret12", phone="+998901234507", first_name="N")
            sent = services.notify(other, "x", telegram_too=False)
        self.assertEqual(wp.call_count, 0)
        self.assertFalse(sent["push"])

    def test_no_keys_means_no_push(self):
        with override_settings(VAPID_PUBLIC_KEY="", VAPID_PRIVATE_KEY=""), mock.patch("gym.pwa.webpush") as wp:
            sent = services.notify(self.u, "x", telegram_too=False)
        self.assertEqual(wp.call_count, 0)
        self.assertFalse(sent["push"])
        self.assertEqual(Notification.objects.count(), 1)  # the inbox message is unaffected

    def failure(self, code):
        err = pwa.WebPushException("gone")
        err.response = mock.Mock(status_code=code)
        return err

    def test_410_and_404_delete_the_subscription(self):
        for code in (410, 404):
            PushSubscription.objects.get_or_create(endpoint=ENDPOINT, defaults={"user": self.u, "p256dh": "p", "auth": "a"})
            with mock.patch("gym.pwa.webpush", side_effect=self.failure(code)):
                sent = services.notify(self.u, "x", telegram_too=False)
            self.assertFalse(sent["push"])
            self.assertEqual(PushSubscription.objects.count(), 0, code)

    def test_other_errors_keep_the_subscription_and_never_raise(self):
        with mock.patch("gym.pwa.webpush", side_effect=self.failure(500)):
            services.notify(self.u, "x", telegram_too=False)
        with mock.patch("gym.pwa.webpush", side_effect=RuntimeError("boom")):
            services.notify(self.u, "x", telegram_too=False)
        self.assertEqual(PushSubscription.objects.count(), 1)
        self.assertEqual(Notification.objects.count(), 2)

    def test_one_dead_device_does_not_stop_the_others(self):
        PushSubscription.objects.create(user=self.u, endpoint="https://fcm.googleapis.com/fcm/send/second", p256dh="p2", auth="a2")
        calls = []

        def fake(**kw):
            calls.append(kw["subscription_info"]["endpoint"])
            if kw["subscription_info"]["endpoint"] == ENDPOINT:
                raise self.failure(410)
        with mock.patch("gym.pwa.webpush", side_effect=fake):
            sent = services.notify(self.u, "x", telegram_too=False)
        self.assertEqual(len(calls), 2)
        self.assertTrue(sent["push"])
        self.assertEqual(list(PushSubscription.objects.values_list("endpoint", flat=True)), ["https://fcm.googleapis.com/fcm/send/second"])

    def test_telegram_style_events_push_too(self):
        from . import telegram
        with mock.patch("gym.pwa.webpush") as wp:
            telegram.notify_user(self.u, "tg_unlinked")
        self.assertEqual(wp.call_count, 1)
