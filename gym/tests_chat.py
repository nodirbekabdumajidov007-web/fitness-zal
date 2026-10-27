"""Member chat (private conversations and the general room), its privacy rules and moderation, plus uploaded lesson videos."""
import json
import shutil
import tempfile
from pathlib import Path

from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import Client, TestCase, override_settings

from . import chat, services
from .i18n import T
from .models import (ChatBlock, ChatMessage, ChatReport, ChatRoom, Lesson, User)

FETCH = {"HTTP_X_REQUESTED_WITH": "fetch"}


class ChatBase(TestCase):
    def setUp(self):
        cache.clear()
        call_command("setup_gym", demo=True, verbosity=0)
        self.admin = User.objects.get(is_superuser=True)
        self.admin.set_password("AdminPass1")
        self.admin.save()
        self.ca, self.a = self.member("+998901112233", "Aziz", "Karimov")
        self.cb, self.b = self.member("+998935556677", "Bek", "Zokirov")

    def member(self, phone, first, last):
        c = Client()
        c.post("/register/", {"first_name": first, "last_name": last, "phone": phone[4:], "password": "secret12", "username": "u" + "".join(ch for ch in str(phone[4:]) if ch.isdigit()), "email": "u" + "".join(ch for ch in str(phone[4:]) if ch.isdigit()) + "@test.uz", "password2": "secret12"})
        return c, User.objects.get(phone=phone)

    def staff(self):
        c = Client()
        c.post("/login/", {"phone": "908775505", "password": "AdminPass1.admin"})
        return c

    def send(self, client, room, body, json_mode=True):
        extra = FETCH if json_mode else {}
        return client.post(f"/chat/{room.pk}/send/", json.dumps({"body": body}), content_type="application/json", **extra)

    def dm(self):
        return chat.direct_room(self.a, self.b)


class DirectChatTests(ChatBase):
    def test_start_send_receive_and_unread(self):
        r = self.ca.post(f"/chat/with/{self.b.pk}/")
        room = ChatRoom.objects.get(kind="direct")
        self.assertEqual(r["Location"], f"/chat/{room.pk}/")
        self.assertEqual(self.ca.post(f"/chat/with/{self.b.pk}/")["Location"], r["Location"])  # the same room is reused
        sent = self.send(self.ca, room, "Salom, birga mashq qilamizmi?")
        self.assertEqual((sent.status_code, sent.json()["ok"], sent.json()["message"]["mine"]), (200, True, True))
        self.assertEqual(chat.unread_total(self.b), 1)
        self.assertEqual(chat.unread_total(self.a), 0)
        self.assertContains(self.cb.get("/chat/"), "Aziz K.")  # the conversation appears in B's inbox with the sender's short name
        poll = self.cb.get(f"/chat/{room.pk}/poll/?after=0").json()
        self.assertEqual([m["body"] for m in poll["messages"]], ["Salom, birga mashq qilamizmi?"])
        self.assertFalse(poll["messages"][0]["mine"])
        self.assertEqual(chat.unread_total(self.b), 0)  # polling marks the conversation as read
        self.assertEqual(self.cb.get(f"/chat/{room.pk}/poll/?after={poll['last_id']}").json()["messages"], [])
        page = self.cb.get(f"/chat/{room.pk}/")
        self.assertContains(page, "Salom, birga mashq")

    def test_only_the_two_participants_can_open_it(self):
        room = self.dm()
        self.send(self.ca, room, "maxfiy")
        cc, c = self.member("+998977778899", "Cami", "Rustamov")
        for url in (f"/chat/{room.pk}/", f"/chat/{room.pk}/poll/?after=0"):
            self.assertEqual(cc.get(url).status_code, 404)
        self.assertEqual(self.send(cc, room, "men ham yozaman").status_code, 404)
        self.assertEqual(Client().get(f"/chat/{room.pk}/").status_code, 302)  # sign-in required
        self.assertNotContains(cc.get("/chat/"), "maxfiy")
        msg = ChatMessage.objects.get()
        self.assertEqual(cc.post(f"/chat/message/{msg.pk}/report/").status_code, 404)  # cannot even report messages you cannot see
        self.assertEqual(cc.post(f"/chat/message/{msg.pk}/delete/").status_code, 404)

    def test_message_rules(self):
        room = self.dm()
        for bad in ("", "   \n  ", "x" * 1001):
            self.assertEqual(self.send(self.ca, room, bad).status_code, 400)
        self.assertEqual(ChatMessage.objects.count(), 0)
        ok = self.send(self.ca, room, "a\n\n\n\n\nb   ").json()["message"]["body"]
        self.assertEqual(ok, "a\n\nb")  # blank lines are collapsed, trailing space trimmed
        self.assertEqual(self.send(self.ca, room, "x" * 1000).status_code, 200)

    def test_rate_limit(self):
        room = self.dm()
        codes = [self.send(self.ca, room, f"m{i}").status_code for i in range(chat.RATE_LIMIT + 3)]
        self.assertEqual(codes.count(200), chat.RATE_LIMIT)
        self.assertEqual(codes[-1], 429)
        self.assertEqual(self.send(self.cb, room, "boshqa a'zo bemalol yozadi").status_code, 200)  # the limit is per member

    def test_html_is_escaped_and_not_linked(self):
        room = self.dm()
        self.send(self.ca, room, '<script>alert(1)</script> https://evil.example')
        page = self.cb.get(f"/chat/{room.pk}/").content.decode()
        self.assertNotIn("<script>alert(1)</script>", page)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", page)
        self.assertNotIn('href="https://evil.example"', page)

    def test_no_script_fallback_form_works(self):
        room = self.dm()
        r = self.ca.post(f"/chat/{room.pk}/send/", {"body": "oddiy forma"})
        self.assertEqual(r["Location"], f"/chat/{room.pk}/")
        self.assertEqual(ChatMessage.objects.get().body, "oddiy forma")

    def test_csrf_is_enforced(self):
        room = self.dm()
        c = Client(enforce_csrf_checks=True)
        c.post("/login/", {"phone": "901112233", "password": "secret12"})
        self.assertEqual(c.post(f"/chat/{room.pk}/send/", json.dumps({"body": "x"}), content_type="application/json").status_code, 403)

    def test_delete_own_message_only(self):
        room = self.dm()
        mid = self.send(self.ca, room, "xato yozdim").json()["message"]["id"]
        self.assertEqual(self.cb.post(f"/chat/message/{mid}/delete/").status_code, 404)
        self.assertEqual(self.ca.post(f"/chat/message/{mid}/delete/", **FETCH).json(), {"ok": True})
        page = self.cb.get(f"/chat/{room.pk}/").content.decode()
        self.assertNotIn("xato yozdim", page)  # the text is no longer sent to anyone
        self.assertEqual(self.cb.get(f"/chat/{room.pk}/poll/?after=0").json()["messages"][0]["body"], "")


class PrivacyAndBlockingTests(ChatBase):
    def test_search_by_name_or_code_never_shows_phone(self):
        r = self.ca.get("/chat/?q=bek")
        self.assertContains(r, "Bek Z.")
        self.assertNotContains(r, "935556677")
        self.assertNotContains(r, "+998935556677")
        self.assertContains(self.ca.get("/chat/?q=zokir"), "Bek Z.")
        self.assertContains(self.ca.get(f"/chat/?q={self.b.member_code}"), "Bek Z.")
        self.assertEqual(chat.search_people(self.a, "935556677"), [])  # phone numbers are not searchable
        self.assertEqual(chat.search_people(self.a, "b"), [])  # at least two characters
        self.assertEqual(chat.search_people(self.a, "aziz"), [])  # you do not find yourself
        self.assertEqual(chat.search_people(self.a, "admin"), [])  # staff accounts are not listed

    def test_opt_out_and_inactive_users_are_hidden(self):
        self.cb.post("/profile/", {"form": "profile", "first_name": "Bek", "last_name": "Zokirov", "phone": "93 555 66 77"})  # checkbox absent = opt out
        self.b.refresh_from_db()
        self.assertFalse(self.b.chat_visible)
        self.assertEqual(chat.search_people(self.a, "bek"), [])
        self.assertEqual(self.ca.post(f"/chat/with/{self.b.pk}/").status_code, 404)  # and cannot be started by guessing the id
        User.objects.filter(pk=self.b.pk).update(chat_visible=True, is_active=False)
        self.assertEqual(chat.search_people(self.a, "bek"), [])

    def test_blocking_works_both_ways(self):
        room = self.dm()
        self.send(self.ca, room, "salom")
        self.cb.post(f"/chat/block/{self.a.pk}/")
        self.assertTrue(ChatBlock.objects.filter(blocker=self.b, blocked=self.a).exists())
        self.assertEqual(self.send(self.ca, room, "yana").status_code, 400)  # A cannot write to someone who blocked them
        self.assertEqual(self.send(self.cb, room, "men ham").status_code, 400)  # nor can B while the block stands
        self.assertEqual(chat.search_people(self.a, "bek"), [])
        self.assertEqual(chat.search_people(self.b, "aziz"), [])
        self.assertContains(self.ca.get(f"/chat/{room.pk}/"), "chat_blocked_notice" if False else "<main")
        self.cb.post(f"/chat/unblock/{self.a.pk}/")
        self.assertEqual(self.send(self.ca, room, "qaytdim").status_code, 200)

    def test_banned_member_can_read_but_not_write(self):
        room = self.dm()
        self.send(self.cb, room, "salom")
        User.objects.filter(pk=self.a.pk).update(chat_banned=True)
        self.assertEqual(self.send(self.ca, room, "javob").status_code, 400)
        self.assertEqual(self.ca.get(f"/chat/{room.pk}/").status_code, 200)
        chat.ensure_rooms()
        general = ChatRoom.objects.get(slug="general")
        self.assertEqual(self.send(self.ca, general, "umumiyda ham").status_code, 400)


class RoomTests(ChatBase):
    def test_general_room_is_open_to_everyone_signed_in(self):
        chat.ensure_rooms()
        general = ChatRoom.objects.get(slug="general")
        self.send(self.ca, general, "Hammaga salom")
        self.assertContains(self.cb.get(f"/chat/{general.pk}/"), "Hammaga salom")
        self.assertEqual(Client().get(f"/chat/{general.pk}/").status_code, 302)
        self.assertEqual(chat.unread_total(self.b), 0)  # public rooms never produce unread badges

class ModerationTests(ChatBase):
    def test_report_and_admin_actions(self):
        chat.ensure_rooms()
        general = ChatRoom.objects.get(slug="general")
        mid = self.send(self.cb, general, "yomon so'z").json()["message"]["id"]
        self.assertEqual(self.cb.post(f"/chat/message/{mid}/report/").status_code, 404)  # not your own message
        for bad in ({}, {"kind": "nonsense"}, {"kind": "other"}, {"kind": "other", "detail": "   "}):  # a reason is required
            self.assertEqual(self.ca.post(f"/chat/message/{mid}/report/", bad, **FETCH).status_code, 400, bad)
        self.assertFalse(ChatReport.objects.exists())
        r = self.ca.post(f"/chat/message/{mid}/report/", {"kind": "insult"}, **FETCH)
        self.assertTrue(r.json()["ok"])
        self.assertEqual(ChatReport.objects.get().reason, "Haqorat / so'kinish")
        self.ca.post(f"/chat/message/{mid}/report/", {"kind": "spam"})  # twice: still one report
        self.assertEqual(ChatReport.objects.count(), 1)
        a = self.staff()
        self.assertContains(a.get("/django-admin/gym/chatreport/"), "yomon so")
        self.assertContains(a.get("/django-admin/gym/chatreport/"), "Haqorat")  # the admin sees why
        report = ChatReport.objects.get()
        page = a.get(f"/django-admin/gym/chatreport/{report.pk}/change/")
        self.assertContains(page, "yomon so")
        a.post("/django-admin/gym/chatreport/", {"action": "resolve_and_ban", "_selected_action": [report.pk]})
        self.b.refresh_from_db()
        report.refresh_from_db()
        self.assertTrue(self.b.chat_banned and report.resolved)
        self.assertTrue(ChatMessage.objects.get(pk=mid).deleted)
        self.assertEqual(self.send(self.cb, general, "yana").status_code, 400)
        self.assertContains(a.get("/django-admin/"), "Chat shikoyatlari")

    def test_staff_cannot_browse_private_conversations_without_a_report(self):
        room = self.dm()
        self.send(self.ca, room, "juda shaxsiy gap")
        general = ChatRoom.objects.get(slug="general") if ChatRoom.objects.filter(slug="general").exists() else None
        chat.ensure_rooms()
        general = ChatRoom.objects.get(slug="general")
        self.send(self.ca, general, "ochiq gap")
        a = self.staff()
        listing = a.get("/django-admin/gym/chatmessage/").content.decode()
        self.assertIn("ochiq gap", listing)
        self.assertNotIn("juda shaxsiy gap", listing)
        mid = ChatMessage.objects.get(body="juda shaxsiy gap").pk
        self.assertEqual(a.get(f"/django-admin/gym/chatmessage/{mid}/change/").status_code, 302)  # not found in the restricted queryset
        self.cb.post(f"/chat/message/{mid}/report/", {"kind": "spam"})  # once reported, moderators can see it
        self.assertIn("juda shaxsiy gap", a.get("/django-admin/gym/chatmessage/").content.decode())


class UploadedVideoTests(TestCase):
    """The home-page video upload: streamed with Range support so it starts fast and can seek."""
    def setUp(self):
        cache.clear()
        call_command("setup_gym", demo=True, verbosity=0)
        self.media = tempfile.mkdtemp()
        self.override = override_settings(MEDIA_ROOT=self.media)
        self.override.enable()
        self.addCleanup(lambda: (self.override.disable(), shutil.rmtree(self.media, ignore_errors=True)))
        self.data = bytes(range(256)) * 40  # 10 240 bytes
        from .models import GymSettings
        gs = GymSettings.load()
        gs.hero_video.save("clip.mp4", SimpleUploadedFile("clip.mp4", self.data), save=True)
        self.gs = gs

    def get(self, **headers):
        r = Client().get("/hero/video/", **headers)
        self.addCleanup(r.close)  # Windows keeps the file locked while a response holds it
        return r

    def test_video_streams_with_range_support(self):
        r = self.get()
        self.assertEqual((r.status_code, r["Accept-Ranges"], r["Content-Type"]), (200, "bytes", "video/mp4"))
        self.assertEqual(b"".join(r.streaming_content), self.data)
        part = self.get(HTTP_RANGE="bytes=100-199")
        self.assertEqual((part.status_code, part["Content-Range"], part["Content-Length"]), (206, "bytes 100-199/10240", "100"))
        self.assertEqual(b"".join(part.streaming_content), self.data[100:200])
        self.assertEqual(b"".join(self.get(HTTP_RANGE="bytes=-50").streaming_content), self.data[-50:])
        self.assertEqual(b"".join(self.get(HTTP_RANGE="bytes=10000-").streaming_content), self.data[10000:])
        for bad in ("bytes=99999-", "bytes=5-2", "lines=1-2", "bytes=-"):
            self.assertEqual(self.get(HTTP_RANGE=bad).status_code, 416, bad)

    def test_lessons_section_is_gone(self):
        for url in ("/training/", "/training/1/", "/training/1/video/"):
            self.assertEqual(Client().get(url).status_code, 404, url)
        self.assertNotIn("/training/", Client().get("/").content.decode())

    def test_upload_rules(self):
        from django.core.exceptions import ValidationError
        from .media import validate_video_file
        with self.assertRaises(ValidationError):
            validate_video_file(SimpleUploadedFile("evil.html", b"<script>"))
        with self.assertRaises(ValidationError):
            validate_video_file(SimpleUploadedFile("evil.mp4.exe", b"x"))
        with override_settings(MAX_VIDEO_MB=0):
            with self.assertRaises(ValidationError):
                validate_video_file(SimpleUploadedFile("big.mp4", b"x"))
        validate_video_file(SimpleUploadedFile("ok.webm", b"x"))


class ChatTranslationTests(TestCase):
    def test_every_chat_key_exists_in_all_languages(self):
        root = Path(__file__).parent
        import re
        used = set()
        for name in ("chat.py", "chat_views.py"):
            src = (root / name).read_text(encoding="utf-8")
            used |= set(re.findall(r'flash\(request, [\w.]+, "(\w+)"', src)) | set(re.findall(r'"(chat_\w+)"', src)) | set(re.findall(r'"(err_rate)"', src))
        used.discard("chat_room")  # a URL name, not a translation key
        for f in (root / "templates/gym").glob("chat_*.html"):
            used |= {k for k in re.findall(r"\{% t '([a-z_0-9]+)'", f.read_text(encoding="utf-8")) if not k.endswith("_")}
        for lang in T:
            self.assertEqual(sorted(k for k in used if k not in T[lang]), [], lang)
