"""Delivery across Uzbekistan: where is the customer, how far, what does it cost and when does it arrive.

No outside service is used (so the customer's position never leaves our server): the places below are a built-in table, the
distance is the great-circle distance times a road factor, and price and time follow from the gym's delivery settings.

Two modes, chosen by the road distance:
  city    a courier from the gym, same day. Price = base fee (covers the first few km) + per-km rate beyond that. Time in minutes.
  region  intercity, sent with a carrier. Price continues from the city price at the edge of the city zone + a handling fee
          + a low per-km rate, so a farther place is never cheaper. Time in days.
"""
import math
from datetime import datetime, timedelta

from django.utils import timezone

# Uzbekistan's bounding box (lat_min, lat_max, lng_min, lng_max) and how far from the nearest known place a point may be
BOUNDS = (37.1, 45.65, 55.9, 73.2)
MAX_FROM_PLACE_KM = 150
ROAD_FACTOR = 1.3          # roads are longer than the straight line
CITY_SPEED_KMH = 25        # a courier in town
REGION_KM_PER_DAY = 500    # a carrier's average day on the road

# key: (uz, ru, en, lat, lng). Regional centres and the main cities of every region.
PLACES = {
    "tashkent": ("Toshkent", "Ташкент", "Tashkent", 41.3111, 69.2797),
    "nurafshon": ("Nurafshon", "Нурафшан", "Nurafshon", 41.0408, 69.3631),
    "chirchiq": ("Chirchiq", "Чирчик", "Chirchiq", 41.4689, 69.5822),
    "angren": ("Angren", "Ангрен", "Angren", 41.0167, 70.1436),
    "olmaliq": ("Olmaliq", "Алмалык", "Almalyk", 40.8500, 69.5983),
    "bekobod": ("Bekobod", "Бекабад", "Bekabad", 40.2208, 69.2697),
    "yangiyol": ("Yangiyo'l", "Янгиюль", "Yangiyul", 41.1119, 69.0475),
    "gulistan": ("Guliston", "Гулистан", "Gulistan", 40.4897, 68.7842),
    "jizzax": ("Jizzax", "Джизак", "Jizzakh", 40.1158, 67.8422),
    "zomin": ("Zomin", "Заамин", "Zaamin", 39.9600, 68.4000),
    "samarqand": ("Samarqand", "Самарканд", "Samarkand", 39.6542, 66.9597),
    "kattaqorgon": ("Kattaqo'rg'on", "Каттакурган", "Kattakurgan", 39.8997, 66.2569),
    "urgut": ("Urgut", "Ургут", "Urgut", 39.4000, 67.2500),
    "buxoro": ("Buxoro", "Бухара", "Bukhara", 39.7747, 64.4286),
    "kogon": ("Kogon", "Каган", "Kagan", 39.7222, 64.5514),
    "navoiy": ("Navoiy", "Навои", "Navoi", 40.0844, 65.3792),
    "zarafshon": ("Zarafshon", "Зарафшан", "Zarafshan", 41.5667, 64.2000),
    "qarshi": ("Qarshi", "Карши", "Karshi", 38.8606, 65.7891),
    "shahrisabz": ("Shahrisabz", "Шахрисабз", "Shakhrisabz", 39.0578, 66.8342),
    "termiz": ("Termiz", "Термез", "Termez", 37.2242, 67.2783),
    "denov": ("Denov", "Денау", "Denau", 38.2667, 67.9000),
    "andijon": ("Andijon", "Андижан", "Andijan", 40.7821, 72.3442),
    "asaka": ("Asaka", "Асака", "Asaka", 40.6400, 72.2400),
    "xonobod": ("Xonobod", "Ханабад", "Khanabad", 40.8000, 73.0000),
    "namangan": ("Namangan", "Наманган", "Namangan", 40.9983, 71.6726),
    "chust": ("Chust", "Чуст", "Chust", 41.0000, 71.2333),
    "pop": ("Pop", "Пап", "Pap", 40.8700, 71.1100),
    "fargona": ("Farg'ona", "Фергана", "Fergana", 40.3842, 71.7843),
    "qoqon": ("Qo'qon", "Коканд", "Kokand", 40.5286, 70.9425),
    "margilon": ("Marg'ilon", "Маргилан", "Margilan", 40.4711, 71.7247),
    "quvasoy": ("Quvasoy", "Кувасай", "Kuvasay", 40.3000, 71.9800),
    "urganch": ("Urganch", "Ургенч", "Urgench", 41.5500, 60.6333),
    "xiva": ("Xiva", "Хива", "Khiva", 41.3783, 60.3639),
    "beruniy": ("Beruniy", "Беруни", "Beruniy", 41.6911, 60.7525),
    "nukus": ("Nukus", "Нукус", "Nukus", 42.4531, 59.6103),
    "xojayli": ("Xo'jayli", "Ходжейли", "Khodjeyli", 42.4000, 59.4500),
    "qongirot": ("Qo'ng'irot", "Кунград", "Kungrad", 43.0833, 58.9000),
    "moynoq": ("Mo'ynoq", "Муйнак", "Muynak", 43.7683, 59.0236),
}


def place_name(key, lang="uz"):
    """The name of a place in the site language (Turkish falls back to English, Kyrgyz and Tajik to Russian)."""
    p = PLACES.get(key)
    if not p:
        return ""
    return p[1] if lang in ("ru", "ky", "tg") else p[2] if lang in ("en", "tr") else p[0]


def place_choices(lang="uz"):
    """[(key, name)] sorted by the name in `lang`, for a <select>."""
    return sorted(((k, place_name(k, lang)) for k in PLACES), key=lambda kv: kv[1])


def place_point(key):
    p = PLACES.get(key)
    return (p[3], p[4]) if p else None


def haversine_km(a, b):
    (la1, lo1), (la2, lo2) = a, b
    p1, p2 = math.radians(la1), math.radians(la2)
    dp, dl = p2 - p1, math.radians(lo2 - lo1)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * 6371.0088 * math.asin(math.sqrt(h))


def inside_bounds(lat, lng):
    return BOUNDS[0] <= lat <= BOUNDS[1] and BOUNDS[2] <= lng <= BOUNDS[3]


def nearest_place(lat, lng):
    """(key, straight distance km) of the closest known place."""
    best = min(PLACES, key=lambda k: haversine_km((lat, lng), place_point(k)))
    return best, haversine_km((lat, lng), place_point(best))


def parse_point(lat, lng):
    """(lat, lng) as floats, or None when missing, not a number or not a real coordinate."""
    try:
        la, lo = float(lat), float(lng)
    except (TypeError, ValueError):
        return None
    if not (math.isfinite(la) and math.isfinite(lo)) or not (-90 <= la <= 90 and -180 <= lo <= 180):
        return None
    return la, lo


def origin_of(gs):
    """Where deliveries start: the delivery point, else the gym's map coordinates, else the chosen city; None when the owner has set none."""
    if gs.delivery_lat is not None and gs.delivery_lng is not None:
        return float(gs.delivery_lat), float(gs.delivery_lng)
    if gs.map_lat is not None and gs.map_lng is not None:
        return float(gs.map_lat), float(gs.map_lng)
    return place_point(gs.delivery_origin) if gs.delivery_origin else None


def _up(n, step=1000):
    return int(math.ceil(n / step) * step)


def city_fee(gs, km):
    """Courier price inside the city zone: the base fee covers the first `delivery_base_km`, each further km costs `delivery_per_km`."""
    return int(gs.delivery_fee) + _up(max(0.0, km - gs.delivery_base_km) * gs.delivery_per_km)


def region_fee(gs, km):
    """Intercity price: the price at the edge of the city zone, plus the carrier's handling fee, plus a low rate for every km beyond it."""
    edge = city_fee(gs, gs.delivery_city_km)
    return edge + int(gs.region_extra_fee) + _up(max(0.0, km - gs.delivery_city_km) * gs.region_per_km)


def dispatch_time(gs, now=None):
    """(when the courier can leave, delayed): now while the gym is open and there is time to finish, else the next opening."""
    now = timezone.localtime(now or timezone.now())
    tz = now.tzinfo

    def at(day, t):
        return timezone.make_aware(datetime.combine(day, t), tz)

    today_open, today_close = at(now.date(), gs.open_time), at(now.date(), gs.close_time)
    if today_open <= now < today_close - timedelta(minutes=30):
        return now, False
    if now < today_open:
        return today_open, True
    return at(now.date() + timedelta(days=1), gs.open_time), True


def _five(n):
    return int(5 * round(n / 5.0))


def quote(gs, lat, lng, subtotal, now=None):
    """Everything the cart and the checkout need to know about delivering to (lat, lng).

    {"ok": False, "error": key}  outside Uzbekistan, or intercity delivery is switched off
    {"ok": True, "priced": False, ...}  the gym has no starting point yet: the old flat fee and no time
    {"ok": True, "priced": True, "mode", "km", "fee", "free", "place", "eta": {...}, ...}"""
    pt = parse_point(lat, lng)
    if pt is None or not inside_bounds(*pt):
        return {"ok": False, "error": "err_geo_out"}
    key, straight_to_place = nearest_place(*pt)
    if straight_to_place > MAX_FROM_PLACE_KM:
        return {"ok": False, "error": "err_geo_out"}
    out = {"ok": True, "place": key, "lat": round(pt[0], 6), "lng": round(pt[1], 6)}
    origin = origin_of(gs)
    if origin is None:
        flat = gs.delivery_cost(subtotal)
        return {**out, "priced": False, "mode": "city", "km": None, "fee": flat, "free": flat == 0, "left_for_free": 0, "eta": None}
    km = round(haversine_km(origin, pt) * ROAD_FACTOR, 1)
    start, delayed = dispatch_time(gs, now)
    if km <= gs.delivery_city_km:
        fee, mode = city_fee(gs, km), "city"
        free_from = gs.free_delivery_from
        minutes = gs.delivery_prep_min + km / CITY_SPEED_KMH * 60 + 5
        a = _five(minutes)
        eta = {"kind": "minutes", "a": a, "b": a + 15, "from": start + timedelta(minutes=a), "to": start + timedelta(minutes=a + 15),
               "delayed": delayed, "opens": gs.open_time.strftime("%H:%M")}
    else:
        if not gs.region_delivery_on:
            return {"ok": False, "error": "err_geo_far"}
        fee, mode = region_fee(gs, km), "region"
        free_from = gs.free_region_from
        d = max(1, math.ceil(km / REGION_KM_PER_DAY)) + (1 if delayed else 0)
        eta = {"kind": "days", "a": d, "b": d + 1, "from": start + timedelta(days=d), "to": start + timedelta(days=d + 1), "delayed": False, "opens": ""}
    free = bool(free_from and subtotal >= free_from)
    if free:
        fee = 0
    return {**out, "priced": True, "mode": mode, "km": km, "fee": fee, "free": free,
            "left_for_free": max(0, free_from - subtotal) if free_from and not free else 0, "eta": eta}
