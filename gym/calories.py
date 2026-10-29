"""Calorie tracker: the built-in food table, the daily target and the split of what is left over the day.

Food values are per 100 g (kcal, protein, fat, carbs): rounded averages of common reference tables, good enough
for tracking, not for medical diets.
"""
import re
from datetime import date
from decimal import Decimal

from django.utils import timezone

MEALS = ["breakfast", "lunch", "dinner", "snack"]
MEAL_SHARE = {"breakfast": 25, "lunch": 35, "dinner": 30, "snack": 10}
MEAL_ICON = {"breakfast": "🍳", "lunch": "🍲", "dinner": "🍽", "snack": "🍎"}
DEFAULT_TARGET = 2200

# name, kcal, protein, fat, carbs per 100 g
FOODS = [
    ("Osh (palov)", 200, 6, 9, 24), ("Lag'mon", 135, 6, 5, 17), ("Manti", 210, 9, 10, 20), ("Somsa (go'shtli)", 290, 9, 17, 26),
    ("Shashlik (mol go'shti)", 230, 24, 15, 0), ("Shashlik (qo'y go'shti)", 260, 22, 19, 0), ("Non (tandir)", 260, 8, 1, 54),
    ("Oq non", 265, 8, 3, 50), ("Guruch (pishirilgan)", 130, 2.7, 0.3, 28), ("Grechka (pishirilgan)", 110, 4, 1, 21),
    ("Suli bo'tqasi (suvda)", 70, 2.5, 1.4, 12), ("Makaron (pishirilgan)", 160, 5.5, 1, 31), ("Kartoshka (qaynatilgan)", 82, 2, 0.4, 17),
    ("Kartoshka fri", 310, 3.8, 15, 41), ("Tuxum (qaynatilgan)", 155, 13, 11, 1.1), ("Omlet", 185, 11, 14, 2),
    ("Tovuq ko'kragi (pishirilgan)", 165, 31, 3.6, 0), ("Tovuq go'shti (qovurilgan)", 240, 27, 14, 0), ("Mol go'shti (qaynatilgan)", 250, 26, 16, 0),
    ("Qo'y go'shti (qaynatilgan)", 290, 25, 21, 0), ("Baliq (qaynatilgan)", 130, 22, 4.5, 0), ("Tuna (konserva)", 116, 26, 1, 0),
    ("Kolbasa (qaynatilgan)", 300, 12, 28, 1.5), ("Sut (2.5%)", 52, 2.9, 2.5, 4.7), ("Kefir (2.5%)", 53, 3, 2.5, 4), ("Qatiq", 60, 3, 3.2, 4),
    ("Tvorog (5%)", 121, 17, 5, 3), ("Tvorog (past yog'li)", 88, 18, 1, 3), ("Pishloq", 350, 25, 27, 1), ("Smetana (20%)", 206, 2.8, 20, 3.2),
    ("Sariyog'", 717, 0.8, 81, 0.6), ("O'simlik moyi", 899, 0, 99.9, 0), ("Banan", 89, 1.1, 0.3, 23), ("Olma", 52, 0.3, 0.2, 14),
    ("Uzum", 69, 0.7, 0.2, 18), ("Behi", 57, 0.4, 0.1, 15), ("Anor", 83, 1.7, 1.2, 19), ("Apelsin", 47, 0.9, 0.1, 12),
    ("Qovun", 35, 0.8, 0.2, 8), ("Tarvuz", 30, 0.6, 0.2, 8), ("O'rik (quritilgan)", 241, 3.4, 0.5, 63), ("Mayiz", 299, 3, 0.5, 79),
    ("Yong'oq (grek)", 654, 15, 65, 14), ("Bodom", 579, 21, 50, 22), ("Pista", 560, 20, 45, 28), ("Pomidor", 18, 0.9, 0.2, 3.9),
    ("Bodring", 15, 0.7, 0.1, 3.6), ("Sabzi", 41, 0.9, 0.2, 10), ("Piyoz", 40, 1.1, 0.1, 9), ("Karam", 25, 1.3, 0.1, 6),
    ("Shirchoy (sho'rva)", 60, 3, 3, 5), ("Mastava", 75, 4, 3, 8), ("Sho'rva", 70, 5, 4, 4), ("Dimlama", 120, 7, 7, 8),
    ("Chuchvara", 230, 11, 10, 25), ("Qozon kabob", 280, 17, 20, 7), ("Pitsa", 266, 11, 10, 33), ("Burger", 250, 13, 12, 22),
    ("Shokolad (sutli)", 535, 7.7, 30, 59), ("Pechenye", 440, 6.5, 17, 66), ("Qand", 387, 0, 0, 100), ("Asal", 304, 0.3, 0, 82),
    ("Choy (shakarsiz)", 1, 0, 0, 0.2), ("Choy (2 qand bilan)", 30, 0, 0, 8), ("Kola", 42, 0, 0, 10.6), ("Apelsin sharbati", 45, 0.7, 0.2, 10),
    ("Protein kukuni (whey)", 400, 80, 6, 8), ("Protein batonchik", 370, 30, 12, 35),
]


def food_table():
    return [{"i": i, "name": n, "kcal": k, "p": p, "f": f, "c": c} for i, (n, k, p, f, c) in enumerate(FOODS)]


def per_portion(food, grams):
    """(kcal, protein, fat, carbs) of `grams` of a food row, rounded to one decimal."""
    _, k, p, f, c = food
    r = lambda v: Decimal(str(round(v * grams / 100, 1)))
    return r(k), r(p), r(f), r(c)


def age_of(birth, today=None):
    if not birth:
        return None
    today = today or timezone.localdate()
    return today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))


def daily_target(user):
    """(kcal, how) - Mifflin-St Jeor with a light-activity factor and the goal's adjustment when the profile has weight,
    height and age; otherwise a plain default. `how` tells the page where the number came from."""
    last = user.bodylogs.order_by("-date", "-id").first()
    age = age_of(user.birth_date)
    if not (last and last.height_cm and age and 10 <= age <= 100):
        return DEFAULT_TARGET, "default"
    # the profile has no sex field: the midpoint between the male (+5) and female (-161) constants
    bmr = 10 * float(last.weight) + 6.25 * last.height_cm - 5 * age - 78
    tdee = bmr * 1.4
    adj = {"lose": -400, "gain": 350, "strength": 200}.get(user.goal, 0)
    return int(round(max(1200, tdee + adj), -1)), "profile"


def day_summary(user, day):
    """Everything the page draws for one day."""
    entries = list(user.food_entries.filter(date=day))
    target, how = daily_target(user)
    tot = {"kcal": Decimal(0), "protein": Decimal(0), "fat": Decimal(0), "carbs": Decimal(0)}
    per_meal = {m: {"kcal": Decimal(0), "items": []} for m in MEALS}
    for e in entries:
        for k in tot:
            tot[k] += getattr(e, k)
        slot = per_meal.setdefault(e.meal, {"kcal": Decimal(0), "items": []})
        slot["kcal"] += e.kcal
        slot["items"].append(e)
    eaten = float(tot["kcal"])
    left = target - eaten
    # macro split by energy: 4 kcal/g protein and carbs, 9 kcal/g fat
    pe, fe, ce = float(tot["protein"]) * 4, float(tot["fat"]) * 9, float(tot["carbs"]) * 4
    energy = (pe + fe + ce) or 1
    macros = [("protein", float(tot["protein"]), round(pe * 100 / energy)), ("fat", float(tot["fat"]), round(fe * 100 / energy)),
              ("carbs", float(tot["carbs"]), round(ce * 100 / energy))]
    meals = []
    for m in MEALS:
        planned = round(target * MEAL_SHARE[m] / 100)
        meals.append({"key": m, "icon": MEAL_ICON[m], "kcal": int(per_meal[m]["kcal"]), "items": per_meal[m]["items"], "planned": planned,
                      "pct": min(100, round(float(per_meal[m]["kcal"]) * 100 / planned)) if planned else 0})
    return {"day": day, "entries": entries, "target": target, "how": how, "eaten": int(round(eaten)), "left": int(round(left)), "over": left < 0,
            "pct": min(100, round(eaten * 100 / target)) if target else 0, "protein": tot["protein"], "fat": tot["fat"], "carbs": tot["carbs"],
            "macros": macros, "has_macros": bool(entries), "meals": meals, "advice": advise(target, per_meal, left)}


def advise(target, per_meal, left):
    """How many kcal each meal that is still empty can take: what is left is spread by the usual shares of those meals."""
    if left <= 0:
        return []
    open_meals = [m for m in MEALS if per_meal[m]["kcal"] == 0]
    if not open_meals:
        return [("snack", int(left))]  # every meal has something: what is left fits one more snack
    total = sum(MEAL_SHARE[m] for m in open_meals)
    return [(m, int(round(left * MEAL_SHARE[m] / total, -1))) for m in open_meals]


def parse_day(raw):
    try:
        d = date.fromisoformat(raw or "")
    except ValueError:
        return timezone.localdate()
    return d if date(2020, 1, 1) <= d <= timezone.localdate() else timezone.localdate()


# ---------------------------------------------------------------- free text -> foods ("2 ta somsa va choy", "200 g osh", "3 tuxum")
# No network and no AI: the words are matched against the built-in table above.

# stems (a word that starts with one of them, up to a short ending, names the food), start of the table name (no apostrophes, lower case),
# grams of one piece (0 = not counted in pieces), default portion in grams when no amount is given
FOOD_ALIASES = [
    (("osh", "palov", "plov", "плов", "pilaf", "pilav"), "osh", 0, 250), (("lagmon", "lagman", "лагман"), "lagmon", 0, 350),
    (("manti", "манты", "мант"), "manti", 70, 210), (("somsa", "samsa", "samosa", "самс"), "somsa", 120, 120),
    (("shashlik", "шашлык", "kebab", "kabob"), "shashlik", 80, 160), (("non", "хлеб", "лепёшк", "лепешк", "bread"), "non", 150, 150),
    (("guruch", "рис", "rice"), "guruch", 0, 200), (("grechka", "grecha", "гречк", "buckwheat"), "grechka", 0, 200),
    (("makaron", "макарон", "pasta"), "makaron", 0, 200), (("kartoshka", "картош", "картоф", "potato"), "kartoshka", 0, 200),
    (("tuxum", "яйц", "яиц", "egg"), "tuxum", 55, 55), (("omlet", "омлет"), "omlet", 0, 150),
    (("tovuq", "куриц", "курин", "chicken"), "tovuq", 0, 150), (("mol", "говяд", "beef"), "mol", 0, 150),
    (("baliq", "рыб", "fish"), "baliq", 0, 150), (("suli", "овсян", "oat"), "suli", 0, 250), (("sut", "молок", "milk"), "sut", 0, 200),
    (("kefir", "кефир"), "kefir", 0, 200), (("qatiq", "катык", "yogurt", "йогурт"), "qatiq", 0, 200),
    (("tvorog", "творог", "cottage"), "tvorog", 0, 150), (("pishloq", "сыр", "cheese"), "pishloq", 20, 30),
    (("banan", "банан"), "banan", 120, 120), (("olma", "яблок", "apple"), "olma", 180, 180), (("uzum", "виноград", "grape"), "uzum", 0, 100),
    (("apelsin", "апельсин", "orange"), "apelsin", 150, 150), (("qovun", "дын", "melon"), "qovun", 0, 200),
    (("tarvuz", "арбуз", "watermelon"), "tarvuz", 0, 300), (("anor", "гранат", "pomegranate"), "anor", 0, 150),
    (("behi", "айв", "quince"), "behi", 0, 150), (("pomidor", "помидор", "томат", "tomato"), "pomidor", 100, 100),
    (("bodring", "огур", "cucumber"), "bodring", 100, 100), (("sabzi", "морков", "carrot"), "sabzi", 80, 80),
    (("yongoq", "грецк", "walnut"), "yongoq", 0, 30), (("bodom", "миндал", "almond"), "bodom", 0, 30),
    (("pista", "фисташк", "pistachio"), "pista", 0, 30), (("mayiz", "изюм", "raisin"), "mayiz", 0, 30),
    (("orik", "курага", "apricot"), "orik", 0, 30), (("asal", "мёд", "мед", "honey"), "asal", 0, 20),
    (("qand", "shakar", "сахар", "sugar"), "qand", 0, 10), (("chuchvara", "пельмен", "dumpling"), "chuchvara", 0, 200),
    (("mastava", "мастав"), "mastava", 0, 300), (("shorva", "шурп", "soup", "суп"), "shorva", 0, 300),
    (("shirchoy",), "shirchoy", 0, 300), (("dimlama", "димлям"), "dimlama", 0, 300), (("pitsa", "pizza", "пицц"), "pitsa", 110, 110),
    (("burger", "бургер", "gamburger"), "burger", 200, 200), (("kolbasa", "колбас", "sausage"), "kolbasa", 50, 100),
    (("tuna", "тунец", "тунц"), "tuna", 0, 100), (("shokolad", "шоколад", "chocolate"), "shokolad", 0, 40),
    (("pechenye", "печень", "cookie", "biscuit"), "pechenye", 12, 36), (("choy", "чай", "tea"), "choy", 200, 200),
    (("kola", "кола", "cola", "coke"), "kola", 330, 330), (("sariyog", "сливочн", "butter"), "sariyog", 10, 10),
    (("protein", "протеин"), "protein kukuni", 30, 30),
]
NUM_WORDS = {"bir": 1, "bitta": 1, "ikki": 2, "ikkita": 2, "uch": 3, "uchta": 3, "tort": 4, "tortta": 4, "besh": 5, "beshta": 5,
             "olti": 6, "oltita": 6, "yetti": 7, "yettita": 7, "sakkiz": 8, "sakkizta": 8, "toqqiz": 9, "toqqizta": 9,
             "один": 1, "одна": 1, "одну": 1, "два": 2, "две": 2, "три": 3, "четыре": 4, "пять": 5, "шесть": 6,
             "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6}
_GRAM_U = {"gramm", "gram", "gr", "g", "г", "гр", "грам", "грамм", "грамма", "граммов", "граммах", "grams", "gramma"}
_KG_U = {"kg", "kilo", "kilogramm", "кг", "кило", "килограмм"}
_PC_U = {"ta", "dona", "шт", "штук", "штуки", "штука", "pcs", "pc", "piece", "pieces", "portion", "porsiya", "порция", "порции"}
_APOS = "ʻʼ’‘`´'"


def _plain(s):
    s = str(s or "").lower().replace("ё", "е")
    for ch in _APOS:
        s = s.replace(ch, "")
    return s


def _resolve_aliases():
    names = [_plain(f[0]) for f in FOODS]
    out = []
    for stems, prefix, piece, default in FOOD_ALIASES:
        idx = next((i for i, n in enumerate(names) if n.startswith(prefix)), None)
        if idx is not None:
            out.append((tuple(_plain(s) for s in stems), idx, piece, default))
    return out


_ALIASES = _resolve_aliases()


def _amount_tokens(toks):
    """[{v, unit, s, e, used}]: every number (digits or a number word) with the unit that follows it."""
    qs, i = [], 0
    while i < len(toks):
        t, v, unit = toks[i], None, None
        if t[0].isdigit():
            v = float(t.replace(",", "."))
        elif t in NUM_WORDS:
            v = float(NUM_WORDS[t])
            unit = "pc" if t.endswith("ta") else None
        if v is None:
            i += 1
            continue
        q = {"v": v, "unit": unit, "s": i, "e": i, "used": False}
        nxt = toks[i + 1] if i + 1 < len(toks) else ""
        if nxt in _GRAM_U:
            q["unit"], q["e"] = "g", i + 1
        elif nxt in _KG_U:
            q["unit"], q["e"] = "kg", i + 1
        elif nxt in _PC_U:
            q["unit"], q["e"] = "pc", i + 1
        qs.append(q)
        i = q["e"] + 1
    return qs


def parse_text(text):
    """Free text -> [{idx, name, grams, kcal, protein, fat, carbs}] for the foods of the built-in table it names, in the order they appear.
    A number before (or just after) a food is its amount: "200 g osh", "2 ta somsa", "osh 300 gramm"; with no amount a usual portion is used."""
    toks = re.findall(r"\d+(?:[.,]\d+)?|[^\W\d_]+", _plain(text)[:300], re.UNICODE)
    qs = _amount_tokens(toks)
    hits = []
    for stems, idx, piece, default in _ALIASES:
        for k, tok in enumerate(toks):
            if tok[0].isdigit():
                continue
            if any(tok.startswith(s) and len(tok) - len(s) <= (3 if len(s) <= 3 else 5) for s in stems):
                hits.append((k, idx, piece, default))
                break
    hits.sort()
    out, seen = [], set()
    for k, idx, piece, default in hits:
        if idx in seen:
            continue
        seen.add(idx)
        q = next((c for c in qs if not c["used"] and c["e"] < k and k - c["e"] <= 2), None) \
            or next((c for c in qs if not c["used"] and c["s"] > k and c["s"] - k <= 3), None)
        unit_g = piece or default
        if q:
            q["used"] = True
            if q["unit"] == "kg":
                grams = q["v"] * 1000
            elif q["unit"] == "g":
                grams = q["v"]
            elif q["unit"] == "pc" or q["v"] < 25:
                grams = q["v"] * unit_g
            else:
                grams = q["v"]
        else:
            grams = unit_g
        grams = max(1, min(5000, int(round(grams))))
        kcal, p, f, c = (float(x) for x in per_portion(FOODS[idx], grams))
        out.append({"idx": idx, "name": FOODS[idx][0], "grams": grams, "kcal": kcal, "protein": p, "fat": f, "carbs": c})
        if len(out) >= 12:
            break
    return out
