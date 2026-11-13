"""PWA plumbing: manifest, service worker, offline page, Android (TWA) asset links and Web Push (VAPID, via pywebpush)."""
import hashlib
import json
import logging
import os
from urllib.parse import urlparse

from django.conf import settings as dj
from django.contrib.auth.decorators import login_required
from django.contrib.staticfiles import finders
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import render
from django.templatetags.static import static
from django.views.decorators.http import require_POST

try:  # pywebpush is optional at import time: without it (or without VAPID keys) push is simply switched off
    from pywebpush import WebPushException, webpush
except ImportError:  # pragma: no cover
    webpush, WebPushException = None, Exception

log = logging.getLogger(__name__)

THEME = "#101318"  # the site's dark background
ICON_SIZES = (48, 72, 96, 128, 144, 152, 192, 256, 384, 512)
# Push services we are willing to POST to. The endpoint comes from the browser, so without a list a member could aim the server at any URL.
PUSH_HOSTS = ("googleapis.com", "mozilla.com", "mozaws.net", "windows.com", "apple.com")
MAX_SUBS_PER_USER = 10


def _s(path):
    return static(path)


def manifest(request):
    icons = [{"src": _s(f"img/icon-{s}.png"), "sizes": f"{s}x{s}", "type": "image/png", "purpose": "any"} for s in ICON_SIZES]
    icons += [{"src": _s(f"img/icon-maskable-{s}.png"), "sizes": f"{s}x{s}", "type": "image/png", "purpose": "maskable"} for s in (192, 512)]
    icons.append({"src": _s("img/icon-monochrome-512.png"), "sizes": "512x512", "type": "image/png", "purpose": "monochrome"})

    def shortcut(name, url, icon):
        return {"name": name, "short_name": name, "url": url, "icons": [{"src": _s(f"img/shortcut-{icon}.png"), "sizes": "96x96", "type": "image/png"}]}

    shots = [{"src": _s(f"img/shots/{n}-375.png"), "sizes": "750x1624", "type": "image/png", "form_factor": "narrow", "label": label}
             for n, label in (("home", "Bosh sahifa"), ("plans", "Abonementlar"), ("calories", "Kaloriya hisobi"), ("dashboard", "Shaxsiy kabinet"))]
    for n, label in (("home", "Bosh sahifa"), ("plans", "Abonementlar")):
        if finders.find(f"img/shots/{n}-1280.png"):  # wide screenshots are optional
            shots.append({"src": _s(f"img/shots/{n}-1280.png"), "sizes": "1280x720", "type": "image/png", "form_factor": "wide", "label": label})
    data = {
        "id": "/", "name": "Fitnes Zal", "short_name": "Fitnes Zal",
        "description": "Fitnes Zal: abonement, mashg'ulotlar jadvali, a'zo kartasi (QR), kaloriya hisobi va do'kon bir ilovada.",
        "start_url": "/?source=pwa", "scope": "/", "display": "standalone",
        "display_override": ["window-controls-overlay", "standalone"], "orientation": "portrait",
        "background_color": THEME, "theme_color": THEME, "lang": "uz", "dir": "ltr",
        "categories": ["health", "fitness", "lifestyle"], "prefer_related_applications": False,
        "icons": icons,
        "shortcuts": [shortcut("Kabinet", "/dashboard/", "dash"), shortcut("A'zo kartasi", "/card/", "card"),
                      shortcut("Mashg'ulotlar", "/classes/", "classes"), shortcut("Kaloriya", "/calories/", "food")],
        "screenshots": shots,
    }
    resp = JsonResponse(data, content_type="application/manifest+json", json_dumps_params={"ensure_ascii": False})
    resp["Cache-Control"] = "public, max-age=3600"
    return resp


def service_worker(request):
    path = finders.find("js/sw.js")
    if not path:
        raise Http404()
    with open(path, encoding="utf-8") as f:
        body = f.read()
    # the cache name changes only when the worker's own text changes, so users see "update available" only for real updates
    body = body.replace("__SW_VERSION__", hashlib.md5(body.encode("utf-8")).hexdigest()[:10])
    resp = HttpResponse(body, content_type="application/javascript")
    resp["Service-Worker-Allowed"] = "/"
    resp["Cache-Control"] = "no-cache"
    return resp


def offline(request):
    resp = render(request, "gym/offline.html")
    resp["Cache-Control"] = "no-cache"
    return resp


APK_STATIC = "app/fitnes-zal.apk"
APK_VERSION = "1.0"


def app_download(request):
    """Android app page: one button for the APK (the same TWA as on Google Play), the install steps and the iPhone way."""
    path = finders.find(APK_STATIC)
    size = round(os.path.getsize(path) / 1048576, 1) if path else None
    return render(request, "gym/app.html", {"apk": static(APK_STATIC) if path else "", "size_mb": size, "version": APK_VERSION})


def assetlinks(request):
    """Digital Asset Links: proves to Android that the Play Store app (TWA) and this site belong together."""
    pkg = (getattr(dj, "ANDROID_PACKAGE_NAME", "") or "").strip()
    prints = [p.strip().upper() for p in (getattr(dj, "ANDROID_SHA256_FINGERPRINTS", "") or "").split(",") if p.strip()]
    data = []
    if pkg and prints:
        data = [{"relation": ["delegate_permission/common.handle_all_urls"],
                 "target": {"namespace": "android_app", "package_name": pkg, "sha256_cert_fingerprints": prints}}]
    return JsonResponse(data, safe=False, content_type="application/json")


# ---------------------------------------------------------------- Web Push
def push_enabled():
    return bool(webpush and getattr(dj, "VAPID_PUBLIC_KEY", "") and getattr(dj, "VAPID_PRIVATE_KEY", ""))


def _allowed_endpoint(endpoint):
    u = urlparse(endpoint)
    host = (u.hostname or "").lower()
    return u.scheme == "https" and any(host == h or host.endswith("." + h) for h in PUSH_HOSTS)


def push_user(user, title, body="", url="/inbox/"):
    """Sends a push to every device the member enabled. Returns how many went out; dead subscriptions (404/410) are removed."""
    if not push_enabled():
        return 0
    from .models import PushSubscription
    subs = list(PushSubscription.objects.filter(user=user))
    if not subs:
        return 0
    payload = json.dumps({"title": title[:120], "body": body[:200], "url": url, "icon": _s("img/icon-192.png"), "badge": _s("img/badge-96.png")},
                         ensure_ascii=False)
    sent = 0
    for s in subs:
        try:
            webpush(subscription_info={"endpoint": s.endpoint, "keys": {"p256dh": s.p256dh, "auth": s.auth}}, data=payload,
                    vapid_private_key=dj.VAPID_PRIVATE_KEY, vapid_claims={"sub": dj.VAPID_SUBJECT}, ttl=86400, timeout=5)
            sent += 1
        except WebPushException as e:
            code = getattr(getattr(e, "response", None), "status_code", None)
            if code in (404, 410):
                s.delete()  # the browser unsubscribed or the app was removed
            else:
                log.warning("push failed (%s): %s", code, e)
        except Exception as e:  # a push must never break the request that triggered it
            log.warning("push error: %s", e)
    return sent


def _json(request):
    try:
        data = json.loads(request.body or b"{}")
        return data if isinstance(data, dict) else {}
    except ValueError:
        return {}


@login_required
@require_POST
def push_subscribe(request):
    from .models import PushSubscription
    if not push_enabled():
        return JsonResponse({"ok": False, "error": "push_off"}, status=503)
    d = _json(request)
    keys = d.get("keys") if isinstance(d.get("keys"), dict) else {}
    endpoint, p256dh, auth = (str(d.get("endpoint") or ""), str(keys.get("p256dh") or ""), str(keys.get("auth") or ""))
    if not (endpoint and p256dh and auth) or len(endpoint) > 600 or len(p256dh) > 255 or len(auth) > 100 or not _allowed_endpoint(endpoint):
        return JsonResponse({"ok": False, "error": "bad_subscription"}, status=400)
    PushSubscription.objects.update_or_create(  # the same browser signing in as someone else takes the subscription over
        endpoint=endpoint, defaults={"user": request.user, "p256dh": p256dh, "auth": auth, "user_agent": request.META.get("HTTP_USER_AGENT", "")[:300]})
    extra = PushSubscription.objects.filter(user=request.user).order_by("-created", "-pk").values_list("pk", flat=True)[MAX_SUBS_PER_USER:]
    PushSubscription.objects.filter(pk__in=list(extra)).delete()
    return JsonResponse({"ok": True})


@login_required
@require_POST
def push_unsubscribe(request):
    from .models import PushSubscription
    endpoint = str(_json(request).get("endpoint") or "")
    n = PushSubscription.objects.filter(user=request.user, endpoint=endpoint).delete()[0] if endpoint else 0
    return JsonResponse({"ok": True, "removed": n})
