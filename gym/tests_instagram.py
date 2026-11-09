"""Instagram Direct bot: webhook handshake and signatures, deduplication, echoes, bot answers / hand-off / pauses / rate limit / 24 hour window,
byte splitting, the admin inbox and token refresh. Meta is never contacted: the single HTTP function (instagram_api._call) is replaced."""
import hashlib
import hmac
import json
import os
from datetime import timedelta
from io import StringIO
from unittest import mock

from django.core.cache import cache
from django.core.management import CommandError, call_command
from django.test import Client, TestCase
from django.utils import timezone

from . import instagram_api as ig
from . import instagram_bot as bot
from .models import GymSettings, IgMessage, IgThread, IgToken, User

SECRET = "app-secret-for-tests"
VERIFY = "verify-me"
TOKEN = "IGQ-test-token-1234567890"
OUR = "9000"
ENV = {"IG_APP_SECRET": SECRET, "IG_VERIFY_TOKEN": VERIFY, "IG_ACCESS_TOKEN": TOKEN, "IG_ACCOUNT_ID": OUR, "FZ_SITE_URL": "https://gym.example"}
URL = "/webhooks/instagram/"


class FakeApi:
    """Stands in for instagram_api._call: records requests and answers like Graph does."""

    def __init__(self):
        self.calls, self.fail_send, self.sent = [], False, 0

    def __call__(self, method, url, token=None, body=None):
        self.calls.append((method, url, token, body))
        if "/me/messages" in url:
            if self.fail_send:
                raise ig.ApiError("boom", 1, 500)
            self.sent += 1
            return {"recipient_id": body["recipient"]["id"], "message_id": f"mid.out{self.sent}"}
        if "refresh_access_token" in url:
            return {"access_token": "REFRESHED-TOKEN-XYZ", "token_type": "bearer", "expires_in": 5184000}
        if "subscribed_apps" in url:
            return {"success": True}
        return {"name": "Ali Valiyev", "username": "ali_v", "profile_pic": "https://cdn.example/p.jpg"}

    def sends(self):
        return [c[3]["message"]["text"] for c in self.calls if "/me/messages" in c[1]]


def payload(sender="111", text="Salom", mid="mid.in1", ts=None, echo=False, attachments=None, **extra):
    msg = {"mid": mid}
    if text is not None:
        msg["text"] = text
    if attachments:
        msg["attachments"] = attachments
    if echo:
        msg["is_echo"] = True
    msg.update(extra)
    ev = {"sender": {"id": OUR if echo else sender}, "recipient": {"id": sender if echo else OUR},
          "timestamp": int((ts or timezone.now()).timestamp() * 1000), "message": msg}
    return {"object": "instagram", "entry": [{"id": OUR, "time": 1, "messaging": [ev]}]}


class Base(TestCase):
    def setUp(self):
        cache.clear()
        patcher = mock.patch.dict(os.environ, ENV)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.api = FakeApi()
        p2 = mock.patch("gym.instagram_api._call", self.api)
        p2.start()
        self.addCleanup(p2.stop)
        self.c = Client()

    def post(self, data, sign=True, secret=SECRET):
        body = json.dumps(data).encode()
        extra = {}
        if sign:
            extra["HTTP_X_HUB_SIGNATURE_256"] = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        return self.c.post(URL, body, content_type="application/json", **extra)

    def thread(self, **kw):
        kw.setdefault("last_user_message_at", timezone.now())
        return IgThread.objects.create(igsid=kw.pop("igsid", "111"), **kw)


class WebhookHandshakeTests(Base):
    def test_verify_ok(self):
        r = self.c.get(URL, {"hub.mode": "subscribe", "hub.verify_token": VERIFY, "hub.challenge": "12345"})
        self.assertEqual((r.status_code, r.content), (200, b"12345"))
        self.assertTrue(r["Content-Type"].startswith("text/plain"))

    def test_verify_bad_token_or_mode(self):
        self.assertEqual(self.c.get(URL, {"hub.mode": "subscribe", "hub.verify_token": "nope", "hub.challenge": "1"}).status_code, 403)
        self.assertEqual(self.c.get(URL, {"hub.mode": "subscribe", "hub.challenge": "1"}).status_code, 403)
        self.assertEqual(self.c.get(URL, {"hub.mode": "unsubscribe", "hub.verify_token": VERIFY, "hub.challenge": "1"}).status_code, 403)

    def test_signature_valid(self):
        r = self.post(payload())
        self.assertEqual(r.status_code, 200)
        self.assertTrue(IgMessage.objects.filter(mid="mid.in1").exists())

    def test_signature_invalid_or_missing(self):
        self.assertEqual(self.post(payload(), secret="wrong").status_code, 403)
        self.assertEqual(self.post(payload(), sign=False).status_code, 403)
        r = self.c.post(URL, b"{}", content_type="application/json", HTTP_X_HUB_SIGNATURE_256="sha256=")
        self.assertEqual(r.status_code, 403)
        self.assertEqual(IgMessage.objects.count(), 0)

    def test_signature_covers_raw_bytes(self):
        body = json.dumps(payload()).encode()
        sig = "sha256=" + hmac.new(SECRET.encode(), body, hashlib.sha256).hexdigest()
        r = self.c.post(URL, body + b" ", content_type="application/json", HTTP_X_HUB_SIGNATURE_256=sig)
        self.assertEqual(r.status_code, 403)

    def test_garbage_but_signed_is_200(self):
        body = b"not json"
        sig = "sha256=" + hmac.new(SECRET.encode(), body, hashlib.sha256).hexdigest()
        self.assertEqual(self.c.post(URL, body, content_type="application/json", HTTP_X_HUB_SIGNATURE_256=sig).status_code, 200)

    def test_disabled_when_not_configured(self):
        for missing in ("IG_APP_SECRET", "IG_VERIFY_TOKEN", "IG_ACCESS_TOKEN"):
            with mock.patch.dict(os.environ, {missing: ""}):
                self.assertEqual(self.c.get(URL, {"hub.mode": "subscribe", "hub.verify_token": VERIFY, "hub.challenge": "1"}).status_code, 404, missing)
                self.assertEqual(self.post(payload()).status_code, 404, missing)
        self.assertEqual(IgMessage.objects.count(), 0)


class StoreTests(Base):
    def test_dedupe_by_mid(self):
        self.post(payload(text="Ish vaqti qanday?", mid="mid.same"))
        self.post(payload(text="Ish vaqti qanday?", mid="mid.same"))
        self.assertEqual(IgMessage.objects.filter(direction="in").count(), 1)
        self.assertEqual(len(self.api.sends()), 1)  # answered once, not twice
        self.assertEqual(IgThread.objects.get().unread, 1)

    def test_own_account_ignored(self):
        data = payload(sender=OUR, text="Ish vaqti qanday?", mid="mid.self")
        data["entry"][0]["messaging"][0]["recipient"] = {"id": "111"}
        self.post(data)
        self.assertEqual(IgMessage.objects.count(), 0)
        self.assertEqual(self.api.sends(), [])

    def test_echo_stored_not_answered(self):
        self.post(payload(text="Ish vaqti qanday?", echo=True, mid="mid.echo1"))
        m = IgMessage.objects.get(mid="mid.echo1")
        self.assertEqual((m.direction, m.kind), ("out", "echo"))
        self.assertEqual(self.api.sends(), [])
        self.assertIsNotNone(IgThread.objects.get().bot_paused_until)  # a person stepped in from the Instagram app

    def test_echo_of_our_own_send_is_not_duplicated(self):
        self.post(payload(text="Ish vaqti qanday?", mid="mid.q"))
        out = IgMessage.objects.get(direction="out")
        self.post(payload(text=out.text, echo=True, mid=out.mid))
        self.assertEqual(IgMessage.objects.filter(direction="out").count(), 1)
        self.assertEqual(IgMessage.objects.get(direction="out").kind, "bot")
        self.assertIsNone(IgThread.objects.get().bot_paused_until)

    def test_read_reaction_edit_events(self):
        self.post(payload(text="Ish vaqti qanday?", mid="mid.e1"))
        for ev in ({"read": {"mid": "mid.e1"}}, {"reaction": {"mid": "mid.e1", "action": "react", "reaction": "love"}}, {"postback": {"mid": "x"}}):
            ev.update(sender={"id": "111"}, recipient={"id": OUR}, timestamp=1)
            self.post({"object": "instagram", "entry": [{"id": OUR, "messaging": [ev]}]})
        self.post({"object": "instagram", "entry": [{"id": OUR, "messaging": [
            {"sender": {"id": "111"}, "recipient": {"id": OUR}, "timestamp": 1, "message_edit": {"mid": "mid.e1", "text": "Narxlar?", "num_edit": 1}}]}]})
        self.assertEqual(IgMessage.objects.get(mid="mid.e1").text, "Narxlar?")
        self.assertEqual(IgMessage.objects.filter(direction="in").count(), 1)

    def test_attachments_stored_and_politely_answered(self):
        att = [{"type": "image", "payload": {"url": "https://cdn.example/a.jpg"}}]
        self.post(payload(text=None, mid="mid.img", attachments=att))
        m = IgMessage.objects.get(mid="mid.img")
        self.assertEqual(m.attachments, [{"type": "image", "url": "https://cdn.example/a.jpg"}])
        self.assertIn("matnli", self.api.sends()[0])
        self.assertTrue(IgThread.objects.get().needs_human)

    def test_malformed_payloads_do_not_crash(self):
        for data in ({"object": "instagram", "entry": "x"}, {"object": "instagram", "entry": [None, {"messaging": [5, {}]}]}, [], {"object": "page"}):
            self.assertEqual(self.post(data).status_code, 200)

    def test_profile_fetched_once_a_day(self):
        self.post(payload(text="Ish vaqti qanday?", mid="mid.p1"))
        t = IgThread.objects.get()
        self.assertEqual((t.name, t.username), ("Ali Valiyev", "ali_v"))
        self.post(payload(text="Manzil qayerda?", mid="mid.p2"))
        profile_calls = [c for c in self.api.calls if "fields=name" in c[1]]
        self.assertEqual(len(profile_calls), 1)
        self.assertTrue(all(c[2] == TOKEN for c in self.api.calls))


class BotTests(Base):
    def test_known_question_answered(self):
        self.post(payload(text="Ish vaqti qanday?"))
        sent = self.api.sends()
        self.assertEqual(len(sent), 1)
        self.assertIn("06:00", sent[0])
        t = IgThread.objects.get()
        self.assertFalse(t.needs_human)
        m = IgMessage.objects.get(direction="out")
        self.assertEqual((m.kind, m.sent_ok), ("bot", True))
        self.assertTrue(IgMessage.objects.get(mid="mid.in1").processed)
        method, url, token, body = [c for c in self.api.calls if "/me/messages" in c[1]][0]
        self.assertEqual((method, token, body["recipient"]["id"]), ("POST", TOKEN, "111"))
        self.assertTrue(url.startswith("https://graph.instagram.com/v27.0/me/messages"))

    def test_answer_has_no_markdown_and_site_links(self):
        self.post(payload(text="Abonement narxi qancha?"))
        text = self.api.sends()[0]
        self.assertNotIn("**", text)
        self.assertIn("https://gym.example/", text)

    def test_unknown_question_hands_off(self):
        self.post(payload(text="qwzxv plmokn jhgfd"))
        self.assertEqual(self.api.sends(), ["Rahmat! Administrator tez orada javob beradi."])
        self.assertTrue(IgThread.objects.get().needs_human)

    def test_fallback_in_russian_and_not_repeated(self):
        self.post(payload(text="Привет", mid="a0"))
        self.api.calls.clear()
        self.post(payload(text="щцкгшо жэдлорп", mid="a1"))
        self.assertIn("Администратор", self.api.sends()[0])
        self.api.calls.clear()
        self.post(payload(text="щцкгшо жэдлорп ещё", mid="a2"))
        self.assertEqual(self.api.sends(), [])  # already told: not again within 30 minutes
        self.assertTrue(IgThread.objects.get().needs_human)

    def test_greeting_gets_welcome_lines(self):
        self.post(payload(text="Salom"))
        text = self.api.sends()[0]
        for word in ("Narxlar", "Ish vaqti", "Manzil", "Mashg'ulotlar"):
            self.assertIn(word, text)
        self.assertFalse(IgThread.objects.get().needs_human)

    def test_emoji_only_is_ignored(self):
        self.post(payload(text="\U0001F44D"))
        self.assertEqual(self.api.sends(), [])
        self.assertTrue(IgMessage.objects.get(direction="in").processed)

    def test_global_switch_off(self):
        gs = GymSettings.load()
        gs.ig_auto_reply = False
        gs.save()
        self.post(payload(text="Ish vaqti qanday?"))
        self.assertEqual(self.api.sends(), [])
        self.assertTrue(IgThread.objects.get().needs_human)
        self.assertEqual(IgMessage.objects.filter(direction="in").count(), 1)

    def test_window_closed_blocks_sending(self):
        old = timezone.now() - timedelta(hours=25)
        self.post(payload(text="Ish vaqti qanday?", ts=old))
        self.assertEqual(self.api.sends(), [])
        t = IgThread.objects.get()
        self.assertFalse(t.window_open())
        sent, err = bot.send_to_thread(t, "hi", "staff")
        self.assertEqual(sent, 0)
        self.assertIn("24", err)
        self.assertEqual(self.api.sends(), [])

    def test_window_edges(self):
        t = self.thread(last_user_message_at=timezone.now() - timedelta(hours=23, minutes=59))
        self.assertTrue(t.window_open())
        t.last_user_message_at = timezone.now() - timedelta(hours=24, seconds=5)
        self.assertFalse(t.window_open())

    def test_staff_reply_pauses_bot(self):
        t = self.thread()
        ok, err = bot.send_staff(t, "Salom, men administratorman", self.make_staff())
        self.assertTrue(ok, err)
        t.refresh_from_db()
        self.assertIsNotNone(t.bot_paused_until)
        self.assertGreater(t.bot_paused_until, timezone.now() + timedelta(hours=11))
        self.api.calls.clear()
        self.post(payload(text="Ish vaqti qanday?", mid="mid.after"))
        self.assertEqual(self.api.sends(), [])
        self.assertTrue(IgThread.objects.get().needs_human)
        # pause over: the bot answers again
        IgThread.objects.update(bot_paused_until=timezone.now() - timedelta(minutes=1))
        self.post(payload(text="Ish vaqti qanday?", mid="mid.after2"))
        self.assertEqual(len(self.api.sends()), 1)

    def test_manual_thread_pause(self):
        self.thread(auto_reply_paused=True)
        self.post(payload(text="Ish vaqti qanday?"))
        self.assertEqual(self.api.sends(), [])

    def test_rate_limit_per_thread(self):
        t = self.thread()
        for i in range(bot.BOT_RATE_PER_MIN):
            IgMessage.objects.create(thread=t, direction="out", kind="bot", text="x", mid=f"mid.r{i}")
        self.post(payload(text="Ish vaqti qanday?"))
        self.assertEqual(self.api.sends(), [])
        IgMessage.objects.filter(kind="bot").update(created=timezone.now() - timedelta(minutes=2))
        self.post(payload(text="Ish vaqti qanday?", mid="mid.again"))
        self.assertEqual(len(self.api.sends()), 1)

    def test_failed_send_is_retried(self):
        self.api.fail_send = True
        self.post(payload(text="Ish vaqti qanday?"))
        m = IgMessage.objects.get(direction="in")
        self.assertFalse(m.processed)
        self.assertFalse(IgMessage.objects.get(direction="out").sent_ok)
        self.assertNotIn(TOKEN, IgMessage.objects.get(direction="out").error)
        self.api.fail_send = False
        IgMessage.objects.filter(pk=m.pk).update(created=timezone.now() - timedelta(minutes=5))
        self.assertEqual(bot.retry_pending(), 1)
        m.refresh_from_db()
        self.assertTrue(m.processed)
        self.assertEqual(len(self.api.sends()), 2)  # the failed attempt and the good one

    def test_member_gets_personal_answer_others_get_handoff(self):
        self.post(payload(text="Abonementim qachon tugaydi?", mid="mid.m1"))
        self.assertTrue(IgThread.objects.get().needs_human)
        self.assertIn("Administrator", self.api.sends()[0])

    def make_staff(self):
        return User.objects.create_user(phone="+998901112299", password="Kuchli-Parol-77", first_name="Xodim", is_staff=True)


class SplitTests(TestCase):
    def test_cyrillic_bytes(self):
        text = " ".join(f"Это предложение номер {i} для проверки разбиения по байтам." for i in range(80))
        parts = ig.split_text(text)
        self.assertGreater(len(parts), 3)
        for p in parts:
            self.assertLessEqual(len(p.encode("utf-8")), 1000)
            self.assertTrue(p.endswith("."))  # cut on sentence ends
        self.assertEqual(" ".join(parts).split(), text.split())

    def test_one_endless_word_and_emoji(self):
        word = "ы" * 1500
        parts = ig.split_text(word + " " + "\U0001F600" * 600)
        self.assertTrue(all(len(p.encode("utf-8")) <= 1000 for p in parts))
        self.assertEqual("".join(parts).replace(" ", ""), word + "\U0001F600" * 600)

    def test_short_and_empty(self):
        self.assertEqual(ig.split_text("  salom  "), ["salom"])
        self.assertEqual(ig.split_text(""), [])
        self.assertEqual(ig.split_text("a\nb"), ["a\nb"])

    def test_format_dm(self):
        self.assertEqual(bot.format_dm("**Narx**: [saytda](https://x.uz/p)\n\n\n\n* bir"), "Narx: saytda (https://x.uz/p)\n\n- bir")

    def test_long_reply_goes_out_in_parts(self):
        with mock.patch.dict(os.environ, ENV), mock.patch("gym.instagram_api._call", FakeApi()) as api:
            t = IgThread.objects.create(igsid="5", last_user_message_at=timezone.now())
            sent, err = bot.send_to_thread(t, "Привет, как дела? " * 200)
            self.assertEqual(err, "")
            self.assertEqual(sent, bot.MAX_CHUNKS)
            self.assertTrue(all(len(x.encode()) <= 1000 for x in api.sends()))


class TokenTests(Base):
    def test_seed_from_env_and_masked(self):
        self.assertEqual(ig.get_token(), TOKEN)
        row = IgToken.objects.get()
        self.assertNotIn(TOKEN, str(row))
        self.assertNotIn(TOKEN, row.masked)

    def test_new_env_token_replaces_stored(self):
        ig.get_token()
        IgToken.objects.update(access_token="old-refreshed")
        self.assertEqual(ig.get_token(), "old-refreshed")  # same env token: the refreshed one is kept
        with mock.patch.dict(os.environ, {"IG_ACCESS_TOKEN": "brand-new-token"}):
            self.assertEqual(ig.get_token(), "brand-new-token")

    def test_refresh_command(self):
        ig.get_token()
        IgToken.objects.update(last_attempt_at=timezone.now() - timedelta(days=2))
        out = StringIO()
        call_command("ig_refresh_token", stdout=out)
        row = IgToken.objects.get()
        self.assertEqual(row.access_token, "REFRESHED-TOKEN-XYZ")
        self.assertIsNotNone(row.refreshed_at)
        self.assertAlmostEqual((row.expires_at - timezone.now()).days, 60, delta=1)
        self.assertNotIn("REFRESHED-TOKEN-XYZ", out.getvalue())
        refresh = [c for c in self.api.calls if "refresh_access_token" in c[1]]
        self.assertIn("grant_type=ig_refresh_token", refresh[0][1])
        self.assertEqual(ig.get_token(), "REFRESHED-TOKEN-XYZ")  # later sends use the new token

    def test_not_due_is_skipped_and_force_works(self):
        ig.get_token()
        IgToken.objects.update(refreshed_at=timezone.now() - timedelta(days=3), last_attempt_at=timezone.now() - timedelta(days=3))
        call_command("ig_refresh_token", stdout=StringIO())
        self.assertEqual([c for c in self.api.calls if "refresh" in c[1]], [])
        call_command("ig_refresh_token", "--force", stdout=StringIO())
        self.assertEqual(len([c for c in self.api.calls if "refresh" in c[1]]), 1)

    def test_refresh_failure_logged_without_token(self):
        ig.get_token()
        IgToken.objects.update(last_attempt_at=timezone.now() - timedelta(days=2))
        with mock.patch("gym.instagram_api._call", side_effect=ig.ApiError("Session has expired", 190, 400)):
            with self.assertLogs("gym.instagram", "WARNING") as logs:
                ok, msg = ig.refresh_token()
        self.assertFalse(ok)
        self.assertNotIn(TOKEN, "".join(logs.output))
        row = IgToken.objects.get()
        self.assertEqual(row.access_token, TOKEN)  # the old token is kept
        self.assertIn("expired", row.last_error)

    def test_lazy_refresh_from_webhook(self):
        ig.get_token()
        IgToken.objects.update(refreshed_at=timezone.now() - timedelta(days=51), last_attempt_at=timezone.now() - timedelta(days=2))
        self.post(payload(text="Ish vaqti qanday?"))
        self.assertEqual(IgToken.objects.get().access_token, "REFRESHED-TOKEN-XYZ")

    def test_subscribe_command(self):
        out = StringIO()
        call_command("ig_subscribe", stdout=out)
        url = [c for c in self.api.calls if "subscribed_apps" in c[1]][0][1]
        for f in ("messages", "messaging_seen", "message_reactions", "message_edit"):
            self.assertIn(f, url)

    def test_commands_refuse_when_not_configured(self):
        with mock.patch.dict(os.environ, {"IG_APP_SECRET": ""}):
            with self.assertRaises(CommandError):
                call_command("ig_subscribe")
            with self.assertRaises(CommandError):
                call_command("ig_refresh_token")


class AdminTests(Base):
    def setUp(self):
        super().setUp()
        call_command("setup_gym", demo=True, verbosity=0)
        self.admin = User.objects.get(is_superuser=True)
        self.admin.set_password("AdminPass1")
        self.admin.save()
        self.staff = Client()
        self.staff.post("/login/", {"login": "admin1", "password": "AdminPass1.admin"})
        self.t = self.thread(name="Ali Valiyev", username="ali_v", unread=2, needs_human=True)
        IgMessage.objects.create(thread=self.t, direction="in", kind="user", text="Salom <b>x</b>", mid="m1")
        IgMessage.objects.create(thread=self.t, direction="out", kind="bot", text="Assalomu alaykum", mid="m2")

    def test_pages_need_staff_in_admin_mode(self):
        User.objects.create_user(phone="+998901234500", password="Kuchli-Parol-77", first_name="A")
        member = Client()
        member.post("/login/", {"login": "+998901234500", "password": "Kuchli-Parol-77"})
        for u in ("/django-admin/instagram/", f"/django-admin/instagram/{self.t.pk}/"):
            self.assertEqual(Client().get(u).status_code, 302)  # anonymous: to the login page
            self.assertEqual(member.get(u).status_code, 404)
        self.assertEqual(self.staff.get("/django-admin/instagram/").status_code, 200)

    def test_inbox_lists_and_badges(self):
        r = self.staff.get("/django-admin/instagram/")
        self.assertContains(r, "Ali Valiyev")
        self.assertContains(r, "@ali_v")
        self.assertContains(r, "Javob kerak")
        self.assertContains(r, "2 yangi")
        self.assertContains(r, "https://gym.example/webhooks/instagram/")
        self.assertContains(r, "Instagram xabarlari")  # sidebar entry
        self.assertNotContains(r, TOKEN)
        self.assertNotContains(r, SECRET)
        self.assertContains(self.staff.get("/django-admin/instagram/?f=unread"), "Ali Valiyev")
        self.assertNotContains(self.staff.get("/django-admin/instagram/?f=human&q=zzz"), "Ali Valiyev")

    def test_nav_unread_badge(self):
        cache.clear()
        from .admin_site import nav_badges
        self.assertEqual(nav_badges()["ig"], 1)

    def test_window_expired_badge_and_form_disabled(self):
        IgThread.objects.update(last_user_message_at=timezone.now() - timedelta(hours=30))
        self.assertContains(self.staff.get("/django-admin/instagram/"), "24 soat o")
        r = self.staff.get(f"/django-admin/instagram/{self.t.pk}/")
        self.assertContains(r, "24 soatdan ko'p o'tgan")
        self.assertContains(r, "<textarea name=\"text\" rows=\"3\" maxlength=\"2000\" placeholder=\"Javob yozing…\" disabled")

    def test_thread_view_bubbles_escaped_and_marks_read(self):
        r = self.staff.get(f"/django-admin/instagram/{self.t.pk}/")
        self.assertContains(r, "ig-b user")
        self.assertContains(r, "ig-b bot")
        self.assertContains(r, "Salom &lt;b&gt;x&lt;/b&gt;")
        self.t.refresh_from_db()
        self.assertEqual(self.t.unread, 0)

    def test_reply_sends_and_pauses(self):
        r = self.staff.post(f"/django-admin/instagram/{self.t.pk}/reply/", {"text": "Kelinglar!"})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(self.api.sends(), ["Kelinglar!"])
        m = IgMessage.objects.filter(kind="staff").get()
        self.assertEqual((m.text, m.author_id), ("Kelinglar!", self.admin.pk))
        self.t.refresh_from_db()
        self.assertFalse(self.t.needs_human)
        self.assertIsNotNone(self.t.bot_paused_until)

    def test_reply_blocked_after_24h_and_when_empty(self):
        IgThread.objects.update(last_user_message_at=timezone.now() - timedelta(hours=30))
        self.staff.post(f"/django-admin/instagram/{self.t.pk}/reply/", {"text": "Kechikdim"})
        self.assertEqual(self.api.sends(), [])
        self.assertFalse(IgMessage.objects.filter(kind="staff").exists())
        IgThread.objects.update(last_user_message_at=timezone.now())
        self.staff.post(f"/django-admin/instagram/{self.t.pk}/reply/", {"text": "   "})
        self.assertEqual(self.api.sends(), [])

    def test_reply_needs_csrf_and_post(self):
        strict = Client(enforce_csrf_checks=True)
        strict.post("/login/", {"login": "admin1", "password": "AdminPass1.admin"})
        # the login form itself needs a token too, so use the signed-in session of the normal client
        strict.cookies = self.staff.cookies
        r = strict.post(f"/django-admin/instagram/{self.t.pk}/reply/", {"text": "x"})
        self.assertEqual(r.status_code, 403)
        self.assertEqual(self.api.sends(), [])
        self.assertEqual(self.staff.get(f"/django-admin/instagram/{self.t.pk}/reply/").status_code, 302)  # GET does nothing
        self.assertEqual(self.api.sends(), [])

    def test_actions(self):
        base = f"/django-admin/instagram/{self.t.pk}/"
        self.staff.post(base + "pause/")
        self.t.refresh_from_db()
        self.assertTrue(self.t.auto_reply_paused)
        self.staff.post(base + "resume/")
        self.t.refresh_from_db()
        self.assertFalse(self.t.auto_reply_paused)
        self.staff.post(base + "resolve/")
        self.t.refresh_from_db()
        self.assertFalse(self.t.needs_human)
        self.assertEqual(self.staff.get(base + "pause/").status_code, 302)  # GET changes nothing
        self.t.refresh_from_db()
        self.assertFalse(self.t.auto_reply_paused)

    def test_link_member(self):
        u = User.objects.create_user(phone="+998901112233", password="Kuchli-Parol-77", first_name="Aziz", username="ali_v")
        r = self.staff.get(f"/django-admin/instagram/{self.t.pk}/")
        self.assertContains(r, "Mos a'zo")
        base = f"/django-admin/instagram/{self.t.pk}/"
        self.staff.post(base + "link/", {"member": "nobody-here"})
        self.t.refresh_from_db()
        self.assertIsNone(self.t.member_id)
        self.staff.post(base + "link/", {"member": "90 111 22 33"})
        self.t.refresh_from_db()
        self.assertEqual(self.t.member_id, u.pk)
        self.assertContains(self.staff.get(base), u.member_code)
        self.staff.post(base + "unlink/")
        self.t.refresh_from_db()
        self.assertIsNone(self.t.member_id)
        self.staff.post(base + "link/", {"member": u.member_code})
        self.t.refresh_from_db()
        self.assertEqual(self.t.member_id, u.pk)

    def test_test_button(self):
        self.staff.post("/django-admin/instagram/test/")
        self.assertEqual(len(self.api.sends()), 1)
        IgThread.objects.all().delete()
        self.assertContains(self.staff.get("/django-admin/instagram/"), "disabled")
        self.staff.post("/django-admin/instagram/test/")
        self.assertEqual(len(self.api.sends()), 1)

    def test_setup_guide_when_not_configured(self):
        with mock.patch.dict(os.environ, {"IG_APP_SECRET": "", "IG_VERIFY_TOKEN": "", "IG_ACCESS_TOKEN": ""}):
            r = self.staff.get("/django-admin/instagram/")
            self.assertContains(r, "Sozlanmagan")
            self.assertContains(r, "Ulash tartibi")
            self.assertContains(r, "IG_APP_SECRET")
            r = self.staff.post(f"/django-admin/instagram/{self.t.pk}/reply/", {"text": "salom"})
            self.assertEqual(self.api.sends(), [])
            self.assertEqual(self.staff.get(f"/django-admin/instagram/{self.t.pk}/").status_code, 200)
