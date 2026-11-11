"""Assistant: live answers that need more than the static knowledge base - the weather at the gym (Open-Meteo, no API key), the admin-panel
hint (different for staff and for everybody else) and the personal "how long should I train" line.

Network rules: one server-side call with a 4 s timeout, the result (or the failure) is cached, and a failure never breaks an answer: the
user just gets "could not get the weather right now". Tests patch `_http_json`; under `manage.py test` it never touches the network.
"""
import json
import sys
import urllib.parse
import urllib.request

from django.core.cache import cache

TASHKENT = (41.3111, 69.2797)  # used when the gym has no map coordinates in GymSettings
TIMEOUT = 4
CACHE_SECONDS = 30 * 60
FAIL_SECONDS = 2 * 60  # do not hammer a dead service on every question
URL = "https://api.open-meteo.com/v1/forecast"

# WMO weather code -> (kind, uz, ru, en). kind drives the training tip.
_WMO = {
    0: ("clear", "ochiq osmon", "ясно", "clear sky"),
    1: ("clear", "asosan ochiq", "преимущественно ясно", "mostly clear"),
    2: ("cloud", "qisman bulutli", "переменная облачность", "partly cloudy"),
    3: ("cloud", "bulutli", "пасмурно", "overcast"),
    45: ("fog", "tuman", "туман", "fog"), 48: ("fog", "qirovli tuman", "изморозь и туман", "freezing fog"),
    51: ("rain", "yengil mayda yomg'ir", "лёгкая морось", "light drizzle"), 53: ("rain", "mayda yomg'ir", "морось", "drizzle"),
    55: ("rain", "kuchli mayda yomg'ir", "сильная морось", "heavy drizzle"),
    56: ("rain", "muzlovchi mayda yomg'ir", "ледяная морось", "freezing drizzle"), 57: ("rain", "kuchli muzlovchi yomg'ir", "сильная ледяная морось", "heavy freezing drizzle"),
    61: ("rain", "yengil yomg'ir", "небольшой дождь", "light rain"), 63: ("rain", "yomg'ir", "дождь", "rain"), 65: ("rain", "kuchli yomg'ir", "сильный дождь", "heavy rain"),
    66: ("rain", "muzlovchi yomg'ir", "ледяной дождь", "freezing rain"), 67: ("rain", "kuchli muzlovchi yomg'ir", "сильный ледяной дождь", "heavy freezing rain"),
    71: ("snow", "yengil qor", "небольшой снег", "light snow"), 73: ("snow", "qor", "снег", "snow"), 75: ("snow", "kuchli qor", "сильный снегопад", "heavy snow"),
    77: ("snow", "qor donalari", "снежная крупа", "snow grains"),
    80: ("rain", "yengil jala", "небольшие ливни", "light rain showers"), 81: ("rain", "jala", "ливни", "rain showers"), 82: ("rain", "kuchli jala", "сильные ливни", "violent rain showers"),
    85: ("snow", "yengil qor yog'ishi", "небольшой снегопад", "light snow showers"), 86: ("snow", "kuchli qor yog'ishi", "сильный снегопад", "heavy snow showers"),
    95: ("storm", "momaqaldiroq", "гроза", "thunderstorm"), 96: ("storm", "do'l bilan momaqaldiroq", "гроза с градом", "thunderstorm with hail"),
    99: ("storm", "kuchli do'l bilan momaqaldiroq", "гроза с сильным градом", "thunderstorm with heavy hail"),
}

L = {
    "now": {"uz": "Zal joylashgan hududda hozir {cond}, havo harorati {t}°C (his etilishi {f}°C), shamol {w} km/soat{rain}. Bugun {lo}…{hi}°C.",
            "ru": "В районе зала сейчас {cond}, температура {t}°C (ощущается как {f}°C), ветер {w} км/ч{rain}. Сегодня {lo}…{hi}°C.",
            "en": "Around the gym right now it is {cond}, {t}°C (feels like {f}°C), wind {w} km/h{rain}. Today {lo}…{hi}°C."},
    "rain": {"uz": ", yog'in {p} mm", "ru": ", осадки {p} мм", "en": ", precipitation {p} mm"},
    "tip": {"uz": "Mashq maslahati: {tip}", "ru": "Совет по тренировке: {tip}", "en": "Training tip: {tip}"},
    "fail": {"uz": "Kechirasiz, ob-havo ma'lumotini hozir olib bo'lmadi (xizmat javob bermadi). Birozdan keyin qayta so'rang yoki ob-havo ilovasiga qarang.",
             "ru": "Сейчас не удалось получить данные о погоде (сервис не ответил). Спросите чуть позже или посмотрите в приложении погоды.",
             "en": "I could not get the weather data right now (the service did not answer). Please ask again in a moment or check a weather app."},
    "tips": {
        "heat": {"uz": "juda issiq: ko'proq suv iching, og'ir kardioni zalning sovuq (konditsionerli) joyida qiling, ochiq havoda mashqni ertalab yoki kechga qoldiring.",
                 "ru": "очень жарко: пейте больше воды, тяжёлое кардио делайте в прохладном зале, уличные тренировки перенесите на утро или вечер.",
                 "en": "very hot: drink more water, do hard cardio indoors in the cool gym and move outdoor sessions to early morning or evening."},
        "warm": {"uz": "iliq/issiq: suvni tez-tez iching, yengil kiyim kiying, razminkani qisqartirsangiz bo'ladi, lekin intensivlikni biroz pasaytiring.",
                 "ru": "тепло/жарко: пейте воду чаще, одевайтесь легче, интенсивность лучше немного снизить.",
                 "en": "warm/hot: sip water often, dress light and ease the intensity a little."},
        "cold": {"uz": "sovuq: razminkani odatdagidan uzoqroq (10-15 daqiqa) qiling, qatlamli kiyining va mushak sovib qolmasin; zalga borish yaxshi tanlov.",
                 "ru": "холодно: разминайтесь дольше обычного (10-15 минут), одевайтесь слоями, не давайте мышцам остывать; зал - хороший выбор.",
                 "en": "cold: warm up longer than usual (10-15 minutes), dress in layers and keep muscles from cooling; the gym is a good choice."},
        "freeze": {"uz": "qattiq sovuq: ochiq havoda mashq qilmang, zalda mashq qiling va uzoqroq razminka qiling; yo'lda issiq kiyining.",
                   "ru": "сильный мороз: на улице не тренируйтесь, занимайтесь в зале и разминайтесь дольше; одевайтесь теплее по дороге.",
                   "en": "freezing: skip outdoor training, work out in the gym and warm up longer; dress warmly on the way."},
        "wet": {"uz": "yomg'ir/qor: ochiq havodagi yugurish o'rniga zalda mashq qiling (yo'lakcha, kuch mashqlari); sirpanchiq yo'lda yugurmang.",
                "ru": "дождь/снег: вместо пробежки на улице тренируйтесь в зале (дорожка, силовые); не бегайте по скользкому.",
                "en": "rain/snow: train indoors instead of running outside (treadmill, strength work) and avoid slippery paths."},
        "storm": {"uz": "momaqaldiroq: ochiq havoda mashq qilmang, zalda qoling.",
                  "ru": "гроза: не тренируйтесь на улице, оставайтесь в зале.",
                  "en": "thunderstorm: do not train outdoors, stay in the gym."},
        "fog": {"uz": "tuman: ko'rinish yomon, ochiq havoda yugurishda ehtiyot bo'ling yoki zalda mashq qiling.",
                "ru": "туман: видимость плохая, на пробежке осторожнее или тренируйтесь в зале.",
                "en": "fog: visibility is poor, be careful when running outside or train indoors."},
        "wind": {"uz": "kuchli shamol: ochiq havoda yugurish qiyin va sovuq his qilinadi, zalda mashq qiling.",
                 "ru": "сильный ветер: бегать на улице тяжело и прохладно, лучше тренироваться в зале.",
                 "en": "strong wind: running outside is hard and chilly, train indoors."},
        "good": {"uz": "mashq uchun qulay ob-havo: ochiq havoda yurish yoki yugurish ham, zalda mashq ham yaxshi. Razminkani unutmang.",
                 "ru": "погода хорошая для тренировки: можно и бегать или гулять на улице, и заниматься в зале. Не забудьте разминку.",
                 "en": "good weather for training: fine for a run or walk outside as well as for the gym. Do not skip the warm-up."},
    },
    "admin_staff": {"uz": "Admin panelga shu havola orqali kiring: /django-admin/. U faqat xodimlar uchun.",
                    "ru": "В админ-панель заходите по ссылке: /django-admin/. Она только для сотрудников.",
                    "en": "Open the admin panel here: /django-admin/. It is for staff only."},
    "admin_other": {"uz": "Admin panel faqat zal xodimlari uchun, a'zolar va mehmonlar uchun ochiq emas. Sizga kerakli narsalar Kabinet (abonement, natijalar, buyurtmalar) va Akkaunt sozlamalarida (profil, parol, til) bor. Agar xodim bo'lsangiz, administratordan huquq so'rang.",
                    "ru": "Админ-панель только для сотрудников зала, участникам и гостям она недоступна. Всё нужное вам есть в Кабинете (абонемент, результаты, заказы) и в Настройках аккаунта (профиль, пароль, язык). Если вы сотрудник, попросите права у администратора.",
                    "en": "The admin panel is for gym staff only and is not available to members or guests. Everything you need is in your Dashboard (membership, progress, orders) and Account settings (profile, password, language). If you are staff, ask the administrator for access."},
    "hours": {"uz": "Kunlik mashq vaqti sizning maqsadingizga bog'liq. Umumiy tavsiya: JSST haftasiga 150-300 daqiqa o'rtacha yoki 75-150 daqiqa kuchli aerobik faollik va haftasiga kamida 2 kun kuchli (kuch) mashqlarni tavsiya qiladi. Odatiy bitta mashg'ulot 45-75 daqiqa (razminka bilan); 90 daqiqadan oshirish kerak emas, sifat soatdan muhimroq.\n\n"
                      "Boshlovchi haftasiga 3 marta, 40-60 daqiqadan boshlasin. Kuch mashqlariga haftasiga 2-4 kun, qolgan kunlarda yurish yoki yengil kardio. Haftasiga kamida 1-2 kun to'liq dam oling: mushak dam olganda o'sadi.\n\n"
                      "Ortiqcha mashq belgilari: uzoq davom etadigan charchoq, uyqusizlik, dam olish pulsining oshishi, natijalarning pasayishi, doimiy og'riq yoki kayfiyatning tushishi. Bunda yukni kamaytiring va dam oling.{goal_hours}",
              "ru": "Сколько тренироваться, зависит от цели. ВОЗ рекомендует 150-300 минут умеренной или 75-150 минут интенсивной аэробной активности в неделю и силовые упражнения минимум 2 дня в неделю. Типичная тренировка занимает 45-75 минут с разминкой; больше 90 минут обычно не нужно, качество важнее часов.\n\n"
                    "Новичку лучше начать с 3 тренировок в неделю по 40-60 минут. Силовые 2-4 дня в неделю, в остальные дни ходьба или лёгкое кардио. Минимум 1-2 дня в неделю полный отдых: мышцы растут во время восстановления.\n\n"
                    "Признаки перетренированности: долгая усталость, бессонница, повышенный пульс в покое, падение результатов, постоянная боль или плохое настроение. Тогда снизьте нагрузку и отдохните.{goal_hours}",
              "en": "How long to train depends on your goal. The WHO recommends 150-300 minutes of moderate or 75-150 minutes of vigorous aerobic activity per week plus strength work on at least 2 days. A typical session is 45-75 minutes including the warm-up; going past 90 minutes is rarely needed, quality beats hours.\n\n"
                    "Beginners should start with 3 sessions a week of 40-60 minutes. Strength work 2-4 days a week, with walking or light cardio on the other days. Take at least 1-2 full rest days a week: muscle grows while you recover.\n\n"
                    "Signs of overtraining: long-lasting fatigue, poor sleep, a higher resting pulse, falling performance, constant aches or a low mood. If you notice them, cut the load and rest.{goal_hours}"},
    "goal_hours": {
        "lose": {"uz": "\n\nMaqsadingiz: ozish. Haftasiga 3-4 kuch mashqi (45-60 daqiqa) + 150 daqiqa yengil/o'rtacha kardio (yurish) yaxshi, lekin ovqat kaloriyasi asosiy omil.",
                 "ru": "\n\nВаша цель: похудение. Хорошо 3-4 силовые (45-60 минут) и 150 минут лёгкого или умеренного кардио (ходьба) в неделю, но главное - калорийность питания.",
                 "en": "\n\nYour goal: fat loss. 3-4 strength sessions (45-60 min) plus about 150 minutes of easy or moderate cardio (walking) a week works well, but food calories matter most."},
        "gain": {"uz": "\n\nMaqsadingiz: massa yig'ish. Haftasiga 3-5 kuch mashqi, har biri 45-75 daqiqa; kardio kam, ovqat va uyquga e'tibor bering.",
                 "ru": "\n\nВаша цель: набор массы. 3-5 силовых в неделю по 45-75 минут; кардио немного, следите за питанием и сном.",
                 "en": "\n\nYour goal: muscle gain. 3-5 strength sessions a week of 45-75 minutes each; keep cardio modest and watch food and sleep."},
        "strength": {"uz": "\n\nMaqsadingiz: kuch. Haftasiga 3-4 mashg'ulot, har biri 60-75 daqiqa (og'ir to'plamlar orasida ko'proq dam), 1-2 kun to'liq dam.",
                     "ru": "\n\nВаша цель: сила. 3-4 тренировки в неделю по 60-75 минут (длиннее отдых между тяжёлыми подходами), 1-2 дня полного отдыха.",
                     "en": "\n\nYour goal: strength. 3-4 sessions a week of 60-75 minutes (longer rests between heavy sets) and 1-2 full rest days."},
        "other": {"uz": "\n\nMaqsadingiz: {g}. Haftasiga 3 marta, 45-60 daqiqa va 2 marta yengil kardio yaxshi boshlanish.",
                  "ru": "\n\nВаша цель: {g}. Хорошее начало: 3 тренировки в неделю по 45-60 минут и 2 лёгких кардио.",
                  "en": "\n\nYour goal: {g}. A good start is 3 sessions a week of 45-60 minutes plus 2 light cardio sessions."},
    },
}


def _http_json(url):
    """GET a JSON document. Raises on any problem; never reaches the network inside `manage.py test` (tests patch this function)."""
    if sys.argv[1:2] == ["test"]:
        raise OSError("network is disabled in tests")
    req = urllib.request.Request(url, headers={"User-Agent": "fitnes-zal-assistant"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return json.loads(r.read().decode("utf-8"))


def coords(gs):
    try:
        if gs.map_lat is not None and gs.map_lng is not None:
            return float(gs.map_lat), float(gs.map_lng)
    except Exception:
        pass
    return TASHKENT


def get_weather(lat, lng):
    """Current conditions + today's range as a flat dict, or None. Cached 30 minutes (a failure 2 minutes)."""
    key = f"assistant:weather:{lat:.2f}:{lng:.2f}"
    try:
        hit = cache.get(key)
    except Exception:
        hit = None
    if hit is not None:
        return hit or None
    q = urllib.parse.urlencode({
        "latitude": f"{lat:.4f}", "longitude": f"{lng:.4f}",
        "current": "temperature_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m",
        "daily": "temperature_2m_max,temperature_2m_min", "timezone": "Asia/Tashkent"})
    data = None
    try:
        raw = _http_json(URL + "?" + q)
        cur, day = raw["current"], raw["daily"]
        data = {"t": float(cur["temperature_2m"]), "f": float(cur["apparent_temperature"]), "p": float(cur.get("precipitation") or 0),
                "code": int(cur["weather_code"]), "w": float(cur.get("wind_speed_10m") or 0),
                "hi": float(day["temperature_2m_max"][0]), "lo": float(day["temperature_2m_min"][0])}
    except Exception:
        data = None
    try:
        cache.set(key, data or {}, CACHE_SECONDS if data else FAIL_SECONDS)
    except Exception:
        pass
    return data


def _n(x):
    return f"{round(x):d}"


def tip_for(d):
    """Key of the training tip for the weather dict."""
    kind = _WMO.get(d["code"], ("cloud",))[0]
    feel = d["f"]
    if kind == "storm":
        return "storm"
    if kind in ("rain", "snow"):
        return "wet"
    if feel >= 35:
        return "heat"
    if feel <= -5:
        return "freeze"
    if feel <= 5:
        return "cold"
    if d["w"] >= 35:
        return "wind"
    if kind == "fog":
        return "fog"
    if feel >= 28:
        return "warm"
    return "good"


def weather_answer(lang, gs):
    lat, lng = coords(gs)
    d = get_weather(lat, lng)
    if not d:
        return L["fail"][lang]
    idx = {"uz": 1, "ru": 2, "en": 3}[lang]
    cond = _WMO.get(d["code"], (None, "o'zgaruvchan", "переменная погода", "changeable"))[idx]
    rain = L["rain"][lang].format(p=f"{d['p']:g}") if d["p"] > 0 else ""
    head = L["now"][lang].format(cond=cond, t=_n(d["t"]), f=_n(d["f"]), w=_n(d["w"]), rain=rain, lo=_n(d["lo"]), hi=_n(d["hi"]))
    return head + " " + L["tip"][lang].format(tip=L["tips"][tip_for(d)][lang])


def admin_answer(lang, user):
    staff = bool(user is not None and getattr(user, "is_authenticated", False) and getattr(user, "is_staff", False))
    return L["admin_staff" if staff else "admin_other"][lang]


def hours_answer(lang, goal=None, goal_name=""):
    """The evidence-based "how long should I train" answer, with a goal-specific paragraph when the member's goal is known."""
    extra = ""
    if goal:
        box = (L["goal_hours"].get(goal) or L["goal_hours"]["other"])[lang]
        extra = box.replace("{g}", goal_name)
    return L["hours"][lang].replace("{goal_hours}", extra)
