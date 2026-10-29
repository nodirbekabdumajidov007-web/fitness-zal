"""Calorie tracker: the built-in food table, the daily target and the split of what is left over the day.

Food values are per 100 g (kcal, protein, fat, carbs): rounded averages of common reference tables, good enough
for tracking, not for medical diets.
"""
import re
from datetime import date
from decimal import Decimal

from django.utils import timezone

from . import food_db

MEALS = ["breakfast", "lunch", "dinner", "snack"]
MEAL_SHARE = {"breakfast": 25, "lunch": 35, "dinner": 30, "snack": 10}
MEAL_ICON = {"breakfast": "🍳", "lunch": "🍲", "dinner": "🍽", "snack": "🍎"}
DEFAULT_TARGET = 2200

# name, kcal, protein, fat, carbs per 100 g. The table lives in gym/food_db.py (~600 foods, searchable in uz / ru / en); the row number of a
# food is its id, the first 68 rows are the original table, so saved links and old code that index FOODS keep working.
FOODS = [(f.name, f.kcal, f.p, f.f, f.c) for f in food_db.FOODS_DB]


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
# No network and no AI: the words are matched against the built-in database (gym/food_db.py) and the member's own foods.

NUM_WORDS = {"bir": 1, "bitta": 1, "ikki": 2, "ikkita": 2, "uch": 3, "uchta": 3, "tort": 4, "tortta": 4, "besh": 5, "beshta": 5,
             "olti": 6, "oltita": 6, "yetti": 7, "yettita": 7, "sakkiz": 8, "sakkizta": 8, "toqqiz": 9, "toqqizta": 9,
             "один": 1, "одна": 1, "одну": 1, "два": 2, "две": 2, "три": 3, "четыре": 4, "пять": 5, "шесть": 6,
             "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6}
_GRAM_U = {"gramm", "gram", "gr", "g", "г", "гр", "грам", "грамм", "грамма", "граммов", "граммах", "grams", "gramma"}
_KG_U = {"kg", "kilo", "kilogramm", "кг", "кило", "килограмм"}
_PC_U = {"ta", "dona", "шт", "штук", "штуки", "штука", "pcs", "pc", "piece", "pieces", "portion", "porsiya", "порция", "порции"}


_APOS = "ʻʼ’‘`´'"


def _plain(s):
    """Lower case, apostrophes dropped; punctuation stays so that "1.5 kg" is still one number."""
    s = str(s or "").lower().replace("ё", "е")
    for ch in _APOS:
        s = s.replace(ch, "")
    return s


def user_foods(user):
    """The member's own foods as search rows (they come before the built-in ones)."""
    if user is None or not getattr(user, "is_authenticated", False):
        return []
    return [food_db.Food(u.pk, u.name, float(u.kcal), float(u.protein), float(u.fat), float(u.carbs), 0, u.portion_g,
                         (_plain(u.name),), (_plain(u.name),), mine=True) for u in user.my_foods.all()[:200]]


def find_food(ref, user=None):
    """A posted food reference ("12" = built-in row, "u5" = the member's own food) -> Food or None."""
    ref = str(ref or "").strip()
    if ref.isdigit() and int(ref) < len(food_db.FOODS_DB):
        return food_db.FOODS_DB[int(ref)]
    if ref[:1] == "u" and ref[1:].isdigit() and user is not None and user.is_authenticated:
        u = user.my_foods.filter(pk=int(ref[1:])).first()
        if u:
            return food_db.Food(u.pk, u.name, float(u.kcal), float(u.protein), float(u.fat), float(u.carbs), 0, u.portion_g,
                                (_plain(u.name),), (_plain(u.name),), mine=True)
    return None


def _amount_tokens(toks):
    """[{v, unit, s, e, used}]: every number (digits or a number word) with the unit that follows it."""
    qs, i = [], 0
    while i < len(toks):
        t, v, unit = toks[i], None, None
        if t.endswith("%"):  # "sut 2.5%" / "kefir 1%": a fat percentage names the product, it is not an amount
            i += 1
            continue
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


def parse_text(text, user=None):
    """Free text -> [{idx, name, grams, kcal, protein, fat, carbs, mine}] for the foods it names (built-in database and the member's own foods),
    in the order they appear. A number before (or just after) a food is its amount: "200 g osh", "2 ta somsa", "osh 300 gramm";
    with no amount a usual portion is used. `idx` is what calories_add takes as `food`."""
    toks = [t.replace(",", ".") if t.endswith("%") else t for t in re.findall(r"\d+(?:[.,]\d+)?%?|[^\W\d_]+", _plain(text)[:300], re.UNICODE)]
    qs = _amount_tokens(toks)
    out = []
    found = food_db.find_foods(toks, user_foods(user))
    for n, (a, b, f) in enumerate(found):
        nxt = found[n + 1][0] if n + 1 < len(found) else None  # a number right before the next food belongs to that food
        q = next((c for c in qs if not c["used"] and c["e"] < a and a - c["e"] <= 2), None)
        q = q or next((c for c in qs if not c["used"] and c["s"] > b and c["s"] - b <= 3
                       and not (nxt is not None and c["e"] < nxt and nxt - c["e"] <= 2)), None)
        unit_g = f.piece or f.default_grams
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
            grams = f.default_grams
        grams = max(1, min(5000, int(round(grams))))
        kcal, p, fat, c = (float(x) for x in per_portion((f.name, f.kcal, f.p, f.f, f.c), grams))
        out.append({"idx": f.as_dict()["id"], "name": f.name, "grams": grams, "kcal": kcal, "protein": p, "fat": fat, "carbs": c, "mine": f.mine})
        if len(out) >= 12:
            break
    return out
