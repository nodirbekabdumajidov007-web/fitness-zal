"""The assistant's knowledge base: the three row lists joined into one list of dicts.

Rows live in assistant_kb_site.py (gym and website + personal + small talk), assistant_kb_train.py (training)
and assistant_kb_food.py (nutrition). See assistant_kb_site.py for the row format.
"""
from .assistant_kb_food import FOOD
from .assistant_kb_site import SITE
from .assistant_kb_train import TRAIN

LANGS = ("uz", "ru", "en")


def _build():
    out, seen = [], set()
    for row in SITE + TRAIN + FOOD:
        eid, topic, kw_uz, kw_ru, kw_en, a_uz, a_ru, a_en, links = row
        if eid in seen:
            raise ValueError(f"duplicate knowledge base id: {eid}")
        seen.add(eid)
        out.append({
            "id": eid, "topic": topic,
            "kw": {"uz": kw_uz.split("|"), "ru": kw_ru.split("|"), "en": kw_en.split("|")},
            "a": {"uz": a_uz, "ru": a_ru, "en": a_en},
            "links": tuple(links),
        })
    return out


ENTRIES = _build()
BY_ID = {e["id"]: e for e in ENTRIES}

# entries that need a signed-in member (their answers are built from the member's own data)
PERSONAL = {"me_membership", "me_calories", "me_profile", "me_target"}
# shown as "try asking" when nothing matched and nothing was close
POPULAR = ["hours", "prices", "beginner_plan", "protein_need", "fat_loss_train", "osh_cal"]
