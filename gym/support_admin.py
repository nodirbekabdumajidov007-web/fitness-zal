"""«Murojaatlar» inside the admin panel: /django-admin/support/...
Mounted by GymAdminSite.get_urls through site.admin_view, so every page needs a signed-in staff member in admin mode and every POST is CSRF protected."""
from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.urls import path
from django.utils import timezone

from . import chat, services, support
from .media import validate_image
from .models import SupportThread

LIMIT = 150
FILTERS = [("open", "Ochiq"), ("pending", "Kutilmoqda"), ("closed", "Yopilgan"), ("all", "Hammasi")]
WHO = [("all", "Hammasi"), ("mine", "Menga biriktirilgan"), ("free", "Biriktirilmagan")]
QUICK_REPLIES = [  # one click puts the text into the reply box (the member's name is added in front)
    "Rahmat murojaatingiz uchun! Hozir tekshirib, tez orada javob beramiz.",
    "Abonementingizni kabinetdagi «Abonementim» sahifasida ko'rishingiz mumkin.",
    "To'lov tasdiqlanishi bir necha daqiqa olishi mumkin. Agar yarim soatdan keyin ham o'zgarmasa, yozing.",
    "Zalga kelib, qabulxonada xodimlarimizga murojaat qilsangiz, joyida hal qilamiz.",
    "Savolingiz hal bo'ldimi? Agar yana yordam kerak bo'lsa, shu yerga yozing.",
]


def _row(t):
    last = t.messages.order_by("-created", "-id").first()
    return {"t": t, "last": last}


def inbox(request):
    chat.touch(request.user)
    flt = request.GET.get("f", "open")
    who = request.GET.get("w", "all")
    qs = SupportThread.objects.select_related("user", "assigned_to")
    if flt in ("open", "pending", "closed"):
        qs = qs.filter(status=flt)
    else:
        flt = "all"
    if who == "mine":
        qs = qs.filter(assigned_to=request.user)
    elif who == "free":
        qs = qs.filter(assigned_to__isnull=True)
    else:
        who = "all"
    q = (request.GET.get("q") or "").strip()[:60]
    if q:
        qs = qs.filter(Q(guest_name__icontains=q) | Q(guest_phone__icontains=q) | Q(user__first_name__icontains=q) | Q(user__last_name__icontains=q)
                       | Q(user__phone__icontains=q))
    counts = {k: SupportThread.objects.filter(status=k).count() for k, _ in FILTERS if k != "all"}
    counts["all"] = sum(counts.values())
    ctx = {**admin.site.each_context(request), "title": "Murojaatlar", "rows": [_row(t) for t in qs.order_by("-last_message_at", "-id")[:LIMIT]],
           "flt": flt, "who": who, "filters": FILTERS, "whos": WHO, "q": q, "counts": counts,
           "n_unread": SupportThread.objects.filter(unread_by_staff__gt=0).count()}
    return TemplateResponse(request, "admin/support_inbox.html", ctx)


def thread_page(request, pk):
    t = get_object_or_404(SupportThread.objects.select_related("user", "assigned_to"), pk=pk)
    chat.touch(request.user)  # staff presence: the widget's green "online" dot
    support.mark_seen_by_staff(t)
    msgs = list(t.messages.select_related("sender_user").order_by("-created", "-id")[:200])[::-1]
    membership = services.active_membership(t.user) if t.user_id else None
    ctx = {**admin.site.each_context(request), "title": t.display_name, "t": t, "msgs": msgs, "membership": membership, "quick": QUICK_REPLIES,
           "last_membership": (t.user.memberships.order_by("-expires").select_related("plan").first() if t.user_id and not membership else None)}
    return TemplateResponse(request, "admin/support_thread.html", ctx)


def _back(pk):
    return redirect("admin:support_thread", pk)


def reply(request, pk):
    t = get_object_or_404(SupportThread, pk=pk)
    if request.method != "POST":
        return _back(pk)
    text = request.POST.get("text", "").strip()
    image = request.FILES.get("image")
    if not text and not image:
        messages.error(request, "Javob matnini yozing.")
        return _back(pk)
    if image is not None:
        try:
            validate_image(image)
        except ValidationError as e:
            messages.error(request, e.messages[0])
            return _back(pk)
    support.staff_reply(t, request.user, text, image)
    messages.success(request, "Javob yuborildi." if t.user_id else "Javob saqlandi: mehmon saytga qaytganda ko'radi.")
    return _back(pk)


def action(request, pk, act):
    t = get_object_or_404(SupportThread, pk=pk)
    if request.method != "POST":
        return _back(pk)
    if act == "assign":
        SupportThread.objects.filter(pk=pk).update(assigned_to=request.user)
        messages.success(request, "Murojaat sizga biriktirildi.")
    elif act == "unassign":
        SupportThread.objects.filter(pk=pk).update(assigned_to=None)
        messages.success(request, "Biriktirish olib tashlandi.")
    elif act == "close":
        SupportThread.objects.filter(pk=pk).update(status=SupportThread.Status.CLOSED, unread_by_staff=0)
        messages.success(request, "Murojaat yopildi.")
    elif act == "reopen":
        SupportThread.objects.filter(pk=pk).update(status=SupportThread.Status.OPEN, last_message_at=timezone.now())
        messages.success(request, "Murojaat qayta ochildi.")
    from django.core.cache import cache
    cache.delete("fz_nav_badges")
    return _back(pk)


def support_urls(site):
    v = site.admin_view
    return [path("support/", v(inbox), name="support_inbox"),
            path("support/<int:pk>/", v(thread_page), name="support_thread"),
            path("support/<int:pk>/reply/", v(reply), name="support_reply"),
            path("support/<int:pk>/<str:act>/", v(action), name="support_action")]
