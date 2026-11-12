"""The assistant's knowledge base: the three row lists joined into one list of dicts.

Rows live in assistant_kb_site.py (gym and website + personal + small talk), assistant_kb_train.py (training)
assistant_kb_food.py (nutrition) and the newer parts: _ex (exercises), _prog (programming, body parts), _health (recovery, health, mindset),
_nutr (more nutrition), _site2 (site, page by page), _misc (small talk, myths). See assistant_kb_site.py for the row format.
"""
from .assistant_kb_ex import EX
from .assistant_kb_ex2 import EX2
from .assistant_kb_faq import BEGINNER, EQUIPMENT, ETIQUETTE, GLOSSARY
from .assistant_kb_faq2 import BEGINNER2
from .assistant_kb_site3 import SITE3, SMALL
from .assistant_kb_food2 import FOOD2
from .assistant_kb_myth import FAQ_LOSS, FAQ_RECOVERY, MYTHS
from .assistant_kb_sport import REHAB, SPORT
from .assistant_kb_food import FOOD
from .assistant_kb_health import HEALTH
from .assistant_kb_live import LIVE
from .assistant_kb_misc import MISC
from .assistant_kb_more import MORE
from .assistant_kb_nutr import NUTR
from .assistant_kb_prog import PROG
from .assistant_kb_site import SITE
from .assistant_kb_site2 import SITE2
from .assistant_kb_train import TRAIN

from .i18n import CHAIN, LANGS  # noqa: E402,F401  (uz, ru, en, tr, ky, tg)


def _build():
    out, seen = [], set()
    for row in SITE + TRAIN + FOOD + EX + PROG + HEALTH + NUTR + SITE2 + MISC + MORE + EX2 + SPORT + REHAB + FOOD2 + MYTHS + FAQ_LOSS + FAQ_RECOVERY + BEGINNER + ETIQUETTE + EQUIPMENT + GLOSSARY + BEGINNER2 + SITE3 + SMALL + LIVE:
        eid, topic, kw_uz, kw_ru, kw_en, a_uz, a_ru, a_en, links = row
        if eid in seen:
            raise ValueError(f"duplicate knowledge base id: {eid}")
        seen.add(eid)
        out.append({
            "id": eid, "topic": topic,
            "kw": {"uz": kw_uz.split("|"), "ru": kw_ru.split("|"), "en": kw_en.split("|"), "tr": [], "ky": [], "tg": []},
            "a": {"uz": a_uz, "ru": a_ru, "en": a_en, "tr": "", "ky": "", "tg": ""},
            "links": tuple(links),
        })
    return out


def _merge_extra(entries):
    """Turkish / Kyrgyz / Tajik keywords and answers (assistant_kb_x*.py): {id: (kw_tr, kw_ky, kw_tg, a_tr, a_ky, a_tg)}. An entry without them is
    still found by its uz / ru / en keywords, and is answered in the fallback language (tr -> en, ky / tg -> ru); keywords can exist without an answer."""
    from .assistant_kb_x import XT
    by_id = {e["id"]: e for e in entries}
    for eid, row in XT.items():
        e = by_id.get(eid)
        if e is None:
            raise ValueError(f"assistant_kb_x: unknown entry id {eid}")
        for lg, kw, ans in zip(("tr", "ky", "tg"), row[:3], row[3:]):
            e["kw"][lg] = [k for k in kw.split("|") if k]
            e["a"][lg] = ans


def answer_text(entry, lang):
    """The answer in `lang`; an entry with no text of its own in that language is answered along the fallback chain (tr -> en, ky / tg -> ru -> uz)."""
    for lg in CHAIN.get(lang, ("uz",)):
        if entry["a"].get(lg):
            return entry["a"][lg]
    return entry["a"]["uz"]


def title_text(entry, lang):
    """The first keyword in `lang` (the entry's title in "did you mean" chips), or in the fallback language when there is none."""
    for lg in CHAIN.get(lang, ("uz",)):
        if entry["kw"].get(lg):
            return entry["kw"][lg][0]
    return entry["kw"]["uz"][0]


ENTRIES = _build()
_merge_extra(ENTRIES)
BY_ID = {e["id"]: e for e in ENTRIES}

# entries that need a signed-in member (their answers are built from the member's own data)
PERSONAL = {"me_membership", "me_calories", "me_profile", "me_target"}
# shown as "try asking" when nothing matched and nothing was close
POPULAR = ["hours", "prices", "beginner_plan", "protein_need", "fat_loss_train", "osh_cal"]
