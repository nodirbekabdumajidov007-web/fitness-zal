"""Offline food database of the calorie tracker: ~600 foods with uz / ru / en names, search that forgives typos, and the matcher behind
the free-text recognition ("2 ta somsa va choy"). No network, no AI: everything is parsed once from gym/food_data1.py and food_data2.py.

Values are per 100 g (kcal, protein, fat, carbs): rounded reference-table averages, home recipes for dishes. The row number of a built-in food
is its id (saved links and the voice assistant use it), so the data files may only be appended to.
"""
import re

from .food_data1 import RAW as _RAW1
from .food_data2 import RAW as _RAW2

_APOS = "ʻʼ’‘`´'"
_NOT_WORD = re.compile(r"[^\w%]+", re.UNICODE)


def plain(s):
    """Lower case, apostrophes dropped (o'rik / o‘rik / orik), ё -> е, punctuation to single spaces."""
    s = str(s or "").lower().replace("ё", "е")
    for ch in _APOS:
        s = s.replace(ch, "")
    return _NOT_WORD.sub(" ", s).strip()


class Food:
    __slots__ = ("id", "name", "kcal", "p", "f", "c", "piece", "portion", "phrases", "parse_phrases", "mine")

    def __init__(self, id, name, kcal, p, f, c, piece, portion, phrases, parse_phrases, mine=False):
        self.id, self.name, self.kcal, self.p, self.f, self.c = id, name, kcal, p, f, c
        self.piece, self.portion, self.phrases, self.parse_phrases, self.mine = piece, portion, phrases, parse_phrases, mine

    @property
    def default_grams(self):
        return self.portion or self.piece or 100

    def as_dict(self):
        return {"id": ("u%d" % self.id) if self.mine else str(self.id), "name": self.name, "kcal": _n(self.kcal), "p": _n(self.p), "f": _n(self.f), "c": _n(self.c),
                "portion": self.default_grams, "piece": self.piece, "mine": self.mine}


def _n(v):
    v = float(v)
    return int(v) if v == int(v) else round(v, 1)


def _load():
    foods = []
    for raw in (_RAW1, _RAW2):
        for line in raw.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = [x.strip() for x in line.split("|")]
            if len(parts) != 4:
                raise ValueError(f"bad food row: {line}")
            name = parts[0]
            k, p, f, c = (float(x) for x in parts[1].split())
            piece, portion = (int(x) for x in parts[2].split())
            aliases = [a.strip() for a in parts[3].split(",") if a.strip()]
            only_listed = bool(aliases) and aliases[0].startswith("=")
            if only_listed:
                aliases[0] = aliases[0][1:].strip()
            base = plain(re.sub(r"\([^)]*\)", " ", name))
            inner = [plain(m) for m in re.findall(r"\(([^)]*)\)", name)]
            auto = [x for x in [base] + inner if x]
            listed = [plain(a) for a in aliases if plain(a)]
            search = list(dict.fromkeys([plain(name)] + auto + listed))
            parse = list(dict.fromkeys(listed if only_listed else auto + listed))
            foods.append(Food(len(foods), name, k, p, f, c, piece, portion, tuple(search), tuple(parse)))
    return foods


FOODS_DB = _load()


# ------------------------------------------------------------------------------------------------ search
def _dist(a, b, limit):
    """Edit distance (insert, delete, replace, swap of neighbours) capped at limit + 1."""
    if abs(len(a) - len(b)) > limit:
        return limit + 1
    prev2, prev = None, list(range(len(b) + 1))
    for i in range(1, len(a) + 1):
        cur = [i] + [0] * len(b)
        lo = i
        for j in range(1, len(b) + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost)
            if prev2 is not None and i > 1 and j > 1 and a[i - 1] == b[j - 2] and a[i - 2] == b[j - 1]:
                cur[j] = min(cur[j], prev2[j - 2] + 1)
            lo = min(lo, cur[j])
        if lo > limit:
            return limit + 1
        prev2, prev = prev, cur
    return prev[-1]


def _token_level(t, words, fuzzy):
    """How well one query token matches the words of a phrase: 4 exact word, 3 word starts with it, 2 inside a word, 1 typo, 0 none."""
    best = 0
    for w in words:
        if w == t:
            return 4
        if w.startswith(t):
            best = max(best, 3)
        elif best < 2 and len(t) >= 3 and t in w:
            best = 2
        elif fuzzy and best < 1 and len(t) >= 5:
            lim = 1 if len(t) < 8 else 2
            if _dist(t, w, lim) <= lim or (len(w) > len(t) and _dist(t, w[:len(t)], 1) <= 1):
                best = 1
    return best


def _score(q, toks, food, fuzzy):
    best = 0.0
    for ph in food.phrases:
        words = ph.split()
        lv = 9
        for t in toks:
            lv = min(lv, _token_level(t, words, fuzzy))
            if not lv:
                break
        if not lv:
            continue
        s = lv * 10 - len(words) * 0.5
        if ph == q:
            s += 60
        elif ph.startswith(q):
            s += 25
        best = max(best, s)
    return best


def search(q, extra=(), limit=10):
    """Foods whose name or alias (uz / ru / en) matches `q`, best first. `extra` are the member's own foods: they come first.
    Prefix, word, substring and (for words of 5+ letters) one or two typos are accepted."""
    q = plain(q)[:60]
    if not q:
        return list(extra)[:limit]
    toks = q.split()[:5]
    out = []
    for fuzzy in (False, True):
        scored = []
        for f in list(extra) + FOODS_DB:
            s = _score(q, toks, f, fuzzy)
            if s:
                scored.append((not f.mine, -round(s), f.id, len(f.name), f))
        scored.sort(key=lambda x: x[:4])
        out = [x[-1] for x in scored]
        if len(out) >= 5 or not any(len(t) >= 5 for t in toks):
            break
    return out[:limit]


# ------------------------------------------------------------------------------------------------ free text
def stem_ok(tok, alias):
    """`tok` is the alias with an ending: osh -> oshni / oshdan, самса -> самсы, somsa -> somsalar."""
    return tok == alias or (tok.startswith(alias) and len(tok) - len(alias) <= (3 if len(alias) <= 3 else 5))


def find_foods(toks, extra=()):
    """[(first_token, last_token, Food)] named in a token list, in text order. The longest phrase wins, then the member's own food,
    then the longest alias, then the earlier table row; two foods never share a word."""
    cands = []
    for f in list(extra) + FOODS_DB:
        for ph in f.parse_phrases:
            words = ph.split()
            m = len(words)
            if m == 1 and len(words[0]) < 3 and not f.mine:
                continue
            for i in range(len(toks) - m + 1):
                if all(toks[i + j] == words[j] for j in range(m - 1)) and stem_ok(toks[i + m - 1], words[-1]):
                    cands.append((-m, not f.mine, -len(ph), f.id, i, i + m - 1, f))
    cands.sort(key=lambda x: x[:4])
    taken, seen, out = set(), set(), []
    for _, _, _, _, a, b, f in cands:
        if (f.mine, f.id) in seen or any(k in taken for k in range(a, b + 1)):
            continue
        taken.update(range(a, b + 1))
        seen.add((f.mine, f.id))
        out.append((a, b, f))
    out.sort(key=lambda x: x[0])
    return out
