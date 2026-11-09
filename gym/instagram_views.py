"""The public webhook Meta calls: /webhooks/instagram/ (GET = ownership check, POST = events).
Not CSRF protected on purpose (Meta cannot send our cookie); the POST is authenticated by the HMAC signature instead."""
import json
import logging

from django.http import HttpResponse, HttpResponseForbidden, HttpResponseNotAllowed, JsonResponse
from django.views.decorators.csrf import csrf_exempt

from . import instagram_api as ig
from . import instagram_bot as bot

log = logging.getLogger("gym.instagram")


@csrf_exempt
def webhook(request):
    if not ig.configured():  # feature switched off: the route does not exist
        return HttpResponse(status=404)
    if request.method == "GET":
        if request.GET.get("hub.mode") == "subscribe" and ig.verify_token_ok(request.GET.get("hub.verify_token")):
            return HttpResponse(request.GET.get("hub.challenge", ""), content_type="text/plain")
        return HttpResponseForbidden("bad verify token")
    if request.method != "POST":
        return HttpResponseNotAllowed(["GET", "POST"])
    body = request.body  # the signature covers the raw bytes, so this is read before anything parses it
    if not ig.signature_ok(body, request.headers.get("X-Hub-Signature-256", "")):
        return HttpResponseForbidden("bad signature")
    try:
        payload = json.loads(body.decode("utf-8"))
    except ValueError:
        return JsonResponse({"ok": True})  # signed but not JSON: nothing to do, and no reason for Meta to retry
    try:
        ig.touch_webhook()
        bot.handle_payload(payload)
        bot.retry_pending()
        ig.maybe_refresh()
    except Exception:  # whatever happens, Meta must get a 200 (it would otherwise resend the same event for a day)
        log.exception("Instagram webhook processing failed")
    return JsonResponse({"ok": True})
