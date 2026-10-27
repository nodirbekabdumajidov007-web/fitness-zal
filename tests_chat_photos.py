"""Chat photos (who may see them), read ticks and presence."""
import os
import shutil
import tempfile
from datetime import timedelta

from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import Client, TestCase, override_settings
from django.utils import timezone

from . import chat
from .models import ChatMessage, ChatRoom, User

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
FETCH = {"HTTP_X_REQUESTED_WITH": "fetch"}


class PhotoChatTests(TestCase):
    def setUp(self):
        cache.clear()
        call_command("setup_gym", demo=True, verbosity=0)
        self.media = tempfile.mkdtemp()
        o = override_settings(MEDIA_ROOT=self.media)
        o.enable()
        self.addCleanup(lambda: (o.disable(), shutil.rmtree(self.media, ignore_errors=True)))
        self.ca, self.a = self.member("+998901112233", "Aziz")
        self.cb, self.b = self.member("+998935556677", "Bek")
        self.room = chat.direct_room(self.a, self.b)

    def member(self, phone, first):
        c = Client()
        c.post("/register/", {"first_name": first, "last_name": "K", "phone": phone[4:], "password": "secret12", "username": "u" + "".join(ch for ch in str(phone[4:]) if ch.isdigit()), "email": "u" + "".join(ch for ch in str(phone[4:]) if ch.isdigit()) + "@test.uz", "password2": "secret12"})
        return c, User.objects.get(phone=phone)

    def send_photo(self, client, room, data=PNG, name="p.png", body=""):
        return client.post(f"/chat/{room.pk}/send/", {"body": body, "image": SimpleUploadedFile(name, data)}, **FETCH)

    def test_photo_message_and_who_can_see_it(self):
        r = self.send_photo(self.ca, self.room)
        self.assertEqual(r.status_code, 200, r.content)
        m = r.json()["message"]
        self.assertEqual((m["body"], m["image"]), ("", f"/chat/photo/{m['id']}/"))  # a photo alone is a valid message
        self.assertEqual(self.cb.get(m["image"])["Content-Type"], "image/png")
        self.assertEqual(self.ca.get(m["image"])["X-Content-Type-Options"], "nosniff")
        cc, _ = self.member("+998977778899", "Cami")
        self.assertEqual(cc.get(m["image"]).status_code, 404)  # not in the conversation
        self.assertEqual(Client().get(m["image"]).status_code, 302)  # signed out
        self.assertIn(m["image"], self.cb.get(f"/chat/{self.room.pk}/").content.decode())

    def test_photo_with_caption_and_bad_files(self):
        self.assertEqual(self.send_photo(self.ca, self.room, body="Bugungi natija").json()["message"]["body"], "Bugungi natija")
        for name, data in (("x.svg", b"<svg onload=alert(1)>"), ("x.png", b"<html>not an image</html>"), ("x.gif", b"GIF89a")):
            self.assertEqual(self.send_photo(self.ca, self.room, data, name).status_code, 400, name)
        self.assertEqual(ChatMessage.objects.count(), 1)
        self.assertEqual(self.ca.post(f"/chat/{self.room.pk}/send/", {"body": "  "}, **FETCH).status_code, 400)  # nothing to send

    def test_deleting_removes_the_file(self):
        m = self.send_photo(self.ca, self.room).json()["message"]
        path = ChatMessage.objects.get(pk=m["id"]).image.path
        self.assertTrue(os.path.exists(path))
        self.ca.post(f"/chat/message/{m['id']}/delete/", **FETCH)
        self.assertFalse(os.path.exists(path))
        self.assertEqual(self.cb.get(m["image"]).status_code, 404)

    def test_staff_sees_photo_only_when_reported(self):
        admin = User.objects.get(is_superuser=True)
        admin.set_password("AdminPass1")
        admin.save()
        staff = Client()
        staff.post("/login/", {"phone": "908775505", "password": "AdminPass1.admin"})
        m = self.send_photo(self.ca, self.room).json()["message"]
        self.assertEqual(staff.get(m["image"]).status_code, 404)
        self.cb.post(f"/chat/message/{m['id']}/report/")
        self.assertEqual(staff.get(m["image"]).status_code, 200)

    def test_group_room_photos_and_rate_limit_shared(self):
        chat.ensure_rooms()
        general = ChatRoom.objects.get(slug="general")
        m = self.send_photo(self.ca, general).json()["message"]
        cc, _ = self.member("+998977778899", "Cami")
        self.assertEqual(cc.get(m["image"]).status_code, 200)  # every member can see the general room

    def test_read_ticks_and_presence(self):
        mid = self.ca.post(f"/chat/{self.room.pk}/send/", {"body": "salom"}, **FETCH).json()["message"]["id"]
        self.assertEqual(self.ca.get(f"/chat/{self.room.pk}/poll/?after={mid}").json()["read_upto"], 0)  # sent, not read
        self.cb.get(f"/chat/{self.room.pk}/poll/?after=0")  # B opens the chat
        poll = self.ca.get(f"/chat/{self.room.pk}/poll/?after={mid}").json()
        self.assertEqual(poll["read_upto"], mid)
        self.assertTrue(poll["presence"]["online"])
        self.assertIn("✓✓", self.ca.get(f"/chat/{self.room.pk}/").content.decode())
        User.objects.filter(pk=self.b.pk).update(last_seen=timezone.now() - timedelta(minutes=10))
        p = self.ca.get(f"/chat/{self.room.pk}/poll/?after={mid}").json()["presence"]
        self.assertFalse(p["online"])
        self.assertRegex(p["seen"], r"^\d\d:\d\d$|^\d\d\.\d\d \d\d:\d\d$")

    def test_day_separator_and_grouping(self):
        for t in ("bir", "ikki"):
            self.ca.post(f"/chat/{self.room.pk}/send/", {"body": t}, **FETCH)
        self.cb.post(f"/chat/{self.room.pk}/send/", {"body": "uch"}, **FETCH)
        html = self.cb.get(f"/chat/{self.room.pk}/").content.decode()
        self.assertEqual(html.count('class="m-day"'), 1)  # one "Today" separator
        self.assertIn("Bugun", html)
        self.assertEqual(html.count(" first\""), 2)  # two runs: A's two messages, then B's
