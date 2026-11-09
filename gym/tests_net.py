"""The visitor's real address behind Render's proxy (gym/net.py) and the rate limits that depend on it."""
import html
import json
import os
from unittest import mock

from django.core.cache import cache
from django.test import Client, RequestFactory, SimpleTestCase, TestCase, override_settings

from .templatetags.gym_tags import translate
from .net import behind_proxy, client_ip

PROXY = "10.1.2.3"


def req(xff=None, remote=PROXY):
    extra = {"REMOTE_ADDR": remote}
    if xff is not None:
        extra["HTTP_X_FORWARDED_FOR"] = xff
    return RequestFactory().get("/", **extra)


class ClientIpTests(SimpleTestCase):
    def setUp(self):
        patcher = mock.patch.dict(os.environ)
        patcher.start()
        self.addCleanup(patcher.stop)
        os.environ.pop("RENDER", None)

    def test_plain_server_ignores_the_header(self):
        """Without a proxy of ours a client could write any X-Forwarded-For itself: REMOTE_ADDR is the only truth."""
        self.assertFalse(behind_proxy())
        self.assertEqual(client_ip(req("1.2.3.4")), PROXY)
        self.assertEqual(client_ip(req(None)), PROXY)

    @override_settings(TRUST_PROXY_HEADERS=True)
    def test_setting_trusts_the_header(self):
        self.assertTrue(behind_proxy())
        self.assertEqual(client_ip(req("203.0.113.9")), "203.0.113.9")
        self.assertEqual(client_ip(req("203.0.113.9, 70.41.3.18, 150.172.238.178")), "203.0.113.9")  # left-most = the visitor

    def test_render_environment_trusts_the_header(self):
        os.environ["RENDER"] = "true"
        self.assertTrue(behind_proxy())
        self.assertEqual(client_ip(req("198.51.100.7, 10.9.9.9")), "198.51.100.7")

    @override_settings(TRUST_PROXY_HEADERS=True)
    def test_invalid_entries_are_skipped(self):
        self.assertEqual(client_ip(req("unknown, 198.51.100.7")), "198.51.100.7")
        self.assertEqual(client_ip(req("  , <script>, 999.1.1.1,  198.51.100.8 ")), "198.51.100.8")
        self.assertEqual(client_ip(req("1.2.3.4.5, 2001:db8::1")), "2001:db8::1")
        self.assertEqual(client_ip(req("2001:0DB8:0000:0000:0000:0000:0000:0001")), "2001:db8::1")  # one canonical spelling = one bucket

    @override_settings(TRUST_PROXY_HEADERS=True)
    def test_falls_back_to_remote_addr(self):
        self.assertEqual(client_ip(req(None)), PROXY)
        self.assertEqual(client_ip(req("")), PROXY)
        self.assertEqual(client_ip(req("unknown, garbage")), PROXY)
        self.assertEqual(client_ip(req("x" * 5000)), PROXY)
        self.assertEqual(client_ip(req(None, remote="")), "")

    def test_no_raw_remote_addr_left_in_the_app(self):
        """Every rate limit must go through client_ip(): a direct REMOTE_ADDR read would be the proxy's address on Render."""
        root = os.path.dirname(__file__)
        for name in sorted(os.listdir(root)):
            if name.endswith(".py") and not name.startswith("tests") and name != "net.py":
                with open(os.path.join(root, name), encoding="utf-8") as fh:
                    self.assertNotIn("REMOTE_ADDR", fh.read(), name)


class RateLimitPerVisitorTests(TestCase):
    """Login attempts and guest questions are counted per visitor, not per proxy."""

    def setUp(self):
        cache.clear()
        patcher = mock.patch.dict(os.environ)
        patcher.start()
        self.addCleanup(patcher.stop)
        os.environ.pop("RENDER", None)

    def login(self, i, ip=None):
        # a different unknown name every time, so only the address bucket (rl:ip) can block
        extra = {"HTTP_X_FORWARDED_FOR": ip} if ip else {}
        r = Client(REMOTE_ADDR=PROXY).post("/login/", {"login": f"nobody{i}", "password": "wrong-pass-1"}, **extra)
        return html.escape(translate("uz", "err_rate")) in r.content.decode()

    def test_behind_proxy_each_visitor_has_own_login_bucket(self):
        os.environ["RENDER"] = "1"
        self.assertEqual([self.login(i, "203.0.113.1") for i in range(8)], [False] * 8)
        self.assertTrue(self.login(99, "203.0.113.1"))  # the 9th attempt of this visitor is blocked ...
        self.assertFalse(self.login(100, "203.0.113.2"))  # ... but another visitor behind the same proxy is not

    def test_plain_server_cannot_dodge_the_limit_with_the_header(self):
        for i in range(8):
            self.login(i, f"203.0.113.{i + 1}")  # a new fake address every time
        self.assertTrue(self.login(99, "203.0.113.200"))

    def ask(self, ip=None):
        extra = {"HTTP_X_FORWARDED_FOR": ip} if ip else {}
        return Client(REMOTE_ADDR=PROXY).post("/assistant/ask/", data=json.dumps({"q": "salom"}), content_type="application/json", **extra)

    @override_settings(TRUST_PROXY_HEADERS=True)
    def test_guest_questions_are_counted_per_visitor(self):
        codes = [self.ask("198.51.100.1").status_code for _ in range(31)]  # a new cookie-less guest every time: only the address identifies them
        self.assertEqual(codes[:30], [200] * 30)
        self.assertEqual(codes[30], 429)
        self.assertEqual(self.ask("198.51.100.2").status_code, 200)

    def test_guest_questions_share_the_proxy_bucket_when_not_trusted(self):
        codes = [self.ask(f"198.51.100.{i + 1}").status_code for i in range(31)]
        self.assertEqual(codes[30], 429)
