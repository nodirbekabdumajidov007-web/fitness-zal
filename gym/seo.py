"""Search engines and link previews: robots.txt, sitemap.xml and the structured data (schema.org HealthClub) of the gym."""
import json
from xml.sax.saxutils import escape

from django.http import HttpResponse
from django.urls import reverse

from .models import GymSettings, Product

# pages that belong to a signed-in member, the staff or a half-finished flow: not for the search index
PRIVATE = ("/django-admin/", "/dashboard/", "/account/", "/cart/", "/checkout/", "/orders/", "/payments/", "/pay/", "/receipt/", "/card/", "/chat/", "/inbox/",
           "/progress/", "/calories/", "/workouts/", "/records/", "/coach/", "/courier/", "/login/", "/register/", "/forgot/", "/reset/", "/password/",
           "/verify/", "/auth/", "/healthz", "/assistant/", "/ai/", "/support/", "/gift/", "/delivery/", "/export/")
PUBLIC_NAMES = ("home", "about", "plans", "classes", "trainers", "shop", "reviews", "faq", "tools", "app_download", "oferta", "privacy", "refund")


def healthz(request):
    """For uptime monitors and the host's health check: 200 when the app answers and the database is reachable, 503 otherwise. No private data."""
    try:
        GymSettings.objects.exists()
    except Exception:
        return HttpResponse("db down", status=503, content_type="text/plain")
    return HttpResponse("ok", content_type="text/plain")


def site_root(request):
    return f"{request.scheme}://{request.get_host()}"


def robots(request):
    lines = ["User-agent: *", "Allow: /"] + [f"Disallow: {p}" for p in PRIVATE] + ["", f"Sitemap: {site_root(request)}/sitemap.xml", ""]
    return HttpResponse("\n".join(lines), content_type="text/plain; charset=utf-8")


def sitemap(request):
    root = site_root(request)
    paths = [reverse(n) for n in PUBLIC_NAMES]
    paths += [reverse("product", args=[pk]) for pk in Product.objects.filter(active=True).values_list("pk", flat=True)]
    body = "".join(f"<url><loc>{escape(root + p)}</loc></url>" for p in paths)
    xml = f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{body}</urlset>'
    return HttpResponse(xml, content_type="application/xml; charset=utf-8")


def gym_ld_json(request, gs=None):
    """schema.org HealthClub for the home and about pages; only facts the owner has entered (hours, phone, map pin, address, social links)."""
    gs = gs or GymSettings.load()
    root = site_root(request)
    data = {"@context": "https://schema.org", "@type": "HealthClub", "name": "Fitnes Zal", "url": root + "/",
            "image": root + "/static/img/og-share.png", "telephone": "+998" + (gs.phone or "").replace(" ", ""),
            "openingHoursSpecification": [{"@type": "OpeningHoursSpecification",
                                           "dayOfWeek": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
                                           "opens": gs.open_time.strftime("%H:%M"), "closes": gs.close_time.strftime("%H:%M")}]}
    if gs.address:
        data["address"] = {"@type": "PostalAddress", "streetAddress": gs.address, "addressCountry": "UZ"}
    if gs.map_lat is not None and gs.map_lng is not None:
        data["geo"] = {"@type": "GeoCoordinates", "latitude": float(gs.map_lat), "longitude": float(gs.map_lng)}
    same = [f"https://instagram.com/{gs.instagram}"] if gs.instagram else []
    if gs.telegram:
        same.append(gs.telegram)
    if same:
        data["sameAs"] = same
    # "</script>" can never appear inside the JSON
    return json.dumps(data, ensure_ascii=False).replace("<", "\\u003c")
