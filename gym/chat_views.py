from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from . import chat
from .consumers import announce
from .media import image_type
from .models import ChatBlock, ChatMessage, ChatReport, ChatRoom, User
from .templatetags.gym_tags import translate
from .views import flash, json_field


def wants_json(request):
    return request.headers.get("X-Requested-With") == "fetch"


def get_room(request, pk):
    room = get_object_or_404(ChatRoom, pk=pk)
    if not chat.can_access(request.user, room):
        raise Http404()
    return room


def day_label(lang, day):
    today = timezone.localdate()
    if day == today:
        return translate(lang, "today_cap")
    if day == today - timedelta(days=1):
        return translate(lang, "yesterday")
    return day.strftime("%d.%m.%Y")


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
        rooms.append({"room": r, "last": last, "last_name": chat.display_name(last.sender) if last else ""})
    return render(request, "gym/chat_inbox.html", {
        "directs": directs, "rooms": rooms, "q": q,
        "results": [{"u": p, "name": chat.display_name(p), "initials": chat.initials(p), "hue": chat.hue(p)} for p in chat.search_people(u, q)],
        "short_q": bool(q) and len(q) < 2,
        "blocks": [(b.blocked, chat.display_name(b.blocked)) for b in u.chat_blocks.select_related("blocked")],
    })


@login_required
def room_view(request, pk):
    room = get_object_or_404(ChatRoom, pk=pk)
    if not chat.can_access(request.user, room):
        raise Http404()
    u = request.user
    chat.touch(u)
    msgs = list(reversed(list(room.messages.select_related("sender").order_by("-id")[:chat.PAGE])))
    last_id = msgs[-1].id if msgs else 0
    read_to = chat.read_upto(room, u)
    chat.mark_read(u, room, last_id)
    if last_id:
        announce(room.pk, {"type": "chat.read", "user": u.pk, "upto": last_id})
    rows, prev = [], None
    for m in msgs:
        d = chat.serialize(m, u, read_to)
        day = timezone.localtime(m.created).date()
        d["show_day"] = day_label(request.lang, day) if (not prev or prev["day"] != d["day"]) else ""
        d["first"] = bool(d["show_day"]) or not prev or prev["sender"] != d["sender"]  # first bubble of a run from one person
        rows.append(d)
        prev = d
    other = room.other(u) if room.kind == "direct" else None
    return render(request, "gym/chat_room.html", {
        "room": room, "msgs": rows, "last_id": last_id, "other": other, "pres": chat.presence(other) if other else None,
        "other_name": chat.display_name(other) if other else "", "other_initials": chat.initials(other) if other else "",
        "other_hue": chat.hue(other) if other else 0, "blocked": bool(other and chat.blocked_between(u, other)),
        "i_blocked": bool(other and ChatBlock.objects.filter(blocker=u, blocked=other).exists()),
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
        body = json_field(request, "body")
    else:
        body = request.POST.get("body", "")
        image = request.FILES.get("image")
    msg, err = chat.post_message(request.user, room, body, image)
    chat.touch(request.user)
    if msg:
        announce(room.pk, {"type": "chat.new", "id": msg.id})  # open sockets in this room get it instantly
    if wants_json(request):
        if err:
            return JsonResponse({"ok": False, "error": translate(request.lang, err)}, status=429 if err == "err_rate" else 400)
        return JsonResponse({"ok": True, "message": chat.serialize(msg, request.user)})
    if err:
        flash(request, messages.ERROR, err)
    return redirect("chat_room", pk=room.pk)


@login_required
def poll(request, pk):
    room = get_room(request, pk)
    chat.touch(request.user)
    try:
        after = int(request.GET.get("after", 0))
    except ValueError:
        after = 0
    read_to = chat.read_upto(room, request.user)
    msgs = list(room.messages.select_related("sender").filter(id__gt=after).order_by("id")[:100])
    last = msgs[-1].id if msgs else after
    if msgs:
        chat.mark_read(request.user, room, last)
        announce(room.pk, {"type": "chat.read", "user": request.user.pk, "upto": last})
    other = room.other(request.user) if room.kind == "direct" else None
    return JsonResponse({"messages": [chat.serialize(m, request.user, read_to) for m in msgs], "last_id": last, "read_upto": read_to,
                         "presence": chat.presence(other) if other else None,
                         "deleted": list(room.messages.filter(deleted=True, id__lte=after).order_by("-id").values_list("id", flat=True)[:50])})


def message_for(request, pk):
    msg = get_object_or_404(ChatMessage.objects.select_related("room", "sender"), pk=pk)
    if not chat.can_access(request.user, msg.room):
        raise Http404()
    return msg


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
    announce(msg.room_id, {"type": "chat.deleted", "id": msg.id})
    if wants_json(request):
        return JsonResponse({"ok": True})
    return redirect("chat_room", pk=msg.room_id)


@require_POST
@login_required
def report_message(request, pk):
    msg = message_for(request, pk)
    if msg.sender_id == request.user.pk or msg.deleted:
        raise Http404()
    ChatReport.objects.get_or_create(message=msg, reporter=request.user, defaults={"reason": request.POST.get("reason", "")[:200]})
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
