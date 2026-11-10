"""Instagram Direct auto-reply: webhook payload -> stored messages -> bot answer (from the assistant's knowledge base) -> send.

Order matters: every event is stored first (deduplicated by message id), only then the bot runs, and a failed send leaves the
incoming message "unprocessed" so a later webhook / `ig_retry` tries again. The bot never answers echoes, other bots' loops
(max 5 replies a minute per thread), paused threads, or a thread whose 24 hour window has closed."""
import logging
import re
from datetime import datetime, timedelta
from datetime import timezone as dt_tz

from django.core.cache import cache
from django.db import IntegrityError, transaction
from django.db.models import F
from django.utils import timezone

from . import assistant, assistant_kb as kb
from . import instagram_api as ig
from .extras import site_url
from .models import GymSettings, IgMessage, IgThread

log = logging.getLogger("gym.instagram")

BOT_RATE_PER_MIN = 5
MAX_CHUNKS = 4
MAX_ATTEMPTS = 3
PROFILE_EVERY = timedelta(days=1)

TXT = {
    "fallback": {"uz": "Rahmat! Administrator tez orada javob beradi.",
                 "ru": "Спасибо! Администратор скоро ответит.",
                 "en": "Thank you! An administrator will reply soon."},
    "attach": {"uz": "Rahmat! Hozircha faqat matnli xabarlarni o'qiy olaman. Savolingizni yozib yuboring, administrator ham tez orada ko'radi.",
               "ru": "Спасибо! Пока я читаю только текстовые сообщения. Напишите вопрос текстом, администратор тоже скоро посмотрит.",
               "en": "Thank you! I can only read text messages for now. Please type your question; an administrator will also take a look soon."},
    "welcome": {"uz": "Assalomu alaykum! Fitnes Zal yordamchisiman. Quyidagilarni so'rab ko'ring:\n- Narxlar\n- Ish vaqti\n- Manzil\n- Mashg'ulotlar\nYoki savolingizni yozing.",
                "ru": "Здравствуйте! Я помощник Fitnes Zal. Спросите, например:\n- Цены\n- Время работы\n- Адрес\n- Занятия\nИли просто напишите свой вопрос.",
                "en": "Hello! I am the Fitnes Zal assistant. Try asking:\n- Prices\n- Opening hours\n- Address\n- Classes\nOr just type your question."},
}
FALLBACKS = set(TXT["fallback"].values())


# ---------------------------------------------------------------- helpers
def _dt(ms):
    """Webhook timestamp (milliseconds since epoch) -> aware datetime, never in the future."""
    now = timezone.now()
    try:
        d = datetime.fromtimestamp(int(ms) / 1000, tz=dt_tz.utc)
    except (TypeError, ValueError, OverflowError, OSError):
        return now
    return min(d, now)


def _attachments(msg):
    out = []
    for a in (msg.get("attachments") or [])[:10]:
        if isinstance(a, dict):
            out.append({"type": str(a.get("type") or "file")[:30], "url": str((a.get("payload") or {}).get("url") or "")[:1500]})
    return out


def _thread(igsid):
    return IgThread.objects.get_or_create(igsid=str(igsid)[:64])[0]


def format_dm(text):
    """Instagram shows plain text: drop markdown marks, keep short paragraphs."""
    t = re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)", r"\1 (\2)", str(text or ""))
    t = re.sub(r"(\*\*|__|`)", "", t)
    t = re.sub(r"^[ \t]{0,3}#{1,6}[ \t]*", "", t, flags=re.M)
    t = re.sub(r"^[ \t]*[*•][ \t]+", "- ", t, flags=re.M)
    t = re.sub(r"[ \t]+\n", "\n", t)
    return re.sub(r"\n{3,}", "\n\n", t).strip()


def detect_lang(text):
    rows, script = assistant._rank(text)
    best = rows[0] if rows and rows[0][0] >= assistant.THRESHOLD else None
    return assistant.guess_lang(text, "uz", script, best[5] if best else None)


def build_reply(text, thread):
    """(reply text, needs_human) for a question."""
    lang = detect_lang(text)
    res = assistant.answer(text, lang, user=thread.member)
    t = TXT
    if not res["matched"] or (res["id"] in kb.PERSONAL and thread.member is None):
        return t["fallback"][lang], True
    base = site_url()
    if res["id"] == "hello":
        return t["welcome"][lang] + (f"\n{base}" if base else ""), False
    out = format_dm(res["answer"])
    if base:
        lines = [f"{lk['label']}: {base}{lk['url']}" for lk in (res.get("links") or [])[:2] if str(lk.get("url", "")).startswith("/")]
        if lines:
            out += "\n\n" + "\n".join(lines)
    return out, bool(res.get("approx"))  # a best-guess answer is still sent, but staff should take a look


# ---------------------------------------------------------------- storing events
def pause_for_staff(thread, gs=None):
    """A person answered: the bot keeps quiet in this thread for the configured number of hours."""
    hours = (gs or GymSettings.load()).ig_staff_pause_hours
    until = timezone.now() + timedelta(hours=hours) if hours else None
    IgThread.objects.filter(pk=thread.pk).update(bot_paused_until=until, needs_human=False, unread=0)


def _store_echo(ev, msg):
    mid = msg.get("mid")
    igsid = str((ev.get("recipient") or {}).get("id") or "")
    if not igsid or (mid and IgMessage.objects.filter(mid=mid).exists()):
        return  # our own API send (already stored) or a replayed event
    thread = _thread(igsid)
    when = _dt(ev.get("timestamp"))
    try:
        with transaction.atomic():
            IgMessage.objects.create(thread=thread, mid=mid, direction="out", kind="echo", text=str(msg.get("text") or ""),
                                     attachments=_attachments(msg), created=when)
    except IntegrityError:
        return
    IgThread.objects.filter(pk=thread.pk).update(last_message_at=when)
    if not cache.get(f"ig_sending_{igsid}"):  # an echo of a message we are sending right now is not a person stepping in
        pause_for_staff(thread)


def _store_incoming(sender, ev, msg):
    mid = msg.get("mid")
    when = _dt(ev.get("timestamp"))
    thread = _thread(sender)
    try:
        with transaction.atomic():
            m = IgMessage.objects.create(thread=thread, mid=mid, direction="in", kind="user", text=str(msg.get("text") or "")[:4000],
                                         attachments=_attachments(msg), created=when, processed=False)
    except IntegrityError:
        return None  # Meta retries deliveries for up to 36 hours: a known message id is ignored
    IgThread.objects.filter(pk=thread.pk).update(unread=F("unread") + 1)
    if not thread.last_user_message_at or when > thread.last_user_message_at:
        IgThread.objects.filter(pk=thread.pk).update(last_user_message_at=when)
    if not thread.last_message_at or when > thread.last_message_at:
        IgThread.objects.filter(pk=thread.pk).update(last_message_at=when)
    return m


def _store_event(ev, our_id):
    """Store one messaging event; returns an incoming IgMessage the bot should look at, or None."""
    msg = ev.get("message")
    sender = str((ev.get("sender") or {}).get("id") or "")
    if isinstance(msg, dict):
        if msg.get("is_deleted"):
            return None
        if msg.get("is_echo"):
            _store_echo(ev, msg)
            return None
        if not sender or (our_id and sender == our_id):
            return None
        return _store_incoming(sender, ev, msg)
    edit = ev.get("message_edit")
    if isinstance(edit, dict) and edit.get("mid") and edit.get("text") is not None:
        IgMessage.objects.filter(mid=edit["mid"]).update(text=str(edit["text"])[:4000])
    # "read", "reaction", "postback" and unknown events carry nothing the inbox needs
    return None


def handle_payload(payload):
    """Entry point of the webhook. Stores everything first, then lets the bot answer. Never raises."""
    if not isinstance(payload, dict) or payload.get("object") not in ("instagram", None):
        return 0
    todo = []
    for entry in payload.get("entry") or []:
        if not isinstance(entry, dict):
            continue
        our_id = ig.account_id() or str(entry.get("id") or "")
        for ev in entry.get("messaging") or []:
            try:
                m = _store_event(ev, our_id) if isinstance(ev, dict) else None
            except Exception:
                log.exception("Instagram event could not be stored")
                continue
            if m is not None:
                todo.append(m)
    for m in todo:
        try:
            process_message(m)
        except Exception:
            log.exception("Instagram bot crashed on message %s", m.pk)
    return len(todo)


# ---------------------------------------------------------------- sending
def send_to_thread(thread, text, kind="bot", author=None):
    """Send `text` (split into <= 1000 byte parts) and store what went out. Returns (sent_parts, error); error is "" when everything went."""
    if not ig.configured():
        return 0, "Instagram sozlanmagan"
    if not thread.window_open():
        return 0, "24 soatlik oyna yopilgan: foydalanuvchi yozmaguncha xabar yuborib bo'lmaydi"
    chunks = ig.split_text(text)[:MAX_CHUNKS]
    sent, error = 0, ""
    cache.set(f"ig_sending_{thread.igsid}", 1, 30)
    try:
        for chunk in chunks:
            try:
                mid = ig.send_text(thread.igsid, chunk)
            except ig.ApiError as e:
                error = f"{e}" + (f" (kod {e.code})" if e.code else "")
                log.warning("Instagram send failed: %s", error)
                IgMessage.objects.create(thread=thread, direction="out", kind=kind, text=chunk, sent_ok=False, error=error[:300], author=author)
                break
            now = timezone.now()
            row = IgMessage.objects.filter(mid=mid).first() if mid else None
            if row:  # the echo webhook beat us to it
                IgMessage.objects.filter(pk=row.pk).update(kind=kind, author=author, text=chunk)
            else:
                IgMessage.objects.create(thread=thread, mid=mid or None, direction="out", kind=kind, text=chunk, author=author, created=now)
            IgThread.objects.filter(pk=thread.pk).update(last_message_at=now)
            sent += 1
    finally:
        cache.delete(f"ig_sending_{thread.igsid}")
    return sent, error


def send_staff(thread, text, user):
    """A staff member answers from the panel: sends, then pauses the bot in this thread and clears the 'needs a person' flag."""
    text = (text or "").strip()
    if not text:
        return False, "Matn bo'sh"
    sent, error = send_to_thread(thread, text, "staff", user)
    if sent:
        pause_for_staff(thread)
        return True, "" if not error else f"Qisman yuborildi: {error}"
    return False, error or "Yuborilmadi"


# ---------------------------------------------------------------- the bot
def _done(msg, error=""):
    IgMessage.objects.filter(pk=msg.pk).update(processed=True, error=error[:300])


def _flag_human(thread):
    IgThread.objects.filter(pk=thread.pk).update(needs_human=True)


def process_message(msg):
    """Let the bot answer one stored incoming message (or decide not to)."""
    if msg.processed:
        return
    thread = IgThread.objects.get(pk=msg.thread_id)
    now = timezone.now()
    IgMessage.objects.filter(pk=msg.pk).update(attempts=F("attempts") + 1)
    gs = GymSettings.load()
    if not ig.configured():
        return
    if not gs.ig_auto_reply or thread.bot_paused(now):
        _flag_human(thread)  # nobody answers automatically: a person has to look
        return _done(msg)
    if not thread.window_open(now):
        return _done(msg, "24 soat o'tgan")
    since = now - timedelta(minutes=1)
    if IgMessage.objects.filter(thread=thread, direction="out", kind="bot", created__gte=since).count() >= BOT_RATE_PER_MIN:
        log.warning("Instagram bot rate limit hit for thread %s", thread.pk)
        _flag_human(thread)
        return _done(msg, "tezlik chegarasi")
    text = (msg.text or "").strip()
    if text and not any(c.isalnum() for c in text):  # only emoji / a thumbs-up: nothing to answer
        return _done(msg)
    if not text:
        if not msg.attachments:
            return _done(msg)
        reply, human = TXT["attach"]["uz"], True  # no words to detect a language from
    else:
        reply, human = build_reply(text, thread)
    if human:
        _flag_human(thread)
        if reply in FALLBACKS and thread.needs_human and IgMessage.objects.filter(
                thread=thread, direction="out", kind="bot", text__in=FALLBACKS, created__gte=now - timedelta(minutes=30)).exists():
            return _done(msg)  # already told them an administrator will answer
    sent, error = send_to_thread(thread, reply, "bot")
    if error and not sent:
        attempts = IgMessage.objects.values_list("attempts", flat=True).get(pk=msg.pk)
        IgMessage.objects.filter(pk=msg.pk).update(error=error[:300])
        if attempts >= MAX_ATTEMPTS:
            _flag_human(thread)
            _done(msg, error)
        return
    _done(msg)
    ensure_profile(thread)


def retry_pending(limit=5):
    """Send again what failed earlier (called after each webhook and by `ig_retry`)."""
    now = timezone.now()
    n = 0
    qs = IgMessage.objects.filter(direction="in", processed=False, attempts__lt=MAX_ATTEMPTS, created__gte=now - timedelta(hours=23),
                                  created__lt=now - timedelta(seconds=30)).select_related("thread").order_by("created")[:limit]
    for m in qs:
        try:
            process_message(m)
            n += 1
        except Exception:
            log.exception("Instagram retry crashed on message %s", m.pk)
    return n


def ensure_profile(thread, force=False):
    """Name, @username and picture of the sender, looked up at most once a day (the picture link expires)."""
    now = timezone.now()
    if not force and thread.profile_fetched_at and now - thread.profile_fetched_at < PROFILE_EVERY:
        return False
    try:
        p = ig.fetch_profile(thread.igsid)
    except ig.ApiError as e:
        log.info("Instagram profile lookup failed: %s", e)
        IgThread.objects.filter(pk=thread.pk).update(profile_fetched_at=now - PROFILE_EVERY + timedelta(hours=1))  # try again in an hour
        return False
    IgThread.objects.filter(pk=thread.pk).update(
        name=str(p.get("name") or "")[:200], username=str(p.get("username") or "")[:100],
        profile_pic_url=str(p.get("profile_pic") or p.get("profile_picture_url") or "")[:1000], profile_fetched_at=now)
    return True
