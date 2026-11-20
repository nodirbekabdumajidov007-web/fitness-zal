"""Chat voice notes: who may play them, what is accepted, deletion."""
import shutil
import tempfile

from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import Client, TestCase, override_settings

from . import chat
from .models import ChatMessage, User

WEBM = b"\x1aE\xdf\xa3" + bytes(range(100))
FETCH = {"HTTP_X_REQUESTED_WITH": "fetch"}


class VoiceChatTests(TestCase):
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
        d = "".join(ch for ch in phone[4:] if ch.isdigit())
        c.post("/register/", {"first_name": first, "last_name": "K", "phone": phone[4:], "password": "secret12", "username": "u" + d,
                              "email": f"u{d}@test.uz", "consent": "1", "password2": "secret12"})
        return c, User.objects.get(phone=phone)

    def send(self, client, data=WEBM, name="voice.webm", secs=7):
        return client.post(f"/chat/{self.room.pk}/send/", {"body": "", "voice": SimpleUploadedFile(name, data), "voice_secs": secs}, **FETCH)

    def test_voice_note_is_a_valid_message_and_only_the_conversation_hears_it(self):
        r = self.send(self.ca)
        self.assertEqual(r.status_code, 200, r.content)
        m = r.json()["message"]
        self.assertEqual((m["body"], m["voice"], m["voice_secs"]), ("", f"/chat/voice/{m['id']}/", 7))
        g = self.cb.get(m["voice"])
        self.assertEqual((g.status_code, g["Content-Type"], g["Accept-Ranges"]), (200, "audio/webm", "bytes"))
        cc, _ = self.member("+998977778899", "Cami")
        self.assertEqual(cc.get(m["voice"]).status_code, 404)
        self.assertEqual(Client().get(m["voice"]).status_code, 302)
        self.assertIn('data-src="' + m["voice"] + '"', self.cb.get(f"/chat/{self.room.pk}/").content.decode())

    def test_byte_ranges_for_safari(self):
        m = self.send(self.ca).json()["message"]
        r = self.cb.get(m["voice"], HTTP_RANGE="bytes=0-9")
        self.assertEqual((r.status_code, r["Content-Range"], len(r.content)), (206, f"bytes 0-9/{len(WEBM)}", 10))
        self.assertEqual(self.cb.get(m["voice"], HTTP_RANGE="bytes=9999-").status_code, 416)

    def test_only_real_audio_is_accepted_whatever_the_name(self):
        self.assertEqual(self.send(self.ca, b"<html>not audio</html>", "voice.webm").status_code, 400)
        self.assertEqual(self.send(self.ca, b"MZ\x90\x00" + b"\x00" * 50, "x.exe").status_code, 400)
        self.assertEqual(ChatMessage.objects.count(), 0)
        self.assertEqual(self.send(self.ca, b"OggS" + b"\x00" * 30, "x.bin").status_code, 200)

    def test_length_is_clamped_and_deleting_removes_the_file(self):
        m = self.send(self.ca, secs=99999).json()["message"]
        self.assertEqual(m["voice_secs"], 180)
        msg = ChatMessage.objects.get(pk=m["id"])
        path = msg.voice.path
        self.assertTrue(path.endswith(".webm"))
        self.assertEqual(self.ca.post(f"/chat/message/{msg.pk}/delete/", **FETCH).status_code, 200)
        msg.refresh_from_db()
        self.assertFalse(msg.voice)
        self.assertEqual(self.cb.get(f"/chat/voice/{msg.pk}/").status_code, 404)
