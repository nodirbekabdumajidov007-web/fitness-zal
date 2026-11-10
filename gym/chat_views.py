import hashlib
import json
import time
from datetime import datetime, timedelta, timezone as dtz

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from . import chat
from .consumers import announce
from .media import image_type
from .models import ChatBlock, ChatMessage, ChatReport, ChatRead, ChatRoom, RoomMute, User
from .templatetags.gym_tags import translate
from .views import flash

HISTORY_PAGE = 50
HISTORY_JUMP = 200  # most messages one "jump to an old message" request may return


def wants_json(request):
    return request.headers.get("X-Requested-With") == "fetch"


def jdata(request):
    """The request's fields, whether they came as JSON or as a form."""
    if request.content_type == "application/json":
        try:
            data = json.loads(request.body)
        except ValueError:
            return {}
        return data if isinstance(data, dict) else {}
    return request.POST


def to_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def staff_mode(request):
    return bool(request.user.is_staff and request.session.get("admin_mode"))


def fail(request, key, status=400):
    return JsonResponse({"ok": False, "error": translate(request.lang, key)}, status=429 if key == "err_rate" else status)


def get_room(request, pk):
    room = get_object_or_404(ChatRoom.objects.select_related("pinned_message__sender"), pk=pk)
    if not chat.can_access(request.user, room):
        raise Http404()
    return room


def day_label(lang, day):
    today = timezone.localdate()
    if day == today:
        return translate(lang, "today_cap")
    if day == today - timedelta(days=1):
        return translate(lang, "yesterday")
    label = translate(lang, "chat_day_fmt", d=day.day, m=translate(lang, "chat_months").split(",")[day.month - 1])
    return label if day.year == today.year else f"{label} {day.year}"


def message_for(request, pk):
    msg = get_object_or_404(ChatMessage.objects.select_related("room", "sender"), pk=pk)
    if not chat.can_access(request.user, msg.room):
        raise Http404()
    return msg


@login_required
def inbox(request):
    chat.ensure_rooms()
    chat.touch(request.user)
    u = request.user
    unread = chat.unread_by_room(u)
    directs = []
    for r in ChatRoom.objects.filter(kind="direct").filter(Q(user_a=u) | Q(user_b=u)).select_related("user_a", "user_b"):
        last = r.messages.order_by("-id").first()
        if last:
            other = r.other(u)
            directs.append({"room": r, "other": other, "name": chat.display_name(other), "initials": chat.initials(other), "hue": chat.hue(other),
                            "last": last, "unread": unread.get(r.id, 0), "blocked": chat.blocked_between(u, other),
                            "online": chat.presence(other)["online"]})
    directs.sort(key=lambda d: d["last"].id, reverse=True)
    q = request.GET.get("q", "").strip()
    rooms = []
    for r in ChatRoom.objects.filter(kind="room").order_by("id"):
        last = r.messages.filter(deleted=False).select_related("sender").order_by("-id").first()
        rooms.append({"room": r, "last": last, "last_name": chat.display_name(last.sender) if last else "", "unread": unread.get(r.id, 0)})
    return render(request, "gym/chat_inbox.html", {
        "directs": directs, "rooms": rooms, "q": q,
        "results": [{"u": p, "name": chat.display_name(p), "initials": chat.initials(p), "hue": chat.hue(p)} for p in chat.search_people(u, q)],
        "short_q": bool(q) and len(q) < 2,
        "blocks": [(b.blocked, chat.display_name(b.blocked)) for b in u.chat_blocks.select_related("blocked")],
    })


def build_rows(msgs, viewer, lang, read_to, divider_id=None):
    """Serialized messages + what the server-rendered page needs: day chip, group edges, highlighted @names."""
    rows, prev = [], None
    for m, d in zip(msgs, chat.serialize_many(msgs, viewer, read_to)):
        d["show_day"] = day_label(lang, timezone.localtime(m.created).date()) if (not prev or prev["day"] != d["day"]) else ""
        d["new_here"] = d["id"] == divider_id
        d["first"] = bool(d["show_day"]) or d["new_here"] or not prev or prev["sender"] != d["sender"]
        if prev:
            prev["last"] = d["first"]
        d["last"] = True
        d["parts"] = chat.split_mentions(d["body"], d["mentions"])
        rows.append(d)
        prev = d
    return rows


@login_required
def room_view(request, pk):
    room = get_room(request, pk)
    u = request.user
    chat.touch(u)
    now = time.time()
    msgs = list(reversed(list(chat.with_related(room.messages).order_by("-id")[:chat.PAGE])))
    last_id = msgs[-1].id if msgs else 0
    seen_row = ChatRead.objects.filter(user=u, room=room).first()
    divider = chat.first_unread(room, u, msgs, seen_row.last_id if seen_row else None)
    read_to = chat.read_upto(room, u)
    chat.mark_read(u, room, last_id)
    if last_id:
        announce(room.pk, {"type": "chat.read", "user": u.pk, "upto": last_id})
    rows = build_rows(msgs, u, request.lang, read_to, divider)
    other = room.other(u) if room.kind == "direct" else None
    return render(request, "gym/chat_room.html", {
        "room": room, "msgs": rows, "last_id": last_id, "other": other, "pres": chat.presence(other) if other else None,
        "other_name": chat.display_name(other) if other else "", "other_initials": chat.initials(other) if other else "",
        "other_hue": chat.hue(other) if other else 0, "blocked": bool(other and chat.blocked_between(u, other)),
        "i_blocked": bool(other and ChatBlock.objects.filter(blocker=u, blocked=other).exists()),
        "has_more": bool(msgs) and room.messages.filter(id__lt=msgs[0].id).exists(), "first_id": msgs[0].id if msgs else 0,
        "muted": chat.is_muted(u, room), "stats": chat.room_stats(room), "pin": chat.pin_payload(room), "can_pin": room.kind == "room" and staff_mode(request),
        "now": now, "reactions": chat.REACTIONS, "edit_minutes": int(chat.EDIT_WINDOW.total_seconds() // 60),
    })


@require_POST
@login_required
def start_direct(request, uid):
    other = get_object_or_404(User, pk=uid, is_active=True, is_superuser=False, chat_visible=True)
    if other.pk == request.user.pk:
        raise Http404()
    if chat.blocked_between(request.user, other):
        flash(request, messages.ERROR, "chat_blocked")
        return redirect("chat")
    return redirect("chat_room", pk=chat.direct_room(request.user, other).pk)


@require_POST
@login_required
def send(request, pk):
    room = get_room(request, pk)
    image = None
    if request.content_type == "application/json":
        body, reply_to = jdata(request).get("body", ""), to_int(jdata(request).get("reply_to"))
        body = body if isinstance(body, str) else ""
    else:
        body, reply_to = request.POST.get("body", ""), to_int(request.POST.get("reply_to"))
        image = request.FILES.get("image")
    msg, err = chat.post_message(request.user, room, body, image, reply_to or None)
    chat.touch(request.user)
    if msg:
        announce(room.pk, {"type": "chat.new", "id": msg.id})  # open sockets in this room get it instantly
        chat.notify_mentions(msg, msg.new_mentions)
        chat.push_direct(msg)
    if wants_json(request):
        if err:
            return JsonResponse({"ok": False, "error": translate(request.lang, err)}, status=429 if err == "err_rate" else 400)
        out = {"ok": True, "message": chat.serialize(msg, request.user)}
        if msg.masked:
            out["notice"] = translate(request.lang, "chat_masked")
        return JsonResponse(out)
    if err:
        flash(request, messages.ERROR, err)
    elif msg.masked:
        flash(request, messages.WARNING, "chat_masked")
    return redirect("chat_room", pk=room.pk)


def rx_window(room, viewer):
    """Reactions of the latest messages, for clients that cannot receive socket events."""
    ids = list(room.messages.order_by("-id").values_list("id", flat=True)[:80])
    found = chat.reactions_map(ids, viewer)
    data = {str(i): found.get(i, []) for i in ids}
    return data, hashlib.md5(json.dumps(data, sort_keys=True).encode()).hexdigest()[:10]


@login_required
def poll(request, pk):
    room = get_room(request, pk)
    u = request.user
    chat.touch(u)
    now = time.time()
    after = to_int(request.GET.get("after"))
    try:
        since = datetime.fromtimestamp(float(request.GET.get("since", "")), dtz.utc)
    except (TypeError, ValueError, OverflowError, OSError):
        since = None
    read_to = chat.read_upto(room, u)
    msgs = list(chat.with_related(room.messages).filter(id__gt=after).order_by("id")[:100])
    last = msgs[-1].id if msgs else after
    if msgs:
        chat.mark_read(u, room, last)
        announce(room.pk, {"type": "chat.read", "user": u.pk, "upto": last})
    other = room.other(u) if room.kind == "direct" else None
    out = {"messages": chat.serialize_many(msgs, u, read_to), "last_id": last, "read_upto": read_to, "now": now,
           "presence": chat.presence(other) if other else None,
           "deleted": list(room.messages.filter(deleted=True, id__lte=after).order_by("-id").values_list("id", flat=True)[:50]),
           "pin": chat.pin_payload(room), "typing": chat.typing_names(room, u), "stats": chat.room_stats(room)}
    if since:
        edited = chat.with_related(room.messages).filter(edited_at__gt=since, id__lte=after, deleted=False).order_by("id")[:50]
        out["edited"] = chat.serialize_many(edited, u, read_to)
    rx, h = rx_window(room, u)
    if request.GET.get("rxh") != h:
        out["rx"], out["rxh"] = rx, h
    else:
        out["rxh"] = h
    return JsonResponse(out)


@login_required
@require_GET
def history(request, pk):
    """Older messages (infinite scroll up). With `target`, everything down to that message (at most HISTORY_JUMP) for jump-to-message."""
    room = get_room(request, pk)
    before, target = to_int(request.GET.get("before")), to_int(request.GET.get("target"))
    qs = chat.with_related(room.messages).filter(id__lt=before) if before else chat.with_related(room.messages).none()
    if target and target < before:
        rows = list(qs.filter(id__gte=target).order_by("-id")[:HISTORY_JUMP])
    else:
        rows = list(qs.order_by("-id")[:HISTORY_PAGE])
    rows.reverse()
    more = bool(rows) and room.messages.filter(id__lt=rows[0].id).exists()
    return JsonResponse({"messages": chat.serialize_many(rows, request.user, chat.read_upto(room, request.user)), "has_more": more})


@login_required
@require_GET
def search(request, pk):
    room = get_room(request, pk)
    if not chat.rate_ok("search", request.user, 30):
        return fail(request, "err_rate")
    return JsonResponse({"results": chat.search_messages(room, request.GET.get("q", ""))})


@login_required
@require_GET
def members(request, pk):
    """Autocomplete for @mentions: people who wrote in this public room lately."""
    room = get_room(request, pk)
    if room.kind != "room":
        return JsonResponse({"members": []})
    found = chat.participants(room, request.user, request.GET.get("q", ""))
    return JsonResponse({"members": [{"name": chat.display_name(p), "initials": chat.initials(p), "hue": chat.hue(p)} for p in found]})


@require_POST
@login_required
def typing(request, pk):
    room = get_room(request, pk)
    u = request.user
    if u.chat_banned or (room.kind == "direct" and chat.blocked_between(u, room.other(u))):
        return JsonResponse({"ok": False}, status=403)
    if chat.rate_ok("typing", u, 40):
        chat.typing_mark(room, u)
        announce(room.pk, {"type": "chat.typing", "user": u.pk, "name": chat.display_name(u)})
    return JsonResponse({"ok": True})


@require_POST
@login_required
def react(request, pk):
    msg = message_for(request, pk)
    emoji = jdata(request).get("emoji", "")
    ok, err = chat.set_reaction(request.user, msg, emoji if isinstance(emoji, str) else "")
    if not ok:
        return fail(request, err, 403 if err in ("chat_forbidden", "chat_blocked", "chat_banned") else 400)
    announce(msg.room_id, {"type": "chat.reaction", "id": msg.id})
    return JsonResponse({"ok": True, "id": msg.id, "reactions": chat.reactions_map([msg.id], request.user).get(msg.id, [])})


@login_required
@require_GET
def reaction_users(request, pk):
    msg = message_for(request, pk)
    return JsonResponse({"groups": chat.reaction_users(msg, request.user)})


@require_POST
@login_required
def edit_message(request, pk):
    msg = message_for(request, pk)
    if msg.sender_id != request.user.pk:
        raise Http404()
    body = jdata(request).get("body", "")
    msg, err = chat.edit_message(request.user, msg, body if isinstance(body, str) else "")
    if err:
        return fail(request, err, 403 if err in ("chat_forbidden", "chat_edit_expired") else 400)
    announce(msg.room_id, {"type": "chat.edit", "id": msg.id})
    chat.notify_mentions(msg, msg.new_mentions)
    out = {"ok": True, "message": chat.serialize(chat.with_related(ChatMessage.objects.filter(pk=msg.pk)).get(), request.user)}
    if msg.masked:
        out["notice"] = translate(request.lang, "chat_masked")
    return JsonResponse(out)


@require_POST
@login_required
def pin_message(request, pk):
    """Staff (admin mode) pin one message per public room, or unpin with id 0."""
    room = get_room(request, pk)
    if room.kind != "room" or not staff_mode(request):
        raise Http404()
    mid = to_int(jdata(request).get("id"))
    if mid:
        msg = get_object_or_404(ChatMessage, pk=mid, room=room, deleted=False)
        room.pinned_message = msg
    else:
        room.pinned_message = None
    room.save(update_fields=["pinned_message"])
    announce(room.pk, {"type": "chat.pin"})
    return JsonResponse({"ok": True, "pin": chat.pin_payload(room)})


@require_POST
@login_required
def mute_room(request, pk):
    room = get_room(request, pk)
    obj = RoomMute.objects.filter(user=request.user, room=room)
    if obj.exists():
        obj.delete()
        muted = False
    else:
        RoomMute.objects.create(user=request.user, room=room)
        muted = True
    return JsonResponse({"ok": True, "muted": muted})


@login_required
def photo(request, pk):
    """A chat photo: only people who can see the conversation get it (staff also for reported messages)."""
    msg = get_object_or_404(ChatMessage.objects.select_related("room"), pk=pk)
    staff_review = request.user.is_staff and request.session.get("admin_mode") and msg.reports.exists()
    if not (chat.can_access(request.user, msg.room) or staff_review) or msg.deleted or not msg.image:
        raise Http404()
    try:
        fh = msg.image.open("rb")
    except (FileNotFoundError, ValueError):
        raise Http404()
    ctype = image_type(fh.read(16))
    fh.seek(0)
    if not ctype:
        fh.close()
        raise Http404()
    resp = FileResponse(fh, content_type=ctype)
    resp["Cache-Control"] = "private, max-age=86400"
    resp["X-Content-Type-Options"] = "nosniff"
    resp["Content-Security-Policy"] = "default-src 'none'; sandbox"
    return resp


@require_POST
@login_required
def delete_message(request, pk):
    msg = message_for(request, pk)
    if msg.sender_id != request.user.pk:
        raise Http404()
    msg.deleted = True
    if msg.image:
        msg.image.delete(save=False)  # the photo is removed from the server, not just hidden
    msg.save(update_fields=["deleted", "image"])
    if msg.room.pinned_message_id == msg.id:
        ChatRoom.objects.filter(pk=msg.room_id).update(pinned_message=None)
        announce(msg.room_id, {"type": "chat.pin"})
    announce(msg.room_id, {"type": "chat.deleted", "id": msg.id})
    if wants_json(request):
        return JsonResponse({"ok": True})
    return redirect("chat_room", pk=msg.room_id)


# why a message is reported (key -> the text the admin sees); the member picks one, "other" needs a few words
REPORT_REASONS = {"insult": "Haqorat / so'kinish", "spam": "Spam / reklama", "scam": "Firibgarlik / pul so'rash",
                  "photo": "Noo'rin rasm", "threat": "Tahdid / bezovta qilish", "other": "Boshqa"}


@require_POST
@login_required
def report_message(request, pk):
    msg = message_for(request, pk)
    if msg.sender_id == request.user.pk or msg.deleted:
        raise Http404()
    data = jdata(request)
    kind, detail = data.get("kind", ""), data.get("detail", "")
    kind, detail = kind if isinstance(kind, str) else "", detail if isinstance(detail, str) else ""
    detail = " ".join(detail.split())[:150]
    if kind not in REPORT_REASONS or (kind == "other" and not detail):  # a report always says why, so the admin can judge it
        if wants_json(request):
            return JsonResponse({"ok": False, "error": translate(request.lang, "chat_report_reason")}, status=400)
        flash(request, messages.ERROR, "chat_report_reason")
        return redirect("chat_room", pk=msg.room_id)
    reason = REPORT_REASONS[kind] + (f": {detail}" if detail else "")
    ChatReport.objects.get_or_create(message=msg, reporter=request.user, defaults={"reason": reason[:200]})
    if wants_json(request):
        return JsonResponse({"ok": True, "text": translate(request.lang, "chat_report_sent")})
    flash(request, messages.SUCCESS, "chat_report_sent")
    return redirect("chat_room", pk=msg.room_id)


@require_POST
@login_required
def block_user(request, uid):
    other = get_object_or_404(User, pk=uid, is_superuser=False)
    if other.pk == request.user.pk:
        raise Http404()
    ChatBlock.objects.get_or_create(blocker=request.user, blocked=other)
    return redirect(request.POST.get("back") if request.POST.get("back", "").startswith("/chat/") else "chat")


@require_POST
@login_required
def unblock_user(request, uid):
    ChatBlock.objects.filter(blocker=request.user, blocked_id=uid).delete()
    return redirect(request.POST.get("back") if request.POST.get("back", "").startswith("/chat/") else "chat")
