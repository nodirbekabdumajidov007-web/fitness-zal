from urllib.parse import quote

from django.contrib.auth import get_user_model
from django.http import Http404
from django.shortcuts import redirect

from .i18n import LANGS

CSP = ("default-src 'self'; script-src 'self' https://accounts.google.com https://appleid.cdn-apple.com; "
       "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://accounts.google.com; "
       "font-src https://fonts.gstatic.com; img-src 'self' data: https:; connect-src 'self' https://accounts.google.com https://appleid.apple.com; "
       "frame-src https://accounts.google.com https://appleid.apple.com https://www.youtube-nocookie.com https://player.vimeo.com https://yandex.uz https://yandex.ru; media-src 'self' https:; "
       "frame-ancestors 'none'; base-uri 'none'; form-action 'self'")


class LangMiddleware:
    """request.lang comes from the fz_lang cookie (uz by default)."""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        lang = request.COOKIES.get("fz_lang", "uz")
        request.lang = lang if lang in LANGS else "uz"
        u = getattr(request, "user", None)
        if u is not None and u.is_authenticated and u.lang != request.lang:  # the Telegram bot and reminders speak the member's language
            get_user_model().objects.filter(pk=u.pk).update(lang=request.lang)
        return self.get_response(request)


class StaffAreaMiddleware:
    """Staff pages and the Django admin open only for staff who signed in with the `.admin` password suffix."""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        p = request.path
        if p.startswith("/django-admin/") or p.startswith("/staff/"):
            if p.startswith("/django-admin/login"):
                return redirect("/login/")
            u = request.user
            if not u.is_authenticated:
                return redirect(f"/login/?next={quote(p)}")
            if not u.is_staff:
                raise Http404()
            if not request.session.get("admin_mode"):
                return redirect("/login/?need_admin=1")
        return self.get_response(request)


class CspMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if not request.path.startswith("/django-admin/"):  # the built-in admin uses inline scripts
            host = request.get_host()  # live chat may open a socket back to this same host only
            response.headers.setdefault("Content-Security-Policy", CSP.replace("connect-src 'self'", f"connect-src 'self' ws://{host} wss://{host}"))
        return response
