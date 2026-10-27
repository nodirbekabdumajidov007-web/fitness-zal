from django import template
from django.utils import timezone

from ..i18n import T

register = template.Library()
DEFAULT_PERKS = {
    "m1": ["perk_all"],
    "m3": ["perk_all", "perk_save", "perk_consult"],
}


def translate(lang, key, **kw):
    s = T.get(lang, T["uz"]).get(key) or T["uz"].get(key) or key
    return s.format(**kw) if kw else s


@register.simple_tag(takes_context=True)
def t(context, key, **kw):
    return translate(context.get("lang", "uz"), key, **kw)


@register.simple_tag(takes_context=True)
def plan_name(context, plan):
    key = "plan_" + plan.code
    return translate(context.get("lang", "uz"), key) if key in T["uz"] else plan.name


@register.simple_tag(takes_context=True)
def plan_perks(context, plan):
    lang = context.get("lang", "uz")
    if plan.code in DEFAULT_PERKS and not plan.perks.strip():
        return [translate(lang, k) for k in DEFAULT_PERKS[plan.code]]
    return [ln.strip() for ln in plan.perks.splitlines() if ln.strip()]


@register.simple_tag(takes_context=True)
def method_label(context, method):
    key = {"cash": "cash", "click": "click_online", "card": "card_transfer"}.get(method)
    return translate(context.get("lang", "uz"), key) if key else method


@register.filter
def short_money(value):
    """1 250 000 -> "1,3 mln", 450 000 -> "450 ming": fits on top of a chart bar."""
    try:
        v = int(value)
    except (TypeError, ValueError):
        return value
    if v >= 1_000_000:
        return f"{v / 1_000_000:.1f}".rstrip("0").rstrip(".").replace(".", ",") + " mln"
    if v >= 1000:
        return f"{v // 1000} ming"
    return str(v)


@register.filter
def get_item(mapping, key):
    try:
        return mapping.get(key, 0)
    except AttributeError:
        return 0


@register.simple_tag
def vstatic(path):
    """Static URL plus a version taken from the file's modification time, so browsers never keep an old CSS/JS after an update."""
    import os
    from django.contrib.staticfiles import finders
    from django.templatetags.static import static
    url = static(path)
    found = finders.find(path)
    return f"{url}?v={int(os.path.getmtime(found))}" if found else url


@register.filter
def money(value):
    try:
        return f"{int(value):,}".replace(",", " ")
    except (TypeError, ValueError):
        return value


@register.filter
def dmy(value):
    if not value:
        return ""
    if hasattr(value, "hour"):
        value = timezone.localtime(value)
    return f"{value:%d.%m.%Y}"


@register.filter
def dmyhm(value):
    return f"{timezone.localtime(value):%d.%m.%Y %H:%M}" if value else ""


@register.filter
def hm(value):
    return f"{value:%H:%M}" if value else ""


@register.filter
def stars(n):
    n = int(n or 0)
    return "★" * n + "☆" * (5 - n)


@register.filter
def split(value, sep=None):
    """"a b c"|split -> ["a", "b", "c"] (for short fixed lists written in a template)."""
    return str(value).split(sep)
