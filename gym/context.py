from django.conf import settings as dj
from django.utils import timezone

from .models import GymSettings


def gym(request):
    s = GymSettings.load()
    now = timezone.localtime().time()
    o, c = s.open_time, s.close_time
    is_open = (o <= now < c) if o <= c else (now >= o or now < c)
    cart = request.session.get("cart", {}) if hasattr(request, "session") else {}
    def chat_unread():
        if not hasattr(request, "_chat_unread"):
            from . import chat
            request._chat_unread = chat.unread_total(request.user) if request.user.is_authenticated else 0
        return request._chat_unread

    def is_trainer():  # only computed if a template asks (the header shows a "Trainer panel" link)
        if not hasattr(request, "_is_trainer"):
            from .models import Trainer
            request._is_trainer = request.user.is_authenticated and Trainer.objects.filter(user=request.user, active=True).exists()
        return request._is_trainer

    def inbox_unread():
        if not hasattr(request, "_inbox_unread"):
            from .models import Notification
            request._inbox_unread = (Notification.objects.filter(user=request.user, read_at__isnull=True).count()
                                     if request.user.is_authenticated else 0)
        return request._inbox_unread

    return {"lang": getattr(request, "lang", "uz"), "is_trainer": is_trainer, "inbox_unread": inbox_unread, "gs": s, "is_open": is_open, "cart_count": sum(cart.values()), "chat_unread": chat_unread,
            "demo_on": bool(s.demo_payments and dj.ALLOW_DEMO_PAYMENTS),
            "admin_mode": bool(request.user.is_authenticated and request.user.is_staff and request.session.get("admin_mode")),
            "google_client_id": s.google_id(), "apple_client_id": s.apple_id(),
            "langs": (("uz", "O'zbekcha"), ("ru", "Русский"), ("en", "English"))}
