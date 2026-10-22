"""Live chat over WebSocket: who may connect, and that messages, typing, read ticks and deletions arrive instantly."""
import json

from asgiref.sync import async_to_sync, sync_to_async
from asgiref.testing import ApplicationCommunicator
from channels.routing import URLRouter
from django.contrib.auth.models import AnonymousUser
from django.core.cache import cache
from django.core.management import call_command
from django.test import Client, TestCase

from . import chat
from .models import ChatMessage, ChatRoom, User
from .routing import websocket_urlpatterns

PW = "Kuchli-Parol-77"
APP = URLRouter(websocket_urlpatterns)


class Sock(ApplicationCommunicator):
    """A tiny WebSocket test client (channels.testing would pull in daphne, which this project does not need)."""

    def __init__(self, user, room):
        super().__init__(APP, {"type": "websocket", "path": f"/ws/chat/{room.pk}/", "headers": [], "subprotocols": [], "user": user})

    async def connect(self, timeout=3):
        await self.send_input({"type": "websocket.connect"})
        r = await self.receive_output(timeout)
        return (True, None) if r["type"] == "websocket.accept" else (False, r.get("code"))

    async def send_json_to(self, data):
        await self.send_input({"type": "websocket.receive", "text": json.dumps(data)})

    async def receive_json_from(self, timeout=3):
        r = await self.receive_output(timeout)
        assert r["type"] == "websocket.send", r
        return json.loads(r["text"])

    async def disconnect(self, code=1000):
        await self.send_input({"type": "websocket.disconnect", "code": code})
        await self.wait(1)


def sock(user, room):
    return Sock(user, room)


class WsTests(TestCase):
    def setUp(self):
        cache.clear()
        call_command("setup_gym", demo=True, verbosity=0)
        chat.ensure_rooms()
        self.a = User.objects.create_user(phone="+998901112233", password=PW, first_name="Aziz", last_name="K")
        self.b = User.objects.create_user(phone="+998935554433", password=PW, first_name="Vali", last_name="A")
        self.room = ChatRoom.objects.filter(kind="room", vip_only=False).first()
        self.ca, self.cb = Client(), Client()
        self.ca.post("/login/", {"phone": "901112233", "password": PW})
        self.cb.post("/login/", {"phone": "935554433", "password": PW})

    def test_who_may_connect(self):
        async def run():
            c = sock(AnonymousUser(), self.room)
            ok, code = await c.connect()
            self.assertFalse(ok)
            self.assertEqual(code, 4403)
            direct = await sync_to_async(chat.direct_room)(self.a, self.b)
            outsider = await sync_to_async(User.objects.create_user)(phone="+998977776655", password=PW, first_name="X", last_name="Y")
            c = sock(outsider, direct)
            ok, code = await c.connect()
            self.assertFalse(ok)  # a private chat is only for its two people
            c = sock(self.a, direct)
            ok, _ = await c.connect()
            self.assertTrue(ok)
            await c.disconnect()
        async_to_sync(run)()

    def test_message_arrives_live_shaped_for_the_reader(self):
        async def run():
            c = sock(self.a, self.room)
            self.assertTrue((await c.connect())[0])
            r = await sync_to_async(self.cb.post)(f"/chat/{self.room.pk}/send/", {"body": "Salom hammaga!"}, HTTP_X_REQUESTED_WITH="fetch")
            self.assertEqual(r.status_code, 200)
            got = await c.receive_json_from(timeout=3)
            self.assertEqual(got["t"], "msg")
            self.assertEqual(got["m"]["body"], "Salom hammaga!")
            self.assertFalse(got["m"]["mine"])  # serialized for Aziz, not for Vali
            self.assertTrue(got["m"]["can_report"])
            mid = got["m"]["id"]
            await sync_to_async(self.cb.post)(f"/chat/message/{mid}/delete/", HTTP_X_REQUESTED_WITH="fetch")
            self.assertEqual(await c.receive_json_from(timeout=3), {"t": "deleted", "id": mid})
            await c.disconnect()
        async_to_sync(run)()

    def test_typing_and_read_ticks_in_private_chat(self):
        async def run():
            direct = await sync_to_async(chat.direct_room)(self.a, self.b)
            ca, cb = sock(self.a, direct), sock(self.b, direct)
            self.assertTrue((await ca.connect())[0])
            self.assertTrue((await cb.connect())[0])
            self.assertEqual((await ca.receive_json_from(timeout=3))["t"], "presence")  # Vali came online
            await cb.send_json_to({"t": "typing"})
            self.assertEqual(await ca.receive_json_from(timeout=3), {"t": "typing", "name": chat.display_name(self.b)})
            msg, _ = await sync_to_async(chat.post_message)(self.a, direct, "Ertaga zalga borasanmi?")
            await cb.send_json_to({"t": "read", "upto": msg.id})
            self.assertEqual(await ca.receive_json_from(timeout=3), {"t": "read", "upto": msg.id})  # Aziz's tick turns ✓✓
            self.assertEqual(await sync_to_async(chat.read_upto)(direct, self.a), msg.id)
            await ca.disconnect()
            await cb.disconnect()
        async_to_sync(run)()

    def test_page_offers_the_socket(self):
        r = self.ca.get(f"/chat/{self.room.pk}/")
        self.assertContains(r, f'data-ws="/ws/chat/{self.room.pk}/"')
        self.assertIn("ws://testserver", r["Content-Security-Policy"])
