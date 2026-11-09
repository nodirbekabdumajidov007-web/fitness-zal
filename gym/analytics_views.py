"""Views of «AI Analitika» (/django-admin/analytics/...): the page, the JSON endpoints behind it, the CSV export, the bulk reminder and the
assistant. Registered by GymAdminSite.get_urls, so every one of them sits behind the staff + admin-mode check.

JSON endpoints answer {"ok": true, ...} or {"ok": false, "error": "..."} with a proper status code; POSTs are CSRF-checked here (instead of
Django's HTML 403 page) so the browser code can show the error text."""
import json
import logging
from functools import wraps

from django.http import HttpResponse, JsonResponse
from django.middleware.csrf import CsrfViewMiddleware
from django.template.response import TemplateResponse
from django.urls import path
from django.utils import timezone

from . import analytics as an
from . import analytics_ai as ai

log = logging.getLogger(__name__)
PERM = "gym.view_payment"  # whoever may see takings may see the analytics built from them
HISTORY_MAX = 24


def fail(msg, status=400):
    return JsonResponse({"ok": False, "error": msg}, status=status)


def api(site, methods=("GET",)):
    def deco(fn):
        @wraps(fn)
        def inner(request, *a, **kw):
            try:
                if request.method not in methods:
                    return fail("Bu metod ruxsat etilmagan.", 405)
                if not request.user.has_perm(PERM):
                    return fail("Sizda bu bo'limga ruxsat yo'q.", 403)
                if request.method == "POST" and CsrfViewMiddleware(lambda r: None).process_view(request, None, (), {}) is not None:
                    return fail("Xavfsizlik tekshiruvi o'tmadi. Sahifani yangilab qayta urinib ko'ring.", 403)
                return fn(request, *a, **kw)
            except ValueError as e:
                return fail(str(e) or "Noto'g'ri so'rov.", 400)
            except Exception:  # noqa: BLE001 - the browser must get JSON, whatever went wrong
                log.exception("analytics api failed: %s", request.path)
                return fail("Ichki xato. Keyinroq qayta urinib ko'ring.", 500)
        inner.csrf_exempt = True  # checked above; keeps admin_view from putting Django's HTML failure page in front
        return site.admin_view(inner)
    return deco


def body(request):
    try:
        data = json.loads(request.body.decode("utf-8") or "{}")
    except (ValueError, UnicodeDecodeError):
        raise ValueError("So'rov JSON ko'rinishida bo'lishi kerak.")
    if not isinstance(data, dict):
        raise ValueError("So'rov JSON ko'rinishida bo'lishi kerak.")
    return data


def analytics_urls(site):
    from . import analytics_ai as _  # noqa: F401

    def page(request):
        p = an.period_from_request(request.GET)
        ctx = {**site.each_context(request), "title": "AI Analitika", "period": p.as_dict(), "data": an.bundle(p), "suggestions": ai.SUGGESTIONS[:6]}
        return TemplateResponse(request, "admin/analytics.html", ctx)

    @api(site)
    def section(request, name):
        p = an.period_from_request(request.GET)
        if name == "all":
            return JsonResponse({"ok": True, "section": "all", "period": p.as_dict(), "data": an.bundle(p)})
        fn = an.SECTIONS.get(name)
        if fn is None:
            return fail("Bunday bo'lim yo'q.", 404)
        return JsonResponse({"ok": True, "section": name, "period": p.as_dict(), "data": fn(p)})

    @api(site, methods=("POST",))
    def remind(request):
        data = body(request)
        ids = data.get("ids")
        if ids is not None:
            if not isinstance(ids, list) or len(ids) > 500 or not all(isinstance(i, int) and not isinstance(i, bool) for i in ids):
                raise ValueError("ids butun sonlar ro'yxati bo'lishi kerak.")
        res = an.send_expiry_reminders(ids, request.user)
        if not res["found"]:
            return JsonResponse({"ok": True, **res, "message": "Eslatma yuboriladigan a'zo topilmadi."})
        return JsonResponse({"ok": True, **res, "message": f"{res['sent']} kishiga eslatma yuborildi" + (f", {res['skipped']} tasiga bugun yuborilgan edi." if res["skipped"] else ".")})

    @api(site, methods=("GET", "POST"))
    def ask(request):
        hist = request.session.get("fz_ai_chat", [])
        if request.method == "GET":
            return JsonResponse({"ok": True, "history": hist, "suggestions": ai.SUGGESTIONS[:8]})
        data = body(request)
        if data.get("clear"):
            request.session["fz_ai_chat"] = []
            return JsonResponse({"ok": True, "history": []})
        q = data.get("q")
        if not isinstance(q, str) or not q.strip():
            raise ValueError("Savol yozing.")
        if len(q) > 500:
            raise ValueError("Savol juda uzun (500 belgigacha).")
        last = next((m["answer"]["intent"] for m in reversed(hist) if m.get("role") == "bot" and m["answer"].get("intent") not in (None, "unknown")), None)
        res = ai.answer(q, last=last)
        try:
            from .models_extra import AdminQuery
            AdminQuery.objects.create(user=request.user, text=ai.mask(q), intent=res.get("intent", ""), matched=res.get("intent") != "unknown")
        except Exception:  # noqa: BLE001 - the log must never break an answer
            log.exception("could not log the assistant question")
        hist = (hist + [{"role": "user", "text": q.strip()[:500]}, {"role": "bot", "answer": res}])[-HISTORY_MAX:]
        request.session["fz_ai_chat"] = hist
        return JsonResponse(res)

    def csv_view(request):
        p = an.period_from_request(request.GET)
        resp = HttpResponse(content_type="text/csv; charset=utf-8")
        resp["Content-Disposition"] = f'attachment; filename="analitika-{p.start:%Y%m%d}-{p.end:%Y%m%d}.csv"'
        return an.write_csv(resp, p)

    return [
        path("analytics/", site.gated(page, PERM), name="analytics"),
        path("analytics/csv/", site.gated(csv_view, PERM), name="analytics_csv"),
        path("analytics/api/ask/", ask, name="analytics_ask"),
        path("analytics/api/remind/", remind, name="analytics_remind"),
        path("analytics/api/<str:name>/", section, name="analytics_api"),
    ]
