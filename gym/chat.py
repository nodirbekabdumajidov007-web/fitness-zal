"""Member chat: rules and queries. Messages are plain text (templates escape them); nothing is auto-linked.
Privacy: people are found by name or member code (never by phone), shown as first name + last initial, and can opt out or block.
Photos are streamed by a view that checks the viewer may see the conversation; they are never public files.
In the public room phone numbers, card numbers and e-mails are masked on the server before the message is saved."""
import re
import time
from datetime import timedelta

from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db.models import Count, F, OuterRef, Q, Subquery
from django.db.models.functions import Coalesce
from django.utils import timezone

from .media import validate_image
from .models import ChatBlock, ChatMessage, ChatRead, ChatRoom, Mention, MessageReaction, RoomMute, User

MAX_LEN = 1000
RATE_LIMIT = 15  # messages per minute per member
PAGE = 50
ONLINE_SECONDS = 70  # the page polls every 3 s, so a minute of silence means the member left
PUBLIC_ROOMS = [("general", "Umumiy xona")]
EDIT_WINDOW = timedelta(minutes=15)
REACTIONS = ("👍", "❤️", "😂", "🔥", "💪", "👏")
TYPING_SECONDS = 4
MAX_MENTIONS = 5
SEARCH_LIMIT = 30


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


def blocked_ids(user):
    """Everyone who blocked `user` or whom `user` blocked."""
    pairs = ChatBlock.objects.filter(Q(blocker=user) | Q(blocked=user)).values_list("blocker_id", "blocked_id")
    return {i for pair in pairs for i in pair} - {user.pk}


def direct_room(a, b):
    lo, hi = sorted([a, b], key=lambda u: u.pk)
    return ChatRoom.objects.get_or_create(kind="direct", user_a=lo, user_b=hi)[0]


def normalize(body):
    lines = [ln.rstrip() for ln in (body or "").replace("\r\n", "\n").replace("\r", "\n").split("\n")]
    text = "\n".join(lines).strip()
    while "\n\n\n" in text:
        text = text.replace("\n\n\n", "\n\n")
    return text


def snippet(body, n=80):
    s = " ".join((body or "").split())
    return s if len(s) <= n else s[:n - 1].rstrip() + "…"


def rate_ok(kind, user, limit, seconds=60):
    key = f"chat:{kind}:{user.pk}"
    try:
        n = cache.incr(key)
    except ValueError:
        cache.set(key, 1, seconds)
        n = 1
    return n <= limit


# ---- privacy guard for the public room -------------------------------------------------------------------------------
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)*\.[A-Za-z]{2,}")
CARD_RE = re.compile(r"(?<!\d)(?:\d[ \-]?){15}\d(?!\d)")
GROUPED_CARD_RE = re.compile(r"^\d{4}([ \-])\d{4}\1\d{4}\1\d{4}$")
PHONE_RE = re.compile(r"(?<![\w+])(?:\+?[ ]?998[\s\-()]*)?\(?\d{2}\)?[\s\-.]*\d{3}[\s\-.]*\d{2}[\s\-.]*\d{2}(?!\d)")


def luhn_ok(digits):
    total = 0
    for i, ch in enumerate(reversed(digits)):
        n = int(ch)
        if i % 2:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return total % 10 == 0


def _mask_email(m):
    s = m.group(0)
    return s[0] + "***@***." + s.rsplit(".", 1)[1]


def _mask_card(m):
    s = m.group(0)
    digits = re.sub(r"\D", "", s)
    if not (luhn_ok(digits) or GROUPED_CARD_RE.match(s)):
        return s
    return "**** **** **** " + digits[-4:]


def _mask_phone(m):
    digits = re.sub(r"\D", "", m.group(0))
    return ("+998 " if len(digits) >= 12 else "") + "** *** ** " + digits[-2:]


def mask_private(text):
    """(masked text, True if something was masked): e-mails, 16-digit cards (Luhn or 4-4-4-4) and Uzbek phone numbers."""
    out = EMAIL_RE.sub(_mask_email, text)
    out = CARD_RE.sub(_mask_card, out)
    out = PHONE_RE.sub(_mask_phone, out)
    return out, out != text


# ---- mentions ---------------------------------------------------------------------------------------------------------
def participants(room, user, q="", limit=8):
    """Members who wrote in the room lately (the people @name can point to), minus the writer and anyone blocked either way."""
    ids = set(ChatMessage.objects.filter(room=room, deleted=False).order_by("-id").values_list("sender_id", flat=True)[:300])
    ids -= {user.pk} | blocked_ids(user)
    qs = User.objects.filter(pk__in=ids, is_active=True, is_superuser=False)
    q = (q or "").strip().lstrip("@")
    if q:
        qs = qs.filter(Q(first_name__istartswith=q) | Q(last_name__istartswith=q) | Q(username__istartswith=q))
    qs = qs.order_by("first_name", "last_name")
    return list(qs[:limit] if limit else qs)


def find_mentions(room, sender, body):
    """Members named as @Aziz K. in a room message (exactly the short name the autocomplete inserts)."""
    if room.kind != "room" or "@" not in body:
        return []
    low, found = body.lower(), []
    for u in participants(room, sender, limit=None):
        tok = "@" + display_name(u).lower()
        i = low.find(tok)
        end = i + len(tok)
        if i >= 0 and (i == 0 or not low[i - 1].isalnum()) and (end >= len(low) or not low[end].isalnum()):
            found.append(u)
    return found[:MAX_MENTIONS]


def split_mentions(body, names):
    """[(text, is_mention)] so a template can highlight the @names that were really resolved."""
    if not names or "@" not in body:
        return [(body, False)]
    pat = re.compile("(" + "|".join(re.escape("@" + n) for n in sorted(names, key=len, reverse=True)) + ")", re.I)
    return [(p, bool(i % 2)) for i, p in enumerate(pat.split(body)) if p]


def sync_mentions(msg, users):
    """Stores who is mentioned; returns the users that are newly mentioned (they get the notification)."""
    have = set(Mention.objects.filter(message=msg).values_list("user_id", flat=True))
    want = {u.pk: u for u in users}
    Mention.objects.filter(message=msg).exclude(user_id__in=want).delete()
    fresh = [u for pk, u in want.items() if pk not in have]
    Mention.objects.bulk_create([Mention(message=msg, user=u) for u in fresh], ignore_conflicts=True)
    return fresh


def is_muted(user, room):
    return RoomMute.objects.filter(user=user, room=room).exists()


def notify_mentions(msg, users):
    """In-app notification (+ push, Telegram per the member's settings). A muted room still delivers mentions."""
    from . import services
    from .templatetags.gym_tags import translate
    for u in users:
        if u.pk == msg.sender_id or not u.is_active:
            continue
        try:
            services.notify(u, translate(u.lang or "uz", "chat_mention_title", name=display_name(msg.sender)), snippet(msg.body, 140),
                            sender=msg.sender, telegram_too=False, url=f"/chat/{msg.room_id}/")
        except Exception:  # a failing push/notification must never break sending
            pass


def push_direct(msg):
    """A private message reaches an offline, un-muted recipient as a push, but only the first unread one (no flood)."""
    room = msg.room
    if room.kind != "direct":
        return
    other = room.other(msg.sender)
    if not other.is_active or is_muted(other, room) or presence(other)["online"]:
        return
    seen = ChatRead.objects.filter(room=room, user=other).values_list("last_id", flat=True).first() or 0
    if room.messages.filter(id__gt=seen, deleted=False).exclude(sender=other).count() > 1:
        return
    try:
        from . import pwa
        pwa.push_user(other, display_name(msg.sender), snippet(msg.body, 120) or "📷", f"/chat/{room.pk}/")
    except Exception:
        pass


# ---- posting / editing ------------------------------------------------------------------------------------------------
def post_message(user, room, body, image=None, reply_to_id=None):
    """Returns (message, error_key). A message needs text, a photo, or both. `message.masked` tells that private data was hidden."""
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
    reply = None
    if reply_to_id:
        reply = ChatMessage.objects.select_related("sender").filter(pk=reply_to_id, room=room).first()
        if not reply:
            return None, "chat_reply_bad"
        if reply.sender_id != user.pk and blocked_between(user, reply.sender):
            return None, "chat_blocked"
    if not rate_ok("rate", user, RATE_LIMIT):
        return None, "err_rate"
    masked = False
    if room.kind == "room":
        body, masked = mask_private(body)
    msg = ChatMessage(room=room, sender=user, body=body, reply_to=reply)
    if image is not None:
        msg.image.save(image.name, image, save=False)
    msg.save()
    msg.masked = masked
    msg.new_mentions = sync_mentions(msg, find_mentions(room, user, body))
    return msg, None


def can_edit(msg, user):
    return (msg.sender_id == user.pk and not msg.deleted and timezone.now() - msg.created <= EDIT_WINDOW)


def edit_message(user, msg, body):
    """Own message, within 15 minutes. Returns (message, error_key)."""
    if user.chat_banned:
        return None, "chat_banned"
    if msg.sender_id != user.pk or msg.deleted:
        return None, "chat_forbidden"
    if timezone.now() - msg.created > EDIT_WINDOW:
        return None, "chat_edit_expired"
    body = normalize(body)
    if not body and not msg.image:
        return None, "chat_empty"
    if len(body) > MAX_LEN:
        return None, "chat_long"
    if msg.room.kind == "direct":
        other = msg.room.other(user)
        if not other.is_active or blocked_between(user, other):
            return None, "chat_blocked"
    if not rate_ok("edit", user, RATE_LIMIT):
        return None, "err_rate"
    masked = False
    if msg.room.kind == "room":
        body, masked = mask_private(body)
    msg.masked, msg.new_mentions = masked, []
    if body != msg.body:
        msg.body, msg.edited_at = body, timezone.now()
        msg.save(update_fields=["body", "edited_at"])
        msg.new_mentions = sync_mentions(msg, find_mentions(msg.room, user, body))
    return msg, None


# ---- reactions --------------------------------------------------------------------------------------------------------
def set_reaction(user, msg, emoji):
    """Toggle / change the member's one reaction on a message. Returns (changed, error_key)."""
    if user.chat_banned:
        return False, "chat_banned"
    if not can_access(user, msg.room) or msg.deleted:
        return False, "chat_forbidden"
    if emoji not in REACTIONS:
        return False, "chat_bad_reaction"
    if msg.sender_id != user.pk and blocked_between(user, msg.sender):
        return False, "chat_blocked"
    if not rate_ok("react", user, 40):
        return False, "err_rate"
    cur = MessageReaction.objects.filter(message=msg, user=user).first()
    if cur and cur.emoji == emoji:
        cur.delete()
    elif cur:
        cur.emoji = emoji
        cur.save(update_fields=["emoji"])
    else:
        MessageReaction.objects.create(message=msg, user=user, emoji=emoji)
    return True, None


def reactions_map(message_ids, viewer):
    """{message_id: [{"e": emoji, "n": count, "mine": bool}]} for several messages in one query, in the picker's order."""
    ids = list(message_ids)
    if not ids:
        return {}
    counts, mine = {}, set()
    for mid, emoji, uid in MessageReaction.objects.filter(message_id__in=ids).values_list("message_id", "emoji", "user_id"):
        counts.setdefault(mid, {}).setdefault(emoji, 0)
        counts[mid][emoji] += 1
        if uid == viewer.pk:
            mine.add((mid, emoji))
    order = {e: i for i, e in enumerate(REACTIONS)}
    return {mid: [{"e": e, "n": n, "mine": (mid, e) in mine} for e, n in sorted(per.items(), key=lambda kv: order.get(kv[0], 99))]
            for mid, per in counts.items()}


def reaction_users(msg, viewer):
    """[{"e": emoji, "names": [...]}] for the "who reacted" sheet."""
    out = {}
    for r in MessageReaction.objects.filter(message=msg).select_related("user").order_by("id"):
        out.setdefault(r.emoji, []).append(display_name(r.user))
    order = {e: i for i, e in enumerate(REACTIONS)}
    return [{"e": e, "names": names} for e, names in sorted(out.items(), key=lambda kv: order.get(kv[0], 99))]


# ---- serialising ------------------------------------------------------------------------------------------------------
def read_upto(room, viewer):
    """In a private chat: up to which message the other person has read (for the double tick)."""
    if room.kind != "direct":
        return 0
    other_id = room.user_b_id if room.user_a_id == viewer.pk else room.user_a_id
    r = ChatRead.objects.filter(room=room, user_id=other_id).first()
    return r.last_id if r else 0


def _reply_payload(r):
    if r is None:
        return None
    alive = not r.deleted
    return {"id": r.id, "name": display_name(r.sender), "text": snippet(r.body, 90) if alive else "",
            "image": f"/chat/photo/{r.id}/" if (alive and r.image) else "", "deleted": r.deleted}


def context_for(msgs, viewer):
    """What serialize() needs besides the message itself, fetched once for the whole list."""
    ids = [m.id for m in msgs]
    return {"rx": reactions_map(ids, viewer),
            "mentions": {}, "me": set(Mention.objects.filter(message_id__in=ids, user=viewer).values_list("message_id", flat=True))
            if ids else set()}


def _mention_names(msg_ids):
    out = {}
    for mid, first, last, username in Mention.objects.filter(message_id__in=msg_ids).values_list("message_id", "user__first_name", "user__last_name", "user__username"):
        out.setdefault(mid, []).append(f"{first} {last[:1]}.".strip() if first else username)
    return out


def serialize(msg, viewer, read_to=0, ctx=None):
    if ctx is None:
        ctx = context_for([msg], viewer)
        ctx["names"] = _mention_names([msg.id])
    local = timezone.localtime(msg.created)
    mine = msg.sender_id == viewer.pk
    alive = not msg.deleted
    return {"id": msg.id, "mine": mine, "sender": msg.sender_id, "name": display_name(msg.sender), "initials": initials(msg.sender),
            "hue": hue(msg.sender), "body": msg.body if alive else "", "deleted": msg.deleted,
            "image": f"/chat/photo/{msg.id}/" if (alive and msg.image) else "",
            "ts": int(msg.created.timestamp()), "time": local.strftime("%H:%M"), "date": local.strftime("%d.%m.%Y"), "day": local.date().isoformat(),
            "read": mine and msg.id <= read_to, "can_delete": mine and alive, "can_report": (not mine) and alive,
            "can_edit": can_edit(msg, viewer), "edited": bool(msg.edited_at) and alive,
            "reply": _reply_payload(msg.reply_to) if msg.reply_to_id else None,
            "reactions": ctx["rx"].get(msg.id, []) if alive else [],
            "mentions": ctx.get("names", {}).get(msg.id, []) if alive else [], "mentioned_me": alive and msg.id in ctx["me"]}


def serialize_many(msgs, viewer, read_to=0):
    """serialize() for a list with a fixed number of queries (reactions, mentions), however long the list is."""
    msgs = list(msgs)
    ctx = context_for(msgs, viewer)
    ctx["names"] = _mention_names([m.id for m in msgs])
    return [serialize(m, viewer, read_to, ctx) for m in msgs]


def with_related(qs):
    return qs.select_related("sender", "reply_to", "reply_to__sender")


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


# ---- typing, stats, pin, search ---------------------------------------------------------------------------------------
def typing_mark(room, user):
    key = f"chat:typers:{room.pk}"
    now = time.time()
    cur = {k: v for k, v in (cache.get(key) or {}).items() if now - v[0] < TYPING_SECONDS}
    cur[user.pk] = (now, display_name(user))
    cache.set(key, cur, 30)


def typing_names(room, viewer):
    now = time.time()
    return [v[1] for k, v in (cache.get(f"chat:typers:{room.pk}") or {}).items() if k != viewer.pk and now - v[0] < TYPING_SECONDS]


def room_stats(room):
    """{"members": n, "online": n} for a public room (cached for 15 s; just counts, never names)."""
    if room.kind != "room":
        return None
    s = cache.get("chat:stats")
    if s is None:
        base = User.objects.filter(is_active=True, is_superuser=False)
        s = {"members": base.count(), "online": base.filter(last_seen__gte=timezone.now() - timedelta(seconds=ONLINE_SECONDS)).count()}
        cache.set("chat:stats", s, 15)
    return s


def pin_payload(room):
    m = room.pinned_message if room.pinned_message_id else None
    if not m or m.deleted:
        return None
    return {"id": m.id, "name": display_name(m.sender), "text": snippet(m.body, 90), "photo": bool(m.image)}


def search_messages(room, q):
    q = " ".join((q or "").split())
    if len(q) < 2:
        return []
    out = []
    for m in room.messages.filter(deleted=False, body__icontains=q).select_related("sender").order_by("-id")[:SEARCH_LIMIT]:
        local = timezone.localtime(m.created)
        out.append({"id": m.id, "name": display_name(m.sender), "text": snippet(m.body, 110), "time": local.strftime("%H:%M"),
                    "date": local.strftime("%d.%m.%Y"), "day": local.date().isoformat()})
    return out


def first_unread(room, user, msgs, seen):
    """Id of the first loaded message from someone else after the member's read marker (None on a first visit: nothing to divide)."""
    if seen is None:
        return None
    for m in msgs:
        if m.id > seen and m.sender_id != user.pk and not m.deleted:
            return m.id
    return None


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
    hidden = blocked_ids(user)
    if hidden:
        qs = qs.exclude(pk__in=hidden)
    digits = "".join(c for c in q if c.isdigit())
    if q.upper().startswith("FZ") and digits:
        return list(qs.filter(pk=int(digits))[:10])
    for word in q.split()[:3]:
        qs = qs.filter(Q(first_name__icontains=word) | Q(last_name__icontains=word))
    return list(qs.order_by("first_name", "last_name")[:10])
