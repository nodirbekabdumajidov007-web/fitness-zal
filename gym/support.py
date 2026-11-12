"""Support widget backend: the member's / guest's conversation with the staff, FAQ search and "was this helpful?" votes.

Every endpoint answers JSON ({"ok": true, ...} or {"ok": false, "error": "..."}), needs the CSRF token on POST and only ever
touches the conversation that belongs to the caller: the signed-in member's own thread, or the guest thread whose secret token is in the
`fz_support` cookie. Thread ids are never accepted from the browser, so another person's conversation cannot be asked for."""
import json
import re
from datetime import timedelta

from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import transaction
from django.db.models import F
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from . import services, telegram
from .forms import normalize_phone
from .media import image_type, validate_image
from .models import FaqFeedback, FaqItem, GymSettings, SupportMessage, SupportThread, User
from .net import client_ip
from .templatetags.gym_tags import translate

COOKIE = "fz_support"
COOKIE_AGE = 60 * 60 * 24 * 365
MAX_TEXT = 1000
RATE_PER_MIN = 10  # messages per minute per member / guest
NEW_GUEST_PER_HOUR = 5  # new guest conversations per IP per hour
SEARCH_PER_MIN = 30
POLL_LIMIT = 100


# ------------------------------------------------------------------ small helpers
def err(request, key, status=400):
    return JsonResponse({"ok": False, "error": translate(getattr(request, "lang", "uz"), key)}, status=status)


def too_many(key, limit, ttl):
    """Counts a hit; True once more than `limit` hits happened inside `ttl` seconds."""
    cache.add(key, 0, ttl)
    try:
        return cache.incr(key) > limit
    except ValueError:
        cache.set(key, 1, ttl)
        return False


def guest_token(request):
    tok = request.COOKIES.get(COOKIE, "")
    return tok if re.fullmatch(r"[A-Za-z0-9_-]{20,64}", tok) else ""


def my_thread(request):
    """The caller's own conversation or None. A signed-in member is found by account, a guest only by the secret token."""
    if request.user.is_authenticated:
        return SupportThread.objects.filter(user=request.user).first()
    tok = guest_token(request)
    return SupportThread.objects.filter(user__isnull=True, guest_token=tok).first() if tok else None


def unread_for(request):
    if not hasattr(request, "_sw_unread"):
        t = my_thread(request)
        request._sw_unread = t.unread_by_user if t else 0
    return request._sw_unread


def staff_name(u):
    return (u.first_name or "").strip() or "Fitnes Zal"


ONLINE_MINUTES = 10  # a staff member who did something in the last 10 minutes shows a green dot


def staff_people():
    """Up to three staff faces for the widget header (people with a photo first). The list is cached for a minute; the green "online"
    dot is worked out from the stored last-activity time on every call, so it is never older than the clock says."""
    got = cache.get("sw:staff")
    if got is None:
        users = list(User.objects.filter(is_staff=True, is_active=True).order_by("-pk")[:12])
        users.sort(key=lambda u: (not u.avatar, -u.pk))
        got = [{"name": staff_name(u), "initials": u.initials, "src": u.avatar_src, "seen": u.last_seen.timestamp() if u.last_seen else 0} for u in users[:3]]
        cache.set("sw:staff", got, 60)
    limit = (timezone.now() - timedelta(minutes=ONLINE_MINUTES)).timestamp()
    return [{**p, "online": p["seen"] >= limit} for p in got]


def staff_online():
    """True when any staff account was active in the last ONLINE_MINUTES (chat / support inbox presence)."""
    got = cache.get("sw:online")
    if got is None:
        got = User.objects.filter(is_staff=True, is_active=True, last_seen__gte=timezone.now() - timedelta(minutes=ONLINE_MINUTES)).exists()
        cache.set("sw:online", got, 30)
    return got


def gym_is_open(gs):
    now = timezone.localtime().time()
    o, c = gs.open_time, gs.close_time
    return (o <= now < c) if o <= c else (now >= o or now < c)


def status(lang, gs=None):
    """The real opening status for the widget: open now, or closed until the opening time. No made-up reply-time promises."""
    gs = gs or GymSettings.load()
    opened = gym_is_open(gs)
    text = translate(lang, "sw_st_open") if opened else translate(lang, "sw_st_closed").replace("{time}", f"{gs.open_time:%H:%M}")
    hours = f"{gs.open_time:%H:%M}–{gs.close_time:%H:%M}"
    return {"open": opened, "text": text, "hours": hours, "online": staff_online(),
            "hours_answer": translate(lang, "sw_hours_ans").replace("{hours}", hours) + " " + text}


def phone_info(gs):
    """{"label", "href"} for the "Call us" row, or None when no phone is set."""
    digits = re.sub(r"\D", "", gs.phone or "")
    if digits.startswith("998"):
        digits = digits[3:]
    if len(digits) < 7:
        return None
    return {"label": f"+998 {gs.phone.strip()}" if not (gs.phone or "").strip().startswith("+") else gs.phone.strip(), "href": f"tel:+998{digits}"}


def membership_card(user, lang):
    """Small "N days left" card data for a signed-in member (None for guests)."""
    if not user.is_authenticated:
        return None
    m = services.active_membership(user)
    if not m:
        return {"active": False, "text": translate(lang, "sw_ms_none"), "days": 0}
    days = (timezone.localtime(m.expires).date() - timezone.localdate()).days
    text = translate(lang, "sw_ms_today") if days <= 0 else translate(lang, "sw_ms_left").replace("{n}", str(days))
    return {"active": True, "text": text, "days": max(days, 0)}


def image_url(msg):
    return f"/support/photo/{msg.pk}/" if msg.image else ""


def serialize(msg):
    who = msg.sender_user if msg.is_staff else None
    return {"id": msg.pk, "staff": msg.is_staff, "text": msg.text, "image": image_url(msg),
            "at": timezone.localtime(msg.created).isoformat(), "name": staff_name(who) if who else ("Fitnes Zal" if msg.is_staff else ""),
            "avatar": who.avatar_src if who else "", "initials": who.initials if who else "FZ", "read": bool(msg.read_at)}


def summary(thread):
    """The "latest message" card: who wrote last, a preview, whether the member has not read it yet."""
    if not thread:
        return None
    m = thread.messages.order_by("-created", "-id").first()
    if not m:
        return None
    s = serialize(m)
    return {"id": m.pk, "staff": m.is_staff, "name": s["name"] if m.is_staff else "", "avatar": s["avatar"], "initials": s["initials"],
            "preview": (m.text or "")[:120], "photo": bool(m.image and not m.text), "at": s["at"], "unread": thread.unread_by_user > 0 and m.is_staff,
            "status": thread.status}


def thread_info(thread):
    return {"status": thread.status, "unread": thread.unread_by_user} if thread else None


# ------------------------------------------------------------------ FAQ
CATEGORY_WORDS = {  # uz/ru/en stems that put an untagged question into a section
    "membership": ("abonement", "muzlat", "абонемент", "заморо", "membership", "freeze", "mehmon", "taklif", "guest"),
    "payment": ("to'lov", "tolov", "pul", "оплат", "платёж", "payment", "pay ", "karta", "refund", "qaytar", "возврат"),
    "classes": ("mashg'ulot", "mashgulot", "bron", "занят", "брон", "class", "book", "murabbiy", "тренер", "trainer"),
    "shop": ("do'kon", "dokon", "buyurtma", "yetkaz", "магазин", "заказ", "достав", "shop", "order", "delivery"),
    "account": ("parol", "profil", "akkaunt", "ro'yxat", "kirish", "пароль", "аккаунт", "профил", "регистр", "password", "account", "sign", "telegram"),
}
CATEGORY_KEYS = {"general": "sw_cat_general", "membership": "sw_cat_membership", "payment": "sw_cat_payment", "classes": "sw_cat_classes",
                 "shop": "sw_cat_shop", "account": "sw_cat_account"}


def category_of(item):
    if item.category:
        return item.category
    blob = f"{item.question_uz} {item.question_ru} {item.question_en}".lower()
    for cat, words in CATEGORY_WORDS.items():
        if any(w in blob for w in words):
            return cat
    return "general"


def faq_rows(lang):
    """Active FAQ items for the widget: id, question, answer (placeholders filled from the settings), section."""
    gs = GymSettings.load()
    fill = {"hours": f"{gs.open_time:%H:%M}–{gs.close_time:%H:%M}", "phone": f"+998 {gs.phone}", "address": gs.address or "—",
            "freeze_min": gs.freeze_min_days, "freeze_max": gs.freeze_max_days, "bonus": gs.referral_bonus_days, "cancel_hours": gs.class_cancel_hours}
    rows = []
    for it in FaqItem.objects.filter(active=True):
        ans = it.a(lang)
        for k, v in fill.items():
            ans = ans.replace("{" + k + "}", str(v))
        rows.append({"id": it.pk, "q": it.q(lang), "a": ans, "cat": category_of(it)})
    return rows


def _norm(s):
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", (s or "").lower().replace("'", "").replace("ʻ", ""))).strip()


def faq_search(rows, query, limit=6):
    words = [w for w in _norm(query).split() if len(w) > 1]
    if not words:
        return []
    scored = []

    def hit(w, text):  # a word matches itself or, for longer words, its first five letters (muzlatish ~ muzlatsa, замороз ~ заморозить)
        if len(w) < 4:  # short words only as whole words ("ish" must not match "ishlaydi")
            return f" {w} " in f" {text} "
        return w in text or (len(w) >= 6 and w[:5] in text)

    for r in rows:
        q, a = _norm(r["q"]), _norm(r["a"])
        score = sum(3 for w in words if hit(w, q)) + sum(1 for w in words if hit(w, a))
        if score:
            scored.append((score, r))
    scored.sort(key=lambda x: -x[0])
    return [r for _, r in scored[:limit]]


def brief(r):
    return {"id": r["id"], "q": r["q"], "cat": r["cat"]}


@require_GET
def faq_list(request):
    rows = faq_rows(request.lang)
    seen = []
    for r in rows:
        if r["cat"] not in seen:
            seen.append(r["cat"])
    cats = [{"key": c, "label": translate(request.lang, CATEGORY_KEYS[c]), "items": [brief(r) for r in rows if r["cat"] == c]} for c in CATEGORY_KEYS if c in seen]
    return JsonResponse({"ok": True, "categories": cats, "top": [brief(r) for r in rows[:4]]})


@require_GET
def faq_article(request, pk):
    row = next((r for r in faq_rows(request.lang) if r["id"] == pk), None)
    if not row:
        return err(request, "sw_err_notfound", 404)
    mine = _vote_filter(request)
    voted = FaqFeedback.objects.filter(faq_id=pk, **mine).first() if mine else None
    return JsonResponse({"ok": True, "id": pk, "q": row["q"], "a": row["a"], "cat": row["cat"], "voted": None if voted is None else voted.helpful})


def _vote_filter(request):
    if request.user.is_authenticated:
        return {"user": request.user}
    if not request.session.session_key:
        return None
    return {"user": None, "session_key": request.session.session_key}


@require_POST
def faq_feedback(request, pk):
    if too_many(f"sw:fb:{client_ip(request) or 'x'}", 30, 60):
        return err(request, "err_rate", 429)
    item = FaqItem.objects.filter(pk=pk, active=True).first()
    if not item:
        return err(request, "sw_err_notfound", 404)
    try:
        helpful = json.loads(request.body or b"{}").get("helpful")
    except (ValueError, AttributeError):
        helpful = None
    if not isinstance(helpful, bool):
        return err(request, "sw_err_bad")
    if not request.user.is_authenticated and not request.session.session_key:
        request.session.save()
    who = {"user": request.user} if request.user.is_authenticated else {"user": None, "session_key": request.session.session_key or ""}
    row, created = FaqFeedback.objects.get_or_create(faq=item, **who, defaults={"helpful": helpful})
    if not created and row.helpful != helpful:
        row.helpful = helpful
        row.save(update_fields=["helpful"])
    return JsonResponse({"ok": True, "helpful": helpful})


@require_GET
def search(request):
    """Help search: FAQ articles first, then the offline assistant's answer (with links) when it understood the question."""
    who = f"u{request.user.pk}" if request.user.is_authenticated else (client_ip(request) or "x")
    if too_many(f"sw:search:{who}", SEARCH_PER_MIN, 60):
        return err(request, "asst_rate", 429)
    q = (request.GET.get("q") or "").strip()[:200]
    if not q:
        return JsonResponse({"ok": True, "faq": [], "assistant": None})
    out = {"ok": True, "faq": [brief(r) for r in faq_search(faq_rows(request.lang), q)], "assistant": None}
    from . import assistant
    res = assistant.answer(q, request.lang, request.user)
    if res.get("matched"):
        links = [{"label": str(x.get("label", ""))[:60], "url": x["url"]} for x in res.get("links", []) if str(x.get("url", "")).startswith("/")]
        out["assistant"] = {"answer": res["answer"], "links": links}
    return JsonResponse(out)


# ------------------------------------------------------------------ the home tab
@require_GET
def home(request):
    t = my_thread(request)
    rows = faq_rows(request.lang)
    gs = GymSettings.load()
    return JsonResponse({"ok": True, "staff": staff_people(), "last": summary(t), "unread": t.unread_by_user if t else 0, "thread": thread_info(t),
                         "top": [brief(r) for r in rows[:4]], "telegram": gs.telegram if gs.telegram.startswith("https://") else "",
                         "status": status(request.lang, gs), "member": membership_card(request.user, request.lang)})


# ------------------------------------------------------------------ the conversation
@require_GET
def thread_view(request):
    """The whole conversation (or, with ?after=<id>, only what is newer: the poll). Always the caller's own thread."""
    t = my_thread(request)
    if not t:
        return JsonResponse({"ok": True, "thread": None, "messages": [], "unread": 0, "last_id": 0})
    qs = t.messages.select_related("sender_user")
    try:
        after = int(request.GET.get("after", 0))
    except ValueError:
        after = 0
    if after > 0:
        msgs = list(qs.filter(pk__gt=after).order_by("pk")[:POLL_LIMIT])
    else:
        msgs = list(qs.order_by("-pk")[:POLL_LIMIT])[::-1]
    seen = qs.filter(is_staff=False, read_at__isnull=False).order_by("-pk").values_list("pk", flat=True).first() or 0  # "seen" ticks on my own bubbles
    return JsonResponse({"ok": True, "thread": thread_info(t), "messages": [serialize(m) for m in msgs], "unread": t.unread_by_user,
                         "last_id": msgs[-1].pk if msgs else after, "read_upto": seen})


@require_POST
def mark_read(request):
    t = my_thread(request)
    if t:
        SupportMessage.objects.filter(thread=t, is_staff=True, read_at__isnull=True).update(read_at=timezone.now())
        SupportThread.objects.filter(pk=t.pk).update(unread_by_user=0)
    return JsonResponse({"ok": True, "unread": 0})


def _clean_guest(request):
    """(name, phone, email, error_key) from the guest form fields."""
    name = re.sub(r"\s+", " ", request.POST.get("name", "")).strip()[:80]
    phone = normalize_phone(request.POST.get("phone", ""))
    email = request.POST.get("email", "").strip()[:120]
    if len(name) < 2 or not phone:
        return None, None, None, "sw_err_contact"
    if email:
        try:
            validate_email(email)
        except ValidationError:
            return None, None, None, "sw_err_email"
    return name, phone, email, None


def staff_alert(thread, text):
    """New visitor message: the admin sidebar badge (cache dropped) and, if configured, Telegram to the staff chat."""
    cache.delete("fz_nav_badges")
    try:
        telegram.alert_admin(f"Yangi murojaat: {thread.display_name} ({thread.phone or '—'})\n{(text or '[rasm]')[:200]}")
    except Exception:  # a Telegram outage must never lose the customer's message
        pass


@require_POST
def send(request):
    if request.POST.get("website", "").strip():  # honeypot: a real person never sees this field. Pretend it worked, store nothing.
        return JsonResponse({"ok": True, "message": None, "thread": None})
    text = re.sub(r"\n{3,}", "\n\n", request.POST.get("text", "").replace("\r\n", "\n")).strip()
    image = request.FILES.get("image")
    if not text and not image:
        return err(request, "sw_err_empty")
    if len(text) > MAX_TEXT:
        return err(request, "sw_err_long")
    who = f"u{request.user.pk}" if request.user.is_authenticated else (guest_token(request) or client_ip(request) or "x")
    if too_many(f"sw:rate:{who}", RATE_PER_MIN, 60):
        return err(request, "err_rate", 429)
    if image is not None:
        try:
            validate_image(image)
        except ValidationError:
            return err(request, "chat_bad_image")
    t = my_thread(request)
    new_token = ""
    if t is None:
        if request.user.is_authenticated:
            t = SupportThread(user=request.user)
        else:
            name, phone, email, bad = _clean_guest(request)
            if bad:
                return err(request, bad)
            if too_many(f"sw:new:{client_ip(request) or 'x'}", NEW_GUEST_PER_HOUR, 3600):
                return err(request, "err_rate", 429)
            t =SupportThread(guest_name=name, guest_phone=phone, guest_email=email, guest_token=_make_token())
            new_token = t.guest_token
    with transaction.atomic():
        was_quiet = t.pk is None or t.unread_by_staff == 0
        t.status = SupportThread.Status.OPEN
        t.last_message_at = timezone.now()
        t.unread_by_user = 0
        t.save()
        msg = SupportMessage(thread=t, sender_user=request.user if request.user.is_authenticated else None, is_staff=False, text=text)
        if image is not None:
            msg.image.save(image.name, image, save=False)
        msg.save()
        SupportMessage.objects.filter(thread=t, is_staff=True, read_at__isnull=True).update(read_at=timezone.now())
        SupportThread.objects.filter(pk=t.pk).update(unread_by_staff=F("unread_by_staff") + 1)
    if was_quiet:
        staff_alert(t, text)
    else:
        cache.delete("fz_nav_badges")
    resp = JsonResponse({"ok": True, "message": serialize(msg), "thread": {"status": t.status, "unread": 0}})
    if new_token:
        resp.set_cookie(COOKIE, new_token, max_age=COOKIE_AGE, httponly=True, samesite="Lax", secure=request.is_secure())
    return resp


def _make_token():
    from .models_support import new_guest_token
    return new_guest_token()


@require_GET
def photo(request, pk):
    """A support photo: only the person it belongs to (member account or guest token) and staff in admin mode may fetch it."""
    msg = SupportMessage.objects.select_related("thread").filter(pk=pk).first()
    if not msg or not msg.image:
        raise Http404()
    mine = my_thread(request)
    staff = request.user.is_authenticated and request.user.is_staff and request.session.get("admin_mode")
    if not (staff or (mine and mine.pk == msg.thread_id)):
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


# ------------------------------------------------------------------ staff side (used by the admin pages)
def staff_reply(thread, staff_user, text, image=None):
    """A reply from staff: stored, the thread waits for the customer, and a signed-in member gets an inbox message + Web Push."""
    text = (text or "").strip()[:2000]
    with transaction.atomic():
        msg = SupportMessage(thread=thread, sender_user=staff_user, is_staff=True, text=text)
        if image is not None:
            msg.image.save(image.name, image, save=False)
        msg.save()
        SupportMessage.objects.filter(thread=thread, is_staff=False, read_at__isnull=True).update(read_at=timezone.now())
        SupportThread.objects.filter(pk=thread.pk).update(
            status=SupportThread.Status.PENDING, last_message_at=timezone.now(), unread_by_staff=0, unread_by_user=F("unread_by_user") + 1,
            assigned_to=thread.assigned_to_id or staff_user.pk)
    cache.delete("fz_nav_badges")
    thread.refresh_from_db()
    if thread.user_id:
        lang = thread.user.lang or "uz"
        try:
            services.notify(thread.user, translate(lang, "sw_notif_title"), text or translate(lang, "sw_notif_photo"), sender=staff_user,
                            telegram_too=False, push_too=True, url="/?support=messages")
        except Exception:
            pass
    return msg


def mark_seen_by_staff(thread):
    SupportMessage.objects.filter(thread=thread, is_staff=False, read_at__isnull=True).update(read_at=timezone.now())
    if thread.unread_by_staff:
        SupportThread.objects.filter(pk=thread.pk).update(unread_by_staff=0)
        cache.delete("fz_nav_badges")


# ------------------------------------------------------------------ page config for the widget
UI_KEYS = [
    "sw_open", "sw_close", "sw_tab_home", "sw_tab_msgs", "sw_tab_help", "sw_hello", "sw_guest", "sw_title", "sw_last", "sw_send_us",
    "sw_find_help", "sw_search_ph", "sw_telegram", "sw_just_now", "sw_min_ago", "sw_hour_ago", "sw_day_ago", "sw_you", "sw_team", "sw_photo",
    "sw_msg_ph", "sw_send", "sw_attach", "sw_remove_photo", "sw_empty_thread", "sw_guest_intro", "sw_name", "sw_phone", "sw_email", "sw_email_opt",
    "sw_closed_note", "sw_err_net", "sw_err_contact", "sw_err_long", "sw_err_empty", "sw_help_hint", "sw_results", "sw_no_results", "sw_ask_assistant",
    "sw_assistant_says", "sw_categories", "sw_back", "sw_helpful", "sw_yes", "sw_no", "sw_thanks", "sw_voice", "sw_voice_sub", "sw_new_msgs", "sw_sending",
    "sw_seen", "sw_status_open", "sw_status_pending", "sw_status_closed", "sw_unread", "sw_loading", "sw_retry", "sw_help_for_you",
    "sw_qa_label", "sw_qa_prices", "sw_qa_hours", "sw_qa_member", "sw_qa_coach", "sw_call", "sw_ask_title", "sw_ask_ph", "sw_ask_go", "sw_continue",
    "sw_ms_extend", "sw_ms_buy", "sw_online", "sw_pg_title", "sw_pg_sub", "sw_pg_chat", "sw_pg_faq", "sw_pg_all", "sw_pg_search", "sw_pg_widget_note",
]
LANG_SPEECH = {"uz": "uz-UZ", "ru": "ru-RU", "en": "en-US", "tr": "tr-TR", "ky": "ky-KG", "tg": "tg-TJ"}


def config(request):
    lang = getattr(request, "lang", "uz")
    from django.urls import reverse
    name = (request.user.first_name or "").strip() if request.user.is_authenticated else ""
    return {"lang": lang, "auth": bool(request.user.is_authenticated), "unread": unread_for(request), "max": MAX_TEXT,
            "name": name or translate(lang, "sw_guest"), "status": status(lang), "phone": phone_info(GymSettings.load()),
            "t": {k.replace("_", "-"): translate(lang, k) for k in UI_KEYS},  # hyphens: the page audit treats "a_b" words as leaked keys
            "urls": {"home": reverse("support_home"), "thread": reverse("support_thread"), "send": reverse("support_send"), "read": reverse("support_read"),
                     "search": reverse("support_search"), "faq": reverse("support_faq"), "faqBase": "/support/faq/", "login": reverse("login"),
                     "plans": reverse("plans"), "membership": reverse("membership"), "ai": reverse("ai"), "page": reverse("support_center")}}


# ------------------------------------------------------------------ the full-page support center (/yordam/)
@require_GET
def center(request):
    """Same conversation as the widget (same thread, same endpoints, guests by the same token cookie) on a roomy page, with the status,
    a call button, Telegram and the top questions in the aside. The floating widget is not drawn here: the page replaces it."""
    gs = GymSettings.load()
    rows = faq_rows(request.lang)
    tg = gs.telegram if (gs.telegram or "").startswith("https://") else ""
    return render(request, "gym/support_center.html", {"no_widget": True, "st": status(request.lang, gs), "call": phone_info(gs), "tg": tg,
                                                       "top_faq": rows[:6], "member_card": membership_card(request.user, request.lang)})
