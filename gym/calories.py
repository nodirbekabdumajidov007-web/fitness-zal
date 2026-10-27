"""Calorie tracker: the built-in food table, the daily target and the split of what is left over the day.

Food values are per 100 g (kcal, protein, fat, carbs): rounded averages of common reference tables, good enough
for tracking, not for medical diets.
"""
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


# ---------------------------------------------------------------- AI estimate

ESTIMATE_SCHEMA = {
    "type": "object",
    "properties": {"items": {"type": "array", "items": {
        "type": "object",
        "properties": {"name": {"type": "string"}, "grams": {"type": "integer"}, "kcal": {"type": "number"},
                       "protein": {"type": "number"}, "fat": {"type": "number"}, "carbs": {"type": "number"}},
        "required": ["name", "grams", "kcal", "protein", "fat", "carbs"], "additionalProperties": False}}},
    "required": ["items"], "additionalProperties": False,
}


def estimate(user, text, lang="uz"):
    """Free text ("2 ta somsa va choy") -> list of dicts for the whole portions. One AI request of the daily limit."""
    import json
    from . import ai
    text = (text or "").strip()[:300]
    if not text:
        raise ai.AIError("ai_empty")
    ai._take_quota(user)
    raw = ai._call(
        max_tokens=2000,
        system=("You estimate food nutrition for a calorie tracker used in Uzbekistan. Split the meal description into separate foods, "
                "guess a realistic portion in grams when it is not given (one somsa about 120 g, one egg 55 g, a cup of tea 200 g), "
                "and give kcal, protein, fat and carbs of the WHOLE portion. Names short, in " + ai.LANG_NAMES.get(lang, "Uzbek (Latin script)") + "."),
        output_config={"effort": "low", "format": {"type": "json_schema", "schema": ESTIMATE_SCHEMA}},
        messages=[{"role": "user", "content": f"<meal>{text}</meal>"}],
    )
    try:
        data = json.loads(raw)
    except ValueError:
        raise ai.AIError("ai_error")
    out = []
    for it in data.get("items", [])[:12]:  # nothing the model returns is trusted blindly
        try:
            grams = max(1, min(int(it["grams"]), 5000))
            vals = [max(0.0, min(float(it[k]), 6000.0)) for k in ("kcal", "protein", "fat", "carbs")]
        except (KeyError, TypeError, ValueError):
            continue
        name = str(it.get("name", "")).strip()[:80]
        if name:
            out.append({"name": name, "grams": grams, "kcal": round(vals[0], 1), "protein": round(vals[1], 1), "fat": round(vals[2], 1), "carbs": round(vals[3], 1)})
    if not out:
        raise ai.AIError("ai_error")
    return out
