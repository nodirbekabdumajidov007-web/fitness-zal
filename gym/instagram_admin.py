"""«Instagram xabarlari» inside the admin panel: /django-admin/instagram/...
Mounted by GymAdminSite.get_urls through site.admin_view, so every page needs a signed-in staff member in admin mode and every POST is CSRF protected."""
import re

from django.contrib import admin, messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils import timezone

from . import instagram_api as ig
from . import instagram_bot as bot
from .extras import site_url
from .forms import normalize_phone
from .models import IgMessage, IgThread, IgToken, User

LIMIT = 150
FILTERS = [("all", "Hammasi"), ("human", "Javob kerak"), ("unread", "O'qilmagan")]


def status(request):
    """The setup / status card shown on top of the inbox."""
    row = IgToken.objects.filter(pk=1).first()
    base = site_url() or f"{request.scheme}://{request.get_host()}"
    token_ok = bool(ig.get_token())
    return {"configured": ig.configured(), "has_secret": bool(ig.app_secret()), "has_verify": bool(ig.verify_token()), "has_token": token_ok,
            "account_id": ig.account_id(), "version": ig.version(), "webhook_url": base + reverse("instagram_webhook"),
            "expires_at": row.expires_at if row else None, "refreshed_at": row.refreshed_at if row else None,
            "last_webhook": row.last_webhook_at if row else None, "last_error": row.last_error if row else "",
            "token_masked": row.masked if row else "—"}


def _hm(delta):
    mins = int(delta.total_seconds() // 60)
    return f"{mins // 60} s {mins % 60} daq"


def _row(t, now):
    last = t.messages.order_by("-created", "-id").first()
    return {"t": t, "last": last, "open": t.window_open(now), "paused": t.bot_paused(now)}


def inbox(request):
    now = timezone.now()
    flt = request.GET.get("f", "all")
    qs = IgThread.objects.all()
    if flt == "human":
        qs = qs.filter(needs_human=True)
    elif flt == "unread":
        qs = qs.filter(unread__gt=0)
    q = (request.GET.get("q") or "").strip()[:60]
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(username__icontains=q.lstrip("@")))
    rows = [_row(t, now) for t in qs.order_by("-last_message_at", "-id")[:LIMIT]]
    ctx = {**admin.site.each_context(request), "title": "Instagram xabarlari", "st": status(request), "rows": rows, "flt": flt, "filters": FILTERS, "q": q,
           "n_human": IgThread.objects.filter(needs_human=True).count(), "n_unread": IgThread.objects.filter(unread__gt=0).count(),
           "n_all": IgThread.objects.count(), "has_threads": IgThread.objects.exists()}
    return TemplateResponse(request, "admin/ig_inbox.html", ctx)


def thread_page(request, pk):
    t = get_object_or_404(IgThread, pk=pk)
    now = timezone.now()
    if t.unread:
        IgThread.objects.filter(pk=t.pk).update(unread=0)
        t.unread = 0
    msgs = list(t.messages.order_by("-created", "-id")[:200])[::-1]
    for m in msgs:
        for a in m.attachments or []:  # only https links become clickable
            a["safe"] = str(a.get("url", "")).startswith("https://")
    guess = None
    if not t.member_id and t.username:
        guess = User.objects.filter(username__iexact=t.username).first()
    ctx = {**admin.site.each_context(request), "title": t.display_name, "t": t, "msgs": msgs, "open": t.window_open(now), "left_txt": _hm(t.window_left(now)),
           "paused": t.bot_paused(now), "guess": guess, "configured": ig.configured(), "st": status(request)}
    return TemplateResponse(request, "admin/ig_thread.html", ctx)


def _back(pk):
    return redirect("admin:ig_thread", pk)


def reply(request, pk):
    t = get_object_or_404(IgThread, pk=pk)
    if request.method != "POST":
        return _back(pk)
    ok, err = bot.send_staff(t, request.POST.get("text", ""), request.user)
    if ok:
        messages.success(request, "Xabar yuborildi. Bot shu suhbatda bir muddat jim turadi.")
        if err:
            messages.warning(request, err)
    else:
        messages.error(request, err)
    return _back(pk)


def action(request, pk, act):
    t = get_object_or_404(IgThread, pk=pk)
    if request.method != "POST":
        return _back(pk)
    if act == "pause":
        IgThread.objects.filter(pk=pk).update(auto_reply_paused=True)
        messages.success(request, "Bot shu suhbatda to'xtatildi.")
    elif act == "resume":
        IgThread.objects.filter(pk=pk).update(auto_reply_paused=False, bot_paused_until=None)
        messages.success(request, "Bot shu suhbatda yana yoqildi.")
    elif act == "resolve":
        IgThread.objects.filter(pk=pk).update(needs_human=False, unread=0)
        messages.success(request, "Hal qilindi deb belgilandi.")
    elif act == "unlink":
        IgThread.objects.filter(pk=pk).update(member=None)
        messages.success(request, "A'zo bog'lanishi olib tashlandi.")
    elif act == "link":
        v = (request.POST.get("member") or "").strip()[:60]
        u = None
        if v:
            m = re.fullmatch(r"(?i)fz-?0*(\d+)", v)
            phone = normalize_phone(v)
            cond = Q(username__iexact=v.lstrip("@"))
            if m:
                cond |= Q(pk=int(m.group(1)))
            if phone:
                cond |= Q(phone=phone)
            u = User.objects.filter(cond).first()
        if u:
            IgThread.objects.filter(pk=pk).update(member=u)
            messages.success(request, f"{u.full_name} bilan bog'landi.")
        else:
            messages.error(request, "Bunday a'zo topilmadi: telefon, login yoki FZ-0001 kodini yozing.")
    elif act == "profile":
        messages.success(request, "Profil yangilandi.") if bot.ensure_profile(t, force=True) else messages.error(request, "Profilni olib bo'lmadi.")
    return _back(pk)


def test_send(request):
    """«Test yuborish»: a short message to the most recent conversation (works only while its 24 hour window is open)."""
    t = IgThread.objects.order_by("-last_message_at", "-id").first()
    if request.method != "POST" or t is None:
        return redirect("admin:ig_inbox")
    sent, err = bot.send_to_thread(t, "Test: Fitnes Zal paneli Instagram bilan ulangan.", "staff", request.user)
    if sent:
        messages.success(request, f"Test xabari yuborildi: {t.display_name}")
    else:
        messages.error(request, err or "Yuborilmadi")
    return redirect("admin:ig_inbox")


def ig_urls(site):
    v = site.admin_view
    return [path("instagram/", v(inbox), name="ig_inbox"),
            path("instagram/test/", v(test_send), name="ig_test"),
            path("instagram/<int:pk>/", v(thread_page), name="ig_thread"),
            path("instagram/<int:pk>/reply/", v(reply), name="ig_reply"),
            path("instagram/<int:pk>/<str:act>/", v(action), name="ig_action")]
