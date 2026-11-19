"""The road from the gym to a customer, for the map in the cart and on the order page.

The browser never talks to a routing service: it asks our server (/delivery/route/), the server asks the public OSRM demo server for the
driving route between two points (only the two coordinates, rounded to ~10 m, go out; no cookie, no name) and keeps the answer in the cache.
Without an answer (service down, no road found, timeout) a straight line and the great-circle distance are returned, marked "line".
"""
import json
import logging
import urllib.error
import urllib.request

from django.core.cache import cache

from . import geo

log = logging.getLogger(__name__)
OSRM = "https://router.project-osrm.org/route/v1/driving/{a_lng},{a_lat};{b_lng},{b_lat}?overview=simplified&geometries=geojson"
CITY_SPEED_KMH = 28
MAX_POINTS = 300


def _key(a, b):
    return "route:%.4f,%.4f:%.4f,%.4f" % (a[0], a[1], b[0], b[1])


def straight(a, b):
    km = round(geo.haversine_km(a, b) * geo.ROAD_FACTOR, 1)
    speed = CITY_SPEED_KMH if km <= 25 else 65  # a courier in town, a carrier on the highway
    return {"ok": True, "source": "line", "coords": [[a[0], a[1]], [b[0], b[1]]], "km": km, "min": max(1, round(km / speed * 60))}


def road(a, b, timeout=6):
    """{"ok", "source": "road" | "line", "coords": [[lat, lng], ...], "km", "min"} from a to b (both (lat, lng))."""
    a, b = (round(a[0], 4), round(a[1], 4)), (round(b[0], 4), round(b[1], 4))
    key = _key(a, b)
    hit = cache.get(key)
    if hit:
        return hit
    out = None
    if geo.haversine_km(a, b) <= 400:  # a demo server is not asked for cross-country routes
        try:
            req = urllib.request.Request(OSRM.format(a_lat=a[0], a_lng=a[1], b_lat=b[0], b_lng=b[1]), headers={"User-Agent": "fitnes-zal-delivery/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                data = json.loads(r.read().decode("utf-8"))
            rt = data["routes"][0]
            pts = rt["geometry"]["coordinates"]  # GeoJSON order: [lng, lat]
            step = max(1, len(pts) // MAX_POINTS)
            coords = [[p[1], p[0]] for p in pts[::step]] + [[pts[-1][1], pts[-1][0]]]
            out = {"ok": True, "source": "road", "coords": coords, "km": round(rt["distance"] / 1000, 1), "min": max(1, round(rt["duration"] / 60))}
        except (urllib.error.URLError, OSError, ValueError, KeyError, IndexError, TypeError) as e:
            log.warning("route: %s", e.__class__.__name__)
    if out is None:
        out = straight(a, b)
        cache.set(key, out, 600)  # a failure is remembered briefly so a down service is not hammered
    else:
        cache.set(key, out, 86400)
    return out
