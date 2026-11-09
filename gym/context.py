from django.conf import settings as dj
from django.utils import timezone

from . import pwa
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

    def my_membership():  # the account menu shows until when the membership runs
        if not hasattr(request, "_my_m"):
            from . import services
            request._my_m = services.active_membership(request.user) if request.user.is_authenticated else None
        return request._my_m

    def has_trainers():  # the Trainers links disappear while no trainer is active (cached for a minute: this runs on every page)
        from django.core.cache import cache
        from .models import Trainer
        got = cache.get("fz_has_trainers")
        if got is None:
            got = Trainer.objects.filter(active=True).exists()
            cache.set("fz_has_trainers", got, 60)
        return got

    return {"has_trainers": has_trainers, "lang": getattr(request, "lang", "uz"), "is_trainer": is_trainer, "my_membership": my_membership, "inbox_unread": inbox_unread, "gs": s, "is_open": is_open, "cart_count": sum(cart.values()), "chat_unread": chat_unread,
            "demo_on": bool(s.demo_payments and dj.ALLOW_DEMO_PAYMENTS),
            "admin_mode": bool(request.user.is_authenticated and request.user.is_staff and request.session.get("admin_mode")),
            "push_vapid": (dj.VAPID_PUBLIC_KEY if pwa.push_enabled() else ""), "google_client_id": s.google_id(), "apple_client_id": s.apple_id(),
            "langs": (("uz", "O'zbekcha"), ("ru", "Русский"), ("en", "English"))}
