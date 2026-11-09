"""Offline assistant: answers questions from the built-in knowledge base (gym/assistant_kb*.py). No network, no external AI.

answer(text, lang, user) -> {"matched", "answer", "links": [{"label", "url"}], "suggest": [titles], "id", "topic"}

How a question is handled:
 0. tiny calculators first: time/date, arithmetic, kg<->lb / km<->mile / cm<->inch, 1RM estimate (100 kg 5 reps), BMI/BMR from text;
 1. the text is normalised (lower case, apostrophes dropped, punctuation removed), spelling variants are mapped to one word (SYN) and every
    word is reduced to a stem (simple Uzbek / Russian / English suffix stripping); a Cyrillic question is also read as Uzbek (transliterated);
 2. every keyword phrase of every entry (all three languages together) is checked against the question: a phrase counts when all its stems
    are present (a long unknown word with one typo is repaired to a known keyword); longer phrases weigh more;
 3. the best entry above a threshold wins and is answered in the language the question is written in; its neighbours become the "related"
    chips. Otherwise the answer says honestly that it does not know, lists the closest topics and offers the chat / phone of the staff.

Facts that change (hours, prices, phone...) are never stored in the answers: they are {placeholders} filled from the database on every call.
"""
import ast
import re
from datetime import timedelta

from django.urls import reverse
from django.utils import timezone

from . import assistant_kb as kb
from .i18n import T

MAX_QUERY = 300
THRESHOLD = 2.0
CHAT_MAX_WORDS = 4  # small talk only answers short messages, so "yaxshi" inside a real question does not start a chat

# ------------------------------------------------------------------ text normalisation and stemming
_APOS = re.compile("[ʻʼ’‘`´ʹ′']")
_CYR = re.compile("[Ѐ-ӿ]")
_UZ_LETTERS = re.compile("[ЎўҚқҒғҲҳ]")
_NONWORD = re.compile(r"[\W_]+", re.UNICODE)

# (suffix, shortest root that may remain). Longest suffix first; two passes.
_LAT = sorted([(s, 3) for s in (
    "larning", "lardan", "larga", "larni", "lar", "ning", "dan", "ga", "ni", "da", "ka", "qa", "ini", "imiz", "ingiz", "miz", "ngiz",
    "im", "ing", "mi", "chi", "dir", "lik", "siz", "ish", "ib", "si", "ta", "ed", "ly", "ness")] + [("s", 4), ("e", 4), ("es", 4)],
    key=lambda p: -len(p[0]))
_RU = sorted([(s, 3) for s in (
    "ами", "ями", "ого", "его", "ому", "ему", "ыми", "ими", "ать", "ять", "ить", "еть", "ует", "ают", "яют", "ешь", "ишь", "ете", "ите",
    "ется", "ится", "ает", "яет", "ая", "яя", "ое", "ее", "ие", "ые", "ий", "ый", "ой", "ей", "ом", "ем", "ам", "ям", "ах", "ях", "ов", "ев", "ою",
    "ею", "ую", "юю", "у", "ю", "а", "я", "ы", "и", "е", "о", "ь", "й")], key=lambda p: -len(p[0]))

# Uzbek Cyrillic -> Latin (apostrophes are dropped by normalize(), so o' / g' are written without them)
_TR = {"а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "yo", "ж": "j", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l",
       "м": "m", "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u", "ф": "f", "х": "x", "ц": "s", "ч": "ch", "ш": "sh",
       "ъ": "", "ь": "", "ы": "i", "э": "e", "ю": "yu", "я": "ya", "ў": "o", "қ": "q", "ғ": "g", "ҳ": "h"}

# Spelling variants and common misspellings -> one canonical word (applied to questions and to keywords alike)
SYN = {
    "protien": "protein", "proteen": "protein", "protin": "protein", "proteyn": "protein", "protien": "protein",
    "kaloria": "kaloriya", "kalloriya": "kaloriya", "kaloreya": "kaloriya", "kkal": "kaloriya", "kcal": "kaloriya", "ккал": "калория",
    "dedlift": "deadlift", "deadlif": "deadlift", "dedlifit": "deadlift", "дедлифт": "deadlift",
    "sqaut": "squat", "skwat": "squat", "squad": "squat", "squatt": "squat",
    "trenajer": "trenajyor", "trenajor": "trenajyor", "trenajyorlar": "trenajyor", "trenazher": "trenajyor",
    "abonent": "abonement", "abonemet": "abonement", "abanement": "abonement", "abinement": "abonement", "abonimet": "abonement",
    "memebership": "membership", "membrship": "membership", "membersip": "membership",
    "otjimaniye": "otjimaniya", "otjimaniy": "otjimaniya", "pushap": "pushup",
    "kreatinn": "kreatin", "creatin": "creatine", "creatinе": "creatine",
    "gantel": "dumbbell", "gantell": "dumbbell", "гантели": "dumbbell", "гантель": "dumbbell",
    "workuot": "workout", "wokrout": "workout", "excersize": "exercise", "excercise": "exercise", "exersice": "exercise",
    "vitamn": "vitamin", "витамин": "vitamin", "vitamine": "vitamin",
    "dieta": "diet", "dyeta": "diet", "диета": "diet",
    "massaa": "massa", "shtanga": "barbell", "штанга": "barbell",
    "tuxum": "tuxum", "tuhum": "tuxum", "tuxm": "tuxum",
    "oqsil": "oqsil", "ogsil": "oqsil", "oksil": "oqsil", "белок": "белок",
}

_NUM = r"\d+(?:\.\d+)?"
_SPECIFIC = ("ex_", "pg_", "hl_", "nu_", "st_", "mx_", "qa_")  # id prefixes of the detailed entries added after the original overview ones


def normalize(text):
    s = _APOS.sub("", str(text or "").lower()).replace("ё", "е")
    return _NONWORD.sub(" ", s).strip()


def translit(text):
    """Uzbek Cyrillic -> Latin, letter by letter (other characters stay)."""
    s = _APOS.sub("", str(text or "").lower())
    return "".join(_TR.get(c, c) for c in s)


def _strip(word, rules):
    for _ in range(2):
        for suf, keep in rules:
            if word.endswith(suf) and len(word) - len(suf) >= keep:
                word = word[:-len(suf)]
                break
        else:
            break
    return word


def stem(word):
    if word.isdigit():
        return word
    return _strip(word, _RU if _CYR.search(word) else _LAT)


def tokens(text):
    return [stem(SYN.get(w, w)) for w in normalize(text).split()]


# ------------------------------------------------------------------ the compiled keyword index
_INDEX = None  # list of (entry, [(stems tuple, weight, languages)])
_VOCAB = None  # {first letter: [stems]} of every keyword stem of length >= 6, for one-typo repair


def _index():
    global _INDEX, _VOCAB
    if _INDEX is None:
        idx, seen_all, vocab = [], {}, {}
        for e in kb.ENTRIES:
            seen, kws = {}, []
            for lang in kb.LANGS:
                for raw in e["kw"][lang]:
                    strong = raw.startswith("!")
                    st = tuple(tokens(raw.lstrip("!")))
                    if not st:
                        continue
                    if st in seen:
                        seen[st][2].add(lang)
                        continue
                    w = (2.0 if (strong or len(st[0]) >= 6) else 1.0) if len(st) == 1 else 2.0 * len(st)
                    seen[st] = (st, w, {lang})
                    kws.append(seen[st])
                    for s in st:
                        if len(s) >= 6 and not s.isdigit():
                            vocab.setdefault(s[0], set()).add(s)
            idx.append((e, kws))
        _INDEX = idx
        _VOCAB = {k: sorted(v) for k, v in vocab.items()}
        del seen_all
    return _INDEX


def _d1(a, b):
    """True when the two words differ by at most one edit (substitution, insertion, deletion or neighbouring swap)."""
    if a == b:
        return True
    la, lb = len(a), len(b)
    if abs(la - lb) > 1:
        return False
    if la == lb:
        diff = [i for i in range(la) if a[i] != b[i]]
        if len(diff) == 1:
            return True
        return len(diff) == 2 and diff[1] == diff[0] + 1 and a[diff[0]] == b[diff[1]] and a[diff[1]] == b[diff[0]]
    if la > lb:
        a, b = b, a
    i = 0
    while i < len(a) and a[i] == b[i]:
        i += 1
    return a[i:] == b[i + 1:]


def _repair(qlist, qset):
    """Questions often carry one typo ("protien", "kaloriyaa"): add the keyword stems that are one edit away from unknown long words."""
    _index()
    extra = set()
    for w in qlist:
        if len(w) < 6 or w.isdigit() or _CYR.search(w):
            continue
        cands = _VOCAB.get(w[0], ())
        if w in cands:
            continue
        found = [c for c in cands if abs(len(c) - len(w)) <= 1 and _d1(w, c)]
        extra.update(found[:2])
    return qset | extra


def _has(stem_, qset):
    if stem_ in qset:
        return True
    if len(stem_) >= 5:  # "kaloriya" ~ "kaloriyali": a long stem may differ from the question word by a short ending
        # ... but not by the English agent ending: "train" (training) is not "trainer" (a coach), "lift" is not "lifter"
        return any(len(q) >= 5 and abs(len(q) - len(stem_)) <= 2 and (q.startswith(stem_) or stem_.startswith(q))
                   and (max(q, stem_, key=len)[min(len(q), len(stem_)):] not in ("er", "ers", "r")) for q in qset)
    return False


def _contiguous(st, qlist):
    n = len(st)
    return any(tuple(qlist[i:i + n]) == st for i in range(len(qlist) - n + 1))


def _score(qlist):
    """[(score, is_not_chat, is_specific, -order, entry, votes)] for every entry that shares a keyword with the question; votes = {lang: weight}."""
    qset = _repair(qlist, set(qlist))
    if not qset:
        return []
    out = []
    for order, (e, kws) in enumerate(_index()):
        if e["topic"] == "chat" and len(qlist) > CHAT_MAX_WORDS:
            continue
        hits = []
        for st, w, langs in kws:
            if all(_has(s, qset) for s in st):
                hits.append((w + (1.0 if len(st) > 1 and _contiguous(st, qlist) else 0.0), langs))
        if hits:
            hits.sort(key=lambda h: -h[0])
            ws = [h[0] for h in hits]
            sc = ws[0] + 0.25 * min(sum(ws[1:]), 4.0)
            chat = e["topic"] == "chat"
            if chat:
                sc = THRESHOLD  # small talk always clears the bar but loses every tie, so a real question wins over "salom"
            votes = {}
            for w, langs in hits:
                for lg in langs:
                    votes[lg] = votes.get(lg, 0.0) + w
            out.append((sc, 0 if chat else 1, 1 if e["id"].startswith(_SPECIFIC) else 0, -order, e, votes))
    out.sort(key=lambda t: t[:4], reverse=True)  # a tie goes to the newer, more specific entries (ex_, pg_...) over the original overview ones
    return out


def _rank(text):
    """(scored rows, script) where script is "uz" when the question is Uzbek written in Cyrillic, else None.
    A Cyrillic question is scored twice (as Russian and transliterated as Uzbek) and the better reading wins."""
    rows = _score(tokens(text))
    if not _CYR.search(str(text or "")):
        return rows, None
    alt = _score(tokens(translit(text)))
    top = lambda r: r[0][0] if r else 0.0
    if _UZ_LETTERS.search(text) or top(alt) > top(rows):
        return alt, "uz"
    return rows, None


def score_all(text):
    """[(score, entry)] for every entry that shares at least one keyword with the text, best first."""
    return [(t[0], t[4]) for t in _rank(text)[0]]


# ------------------------------------------------------------------ language of the answer
_FUNC = {
    "uz": {"qanday", "qanaqa", "nima", "necha", "qancha", "uchun", "bilan", "men", "menga", "mening", "bormi", "kerak", "qayerda", "qachon", "va",
           "yoki", "mumkinmi", "bolad", "boladimi", "bolsa", "ham", "emas", "yoq", "bor", "keyin", "oldin", "kuniga", "haftasiga", "yaxshi", "qilish"},
    "en": {"the", "how", "what", "is", "are", "do", "does", "can", "i", "my", "to", "for", "of", "and", "should", "where", "when", "why", "which",
           "a", "an", "in", "on", "with", "it", "you", "your", "me", "about", "much", "many"},
}


def guess_lang(text, site_lang, script=None, votes=None):
    """The language to answer in: the one the question is written in (Cyrillic -> Russian unless Uzbek, Latin -> Uzbek or English by its
    function words and by which language's keywords matched), otherwise the site language."""
    site_lang = site_lang if site_lang in kb.LANGS else "uz"
    letters = [c for c in str(text or "") if c.isalpha()]
    if script == "uz":
        return "uz"
    if letters and sum(1 for c in letters if _CYR.match(c)) * 2 > len(letters):
        return "uz" if _UZ_LETTERS.search(text) else "ru"
    words = set(normalize(text).split())
    sc = {lg: len(words & fw) for lg, fw in _FUNC.items()}
    if votes:
        vt = {lg: votes.get(lg, 0.0) for lg in ("uz", "en")}
        if abs(vt["uz"] - vt["en"]) >= 1.0:
            sc[max(vt, key=vt.get)] += 2
    if sc["uz"] != sc["en"] and max(sc.values()) >= 1 and (letters and not _CYR.search(str(text))):
        return max(sc, key=sc.get)
    return site_lang


# ------------------------------------------------------------------ tiny calculators (answered before the knowledge base)
_UNITS = {  # word -> (family, size in the family's base unit)
    **{w: ("mass", 1.0) for w in ("kg", "kilo", "kilogram", "kilogramm", "kilograms", "кг", "кило", "килограмм", "килограммов", "килограмма")},
    **{w: ("mass", 0.45359237) for w in ("lb", "lbs", "pound", "pounds", "funt", "funta", "фунт", "фунта", "фунтов")},
    **{w: ("dist", 1.0) for w in ("km", "kilometr", "kilometer", "kilometre", "kilometers", "км", "километр", "километров", "километра")},
    **{w: ("dist", 1.609344) for w in ("mile", "miles", "mil", "milya", "миля", "миль", "мили", "милях")},
    **{w: ("len", 1.0) for w in ("cm", "sm", "santimetr", "centimeter", "centimetre", "см", "сантиметр", "сантиметров")},
    **{w: ("len", 2.54) for w in ("inch", "inches", "dyuym", "дюйм", "дюймов", "дюйма")},
    **{w: ("len", 30.48) for w in ("ft", "feet", "foot", "fut", "фут", "футов", "фута")},
}
_UNIT_NAME = {("mass", 1.0): "kg", ("mass", 0.45359237): "lb", ("dist", 1.0): "km", ("dist", 1.609344): "mile",
              ("len", 1.0): "cm", ("len", 2.54): "inch", ("len", 30.48): "ft"}
_WORDS = re.compile(_NUM + r"|[^\W\d_]+", re.UNICODE)
_WEEKDAY = {"uz": ("dushanba", "seshanba", "chorshanba", "payshanba", "juma", "shanba", "yakshanba"),
            "ru": ("понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"),
            "en": ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")}
_MONTH = {"uz": ("yanvar", "fevral", "mart", "aprel", "may", "iyun", "iyul", "avgust", "sentabr", "oktabr", "noyabr", "dekabr"),
          "ru": ("января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа", "сентября", "октября", "ноября", "декабря"),
          "en": ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December")}
_TIME_RE = re.compile(r"\b(soat nechi|soat nechchi|soat necha boldi|hozir soat|xozir soat|который час|сколько времени|сколько сейчас времени|"
                      r"what time is it|what is the time|whats the time|current time|time now|time is it now)\b")
_DATE_RE = re.compile(r"(bugun qaysi kun|bugun nechanchi|bugungi sana|bugun sana|bugun qanaqa kun|какое сегодня число|какое число|какой сегодня день|"
                      r"какая сегодня дата|сегодняшняя дата|what day is it|what is the date|whats the date|todays date|current date|what is today)")
_REPS_WORD = r"(?:marta|mart|ta|раз|раза|reps?|rep|takror\w*|повтор\w*|times|rep\.)"
_RM_A = re.compile(r"(" + _NUM + r")\s*(?:kg|кг|kilo|lbs?)?\s*[x×*х]\s*(\d{1,2})\b")
_RM_B = re.compile(r"(" + _NUM + r")\s*(kg|кг|kilo|lbs?)?\s*(?:ga|da|bilan|на|по|for|ni|ta|dan|@)?\s*(\d{1,2})\s*" + _REPS_WORD + r"\b")
_LIFT_HINT = re.compile(r"(1rm|\brm\b|maks|макс|max|bench|press|squat|skvat|присед|жим|тяг|deadlift|lift|ko'tar|kotar|ko'tard|поднял|поднима|"
                        r"yotib|surdim|surish|ko'tara)")
_ARITH_LEAD = re.compile(r"^(?:hisobla\w*|calculate|calc|посчитай|вычисли|сколько будет|necha bo'?ladi|nechaga teng|=|how much is|what is)\s+", re.I)


def _fmt(x, nd=2):
    s = f"{x:.{nd}f}".rstrip("0").rstrip(".")
    return s or "0"


def _num(s):
    return float(s)


def _calc_time(raw, lang):
    n = normalize(raw)
    now = timezone.localtime()
    if _TIME_RE.search(n):
        return {"uz": f"Hozir soat {now:%H:%M} (server vaqti).", "ru": f"Сейчас {now:%H:%M} (время сервера).",
                "en": f"It is {now:%H:%M} now (server time)."}[lang], "calc_time"
    if _DATE_RE.search(n):
        wd, mo = _WEEKDAY[lang][now.weekday()], _MONTH[lang][now.month - 1]
        return {"uz": f"Bugun {now.day}-{mo} {now.year}, {wd}.", "ru": f"Сегодня {now.day} {mo} {now.year}, {wd}.",
                "en": f"Today is {wd}, {mo} {now.day}, {now.year}."}[lang], "calc_date"
    return None


def _calc_units(raw, lang):
    s = re.sub(r"(?<=\d),(?=\d)", ".", _APOS.sub("", str(raw).lower()))
    words = _WORDS.findall(s)
    src = None
    for i, w in enumerate(words[:-1]):
        if re.fullmatch(_NUM, w) and words[i + 1] in _UNITS:
            src = (_num(w), _UNITS[words[i + 1]], words[i + 1])
            break
    if not src:
        return None
    fam = src[1][0]
    target = next((_UNITS[w] for w in words if w in _UNITS and _UNITS[w][0] == fam and _UNITS[w][1] != src[1][1]), None)
    if not target:
        return None
    base = src[0] * src[1][1]
    out = base / target[1]
    a, b = _UNIT_NAME[(fam, src[1][1])], _UNIT_NAME[(fam, target[1])]
    if b == "ft":
        ft = int(out)
        return f"{_fmt(src[0])} {a} = {_fmt(out)} ft ({ft} ft {_fmt((out - ft) * 12, 1)} in)", "calc_units"
    return f"{_fmt(src[0])} {a} = {_fmt(out)} {b}", "calc_units"


def _calc_1rm(raw, lang):
    s = re.sub(r"(?<=\d),(?=\d)", ".", _APOS.sub("", str(raw).lower()))
    m = _RM_A.search(s)
    if m:
        w, r = _num(m.group(1)), int(m.group(2))
    else:
        m = _RM_B.search(s)
        if not m or not (m.group(2) or _LIFT_HINT.search(s)):
            return None
        w, r = _num(m.group(1)), int(m.group(3))
    if not (2 <= w <= 600) or not (1 <= r <= 30):
        return None
    rm = w if r == 1 else w * (1 + r / 30.0)
    tbl = ", ".join(f"{p}% = {_fmt(rm * p / 100, 1)}" for p in (60, 70, 80, 90))
    note = {"uz": " (12 dan ko'p takrorda baho noaniqroq)", "ru": " (при более чем 12 повторах оценка менее точна)",
            "en": " (the estimate is less accurate above 12 reps)"}[lang] if r > 12 else ""
    return {"uz": f"Taxminiy 1RM (Epley formulasi): {_fmt(rm, 1)} kg{note}. Ish og'irliklari: {tbl} kg. Bu taxmin: maksimumni sinashda sherik/spotter bo'lsin.",
            "ru": f"Примерный 1ПМ (формула Эпли): {_fmt(rm, 1)} кг{note}. Рабочие веса: {tbl} кг. Это оценка: максимум пробуйте со страхующим.",
            "en": f"Estimated 1RM (Epley formula): {_fmt(rm, 1)} kg{note}. Working weights: {tbl} kg. It is an estimate: test a true max with a spotter."}[lang], "calc_1rm"


def _grab(s, before, after_units):
    """A number right after one of the words in `before`, or right before one of the units in `after_units`."""
    m = re.search(r"(?:" + before + r")\D{0,12}?(" + _NUM + r")", s)
    if m:
        return _num(m.group(1))
    m = re.search(r"(" + _NUM + r")\s*(?:" + after_units + r")\b", s)
    return _num(m.group(1)) if m else None


def _calc_body(raw, lang):
    s = re.sub(r"(?<=\d),(?=\d)", ".", _APOS.sub("", str(raw).lower()))
    w = _grab(s, r"vazn\w*|ves|вес\w*|weight|massa\w*|i weigh|weigh", r"kg|кг|kilo")
    h = _grab(s, r"boy\w*|рост\w*|height|tall", r"cm|sm|см")
    if h is None:
        m = re.search(r"\b([12](?:\.\d{1,2}))\s*(?:m|metr|м|meter|metre)\b", s)
        if m:
            h = _num(m.group(1)) * 100
    if w is None or h is None or not (25 <= w <= 300) or not (100 <= h <= 250):
        return None
    bmi = w / ((h / 100) ** 2)
    cat = ("underweight", "normal", "overweight", "obese")[0 if bmi < 18.5 else 1 if bmi < 25 else 2 if bmi < 30 else 3]
    cat_t = {"underweight": {"uz": "vazn yetishmaydi", "ru": "недостаточный вес", "en": "underweight"},
             "normal": {"uz": "normal oraliq", "ru": "норма", "en": "normal range"},
             "overweight": {"uz": "ortiqcha vazn", "ru": "избыточный вес", "en": "overweight"},
             "obese": {"uz": "semizlik oralig'i", "ru": "ожирение", "en": "obesity range"}}[cat][lang]
    age = _grab(s, r"yosh\w*|age|возраст\w*|лет|years", r"yosh\w*|yoshda|лет|года|год|years|yo|y o")
    male = re.search(r"\b(erkak|male|man|муж\w*|парень|yigit)\b", s)
    female = re.search(r"\b(ayol|qiz|female|woman|жен\w*|девушка|девочка)\b", s)
    extra = ""
    if age and 10 <= age <= 100 and (male or female):
        bmr = 10 * w + 6.25 * h - 5 * age + (5 if male and not female else -161)
        extra = {"uz": f" Bazal almashinuv (Mifflin): ~{int(bmr)} kkal; o'rtacha faollikda kunlik sarf ~{int(bmr * 1.55)} kkal.",
                 "ru": f" Базовый обмен (Миффлин): ~{int(bmr)} ккал; при средней активности суточный расход ~{int(bmr * 1.55)} ккал.",
                 "en": f" Basal metabolism (Mifflin): ~{int(bmr)} kcal; with moderate activity daily burn is ~{int(bmr * 1.55)} kcal."}[lang]
    return {"uz": f"BMI = {_fmt(bmi, 1)} ({cat_t}; vazn {_fmt(w)} kg, bo'y {_fmt(h)} sm). BMI taxminiy ko'rsatkich: mushakli odamlarda noto'g'ri chiqishi mumkin.{extra}",
            "ru": f"ИМТ = {_fmt(bmi, 1)} ({cat_t}; вес {_fmt(w)} кг, рост {_fmt(h)} см). ИМТ ориентировочный: у мускулистых людей он может завышаться.{extra}",
            "en": f"BMI = {_fmt(bmi, 1)} ({cat_t}; weight {_fmt(w)} kg, height {_fmt(h)} cm). BMI is a rough guide and can mislead in muscular people.{extra}"}[lang], "calc_bmi"


def _safe_eval(node, depth=0):
    if depth > 12:
        raise ValueError
    if isinstance(node, ast.Expression):
        return _safe_eval(node.body, depth + 1)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
        return float(node.value)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
        v = _safe_eval(node.operand, depth + 1)
        return v if isinstance(node.op, ast.UAdd) else -v
    if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div)):
        a, b = _safe_eval(node.left, depth + 1), _safe_eval(node.right, depth + 1)
        return a + b if isinstance(node.op, ast.Add) else a - b if isinstance(node.op, ast.Sub) else a * b if isinstance(node.op, ast.Mult) else a / b
    raise ValueError


def _calc_arith(raw, lang):
    s = str(raw or "").strip().lower().rstrip("?=! ").strip()
    s = _ARITH_LEAD.sub("", s)
    s = re.sub(r"(?<=\d),(?=\d)", ".", s).replace("×", "*").replace("÷", "/").replace(":", "/").replace("х", "x")
    s = re.sub(r"(?<=[\d)])\s*x\s*(?=[\d(])", "*", s)
    if re.fullmatch(r"\d+-\d+", s) or not re.fullmatch(r"[\d\s+\-*/().]+", s) or not re.search(r"\d\s*[+\-*/]\s*[\d(]", s) or len(s) > 60:
        return None
    try:
        v = _safe_eval(ast.parse(s.strip(), mode="eval"))
    except (ValueError, SyntaxError, ZeroDivisionError, RecursionError):
        return None
    if abs(v) > 1e12:
        return None
    return f"{s.strip()} = {_fmt(v, 4)}", "calc_math"


def calculator(raw, lang):
    """(answer, id) for a question that is really a small calculation, else None. Pure text work: no database, no network."""
    for fn in (_calc_time, _calc_arith, _calc_units, _calc_1rm, _calc_body):
        res = fn(raw, lang)
        if res:
            return res
    return None


# ------------------------------------------------------------------ language-dependent phrases for dynamic facts
TXT = {
    "state_open": {"uz": "Hozir zal ochiq.", "ru": "Сейчас зал открыт.", "en": "The gym is open right now."},
    "state_closed": {"uz": "Hozir zal yopiq.", "ru": "Сейчас зал закрыт.", "en": "The gym is closed right now."},
    "addr": {"uz": "Manzil: {a}.", "ru": "Адрес: {a}.", "en": "Address: {a}."},
    "no_addr": {"uz": "Aniq manzil saytda hali ko'rsatilmagan, telefon orqali so'rang: {p}.",
                "ru": "Точный адрес на сайте пока не указан, уточните по телефону: {p}.",
                "en": "The exact address is not on the site yet, please ask by phone: {p}."},
    "no_plans": {"uz": "hozir sotuvda abonement yo'q ({p} ga qo'ng'iroq qiling)", "ru": "сейчас абонементов в продаже нет (звоните {p})",
                 "en": "no memberships on sale right now (call {p})"},
    "deliv_on": {"uz": "yetkazish narxi {fee}; {free} dan ortiq xaridda bepul; hudud: {area}.",
                 "ru": "стоимость доставки {fee}; при заказе от {free} бесплатно; зона: {area}.",
                 "en": "delivery costs {fee}; free for orders over {free}; area: {area}."},
    "deliv_on_nofree": {"uz": "yetkazish narxi {fee}; hudud: {area}.", "ru": "стоимость доставки {fee}; зона: {area}.",
                        "en": "delivery costs {fee}; area: {area}."},
    "deliv_off": {"uz": "hozir yetkazib berish o'chirilgan, mahsulotni zaldan olib keting.",
                  "ru": "сейчас доставка отключена, товар можно забрать в зале.",
                  "en": "delivery is switched off right now, please pick the goods up at the gym."},
    "pm_cash": {"uz": "qabulxonada naqd to'lov", "ru": "наличные на ресепшене", "en": "cash at the front desk"},
    "pm_card": {"uz": "karta orqali o'tkazma", "ru": "перевод на карту", "en": "card transfer"},
    "pm_click": {"uz": "Click (onlayn)", "ru": "Click (онлайн)", "en": "Click (online)"},
    "pm_demo": {"uz": "Payme, Click, Uzum (sinov rejimi)", "ru": "Payme, Click, Uzum (тестовый режим)", "en": "Payme, Click, Uzum (test mode)"},
    "m_active": {"uz": "Abonementingiz faol: {plan}, {date} gacha ({n} kun qoldi).",
                 "ru": "Ваш абонемент действует: {plan}, до {date} (осталось дней: {n}).",
                 "en": "Your membership is active: {plan}, until {date} ({n} days left)."},
    "m_active_last": {"uz": " Tugashiga oz qoldi: yangilash uchun Abonementlar sahifasiga o'ting.",
                      "ru": " Скоро заканчивается: продлите на странице «Абонементы».",
                      "en": " It ends soon: renew it on the Memberships page."},
    "m_expired": {"uz": "Abonementingiz {date} da tugagan. Yangilash uchun Abonementlar sahifasiga o'ting.",
                  "ru": "Ваш абонемент закончился {date}. Продлить можно на странице «Абонементы».",
                  "en": "Your membership ended on {date}. You can renew it on the Memberships page."},
    "m_none": {"uz": "Hozircha abonementingiz yo'q. Abonementlar sahifasidan tanlab olishingiz mumkin.",
               "ru": "У вас пока нет абонемента. Выбрать его можно на странице «Абонементы».",
               "en": "You do not have a membership yet. You can pick one on the Memberships page."},
    "cal_none": {"uz": "Bugun hali ovqat yozilmagan. Kunlik me'yoringiz taxminan {t} kkal.",
                 "ru": "Сегодня еда ещё не записана. Ваша дневная норма примерно {t} ккал.",
                 "en": "No food is logged today yet. Your daily target is about {t} kcal."},
    "cal_left": {"uz": "Bugun {e} kkal yegansiz (me'yor {t} kkal), {l} kkal qoldi. Oqsil {p} g.",
                 "ru": "Сегодня вы съели {e} ккал (норма {t} ккал), осталось {l} ккал. Белок {p} г.",
                 "en": "Today you ate {e} kcal (target {t} kcal), {l} kcal left. Protein {p} g."},
    "cal_over": {"uz": "Bugun {e} kkal yegansiz, bu me'yordan ({t} kkal) {o} kkal ko'p. Oqsil {p} g.",
                 "ru": "Сегодня вы съели {e} ккал, это на {o} ккал больше нормы ({t} ккал). Белок {p} г.",
                 "en": "Today you ate {e} kcal, which is {o} kcal over your target ({t} kcal). Protein {p} g."},
    "tgt_profile": {"uz": "Vazn, bo'y va yoshingiz bo'yicha taxminiy kunlik me'yoringiz: {t} kkal (maqsadingizga moslangan).",
                    "ru": "Ваша примерная дневная норма по весу, росту и возрасту: {t} ккал (с поправкой на цель).",
                    "en": "Your estimated daily target from weight, height and age: {t} kcal (adjusted for your goal)."},
    "tgt_default": {"uz": "Standart me'yor {t} kkal. Aniqroq hisoblash uchun profilingizga tug'ilgan kun va maqsadni kiriting, \"Natijalarim\"da vazn va bo'yni yozing.",
                    "ru": "Стандартная норма {t} ккал. Для точного расчёта укажите в профиле дату рождения и цель, а в «Моих результатах» вес и рост.",
                    "en": "The default target is {t} kcal. For a better estimate add your birth date and goal to your profile and log weight and height in Progress."},
    "prof_body": {"uz": "Vazn {w} kg", "ru": "Вес {w} кг", "en": "Weight {w} kg"},
    "prof_h": {"uz": ", bo'y {h} sm, BMI {b}", "ru": ", рост {h} см, ИМТ {b}", "en": ", height {h} cm, BMI {b}"},
    "prof_goal": {"uz": "; maqsad: {g}", "ru": "; цель: {g}", "en": "; goal: {g}"},
    "prof_target": {"uz": "; maqsad vazni {t} kg", "ru": "; целевой вес {t} кг", "en": "; target weight {t} kg"},
    "prof_nobody": {"uz": "Vazn hali kiritilmagan. \"Natijalarim\" sahifasida vazn va bo'yingizni yozing.",
                    "ru": "Вес пока не записан. Укажите вес и рост на странице «Мои результаты».",
                    "en": "No weight logged yet. Add your weight and height on the Progress page."},
    "prof_nogoal": {"uz": " Maqsad tanlanmagan: profil sahifasida belgilang.", "ru": " Цель не выбрана: отметьте её в профиле.",
                    "en": " No goal is set: choose one in your profile."},
    "tip_ask": {"uz": "Maqsadingizni profilda tanlang (ozish, massa, kuch...), shunda aniqroq maslahat beraman. Hozircha: boshlovchi uchun haftasiga 3 marta butun tana mashqi va yetarli oqsil yaxshi boshlanish. Sizga reja kerak bo'lsa, shu sahifada \"Reja tuzish\" bo'limidan foydalaning.",
                "ru": "Выберите цель в профиле (похудение, масса, сила...), и я дам более точный совет. Пока: для начала хороши 3 тренировки на всё тело в неделю и достаточно белка. Нужен план? Воспользуйтесь разделом «Составить план» на этой странице.",
                "en": "Pick your goal in your profile (fat loss, muscle, strength...) and I can advise more precisely. For now, 3 full-body sessions a week and enough protein is a good start. Need a plan? Use the \"Build my plan\" section on this page."},
    "goal_lose": {"uz": "Ozish", "ru": "Похудение", "en": "Fat loss"}, "goal_keep": {"uz": "Formani saqlash", "ru": "Поддержание формы", "en": "Stay in shape"},
    "goal_gain": {"uz": "Massa olish", "ru": "Набор массы", "en": "Muscle gain"}, "goal_strength": {"uz": "Kuch", "ru": "Сила", "en": "Strength"},
    "goal_health": {"uz": "Sog'liq", "ru": "Здоровье", "en": "Health"},
    "tip_lose": {"uz": "Maqsadingiz ozish. Haftasiga 3-4 kuch mashqi, 2-3 yengil kardio, kuniga 7-10 ming qadam, 300-500 kkal tanqislik va oqsil 1,6-2,2 g/kg. Reja kerak bo'lsa, \"Reja tuzish\" ni \"Ozish\" tanlab bosing.",
                 "ru": "Ваша цель — похудение. 3-4 силовые в неделю, 2-3 лёгких кардио, 7-10 тысяч шагов в день, дефицит 300-500 ккал и белок 1,6-2,2 г/кг. Нужен план? Нажмите «Составить план» с целью «Похудение».",
                 "en": "Your goal is fat loss. 3-4 strength sessions a week, 2-3 light cardio, 7-10 thousand steps a day, a 300-500 kcal deficit and protein of 1.6-2.2 g/kg. Want a plan? Press \"Build my plan\" with the fat loss goal."},
    "tip_gain": {"uz": "Maqsadingiz massa olish. Haftasiga 3-5 mashq, har mushak 2 marta, 6-12 takror, sarfdan 250-400 kkal ko'p yeng, oqsil 1,6-2,2 g/kg va 7-9 soat uyqu. \"Reja tuzish\" da \"Mushak o'stirish\" ni tanlang.",
                 "ru": "Ваша цель — набор массы. 3-5 тренировок в неделю, каждая мышца 2 раза, 6-12 повторов, на 250-400 ккал больше расхода, белок 1,6-2,2 г/кг и 7-9 часов сна. В «Составить план» выберите «Рост мышц».",
                 "en": "Your goal is muscle gain. Train 3-5 times a week, each muscle twice, 6-12 reps, eat 250-400 kcal above your burn, protein 1.6-2.2 g/kg and sleep 7-9 hours. In \"Build my plan\" choose the muscle goal."},
    "tip_strength": {"uz": "Maqsadingiz kuch. Asosiy mashqlarga (o'tirib turish, deadlift, yotib surish, yelka surish) tayaning: 3-5 yondashuv x 3-6 takror, dam 2-4 daqiqa, og'irlikni oz-ozdan oshiring. \"Reja tuzish\" da \"Kuch\" ni tanlang.",
                     "ru": "Ваша цель — сила. Опирайтесь на базу (присед, становая, жим лёжа, жим стоя): 3-5 подходов по 3-6 повторов, отдых 2-4 минуты, вес прибавляйте понемногу. В «Составить план» выберите «Сила».",
                     "en": "Your goal is strength. Lean on the main lifts (squat, deadlift, bench press, overhead press): 3-5 sets of 3-6 reps, 2-4 minutes rest, add weight in small steps. In \"Build my plan\" choose strength."},
    "tip_other": {"uz": "Maqsadingiz: {g}. Haftasiga 3 marta butun tana kuch mashqi, 2 marta yengil kardio, ko'p harakat va muvozanatli ovqat yaxshi asos. \"Reja tuzish\" da \"Umumiy fitnes\" ni tanlang.",
                  "ru": "Ваша цель: {g}. Хорошая база: 3 силовые на всё тело в неделю, 2 лёгких кардио, больше движения и сбалансированное питание. В «Составить план» выберите «Общая физическая форма».",
                  "en": "Your goal: {g}. A good base is 3 full-body strength sessions a week, 2 light cardio sessions, more daily movement and balanced food. In \"Build my plan\" choose general fitness."},
}


def tx(key, lang, **kw):
    s = TXT[key].get(lang) or TXT[key]["uz"]
    return s.format(**kw) if kw else s


def _t(lang, key):
    return T.get(lang, T["uz"]).get(key) or T["uz"].get(key) or key


def money(n, lang):
    return f"{int(n):,}".replace(",", " ") + " " + _t(lang, "price_unit")


# ------------------------------------------------------------------ dynamic facts (read from the database at answer time)
class Facts:
    """Lazy mapping used to fill {placeholders}: a value is computed only when an answer asks for it."""

    def __init__(self, lang, user=None):
        self.lang, self.user = lang, user if (user is not None and user.is_authenticated) else None
        self._gs, self._cache = None, {}

    @property
    def gs(self):
        if self._gs is None:
            from .models import GymSettings
            self._gs = GymSettings.load()
        return self._gs

    def get(self, key):
        if key not in self._cache:
            fn = getattr(self, "f_" + key, None)
            self._cache[key] = fn() if fn else None
        return self._cache[key]

    @staticmethod
    def _hm(v):
        return v.strftime("%H:%M") if hasattr(v, "strftime") else str(v)[:5]

    def f_open(self): return self._hm(self.gs.open_time)
    def f_close(self): return self._hm(self.gs.close_time)
    def f_hours(self): return f"{self.f_open()}–{self.f_close()}"
    def f_phone(self): return "+998 " + self.gs.phone
    def f_instagram(self): return self.gs.instagram
    def f_telegram(self): return self.gs.telegram
    def f_freeze_max(self): return str(self.gs.freeze_max_days)
    def f_bonus_days(self): return str(self.gs.referral_bonus_days)

    def f_state(self):
        from .voice import _is_open
        gs = self.gs
        o, c = gs.open_time, gs.close_time
        if not hasattr(o, "hour"):
            return ""
        return tx("state_open" if _is_open(gs, timezone.localtime().time()) else "state_closed", self.lang)

    def f_address_line(self):
        a = (self.gs.address or "").strip()
        return tx("addr", self.lang, a=a) if a else tx("no_addr", self.lang, p=self.f_phone())

    def f_plans(self):
        from .models import Plan
        rows = []
        for p in Plan.objects.filter(active=True):
            key = "plan_" + p.code
            name = _t(self.lang, key) if key in T["uz"] else p.name
            rows.append(f"{name} — {money(p.price, self.lang)}")
        return "; ".join(rows) if rows else tx("no_plans", self.lang, p=self.f_phone())

    def f_crowd(self):
        from .views import crowd_level
        return _t(self.lang, "vc_crowd_" + crowd_key(crowd_level()["level"]))

    def f_delivery_info(self):
        gs = self.gs
        if not gs.delivery_on:
            return tx("deliv_off", self.lang)
        kw = {"fee": money(gs.delivery_fee, self.lang) if gs.delivery_fee else {"uz": "bepul", "ru": "бесплатно", "en": "free"}[self.lang],
              "free": money(gs.free_delivery_from, self.lang), "area": gs.delivery_area}
        return tx("deliv_on" if gs.free_delivery_from else "deliv_on_nofree", self.lang, **kw)

    def f_pay_methods(self):
        from . import click, services
        names = [tx("pm_cash", self.lang)]
        if services.current_card():
            names.append(tx("pm_card", self.lang))
        if services.demo_enabled(self.gs):
            names.append(tx("pm_demo", self.lang))
        elif click.enabled():
            names.append(tx("pm_click", self.lang))
        return ", ".join(names)

    # ---- the signed-in member's own data
    def f_m_status(self):
        from . import services
        u, lang = self.user, self.lang
        m = services.active_membership(u)
        if m:
            days = max(0, (m.expires - timezone.now()).days)
            name = _t(lang, "plan_" + m.plan.code) if ("plan_" + m.plan.code) in T["uz"] else m.plan.name
            s = tx("m_active", lang, plan=name, date=timezone.localtime(m.expires).strftime("%d.%m.%Y"), n=days)
            return s + (tx("m_active_last", lang) if days <= 3 else "")
        last = services.paid_until(u)
        if last:
            return tx("m_expired", lang, date=timezone.localtime(last).strftime("%d.%m.%Y"))
        return tx("m_none", lang)

    def _day(self):
        from . import calories
        return calories.day_summary(self.user, timezone.localdate())

    def f_cal_today(self):
        s = self._day()
        if not s["entries"]:
            return tx("cal_none", self.lang, t=s["target"])
        p = int(round(float(s["protein"])))
        if s["over"]:
            return tx("cal_over", self.lang, e=s["eaten"], t=s["target"], o=-s["left"], p=p)
        return tx("cal_left", self.lang, e=s["eaten"], t=s["target"], l=s["left"], p=p)

    def f_cal_target(self):
        from . import calories
        t, how = calories.daily_target(self.user)
        return tx("tgt_profile" if how == "profile" else "tgt_default", self.lang, t=t)

    def _goal_name(self, u):
        return tx("goal_" + u.goal, self.lang) if u.goal else ""

    def f_p_profile(self):
        u, lang = self.user, self.lang
        last = u.bodylogs.order_by("-date", "-id").first()
        if not last:
            return tx("prof_nobody", lang)
        s = tx("prof_body", lang, w=last.weight)
        if last.height_cm:
            s += tx("prof_h", lang, h=last.height_cm, b=last.bmi)
        if u.goal:
            s += tx("prof_goal", lang, g=self._goal_name(u))
        if u.target_weight:
            s += tx("prof_target", lang, t=u.target_weight)
        return s + "." + ("" if u.goal else tx("prof_nogoal", lang))

    def f_goal_tip(self):
        u, lang = self.user, self.lang
        if not u or not u.goal:
            return tx("tip_ask", lang)
        key = {"lose": "tip_lose", "gain": "tip_gain", "strength": "tip_strength"}.get(u.goal)
        return tx(key, lang) if key else tx("tip_other", lang, g=self._goal_name(u))


def crowd_key(level):
    return level if level in ("calm", "mid", "busy") else "mid"


_PH = re.compile(r"\{(\w+)\}")


def fill(text, facts):
    def sub(m):
        v = facts.get(m.group(1))
        return m.group(0) if v is None else str(v)
    return _PH.sub(sub, text)


# ------------------------------------------------------------------ public API
TXT.update({
    "unk": {"uz": "Bu savolga hozircha aniq javobim yo'q, o'ylab topib aytmayman. Eng yaqin mavzular pastda; savolni boshqacha yoki qisqaroq yozib ko'ring. Murabbiy yoki administratorga Chatda yozing yoki qo'ng'iroq qiling: {phone}.",
            "ru": "На этот вопрос у меня пока нет точного ответа, и выдумывать я не буду. Ближайшие темы ниже; попробуйте переформулировать короче. Напишите тренеру или администратору в Чат или позвоните: {phone}.",
            "en": "I do not have a sure answer to that yet and I will not make one up. The closest topics are below; try rephrasing it shorter. Message a trainer or the admin in Chat or call: {phone}."},
    "chat_label": {"uz": "Chat", "ru": "Чат", "en": "Chat"},
})



def detect_lang(text, lang):
    """Kept for callers: the language of the answer for a question with no match information (see guess_lang)."""
    return guess_lang(text, lang)


def title_of(entry, lang):
    first = entry["kw"][lang][0].lstrip("!")
    return first[:1].upper() + first[1:]


def _links(entry, lang):
    out = []
    for label_key, url_name in entry["links"]:
        try:
            out.append({"label": _t(lang, label_key), "url": reverse(url_name)})
        except Exception:  # a renamed url must never break an answer
            continue
    return out


def _neighbours(entry, n):
    """Entries written next to this one in the knowledge base (same topic group) - related topics for the chips."""
    ids = [e["id"] for e in kb.ENTRIES]
    i = ids.index(entry["id"])
    out = []
    for d in range(1, 6):
        for j in (i + d, i - d):
            if 0 <= j < len(ids) and kb.ENTRIES[j]["topic"] == entry["topic"] and kb.ENTRIES[j]["topic"] != "chat":
                out.append(ids[j])
    return out[:n]


def suggestions(scored, lang, skip=None, n=4, entry=None):
    ids = [e["id"] for _, e in scored if e["id"] != skip and e["topic"] != "chat"][:n]
    if entry is not None:
        for nid in _neighbours(entry, n):
            if len(ids) >= n:
                break
            if nid not in ids and nid != skip:
                ids.append(nid)
    for pid in kb.POPULAR:
        if len(ids) >= n:
            break
        if pid not in ids and pid != skip:
            ids.append(pid)
    return [title_of(kb.BY_ID[i], lang) for i in ids[:n]]


def _result(matched, answer_, links, suggest, eid, topic):
    return {"matched": matched, "answer": answer_, "links": links, "suggest": suggest, "id": eid, "topic": topic}


def answer(text, lang="uz", user=None):
    text = str(text or "").strip()[:MAX_QUERY]
    rows, script = _rank(text)
    best_row = rows[0] if rows and rows[0][0] >= THRESHOLD else None
    lang = guess_lang(text, lang, script, best_row[5] if best_row else None)
    authed = user is not None and user.is_authenticated
    scored = [(r[0], r[4]) for r in rows]
    calc = calculator(text, lang) if text else None
    if calc:
        return _result(True, calc[0], [], suggestions(scored, lang), calc[1], "calc")
    if best_row is None:
        facts = Facts(lang, user)
        links = []
        try:
            links = [{"label": tx("chat_label", lang), "url": reverse("chat")}]
        except Exception:
            pass
        return _result(False, fill(tx("unk", lang), facts), links, suggestions(scored, lang), None, None)
    best = best_row[4]
    if best["id"] in kb.PERSONAL and not authed:
        return _result(True, _t(lang, "asst_login"), [{"label": _t(lang, "login"), "url": reverse("login")}],
                       suggestions(scored, lang, skip=best["id"], entry=best), best["id"], best["topic"])
    facts = Facts(lang, user)
    return _result(True, fill(best["a"][lang], facts), _links(best, lang), suggestions(scored, lang, skip=best["id"], entry=best),
                   best["id"], best["topic"])
