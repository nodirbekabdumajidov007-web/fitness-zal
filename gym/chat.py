"""Member chat: rules and queries. Messages are plain text (templates escape them); nothing is auto-linked.
Privacy: people are found by name or member code (never by phone), shown as first name + last initial, and can opt out or block.
Photos are streamed by a view that checks the viewer may see the conversation; they are never public files."""
from datetime import timedelta

from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db.models import Count, F, OuterRef, Q, Subquery
from django.db.models.functions import Coalesce
from django.utils import timezone

from .media import validate_image
from .models import ChatBlock, ChatMessage, ChatRead, ChatRoom, User

MAX_LEN = 1000
RATE_LIMIT = 15  # messages per minute per member
PAGE = 50
ONLINE_SECONDS = 70  # the page polls every 3 s, so a minute of silence means the member left
PUBLIC_ROOMS = [("general", "Umumiy xona")]


def ensure_rooms():
    for slug, title in PUBLIC_ROOMS:
        ChatRoom.objects.get_or_create(slug=slug, defaults={"kind": "room", "title": title})


def display_name(u):
    return f"{u.first_name} {u.last_name[:1]}.".strip() if u.first_name else u.username


def initials(u):
    return ((u.first_name[:1] or u.username[:1] or "?") + (u.last_name[:1] or "")).upper()


def hue(u):
    return (u.pk * 47) % 360  # a stable colour per member for the avatar


def can_access(user, room):
    if room.kind == "direct":
        return user.pk in (room.user_a_id, room.user_b_id)
    return True


def blocked_between(a, b):
    return ChatBlock.objects.filter(Q(blocker=a, blocked=b) | Q(blocker=b, blocked=a)).exists()


def direct_room(a, b):
    lo, hi = sorted([a, b], key=lambda u: u.pk)
    return ChatRoom.objects.get_or_create(kind="direct", user_a=lo, user_b=hi)[0]


def normalize(body):
    lines = [ln.rstrip() for ln in (body or "").replace("\r\n", "\n").replace("\r", "\n").split("\n")]
    text = "\n".join(lines).strip()
    while "\n\n\n" in text:
        text = text.replace("\n\n\n", "\n\n")
    return text


def post_message(user, room, body, image=None):
    """Returns (message, error_key). A message needs text, a photo, or both."""
    if user.chat_banned:
        return None, "chat_banned"
    if not can_access(user, room):
        return None, "chat_forbidden"
    body = normalize(body)
    if not body and not image:
        return None, "chat_empty"
    if len(body) > MAX_LEN:
        return None, "chat_long"
    if image is not None:
        try:
            validate_image(image)
        except ValidationError:
            return None, "chat_bad_image"
    if room.kind == "direct":
        other = room.other(user)
        if not other.is_active or blocked_between(user, other):
            return None, "chat_blocked"
    key = f"chat:rate:{user.pk}"
    try:
        n = cache.incr(key)
    except ValueError:
        cache.set(key, 1, 60)
        n = 1
    if n > RATE_LIMIT:
        return None, "err_rate"
    msg = ChatMessage(room=room, sender=user, body=body)
    if image is not None:
        msg.image.save(image.name, image, save=False)
    msg.save()
    return msg, None


def read_upto(room, viewer):
    """In a private chat: up to which message the other person has read (for the double tick)."""
    if room.kind != "direct":
        return 0
    other_id = room.user_b_id if room.user_a_id == viewer.pk else room.user_a_id
    r = ChatRead.objects.filter(room=room, user_id=other_id).first()
    return r.last_id if r else 0


def serialize(msg, viewer, read_to=0):
    local = timezone.localtime(msg.created)
    mine = msg.sender_id == viewer.pk
    alive = not msg.deleted
    return {"id": msg.id, "mine": mine, "sender": msg.sender_id, "name": display_name(msg.sender), "initials": initials(msg.sender),
            "hue": hue(msg.sender), "body": msg.body if alive else "", "deleted": msg.deleted,
            "image": f"/chat/photo/{msg.id}/" if (alive and msg.image) else "",
            "time": local.strftime("%H:%M"), "date": local.strftime("%d.%m.%Y"), "day": local.date().isoformat(),
            "read": mine and msg.id <= read_to, "can_delete": mine and alive, "can_report": (not mine) and alive}


def mark_read(user, room, last_id):
    obj, _ = ChatRead.objects.get_or_create(user=user, room=room)
    if last_id > obj.last_id:
        obj.last_id = last_id
        obj.save(update_fields=["last_id"])


def touch(user):
    """Remembers when the member was last active in chat (at most one write per 30 seconds)."""
    now = timezone.now()
    if not user.last_seen or now - user.last_seen > timedelta(seconds=30):
        User.objects.filter(pk=user.pk).update(last_seen=now)
        user.last_seen = now


def presence(u):
    if not u or not u.last_seen:
        return {"online": False, "seen": ""}
    if timezone.now() - u.last_seen < timedelta(seconds=ONLINE_SECONDS):
        return {"online": True, "seen": ""}
    local = timezone.localtime(u.last_seen)
    same_day = local.date() == timezone.localdate()
    return {"online": False, "seen": local.strftime("%H:%M") if same_day else local.strftime("%d.%m %H:%M")}


def unread_by_room(user):
    """{room_id: unread count} for the member's private conversations, in one query."""
    rooms = ChatRoom.objects.filter(kind="direct").filter(Q(user_a=user) | Q(user_b=user))
    last = Subquery(ChatRead.objects.filter(user=user, room=OuterRef("room")).values("last_id")[:1])
    rows = (ChatMessage.objects.filter(room__in=rooms, deleted=False).exclude(sender=user).annotate(seen=Coalesce(last, 0)).filter(id__gt=F("seen"))
            .values("room_id").annotate(n=Count("id")))
    return {r["room_id"]: r["n"] for r in rows}


def unread_total(user):
    return sum(unread_by_room(user).values())


def search_people(user, q):
    q = (q or "").strip()
    if len(q) < 2:
        return []
    qs = User.objects.filter(is_active=True, is_superuser=False, chat_visible=True).exclude(pk=user.pk)
    blocked = ChatBlock.objects.filter(Q(blocker=user) | Q(blocked=user)).values_list("blocker_id", "blocked_id")
    hidden = {i for pair in blocked for i in pair} - {user.pk}
    if hidden:
        qs = qs.exclude(pk__in=hidden)
    digits = "".join(c for c in q if c.isdigit())
    if q.upper().startswith("FZ") and digits:
        return list(qs.filter(pk=int(digits))[:10])
    for word in q.split()[:3]:
        qs = qs.filter(Q(first_name__icontains=word) | Q(last_name__icontains=word))
    return list(qs.order_by("first_name", "last_name")[:10])
