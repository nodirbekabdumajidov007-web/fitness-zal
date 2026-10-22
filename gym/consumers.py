"""Live chat over WebSocket (Django Channels).

Sending stays a normal HTTP POST (photos, rate limits and validation live there). Once a message is saved, the view
announces it to the room's group and every open socket fetches it from the database and serializes it *for its own user*
(mine / can delete / read ticks), so nobody receives data shaped for someone else. The socket also carries "typing...",
read receipts and presence. If the socket cannot connect, chat.js falls back to polling."""
from asgiref.sync import async_to_sync
from channels.generic.websocket import JsonWebsocketConsumer

from . import chat
from .models import ChatMessage, ChatRoom


def group(room_id):
    return f"chat_{room_id}"


def announce(room_id, event):
    """Called from ordinary (sync) views; silently does nothing when no channel layer is configured."""
    from channels.layers import get_channel_layer
    layer = get_channel_layer()
    if layer is None:
        return
    try:
        async_to_sync(layer.group_send)(group(room_id), event)
    except Exception:  # a broken layer must never break sending a message
        pass


class ChatConsumer(JsonWebsocketConsumer):
    def connect(self):
        user = self.scope.get("user")
        try:
            room = ChatRoom.objects.get(pk=int(self.scope["url_route"]["kwargs"]["room"]))
        except (ChatRoom.DoesNotExist, ValueError):
            return self.close(code=4404)
        if not user or not user.is_authenticated or not user.is_active or not chat.can_access(user, room):
            return self.close(code=4403)
        self.user, self.room = user, room
        self.group = group(room.pk)
        async_to_sync(self.channel_layer.group_add)(self.group, self.channel_name)
        self.accept()
        chat.touch(user)
        self._presence(True)

    def disconnect(self, code):
        if hasattr(self, "group"):
            self._presence(False)
            async_to_sync(self.channel_layer.group_discard)(self.group, self.channel_name)

    def _presence(self, online):
        if self.room.kind == "direct":
            self._send_group({"type": "chat.presence", "user": self.user.pk, "online": online})

    def _send_group(self, event):
        async_to_sync(self.channel_layer.group_send)(self.group, event)

    # ---- from the browser
    def receive_json(self, content, **kwargs):
        t = content.get("t") if isinstance(content, dict) else None
        if t == "typing":
            self._send_group({"type": "chat.typing", "user": self.user.pk, "name": chat.display_name(self.user)})
        elif t == "read":
            try:
                upto = int(content.get("upto", 0))
            except (TypeError, ValueError):
                return
            if upto > 0 and self.room.messages.filter(id=upto).exists():
                chat.mark_read(self.user, self.room, upto)
                self._send_group({"type": "chat.read", "user": self.user.pk, "upto": upto})
        elif t == "ping":
            chat.touch(self.user)

    # ---- from the group
    def chat_new(self, event):
        msg = ChatMessage.objects.select_related("sender").filter(pk=event["id"], room=self.room).first()
        if msg:
            self.send_json({"t": "msg", "m": chat.serialize(msg, self.user, chat.read_upto(self.room, self.user))})

    def chat_deleted(self, event):
        self.send_json({"t": "deleted", "id": event["id"]})

    def chat_read(self, event):
        if event["user"] != self.user.pk:  # the other person read up to here: my ticks turn blue
            self.send_json({"t": "read", "upto": event["upto"]})

    def chat_typing(self, event):
        if event["user"] != self.user.pk:
            self.send_json({"t": "typing", "name": event["name"]})

    def chat_presence(self, event):
        if event["user"] != self.user.pk:
            self.send_json({"t": "presence", "online": event["online"], "seen": ""})
