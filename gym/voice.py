"""Voice assistant: the public facts it can read out (GET /voice/info/) and the config handed to gym/static/js/voice.js.

Speech recognition and speech synthesis run in the browser (Web Speech API); the server only answers with public gym facts.
Nothing personal is returned here: no member data, no phone numbers of members, only what the home page already shows.
"""
from django.core.cache import cache
from django.http import JsonResponse
from django.urls import reverse
from django.utils import timezone

from .i18n import T
from .models import GymSettings, Plan

# translation keys the script needs (the page puts them into <script type="application/json" id="voice-i18n">)
UI_KEYS = [
    "vc_title", "vc_open", "vc_close", "vc_idle", "vc_listening", "vc_start", "vc_stop", "vc_speaker_on", "vc_speaker_off", "vc_unsupported",
    "vc_ph", "vc_send", "vc_privacy", "vc_ex1", "vc_ex2", "vc_ex3", "vc_ex4", "vc_examples", "vc_help", "vc_mic_denied", "vc_no_speech",
    "vc_login_cal", "vc_login", "vc_going", "vc_state_open", "vc_state_closed", "vc_hours", "vc_phone", "vc_address",
    "vc_no_address", "vc_social", "vc_crowd_calm", "vc_crowd_mid", "vc_crowd_busy", "vc_plans", "vc_no_plans", "vc_added", "vc_cal_unknown",
    "vc_thinking", "vc_error", "vc_you", "vc_answer", "vc_cal_open", "vc_net",
    "nav_home", "nav_plans", "nav_shop", "nav_classes", "nav_trainers", "nav_calories", "nav_dash", "chat", "cart", "ai_coach",
    "tools", "nav_reviews", "nav_profile", "acc_title", "price_unit",
]

PAGES = {  # id -> url name
    "home": "home", "plans": "plans", "shop": "shop", "classes": "classes", "trainers": "trainers", "calories": "calories",
    "dashboard": "dashboard", "chat": "chat", "cart": "cart", "ai": "ai", "tools": "tools", "reviews": "reviews", "profile": "profile",
    "account": "account",
}
PAGE_LABEL = {  # id -> i18n key of the page name read out ("opening: Shop")
    "home": "nav_home", "plans": "nav_plans", "shop": "nav_shop", "classes": "nav_classes", "trainers": "nav_trainers",
    "calories": "nav_calories", "dashboard": "nav_dash", "chat": "chat", "cart": "cart", "ai": "ai_coach", "tools": "tools",
    "reviews": "nav_reviews", "profile": "nav_profile", "account": "acc_title",
}
SPEECH_LANG = {"uz": "uz-UZ", "ru": "ru-RU", "en": "en-US"}


def _t(lang, key):
    return T.get(lang, T["uz"]).get(key) or T["uz"].get(key) or key


def config(request):
    """Everything voice.js needs, except the facts (those come from /voice/info/ when asked)."""
    lang = getattr(request, "lang", "uz")
    return {
        "lang": lang, "speechLang": SPEECH_LANG.get(lang, "uz-UZ"),
        "auth": bool(request.user.is_authenticated),
        "t": {k.replace("_", "-"): _t(lang, k) for k in UI_KEYS},  # no underscores: the page audit treats "a_b" words as leaked keys
        "pages": {k: {"url": reverse(name), "label": _t(lang, PAGE_LABEL[k])} for k, name in PAGES.items()},
        "urls": {"assistant": "/assistant/ask/", "info": reverse("voice_info"), "calAdd": reverse("calories_add"), "calParse": reverse("calories_parse"),
                 "login": reverse("login"), "calories": reverse("calories")},
    }


def _is_open(gs, now):
    o, c = gs.open_time, gs.close_time
    return (o <= now < c) if o <= c else (now >= o or now < c)


def info(request):
    """Public gym facts for the assistant. Cached for a minute per language; the open/closed flag is always computed fresh."""
    from .views import crowd_level
    lang = getattr(request, "lang", "uz")
    key = f"voice:info:{lang}"
    data = cache.get(key)
    if data is None:
        gs = GymSettings.load()
        crowd = crowd_level()
        data = {
            "open": f"{gs.open_time:%H:%M}", "close": f"{gs.close_time:%H:%M}",
            "phone": "+998 " + gs.phone, "address": gs.address, "instagram": gs.instagram, "telegram": gs.telegram,
            "crowd": crowd["level"], "crowd_pct": crowd["pct"],
            "plans": [{"code": p.code, "name": _t(lang, "plan_" + p.code) if ("plan_" + p.code) in T["uz"] else p.name,
                       "months": p.months, "price": int(p.price)} for p in Plan.objects.filter(active=True)],
        }
        cache.set(key, data, 60)
    gs = GymSettings.load()
    out = dict(data, is_open=_is_open(gs, timezone.localtime().time()))
    resp = JsonResponse(out)
    resp["Cache-Control"] = "public, max-age=30"
    return resp
