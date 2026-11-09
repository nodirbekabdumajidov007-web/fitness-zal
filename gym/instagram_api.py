"""Instagram API with Instagram Login (graph.instagram.com): settings from env, sending, profile lookup, token refresh, webhook subscription.

Everything is read from the environment on every call, so the feature is off until IG_APP_SECRET, IG_VERIFY_TOKEN and a token are set.
Tokens are never logged: errors are reduced to Meta's own error code and message before they reach the log."""
import hashlib
import hmac
import json
import logging
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import timedelta

from django.utils import timezone

log = logging.getLogger("gym.instagram")

HOST = "https://graph.instagram.com"
TIMEOUT = 5  # seconds: the webhook answers inline, a slow Meta must not hang it
MAX_BYTES = 1000  # Instagram text limit is 1000 bytes of UTF-8 (Cyrillic letters take 2)
REFRESH_AFTER = timedelta(days=50)
SUBSCRIBED_FIELDS = "messages,messaging_seen,message_reactions,message_edit"


# ---------------------------------------------------------------- settings
def app_secret():
    return os.environ.get("IG_APP_SECRET", "").strip()


def verify_token():
    return os.environ.get("IG_VERIFY_TOKEN", "").strip()


def account_id():
    return os.environ.get("IG_ACCOUNT_ID", "").strip()


def version():
    return os.environ.get("IG_API_VERSION", "").strip() or "v27.0"


def env_token():
    return os.environ.get("IG_ACCESS_TOKEN", "").strip()


def configured():
    """True only when the app secret, the webhook verify token and an access token exist. Otherwise every Instagram route does nothing."""
    return bool(app_secret() and verify_token() and get_token())


# ---------------------------------------------------------------- token storage
def _fingerprint(token):
    return hashlib.sha256(token.encode()).hexdigest()[:16]


def get_token():
    """The token to use: the one stored (and refreshed) in the database; a different IG_ACCESS_TOKEN pasted later replaces it."""
    from .models import IgToken
    env = env_token()
    row = IgToken.objects.filter(pk=1).first()
    if env and (row is None or row.seed_hash != _fingerprint(env)):
        row = IgToken.load()
        row.access_token, row.seed_hash = env, _fingerprint(env)
        row.refreshed_at = row.expires_at = None  # age unknown: refreshed on the first run after 24 hours (Instagram refuses younger tokens)
        row.last_attempt_at = timezone.now()
        row.last_error = ""
        row.save()
    return row.access_token if row else ""


def touch_webhook():
    from .models import IgToken
    IgToken.objects.get_or_create(pk=1)
    IgToken.objects.filter(pk=1).update(last_webhook_at=timezone.now())


# ---------------------------------------------------------------- signatures
def signature_ok(body, header):
    """X-Hub-Signature-256 = "sha256=" + HMAC-SHA256(app secret, raw body)."""
    secret = app_secret()
    if not secret or not header:
        return False
    expected = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected.encode(), header.strip().encode("utf-8", "ignore"))


def verify_token_ok(given):
    want = verify_token()
    return bool(want) and hmac.compare_digest(want.encode(), str(given or "").encode("utf-8", "ignore"))


# ---------------------------------------------------------------- text splitting
_SENTENCE_END = re.compile(r"(?<=[.!?…])(?=\s)|(?<=\n)")


def _blen(s):
    return len(s.encode("utf-8"))


def _hard_cut(piece, limit):
    """Cut a piece that is longer than the limit: on spaces first, then (a very long word) on character boundaries."""
    out, cur = [], ""
    for word in piece.split(" "):
        while _blen(word) > limit:
            room = ""
            for ch in word:
                if _blen(room + ch) > limit:
                    break
                room += ch
            if cur:
                out.append(cur)
                cur = ""
            out.append(room)
            word = word[len(room):]
        cand = f"{cur} {word}" if cur else word
        if _blen(cand) > limit:
            out.append(cur)
            cur = word
        else:
            cur = cand
    if cur:
        out.append(cur)
    return out


def split_text(text, limit=MAX_BYTES):
    """Chunks of at most `limit` UTF-8 bytes, cut on sentence / line boundaries where possible."""
    text = (text or "").strip()
    if not text:
        return []
    chunks, cur = [], ""
    for piece in _SENTENCE_END.split(text):
        if not piece.strip():
            continue
        if _blen(piece.strip()) > limit:  # one huge sentence: flush what we have, cut it by words
            if cur.strip():
                chunks.append(cur.strip())
            cuts = [c for c in _hard_cut(piece.strip(), limit) if c]
            chunks.extend(cuts[:-1])
            cur = cuts[-1]
            continue
        cand = f"{cur}{piece}" if cur else piece.lstrip()
        if cur and _blen(cand.strip()) > limit:
            chunks.append(cur.strip())
            cand = piece.lstrip()
        cur = cand
    if cur.strip():
        chunks.append(cur.strip())
    return chunks


# ---------------------------------------------------------------- HTTP
class ApiError(Exception):
    """A failed call, reduced to something safe to log and show (never contains a token)."""

    def __init__(self, message, code=None, status=None):
        super().__init__(message)
        self.code, self.status = code, status


def _call(method, url, token=None, body=None):
    """One HTTP call; returns the parsed JSON or raises ApiError. `url` may contain a token (refresh): it is never logged."""
    headers = {"Accept": "application/json"}
    data = None
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            raw = r.read()
            return json.loads(raw.decode("utf-8", "replace") or "{}")
    except urllib.error.HTTPError as e:
        try:
            err = json.loads(e.read().decode("utf-8", "replace")).get("error", {})
        except Exception:
            err = {}
        raise ApiError(str(err.get("message") or f"HTTP {e.code}")[:200], err.get("code"), e.code) from None
    except Exception as e:  # timeout, DNS, TLS, bad JSON
        raise ApiError(f"{type(e).__name__}", None, None) from None


def _url(path, **params):
    q = ("?" + urllib.parse.urlencode(params)) if params else ""
    return f"{HOST}/{version()}/{path.lstrip('/')}{q}"


def send_text(igsid, text):
    """Send one message (already <= 1000 bytes). Returns the new message id or raises ApiError."""
    if _blen(text) > MAX_BYTES:
        raise ApiError("text too long")
    token = get_token()
    if not token:
        raise ApiError("no token")
    res = _call("POST", _url("me/messages"), token, {"recipient": {"id": str(igsid)}, "message": {"text": text}})
    return res.get("message_id") or ""


def fetch_profile(igsid):
    """{name, username, profile_pic} of a user who has messaged us (profile_pic links expire, so they are cached only for a day)."""
    token = get_token()
    if not token:
        raise ApiError("no token")
    return _call("GET", _url(urllib.parse.quote(str(igsid), safe=""), fields="name,username,profile_pic"), token)


def subscribe():
    """Subscribe our account to the webhook fields; returns the API answer ({"success": true})."""
    token = get_token()
    if not token:
        raise ApiError("no token")
    return _call("POST", _url("me/subscribed_apps", subscribed_fields=SUBSCRIBED_FIELDS), token)


# ---------------------------------------------------------------- token refresh
def refresh_due(row=None, now=None):
    from .models import IgToken
    row = row or IgToken.objects.filter(pk=1).first()
    now = now or timezone.now()
    if row is None or not row.access_token:
        return False
    return row.refreshed_at is None or now - row.refreshed_at >= REFRESH_AFTER


def refresh_token(force=False):
    """Exchange the stored long-lived token for a fresh one (60 more days). Returns (ok, message). Tries at most once a day unless forced."""
    from .models import IgToken
    get_token()  # makes sure a freshly pasted IG_ACCESS_TOKEN is in the table
    row = IgToken.objects.filter(pk=1).first()
    now = timezone.now()
    if row is None or not row.access_token:
        return False, "token yo'q"
    if not force:
        if not refresh_due(row, now):
            return True, "hali yangilash kerak emas"
        if row.last_attempt_at and now - row.last_attempt_at < timedelta(hours=24):
            return True, "bugun urinib ko'rilgan"
    IgToken.objects.filter(pk=1).update(last_attempt_at=now)
    try:
        res = _call("GET", f"{HOST}/refresh_access_token?" + urllib.parse.urlencode({"grant_type": "ig_refresh_token", "access_token": row.access_token}))
        new = res.get("access_token")
        if not new:
            raise ApiError("javobda token yo'q")
        days_s = int(res.get("expires_in") or 60 * 86400)
    except ApiError as e:
        log.warning("Instagram token refresh failed: %s (code %s)", e, e.code)
        IgToken.objects.filter(pk=1).update(last_error=str(e)[:300])
        return False, str(e)
    IgToken.objects.filter(pk=1).update(access_token=new, refreshed_at=now, expires_at=now + timedelta(seconds=days_s), last_error="")
    return True, "yangilandi"


def maybe_refresh():
    """Lazy trigger (called from the webhook): cheap when nothing is due, never raises."""
    try:
        if configured() and refresh_due():
            refresh_token()
    except Exception:
        log.exception("Instagram lazy token refresh crashed")
