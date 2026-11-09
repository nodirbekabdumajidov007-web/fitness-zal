"""AI yordamchi: an offline question-answering engine for the admin (no external service, no model, no network).

A question in Uzbek (Latin or Cyrillic), Russian or English goes through three steps:
  1. prepare()    - lower-case, unify apostrophes, transliterate Cyrillic to Latin, so one set of stems serves every script;
  2. understand() - find entities (period, top-N, plan, product, number of days) and pick the intent with ordered rules;
  3. run()        - answer from the real database with a sentence, a small table or bar chart, and links to the right admin pages.
Unknown questions get an honest "tushunmadim" with suggestions. Answers are always in Uzbek, like the rest of the admin."""
import difflib
import re
from dataclasses import dataclass, field
from datetime import date, timedelta

from django.db.models import Avg, Count, ExpressionWrapper, F, Max, Q, Sum
from django.db.models.fields import BigIntegerField
from django.db.models.functions import Coalesce
from django.urls import reverse
from django.utils import timezone

from . import analytics as an
from .analytics import Period, money

# ---------- text preparation ----------
CYR = {"а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "yo", "ж": "j", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m",
       "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u", "ф": "f", "х": "x", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "sh",
       "ъ": "'", "ы": "i", "ь": "", "э": "e", "ю": "yu", "я": "ya", "ў": "o'", "қ": "q", "ғ": "g'", "ҳ": "h", "ӣ": "i", "ҷ": "j"}
APOS = "ʻʼ’‘`´′"


def prepare(q):
    """(haystack, tokens): Latin transliteration without apostrophes, a bar, then the Russian original, so stems of every language match."""
    t = (q or "").lower().strip()[:300]
    for ch in APOS:
        t = t.replace(ch, "'")
    lat = "".join(CYR.get(c, c) for c in t).replace("'", "")
    ru = t.replace("'", "")
    hay = re.sub(r"\s+", " ", lat) + " | " + re.sub(r"\s+", " ", ru)
    return hay, re.findall(r"[a-zа-яё0-9]+", lat) + re.findall(r"[а-яё]+", ru)


B = r"(?<![a-zа-яё0-9])"


def _rx(p):
    return re.compile(B + "(?:" + p + ")", re.I)


CONCEPTS = {
    "revenue": r"tushum|daromad|tushgan|pul(?![a-z])|puli|kassa|moliya|savdo|выруч|доход|оборот|прибыл|заработ|продаж|касс|revenue|income|earn|takings|turnover|profit|sales",
    "shop": r"dokon|магазин|shop|store|retail",
    "product": r"mahsulot|tovar|товар|продукт|product|goods",
    "sold": r"sotil|sotgan|sotuv|sold|sell|продан|продаваем|продавал|реализ",
    "stock": r"ombor|zaxira|qoldiq|qoldi|qolgan|qolyapti|stock|inventory|остат|склад|осталось|осталос|kam qol|low stock|out of stock|run(?:ning)? out|tugab qol|tugab bor",
    "expiring": r"tugay|tugagan|tugash|tugaydi|muddati|expir|истека|истёк|заканчива|кончает|окончан|ending|ends(?![a-z])|will end",
    "visits": r"tashrif|kelgan|keldi|keladi|kelish|kirish|kirgan|visit|attend|traffic|посещ|приход|пришл|пришёл|заход|footfall|check.?in|came|come",
    "inactive": r"kelmagan|kelmayot|kelmaydi|kelmadi|kelishmagan|qatnashmagan|bormagan|haven.?t|hasn.?t|not (?:come|visit|attend)|inactive|absent|не приход|не посещ|не был|не ходил|давно не|пропал|отсутств|yoqolgan|sleeping|didn.?t (?:come|visit)",
    "new": r"yangi|new(?![a-z])|нов|qoshil|joined|signup|sign up|royxatdan|регистр|registr|newcomers",
    "member": r"azo|mijoz|client|member|клиент|участник|посетител|odam|kishi|customer|люд|человек|people|users?(?![a-z])|foydalanuvchi|abonent",
    "active": r"faol|active|актив|действ|amal qil|ishlayotgan|hozir(?![a-z])|currently",
    "peak": r"gavjum|peak|busiest|busy|crowd|час пик|пик(?![а-я])|загружен|zich|rush|odam kop|eng kop kel|ko.?p kel",
    "hour": r"soat|hour|час",
    "day": r"kun(?![a-z])|kunlar|day(?![a-z])|days|день|дни|дня|weekday|haftaning",
    "trainer": r"murabbiy|trener|тренер|trainer|coach",
    "best": r"eng yaxshi|yaxshi|best|top(?![a-z])|лучш|reyting|rating|baho|рейтинг|оценк|eng kop|most(?![a-z])|eng zo",
    "class": r"mashgulot|dars|class|занят|групп|zumba|yoga|joga|boks|boxing",
    "attendance": r"davomat|attendance|посещаем|noshow|no show|no-show|bron|booking|брон|заполн|kelmagan|не пришл",
    "guest": r"mehmon|guest|гост",
    "freeze": r"muzlat|muzlag|freez|froz|заморо",
    "referral": r"taklif|referr|рефер|пригла|invite|bonus",
    "pending": r"kutil|kutay|kutmoq|pending|ожида|в ожидании|tasdiq|unconfirmed|waiting|не подтвержд|неподтвержд|javobsiz",
    "payment": r"tolov|payment|платеж|платёж|оплат",
    "order": r"buyurtma|order|заказ",
    "avg": r"ortacha|average|avg|средн",
    "check": r"chek|check(?![a-z])|чек|bill|receipt|xarid|purchase|покупк",
    "method": r"usul|method|способ|naqd|karta|card|click|payme|uzum|cash|налич|терминал",
    "plan": r"tarif|plan(?![a-z])|абонемент|тариф|subscription|membership|obuna|abonement",
    "compare": r"nisbatan|taqqos|solishtir|compare|comparison|versus|vs(?![a-z])|сравн|по сравнению|oldingi|previous|prior|avvalgi|against|growth|osish|o.sish|рост|динамик",
    "churn": r"churn|ketib|ketgan|ketdi|отток|ушл|qaytmagan|uzaytirmagan|не продлил|lost",
    "renewal": r"uzaytir|renew|продл|qayta obuna",
    "help": r"yordam|help|nima qila|what can you|что ты умеешь|помощь|salom|assalom|hello|hi(?![a-z])|привет|здравствуй|commands|imkoniyat",
    "least": r"eng kam|least|worst|lowest|меньше|наименее|худш|kam sotil|sust|slow|eng past",
    "total": r"jami|total|barcha|всего|итого|umumiy|nechta|qancha|сколько|how many|how much|count|soni",
}
CRX = {k: _rx(v) for k, v in CONCEPTS.items()}
PAST_RX = _rx(r"tugagan|expired|истек(?:ш|ли|ла)|истёк|закончил|muddati otgan")
METHODS = {"cash": r"naqd|cash|налич", "card": r"karta|card|карт", "click": r"click|клик", "payme": r"payme|пейм", "uzum": r"uzum|узум"}

MONTH_PATTERNS = [
    r"yanvar\w*|январ\w*|january|jan(?![a-z])", r"fevral\w*|феврал\w*|february|feb(?![a-z])", r"mart(?![a-z])|marta|март\w*|march",
    r"aprel\w*|апрел\w*|april|apr(?![a-z])", r"may(?![a-z])|ма[йяе](?![а-яё])", r"iyun\w*|июн\w*|june|jun(?![a-z])",
    r"iyul\w*|июл\w*|july|jul(?![a-z])", r"avgust\w*|август\w*|august|aug(?![a-z])", r"sentabr\w*|сентябр\w*|september|sept?(?![a-z])",
    r"oktyabr\w*|октябр\w*|october|oct(?![a-z])", r"noyabr\w*|ноябр\w*|november|nov(?![a-z])", r"dekabr\w*|декабр\w*|december|dec(?![a-z])",
]
MONTH_ALT = "|".join(f"(?P<m{i + 1}>{p})" for i, p in enumerate(MONTH_PATTERNS))
MONTH_RX = re.compile(B + r"(?:(?P<d1>\d{1,2})\s*(?:-?\s*(?:chi|inchi|ое|го))?\s+)?(?:(?P<y1>20\d\d)\s+)?(?:" + MONTH_ALT + r")(?:\s+(?P<y2>20\d\d))?", re.I)
ISO_RX = re.compile(r"(\d{4})-(\d{1,2})-(\d{1,2})")
DMY_RX = re.compile(r"(?<!\d)(\d{1,2})\.(\d{1,2})\.(\d{4})(?!\d)")

REL = [  # (kind, regex): checked in this order, each phrase is blanked after it matched
    ("last_week", r"(?:otgan|oldingi|avvalgi) haf|[hx]afta otgan|last week|previous week|прошл\w+ недел"),
    ("this_week", r"(?:bu|shu|joriy) [hx]afta|this week|(?:эта|этой|этую|текущ\w+) недел|на этой неделе"),
    ("last_month", r"(?:otgan|oldingi|avvalgi) oy|last month|previous month|прошл\w+ месяц"),
    ("this_month", r"(?:bu|shu|joriy) oy|this month|(?:этот|этом|этого|текущ\w+) месяц"),
    ("last_year", r"(?:otgan|oldingi|avvalgi) yil|last year|прошл\w+ год"),
    ("this_year", r"(?:bu|shu|joriy) yil|this year|(?:этот|этом|этого) год"),
    ("trail_week", r"(?:oxirgi|songgi|last|past|последн\w+|за) (?:[hx]afta|week|недел)|за неделю"),
    ("trail_month", r"(?:oxirgi|songgi|past|последн\w+|за) (?:oy|month|месяц)|за месяц"),
    ("trail_year", r"(?:oxirgi|songgi|past|последн\w+|за) (?:yil|year|год)|за год"),
    ("yesterday", r"kecha\w*|yesterday|вчера\w*"),
    ("tomorrow", r"ertaga\w*|tomorrow|завтра"),
    ("today", r"bugun\w*|today|сегодня|нынче"),
]
REL_RX = [(k, _rx(p)) for k, p in REL]
UNIT_RX = re.compile(B + r"(\d{1,4})\s*-?\s*(kun|day|days|дн|ден|oy|month|месяц|[hx]afta|week|недел)\w*", re.I)
TOP_RX = re.compile(B + r"(?:top|топ|first|eng(?: yaxshi| kop)?|лучш\w+|первые)\s*(\d{1,2})|(\d{1,2})\s*(?:ta(?![a-z])|dona|шт|ta |best|top)", re.I)

SUGGESTIONS = ["Bugun tushum qancha?", "Bu oy yangi a'zolar nechta?", "Bu hafta kimning abonementi tugaydi?", "14 kundan beri kelmaganlar",
               "Eng ko'p sotilgan mahsulotlar", "Qaysi mahsulot tugayapti?", "Kutilayotgan to'lovlar", "O'rtacha chek qancha?",
               "Eng yaxshi murabbiy kim?", "Tushum o'tgan oyga nisbatan", "Eng gavjum soat qaysi?", "Muzlatilgan abonementlar", "Mashg'ulotlar davomati",
               "Mehmon taklifnomalari", "Taklif qilish statistikasi", "Uzaytirish ulushi"]
VOCAB = {"tushum": "Bugun tushum qancha?", "daromad": "Bu oy daromad qancha?", "tashrif": "Bugun nechta tashrif bo'ldi?", "abonement": "Bu hafta kimning abonementi tugaydi?",
         "mahsulot": "Eng ko'p sotilgan mahsulotlar", "murabbiy": "Eng yaxshi murabbiy kim?", "mehmon": "Mehmon taklifnomalari", "muzlatish": "Muzlatilgan abonementlar",
         "davomat": "Mashg'ulotlar davomati", "xarid": "O'rtacha chek qancha?", "taklif": "Taklif qilish statistikasi", "ombor": "Qaysi mahsulot tugayapti?",
         "revenue": "Revenue today", "visits": "Visits this week", "members": "New members this month", "выручка": "Какая выручка за этот месяц?"}


# ---------- periods ----------
@dataclass
class When_:
    start: date
    end: date
    kind: str
    pos: int = 0

    @property
    def days(self):
        return (self.end - self.start).days + 1


def _last_day(y, m):
    return ((date(y, m, 28) + timedelta(days=4)).replace(day=1)) - timedelta(days=1)


def _add_months(d, n):
    m = d.month - 1 + n
    y, m = d.year + m // 12, m % 12 + 1
    return date(y, m, min(d.day, _last_day(y, m).day))


def parse_whens(hay, today):
    """Every time phrase found in the text, in order of appearance. Each matched phrase is blanked so no other rule reads it twice."""
    work = hay
    found = []

    def blank(m):
        nonlocal work
        work = work[:m.start()] + " " * (m.end() - m.start()) + work[m.end():]

    isos = []
    for m in list(ISO_RX.finditer(work)):
        try:
            isos.append((m.start(), date(int(m.group(1)), int(m.group(2)), int(m.group(3)))))
            blank(m)
        except ValueError:
            pass
    for m in list(DMY_RX.finditer(work)):
        try:
            isos.append((m.start(), date(int(m.group(3)), int(m.group(2)), int(m.group(1)))))
            blank(m)
        except ValueError:
            pass
    if isos:
        ds = [d for _, d in isos]
        found.append(When_(min(ds), max(ds), "custom", min(p for p, _ in isos)))
    for m in list(MONTH_RX.finditer(work)):
        mon = next(i for i in range(1, 13) if m.group(f"m{i}"))
        year = int(m.group("y1") or m.group("y2") or 0)
        day = int(m.group("d1")) if m.group("d1") else 0
        if not year:
            year = today.year if mon <= today.month else today.year - 1
        if day and 1 <= day <= _last_day(year, mon).day:
            d = date(year, mon, day)
            found.append(When_(d, d, "day", m.start()))
        elif not m.group("d1") or day == 0 or day > 31:
            found.append(When_(date(year, mon, 1), _last_day(year, mon), "month_name", m.start()))
        else:
            continue
        blank(m)
    for kind, rx in REL_RX:
        for m in list(rx.finditer(work)):
            monday = today - timedelta(days=today.weekday())
            if kind == "today":
                w = When_(today, today, "today", m.start())
            elif kind == "yesterday":
                w = When_(today - timedelta(days=1), today - timedelta(days=1), "yesterday", m.start())
            elif kind == "tomorrow":
                w = When_(today + timedelta(days=1), today + timedelta(days=1), "tomorrow", m.start())
            elif kind == "this_week":
                w = When_(monday, today, "week", m.start())
            elif kind == "last_week":
                w = When_(monday - timedelta(days=7), monday - timedelta(days=1), "last_week", m.start())
            elif kind == "this_month":
                w = When_(today.replace(day=1), today, "month", m.start())
            elif kind == "last_month":
                first = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
                w = When_(first, today.replace(day=1) - timedelta(days=1), "last_month", m.start())
            elif kind == "this_year":
                w = When_(today.replace(month=1, day=1), today, "year", m.start())
            elif kind == "last_year":
                w = When_(date(today.year - 1, 1, 1), date(today.year - 1, 12, 31), "last_year", m.start())
            elif kind == "trail_week":
                w = When_(today - timedelta(days=6), today, "days", m.start())
            elif kind == "trail_month":
                w = When_(today - timedelta(days=29), today, "days", m.start())
            else:
                w = When_(today - timedelta(days=364), today, "days", m.start())
            found.append(w)
            blank(m)
    for m in list(UNIT_RX.finditer(work)):
        n, unit = int(m.group(1)), m.group(2).lower()
        if n <= 0:
            continue
        if unit.startswith(("kun", "day", "дн", "ден")):
            start = today - timedelta(days=min(n, an.MAX_DAYS) - 1)
        elif unit.startswith(("oy", "month", "месяц")):
            start = _add_months(today, -min(n, 24)) + timedelta(days=1)
        else:
            start = today - timedelta(days=min(n * 7, an.MAX_DAYS) - 1)
        found.append(When_(start, today, "days", m.start()))
        blank(m)
    for m in list(re.finditer(B + r"(20\d\d)(?![\d])", work)):
        y = int(m.group(1))
        if 2000 <= y <= today.year:
            found.append(When_(date(y, 1, 1), min(date(y, 12, 31), today), "year_num", m.start()))
            blank(m)
    uniq = {}
    for w in sorted(found, key=lambda w: w.pos):  # the haystack holds the text twice (Latin | original), so every phrase was found twice
        uniq.setdefault((w.start, w.end), w)
    return list(uniq.values())


def prev_span(w):
    """What «compared to before» means: a month (or month so far) against the previous month's same days, otherwise the equally long range before."""
    if w.start.day == 1 and w.start.month == w.end.month and w.start.year == w.end.year and w.kind in ("month", "last_month", "month_name"):
        ps = (w.start - timedelta(days=1)).replace(day=1)
        return ps, min(ps + timedelta(days=w.days - 1), _last_day(ps.year, ps.month))
    n = w.days
    return w.start - timedelta(days=n), w.start - timedelta(days=1)


def human(w):
    labels = {"today": "Bugun", "yesterday": "Kecha", "week": "Bu hafta", "last_week": "O'tgan hafta", "month": "Bu oy", "last_month": "O'tgan oy",
              "year": "Bu yil", "last_year": "O'tgan yil"}
    base = labels.get(w.kind)
    if w.kind == "month_name":
        base = f"{an.MONTHS_UZ[w.start.month - 1].capitalize()} {w.start.year}"
    if w.kind == "days":
        base = f"Oxirgi {w.days} kun"
    rng = f"{w.start:%d.%m.%Y}" if w.days == 1 else f"{w.start:%d.%m.%Y} – {w.end:%d.%m.%Y}"
    if not base:
        return rng
    return base if w.kind in ("today", "yesterday") else f"{base} ({rng})"


# ---------- understanding ----------
@dataclass
class Understood:
    intent: str
    ent: dict = field(default_factory=dict)
    when: When_ | None = None


def _norm_tokens(s):
    lat = "".join(CYR.get(c, c) for c in s.lower()).replace("'", "")
    return re.findall(r"[a-z]+", lat)


def find_product(tokens):
    """Active products whose name words appear in the question (word start, so «proteinni» finds «protein»); the best-scoring ones only."""
    from .models import Product
    qs = set(tokens)
    best, hits = None, []
    for pk, name in Product.objects.filter(active=True).values_list("pk", "name"):
        toks = [t for t in _norm_tokens(name) if len(t) >= 3]
        got = [t for t in toks if any(q.startswith(t) for q in qs)]
        if not got or len(got) / len(toks) < 0.5:
            continue
        val = (len(got) / len(toks), len(got), max(len(t) for t in got))
        if best is None or val > best:
            best, hits = val, [(pk, name)]
        elif val == best:
            hits.append((pk, name))
    return hits


GENERIC_PLAN = {"oylik", "abonement", "kunlik", "yillik", "oyli", "tarif", "plan", "month", "months", "oy"}


def find_plan(hay):
    """Plans named in the question: by the full name when it has a number («3 oylik»), otherwise by its distinctive words («premium»)."""
    from .models import Plan
    out = []
    for pk, name in Plan.objects.values_list("pk", "name"):
        norm = re.sub(r"\s+", " ", "".join(CYR.get(c, c) for c in name.lower()).replace("'", "")).strip()
        hit = None
        if re.search(r"\d", name) and norm and re.search(B + re.escape(norm), hay):
            hit = norm
        words = [w for w in _norm_tokens(name) if len(w) >= 3 and w not in GENERIC_PLAN]
        if not hit and words and all(re.search(B + re.escape(w), hay) for w in words):
            hit = words[0]
        if hit:
            out.append((pk, name, hit))
    return out


def understand(question, today=None, last=None):
    today = today or timezone.localdate()
    hay, tokens = prepare(question)
    c = {k for k, rx in CRX.items() if rx.search(hay)}
    ent = {}
    prods = find_product(tokens) if tokens else []
    plans = find_plan(hay)
    work = hay
    for _, _, hit in plans:  # «3 oylik» is a plan name, not "3 months": take it out before the periods are read
        work = re.sub(re.escape(hit), " ", work)
    if prods:
        ent["product_ids"] = [p for p, _ in prods][:6]
    if plans:
        ent["plan_id"], ent["plan"] = plans[0][0], plans[0][1]
    whens = parse_whens(work, today)
    when = whens[0] if whens else None
    top_n = None
    m = TOP_RX.search(work)
    if m:
        top_n = int(m.group(1) or m.group(2))
        top_n = max(1, min(top_n, 20))
        ent["top"] = top_n
    days_m = re.search(B + r"(\d{1,3})\s*(?:kun|day|дн|ден)", work)
    days_n = int(days_m.group(1)) if days_m else None
    if days_n:
        ent["days"] = days_n
    method = next((k for k, v in METHODS.items() if re.search(B + "(?:" + v + ")", hay)), None)
    if method:
        ent["method"] = method
    compare = "compare" in c
    if compare:
        ent["compare"] = True
        if len(whens) >= 2:  # «bu oy o'tgan oy bilan»: the later range is the one being asked about
            when = max(whens, key=lambda w: w.start)

    def done(name, **extra):
        e = {**ent, **extra}
        metric = {"revenue_total": "revenue", "new_members": "new_members", "visits_total": "visits", "avg_check": "avg_check", "shop_sales": "shop"}.get(name)
        if compare and metric:
            e["metric"] = metric
            return Understood("compare", e, when)
        return Understood(name, e, when)

    only_help = c <= {"help", "total"} and "help" in c
    if only_help and not prods:
        return Understood("help", ent, when)
    if prods:
        return Understood("product_info", ent, when)
    if "inactive" in c and "class" not in c:
        weeks = re.search(B + r"(\d{1,2})\s*(?:[hx]afta|week|недел)", work)
        if weeks and not days_n:
            days_n = int(weeks.group(1)) * 7
        week = re.search(B + r"(?:[hx]afta|week|недел)", work)
        month = re.search(B + r"(?:oy|month|месяц)", work)
        return done("inactive_members", days=days_n or (7 if week else 30 if month else 14))
    if "trainer" in c:
        return done("best_trainer")
    if "class" in c:
        return done("class_attendance")
    if "guest" in c:
        return done("guest_passes")
    if "freeze" in c:
        return done("freezes")
    if "referral" in c:
        return done("referrals")
    if "stock" in c or ("product" in c and "expiring" in c):
        return done("low_stock")
    if "product" in c or ("sold" in c and ("best" in c or "least" in c or "revenue" not in c)):
        if "least" in c:
            return done("least_products")
        if "revenue" in c and "best" not in c and "sold" not in c:
            return done("shop_sales")
        return done("top_products")
    if "pending" in c and "revenue" not in c:
        return done("pending_items")
    if (PAST_RX.search(hay) and "member" not in c) or "churn" in c:
        return done("churn")
    if "expiring" in c:
        return done("expiring_members")
    if plans:
        return done("revenue_by_plan" if "revenue" in c else "plan_info")
    if "renewal" in c:
        return done("renewal_rate")
    if "avg" in c and ("check" in c or "payment" in c or "order" in c or "revenue" in c):
        return done("avg_check")
    if "peak" in c:
        return done("peak_days" if ("day" in c and "hour" not in c) else "peak_hours")
    if "revenue" in c or ("method" in c and "payment" in c):
        if "method" in c:
            return done("revenue_by_method")
        if "shop" in c:
            return done("shop_sales")
        if "plan" in c:
            return done("revenue_by_plan")
        return done("revenue_total")
    if "shop" in c:
        return done("shop_sales")
    if "new" in c and "order" not in c and ("member" in c or "plan" not in c):
        return done("new_members")
    if "active" in c and ("member" in c or "plan" in c):
        return done("active_members")
    if "visits" in c:
        return done("visits_total")
    if "order" in c:
        return done("pending_items")
    if "payment" in c:
        return done("revenue_total")
    if "member" in c:
        return done("members_total")
    if last and (when or compare):
        return Understood(last, dict(ent), when)
    return Understood("unknown", ent, when)


# ---------- answers ----------
def A(intent, text, table=None, chart=None, links=None, ent=None, follow=None):
    return {"ok": True, "intent": intent, "text": text, "table": table, "chart": chart, "links": links or [], "entities": ent or {}, "suggestions": follow or []}


def U(name, **kw):
    return reverse(f"admin:{name}", **kw)


def _period(u, default="month", today=None):
    """(When_, Period) for the question; no period named means `default`, and nothing ever reaches into the future."""
    today = today or timezone.localdate()
    w = u.when
    if w is None or w.start > today:
        if default == "30d":
            w = When_(today - timedelta(days=29), today, "days")
        elif default == "today":
            w = When_(today, today, "today")
        else:
            w = When_(today.replace(day=1), today, "month")
    elif w.end > today:
        w = When_(w.start, today, w.kind)
    return w, Period("ask", w.start, w.end)


def _bars(items, unit="so'm"):
    return {"items": [{"label": str(a), "value": int(b), "text": f"{money(b)} {unit}".strip()} for a, b in items], "unit": unit}


def _ent_json(u, w):
    e = {k: v for k, v in u.ent.items() if k not in ("product_ids",)}
    if w:
        e["period"] = {"start": w.start.isoformat(), "end": w.end.isoformat(), "label": human(w)}
    return e


def _pct(cur, prev):
    d = an._delta(cur, prev)
    if d is None:
        return "oldingi davrda ma'lumot yo'q" if not prev else ""
    return f"{'+' if d > 0 else ''}{d:g}%"


def _members_table(rows):
    return {"cols": ["A'zo", "Telefon", "Izoh"], "rows": rows}


def run(u, today=None):
    today = today or timezone.localdate()
    fn = RUNNERS.get(u.intent)
    if fn is None:
        return unknown(u)
    return fn(u, today)


def r_revenue_total(u, today):
    w, p = _period(u, today=today)
    t = an.totals(p)
    plan = t["revenue"] - t["shop"]
    return A("revenue_total", f"{human(w)} tushum: {money(t['revenue'])} so'm ({t['paid_n']} ta to'lov). Abonement va boshqa: {money(plan)} so'm, do'kon: {money(t['shop'])} so'm.",
             chart=_bars([("Abonement", plan), ("Do'kon", t["shop"])]), links=[{"label": "Hisobotlar", "url": U("reports")}, {"label": "Kassa", "url": U("cash")}],
             ent=_ent_json(u, w), follow=["Tushum o'tgan oyga nisbatan", "To'lov usullari bo'yicha tushum", "O'rtacha chek qancha?"])


def r_revenue_by_method(u, today):
    w, p = _period(u, today=today)
    rows = an.methods_section(p)["rows"]
    if not rows:
        return A("revenue_by_method", f"{human(w)} davrida to'langan to'lov yo'q.", ent=_ent_json(u, w))
    top = rows[0]
    one = ""
    if u.ent.get("method"):
        mine = next((r for r in rows if r["key"] == u.ent["method"]), None)
        one = f" {an.METHOD_LABELS.get(u.ent['method'])}: {money(mine['value']) if mine else 0} so'm."
    return A("revenue_by_method", f"{human(w)}: eng ko'p {top['label']} orqali — {money(top['value'])} so'm.{one}",
             table={"cols": ["Usul", "To'lovlar", "Summa (so'm)"], "rows": [[r["label"], r["count"], money(r["value"])] for r in rows]},
             chart=_bars([(r["label"], r["value"]) for r in rows]), links=[{"label": "To'lovlar", "url": U("gym_payment_changelist")}], ent=_ent_json(u, w))


def r_revenue_by_plan(u, today):
    from .models import Payment
    w, p = _period(u, today=today)
    qs = an.paid_in(p).filter(kind="plan")
    if u.ent.get("plan_id"):
        a = qs.filter(plan_id=u.ent["plan_id"]).aggregate(s=Sum("amount"), n=Count("id"))
        return A("revenue_by_plan", f"{human(w)}: «{u.ent['plan']}» abonementidan {money(a['s'] or 0)} so'm tushgan ({a['n']} ta sotuv).",
                 links=[{"label": "Abonement turlari", "url": U("gym_plan_changelist")}], ent=_ent_json(u, w))
    rows = list(qs.values("plan__name").annotate(s=Sum("amount"), n=Count("id")).order_by("-s"))
    if not rows:
        return A("revenue_by_plan", f"{human(w)} davrida abonement sotilmagan.", ent=_ent_json(u, w))
    return A("revenue_by_plan", f"{human(w)}: eng ko'p tushum «{rows[0]['plan__name'] or '—'}» abonementidan — {money(rows[0]['s'])} so'm.",
             table={"cols": ["Abonement", "Sotildi", "Summa (so'm)"], "rows": [[r["plan__name"] or "—", r["n"], money(r["s"])] for r in rows]},
             chart=_bars([(r["plan__name"] or "—", r["s"]) for r in rows]), links=[{"label": "Abonement turlari", "url": U("gym_plan_changelist")}], ent=_ent_json(u, w))


def r_shop_sales(u, today):
    from .models import Order
    w, p = _period(u, today=today)
    t = an.totals(p)
    orders = Order.objects.filter(created__gte=p.start_dt, created__lt=p.end_dt).exclude(status="cancelled").count()
    tops = an.products_section(p)["rows"][:3]
    extra = " Eng ko'p: " + ", ".join(f"{r['label']} ({r['value']} dona)" for r in tops) + "." if tops else ""
    return A("shop_sales", f"{human(w)} do'kon savdosi: {money(t['shop'])} so'm, {orders} ta buyurtma.{extra}",
             links=[{"label": "Buyurtmalar", "url": U("gym_order_changelist")}, {"label": "Mahsulotlar", "url": U("gym_product_changelist")}], ent=_ent_json(u, w),
             follow=["Eng ko'p sotilgan mahsulotlar", "Qaysi mahsulot tugayapti?"])


def r_compare(u, today):
    metric = u.ent.get("metric", "revenue")
    w, _ = _period(u, today=today)
    ps, pe = prev_span(w)
    p, pv = Period("ask", w.start, w.end), Period("ask", ps, pe)
    cur, old = an.totals(p), an.totals(pv)
    names = {"revenue": ("Tushum", "so'm"), "new_members": ("Yangi a'zolar", "ta"), "visits": ("Tashriflar", "ta"), "avg_check": ("O'rtacha chek", "so'm"), "shop": ("Do'kon savdosi", "so'm")}
    name, unit = names[metric]
    a, b = cur[metric], old[metric]
    d = _pct(a, b)
    trend = "o'zgarmagan" if a == b else ("oshgan" if a > b else "kamaygan")
    return A("compare", f"{name}: {human(w)} — {money(a)} {unit}, oldingi davr ({ps:%d.%m}–{pe:%d.%m.%Y}) — {money(b)} {unit}. {d} ({trend}).".replace("  ", " "),
             chart=_bars([("Hozirgi", a), ("Oldingi", b)], unit), links=[{"label": "Hisobotlar", "url": U("reports")}], ent={**_ent_json(u, w), "metric": metric, "delta": an._delta(a, b)})


def r_new_members(u, today):
    w, p = _period(u, today=today)
    n = an.totals(p)["new_members"]
    rows = an.members_section(p)["rows"]
    chart = _bars([(r["label"], r["value"]) for r in rows], "ta") if 1 < len(rows) <= 14 else None
    return A("new_members", f"{human(w)} {n} ta yangi a'zo ro'yxatdan o'tgan.", chart=chart, links=[{"label": "A'zolar", "url": U("gym_user_changelist")}], ent=_ent_json(u, w),
             follow=["Yangi a'zolar o'tgan oyga nisbatan", "Taklif qilish statistikasi"])


def r_active_members(u, today):
    from .models import Membership
    now = timezone.now()
    live = Membership.objects.filter(user__is_superuser=False, starts__lte=now, expires__gt=now)
    n = live.values("user").distinct().count()
    by = list(live.values("plan__name").annotate(c=Count("user", distinct=True)).order_by("-c"))
    return A("active_members", f"Hozir {n} ta faol abonement egasi bor.", chart=_bars([(r["plan__name"] or "—", r["c"]) for r in by], "ta"),
             links=[{"label": "Abonementlar", "url": U("gym_membership_changelist")}], ent={"count": n}, follow=["Muzlatilgan abonementlar", "Bu hafta kimning abonementi tugaydi?"])


def r_members_total(u, today):
    from .models import User
    total = an.members_qs().count()
    now = timezone.now()
    new = an.members_qs().filter(created__gte=an._start_of(today.replace(day=1))).count()
    act = an.active_at(now)
    return A("members_total", f"Jami {total} ta a'zo ro'yxatdan o'tgan, {act} tasining abonementi hozir amal qiladi; shu oy {new} ta yangi.",
             links=[{"label": "A'zolar", "url": U("gym_user_changelist")}], ent={"total": total, "active": act}, follow=["Bu oy yangi a'zolar nechta?"])


def r_visits_total(u, today):
    w, p = _period(u, today=today)
    v = an.visits_section(p)
    per = round(v["total"] / p.days, 1) if p.days else 0
    peak = f" Eng gavjum soat {v['peak_hour']:02d}:00." if v["peak_hour"] is not None else ""
    return A("visits_total", f"{human(w)} {v['total']} ta tashrif bo'lgan (kuniga o'rtacha {per}).{peak}", chart=_bars([(r["full"], r["value"]) for r in v["weekday"]], "ta") if p.days > 1 else None,
             links=[{"label": "Tashriflar", "url": U("gym_visit_changelist")}], ent=_ent_json(u, w), follow=["Eng gavjum soat qaysi?", "14 kundan beri kelmaganlar"])


def r_peak(u, today):
    w, p = _period(u, default="30d", today=today)
    v = an.visits_section(p)
    if not v["total"]:
        return A(u.intent, f"{human(w)} davrida tashrif yo'q.", ent=_ent_json(u, w))
    if u.intent == "peak_days":
        order = sorted(v["weekday"], key=lambda r: -r["value"])
        return A("peak_days", f"{human(w)}: eng gavjum kun — {order[0]['full']} ({order[0]['value']} tashrif), eng bo'sh — {order[-1]['full']} ({order[-1]['value']}).",
                 chart=_bars([(r["full"], r["value"]) for r in v["weekday"]], "ta"), links=[{"label": "Haftalik jadval", "url": U("schedule")}], ent=_ent_json(u, w))
    hours = sorted(v["hours"], key=lambda r: -r["value"])[:3]
    return A("peak_hours", f"{human(w)}: eng gavjum soatlar — " + ", ".join(f"{r['label']}:00 ({r['value']})" for r in hours) + ".",
             chart=_bars([(f"{r['label']}:00", r["value"]) for r in v["hours"]], "ta"), links=[{"label": "Haftalik jadval", "url": U("schedule")}], ent=_ent_json(u, w),
             follow=["Eng gavjum kun qaysi?"])


def r_expiring(u, today):
    now = timezone.now()
    w = u.when
    if w and w.kind == "today":
        end, label = an._start_of(today + timedelta(days=1)), "bugun"
    elif w and w.kind == "tomorrow":
        now, end, label = an._start_of(today + timedelta(days=1)), an._start_of(today + timedelta(days=2)), "ertaga"
    elif w and w.kind == "week":
        end, label = an._start_of(today + timedelta(days=7 - today.weekday())), "shu hafta ichida"
    elif u.ent.get("days"):
        end, label = now + timedelta(days=u.ent["days"]), f"{u.ent['days']} kun ichida"
    else:
        end, label = now + timedelta(days=7), "7 kun ichida"
    qs = an.members_qs().filter(is_active=True).annotate(until=Max("memberships__expires")).filter(until__gt=now, until__lte=end)
    n = qs.count()
    rows = list(qs.order_by("until")[:10])
    ids = ",".join(str(x) for x in qs.order_by("until").values_list("pk", flat=True)[:40])
    links = [{"label": "Analitika sahifasi", "url": U("analytics")}]
    if n:
        links.insert(0, {"label": "Xabar yozish", "url": U("message") + f"?ids={ids}"})
    return A("expiring_members", f"{label.capitalize()} {n} ta a'zoning abonementi tugaydi." if n else f"{label.capitalize()} abonementi tugaydigan a'zo yo'q.",
             table=_members_table([[f"{x.first_name} {x.last_name}".strip() or x.username, x.phone or "—", timezone.localtime(x.until).strftime("%d.%m.%Y")] for x in rows]) if rows else None,
             links=links, ent={"count": n, "window": label}, follow=["Kimlar 14 kundan beri kelmagan?"])


def r_inactive(u, today):
    days = max(1, min(u.ent.get("days", 14), 365))
    qs = an.at_risk_qs(days)
    n = qs.count()
    rows = list(qs.order_by("last")[:10])
    ids = ",".join(str(x) for x in qs.order_by("last").values_list("pk", flat=True)[:40])
    links = [{"label": "Xabar yozish", "url": U("message") + f"?ids={ids}"}] if n else []
    return A("inactive_members", f"{n} ta faol a'zo {days} kundan beri zalga kelmagan." if n else f"{days} kundan beri kelmagan faol a'zo yo'q.",
             table=_members_table([[f"{x.first_name} {x.last_name}".strip() or x.username, x.phone or "—", timezone.localtime(x.last).strftime("%d.%m.%Y") if x.last else "hech kelmagan"] for x in rows]) if rows else None,
             links=links, ent={"count": n, "days": days}, follow=["Bu hafta kimning abonementi tugaydi?"])


def _product_sales(p, order, limit):
    from .models import Product
    amount = ExpressionWrapper(F("orderitem__price") * F("orderitem__qty"), output_field=BigIntegerField())
    live = Q(orderitem__order__created__gte=p.start_dt, orderitem__order__created__lt=p.end_dt) & ~Q(orderitem__order__status="cancelled")
    return list(Product.objects.filter(active=True).annotate(sold=Coalesce(Sum("orderitem__qty", filter=live), 0, output_field=BigIntegerField()), rev=Coalesce(Sum(amount, filter=live), 0, output_field=BigIntegerField()))
                .order_by(order, "name")[:limit])


def r_products(u, today):
    w, p = _period(u, default="30d", today=today)
    n = u.ent.get("top", 5)
    least = u.intent == "least_products"
    rows = _product_sales(p, "sold" if least else "-sold", n)
    if not rows or (not least and not rows[0].sold):
        return A(u.intent, f"{human(w)} davrida mahsulot sotilmagan.", ent=_ent_json(u, w))
    head = f"{human(w)}: eng kam sotilgan {len(rows)} ta mahsulot." if least else f"{human(w)}: eng ko'p sotilgan — {rows[0].name} ({rows[0].sold} dona)."
    return A(u.intent, head, table={"cols": ["Mahsulot", "Sotildi", "Tushum (so'm)", "Omborda"], "rows": [[x.name, x.sold, money(x.rev), x.stock] for x in rows]},
             chart=_bars([(x.name, x.sold) for x in rows], "dona"), links=[{"label": "Mahsulotlar", "url": U("gym_product_changelist")}], ent=_ent_json(u, w),
             follow=["Qaysi mahsulot tugayapti?", "Eng kam sotilgan mahsulotlar"] if not least else ["Eng ko'p sotilgan mahsulotlar"])


def r_low_stock(u, today):
    st = an.stock_section()
    if not st["rows"]:
        return A("low_stock", f"Hamma mahsulot yetarli: {st['threshold']} donadan kam qolgani yo'q.", links=[{"label": "Mahsulotlar", "url": U("gym_product_changelist")}])
    return A("low_stock", f"{st['total']} ta mahsulot tugayapti (ogohlantirish chegarasi: {st['threshold']} dona).",
             table={"cols": ["Mahsulot", "Omborda", "Olib kelish kerak"], "rows": [[r["label"], r["stock"], r["need"]] for r in st["rows"]]},
             chart=_bars([(r["label"], r["stock"]) for r in st["rows"]], "dona"), links=[{"label": "Mahsulotlar", "url": U("gym_product_changelist")}], ent={"count": st["total"]})


def r_product_info(u, today):
    from .models import Product
    w, p = _period(u, default="30d", today=today)
    ids = u.ent.get("product_ids", [])
    amount = ExpressionWrapper(F("orderitem__price") * F("orderitem__qty"), output_field=BigIntegerField())
    live = Q(orderitem__order__created__gte=p.start_dt, orderitem__order__created__lt=p.end_dt) & ~Q(orderitem__order__status="cancelled")
    rows = list(Product.objects.filter(pk__in=ids).annotate(sold=Coalesce(Sum("orderitem__qty", filter=live), 0, output_field=BigIntegerField()), rev=Coalesce(Sum(amount, filter=live), 0, output_field=BigIntegerField())).order_by("name"))
    if len(rows) == 1:
        x = rows[0]
        return A("product_info", f"«{x.name}»: narxi {money(x.price)} so'm, omborda {x.stock} dona. {human(w)} {x.sold} dona sotilgan ({money(x.rev)} so'm).",
                 links=[{"label": "Mahsulotni ochish", "url": U("gym_product_change", args=[x.pk])}], ent=_ent_json(u, w))
    return A("product_info", f"{len(rows)} ta mos mahsulot topildi. {human(w)} bo'yicha:",
             table={"cols": ["Mahsulot", "Narx", "Omborda", "Sotildi"], "rows": [[x.name, money(x.price), x.stock, x.sold] for x in rows]},
             links=[{"label": "Mahsulotlar", "url": U("gym_product_changelist")}], ent=_ent_json(u, w))


def r_plan_info(u, today):
    from .models import Membership
    w, p = _period(u, default="30d", today=today)
    pid = u.ent["plan_id"]
    now = timezone.now()
    sold = Membership.objects.filter(plan_id=pid, starts__gte=p.start_dt, starts__lt=p.end_dt).count()
    live = Membership.objects.filter(plan_id=pid, starts__lte=now, expires__gt=now).values("user").distinct().count()
    return A("plan_info", f"«{u.ent['plan']}»: {human(w)} {sold} ta sotilgan, hozir {live} kishida amal qiladi.", links=[{"label": "Abonement turlari", "url": U("gym_plan_changelist")}], ent=_ent_json(u, w))


def r_pending(u, today):
    from .models import Order, Payment, PTSession
    pays = Payment.objects.filter(status="pending")
    n_pay, n_ord = pays.count(), Order.objects.filter(status="new").count()
    n_pt = PTSession.objects.filter(status="requested", starts__gte=timezone.now()).count()
    rows = list(pays.select_related("user").order_by("-created")[:8])
    return A("pending_items", f"Kutilayotgan: {n_pay} ta to'lov, {n_ord} ta yangi buyurtma, {n_pt} ta shaxsiy mashg'ulot so'rovi.",
             table={"cols": ["To'lov", "A'zo", "Summa (so'm)", "Sana"], "rows": [[f"#{x.pk}", (x.user.first_name if x.user else "—"), money(x.amount), timezone.localtime(x.created).strftime("%d.%m %H:%M")] for x in rows]} if rows else None,
             links=[{"label": "To'lovlar", "url": U("gym_payment_changelist") + "?status__exact=pending"}, {"label": "Buyurtmalar", "url": U("gym_order_changelist") + "?status__exact=new"}, {"label": "Qabulxona", "url": U("desk")}],
             ent={"payments": n_pay, "orders": n_ord, "pt": n_pt})


def r_avg_check(u, today):
    w, p = _period(u, today=today)
    ps, pe = prev_span(w)
    cur, old = an.totals(p), an.totals(Period("ask", ps, pe))
    d = _pct(cur["avg_check"], old["avg_check"])
    return A("avg_check", f"{human(w)} o'rtacha chek: {money(cur['avg_check'])} so'm ({cur['paid_n']} ta to'lov). Oldingi davr: {money(old['avg_check'])} so'm{', ' + d if d else ''}.",
             chart=_bars([("Hozirgi", cur["avg_check"]), ("Oldingi", old["avg_check"])]), links=[{"label": "Hisobotlar", "url": U("reports")}], ent=_ent_json(u, w))


def r_trainer(u, today):
    from .models import PTSession, Trainer
    from .models_extra import TrainerReview
    w, p = _period(u, today=today)
    pt = {r["trainer"]: r["n"] for r in PTSession.objects.filter(status="confirmed", starts__gte=p.start_dt, starts__lt=p.end_dt).values("trainer").annotate(n=Count("id"))}
    rt = {r["trainer"]: (r["a"], r["n"]) for r in TrainerReview.objects.filter(hidden=False).values("trainer").annotate(a=Avg("rating"), n=Count("id"))}
    rows = []
    for t in Trainer.objects.filter(active=True):
        avg, n = rt.get(t.pk, (None, 0))
        rows.append((t, pt.get(t.pk, 0), avg, n))
    if not rows:
        return A("best_trainer", "Faol murabbiy yo'q.", links=[{"label": "Murabbiylar", "url": U("gym_trainer_changelist")}])
    rows.sort(key=lambda r: (-r[1], -(r[2] or 0), r[0].name))
    t, n, avg, nr = rows[0]
    by_rating = max((r for r in rows if r[2]), key=lambda r: (r[2], r[3]), default=None)
    extra = f" Baho bo'yicha eng yaxshisi: {by_rating[0].name} ({by_rating[2]:.1f}/5, {by_rating[3]} ta fikr)." if by_rating else " Hali baho yo'q."
    return A("best_trainer", f"{human(w)}: eng ko'p shaxsiy mashg'ulot — {t.name} ({n} ta).{extra}",
             table={"cols": ["Murabbiy", "Shaxsiy mashg'ulot", "Baho", "Fikrlar"], "rows": [[r[0].name, r[1], f"{r[2]:.1f}" if r[2] else "—", r[3]] for r in rows]},
             chart=_bars([(r[0].name, r[1]) for r in rows], "ta"), links=[{"label": "Murabbiylar", "url": U("gym_trainer_changelist")}, {"label": "Baholar", "url": U("gym_trainerreview_changelist")}], ent=_ent_json(u, w))


def r_class_attendance(u, today):
    from .models import Booking
    w, p = _period(u, default="30d", today=today)
    qs = Booking.objects.filter(date__gte=p.start, date__lte=p.end)
    a = qs.aggregate(n=Count("id"), come=Count("id", filter=Q(checked_in_at__isnull=False)), miss=Count("id", filter=Q(no_show=True)))
    rows = list(qs.values("gym_class__name").annotate(n=Count("id"), miss=Count("id", filter=Q(no_show=True)), come=Count("id", filter=Q(checked_in_at__isnull=False))).order_by("-n")[:10])
    if not a["n"]:
        return A("class_attendance", f"{human(w)} davrida mashg'ulotga bron qilinmagan.", links=[{"label": "Bronlar", "url": U("gym_booking_changelist")}], ent=_ent_json(u, w))
    rate = round(a["miss"] / a["n"] * 100)
    return A("class_attendance", f"{human(w)}: {a['n']} ta bron, {a['come']} tasi belgilangan (keldi), {a['miss']} ta kelmadi ({rate}%).",
             table={"cols": ["Mashg'ulot", "Bron", "Keldi", "Kelmadi"], "rows": [[r["gym_class__name"], r["n"], r["come"], r["miss"]] for r in rows]},
             chart=_bars([(r["gym_class__name"], r["n"]) for r in rows], "ta"), links=[{"label": "Davomat", "url": U("desk_classes")}, {"label": "Bronlar", "url": U("gym_booking_changelist")}], ent=_ent_json(u, w))


def r_guests(u, today):
    from .models_extra import GuestPass
    w, p = _period(u, default="30d", today=today)
    qs = GuestPass.objects.filter(date__gte=p.start, date__lte=p.end)
    a = qs.aggregate(n=Count("id"), used=Count("id", filter=Q(used_at__isnull=False)), canc=Count("id", filter=Q(cancelled_at__isnull=False)))
    return A("guest_passes", f"{human(w)}: {a['n']} ta mehmon taklifnomasi berilgan, {a['used']} tasi ishlatilgan, {a['canc']} tasi bekor qilingan.",
             chart=_bars([("Berilgan", a["n"]), ("Ishlatilgan", a["used"]), ("Bekor", a["canc"])], "ta"), links=[{"label": "Taklifnomalar", "url": U("gym_guestpass_changelist")}], ent=_ent_json(u, w))


def r_freezes(u, today):
    from .models_extra import MembershipFreeze
    now_rows = list(MembershipFreeze.objects.filter(start_date__lte=today, end_date__gt=today).select_related("membership__user").order_by("end_date")[:10])
    total_now = MembershipFreeze.objects.filter(start_date__lte=today, end_date__gt=today).values("membership__user").distinct().count()
    w, p = _period(u, default="30d", today=today)
    started = MembershipFreeze.objects.filter(start_date__gte=p.start, start_date__lte=p.end, end_date__gt=F("start_date")).count()
    return A("freezes", f"Hozir {total_now} ta abonement muzlatilgan; {human(w)} {started} ta yangi muzlatish boshlangan.",
             table={"cols": ["A'zo", "Qaytadi", "Kun"], "rows": [[f"{f.membership.user.first_name} {f.membership.user.last_name}".strip() or f.membership.user.username, f.end_date.strftime("%d.%m.%Y"), f.days] for f in now_rows]} if now_rows else None,
             links=[{"label": "Muzlatishlar", "url": U("gym_membershipfreeze_changelist")}], ent={**_ent_json(u, w), "now": total_now, "started": started})


def r_referrals(u, today):
    from .models import User
    from .models_extra import ReferralReward
    w, p = _period(u, default="30d", today=today)
    invited = an.members_qs().filter(referred_by__isnull=False, created__gte=p.start_dt, created__lt=p.end_dt).count()
    rewards = ReferralReward.objects.filter(created__gte=p.start_dt, created__lt=p.end_dt).aggregate(n=Count("id"), d=Sum("days"))
    top = list(an.members_qs().annotate(c=Count("referrals")).filter(c__gt=0).order_by("-c")[:5])
    return A("referrals", f"{human(w)}: {invited} ta do'st taklif orqali kelgan, {rewards['n']} marta bonus berilgan (jami {rewards['d'] or 0} kun).",
             table={"cols": ["A'zo", "Taklif qilganlar"], "rows": [[f"{x.first_name} {x.last_name}".strip() or x.username, x.c] for x in top]} if top else None,
             links=[{"label": "Taklif bonuslari", "url": U("gym_referralreward_changelist")}], ent=_ent_json(u, w))


def r_churn(u, today):
    w, p = _period(u, default="30d", today=today)
    k = an.kpis(p)
    from .models import Membership
    cut = min(p.end_dt, timezone.now())
    window = Membership.objects.filter(user__is_superuser=False, expires__gte=p.start_dt, expires__lt=cut)
    lapsed = list(an.members_qs().filter(pk__in=window.values("user")).annotate(until=Max("memberships__expires")).filter(until__lt=cut).order_by("until")[:10])
    return A("churn", f"{human(w)}: {k['ended']} kishining abonementi tugagan, {k['renewed']} tasi uzaytirgan, {k['churn']} tasi uzaytirmagan.",
             table=_members_table([[f"{x.first_name} {x.last_name}".strip() or x.username, x.phone or "—", timezone.localtime(x.until).strftime("%d.%m.%Y")] for x in lapsed]) if lapsed else None,
             links=[{"label": "Analitika", "url": U("analytics")}], ent={**_ent_json(u, w), "churn": k["churn"]})


def r_renewal(u, today):
    w, p = _period(u, default="30d", today=today)
    k = an.kpis(p)
    card = next(c for c in k["cards"] if c["key"] == "renewal")
    if card["value"] is None:
        return A("renewal_rate", f"{human(w)} davrida abonementi tugagan a'zo yo'q.", ent=_ent_json(u, w))
    return A("renewal_rate", f"{human(w)} uzaytirish ulushi: {card['value']}% ({k['renewed']} / {k['ended']}).", links=[{"label": "Analitika", "url": U("analytics")}], ent={**_ent_json(u, w), "rate": card["value"]})


def r_help(u, today):
    return A("help", "Men admin panel ma'lumotlaridan javob beraman: tushum, a'zolar, tashriflar, abonementlar, mahsulotlar, to'lovlar, murabbiylar va mashg'ulotlar haqida so'rang. O'zbekcha (lotin/kirill), ruscha yoki inglizcha yozishingiz mumkin.",
             follow=SUGGESTIONS[:8])


def unknown(u, question=""):
    tips = []
    _, tokens = prepare(question)
    for t in tokens:
        if len(t) >= 4:
            for hit in difflib.get_close_matches(t, list(VOCAB), n=1, cutoff=0.72):
                if VOCAB[hit] not in tips:
                    tips.append(VOCAB[hit])
    return {"ok": True, "intent": "unknown", "text": "Tushunmadim. Savolni boshqacha yozib ko'ring yoki quyidagilardan birini tanlang.", "table": None, "chart": None, "links": [],
            "entities": {}, "suggestions": (tips + SUGGESTIONS)[:8]}


RUNNERS = {
    "revenue_total": r_revenue_total, "revenue_by_method": r_revenue_by_method, "revenue_by_plan": r_revenue_by_plan, "shop_sales": r_shop_sales, "compare": r_compare,
    "new_members": r_new_members, "active_members": r_active_members, "members_total": r_members_total, "visits_total": r_visits_total, "peak_hours": r_peak, "peak_days": r_peak,
    "expiring_members": r_expiring, "inactive_members": r_inactive, "top_products": r_products, "least_products": r_products, "low_stock": r_low_stock,
    "product_info": r_product_info, "plan_info": r_plan_info, "pending_items": r_pending, "avg_check": r_avg_check, "best_trainer": r_trainer, "class_attendance": r_class_attendance,
    "guest_passes": r_guests, "freezes": r_freezes, "referrals": r_referrals, "churn": r_churn, "renewal_rate": r_renewal, "help": r_help,
}
INTENTS = sorted(RUNNERS) + ["unknown"]


def answer(question, last=None, today=None):
    """The public entry point: returns a JSON-ready dict. `last` is the previous intent, used when a follow-up only names a new period («o'tgan oy?»)."""
    question = (question or "").strip()
    if not question:
        return {"ok": False, "error": "Savol yozing."}
    today = today or timezone.localdate()
    u = understand(question, today=today, last=last if last in RUNNERS else None)
    if u.intent == "unknown":
        return unknown(u, question)
    return run(u, today)


def mask(text):
    """For the question log: long digit runs (phone numbers, card numbers) never get stored."""
    return re.sub(r"\d{5,}", "#", text or "")[:200]
