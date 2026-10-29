"""Offline assistant: answers questions from the built-in knowledge base (gym/assistant_kb*.py). No network, no external AI.

answer(text, lang, user) -> {"matched", "answer", "links": [{"label", "url"}], "suggest": [titles], "id", "topic"}

How a question is matched:
 1. the text is normalised (lower case, apostrophes dropped, punctuation removed) and every word is reduced to a stem
    (simple Uzbek / Russian / English suffix stripping), so "kaloriyani", "калории" and "calories" meet their keywords;
 2. every keyword phrase of every entry (all three languages together) is checked against the question: a phrase counts when all its
    stems are present; longer phrases weigh more, so "ish vaqti" beats the lone word "vaqt";
 3. the best entry above a threshold wins, otherwise the answer is "unknown" with the titles of the closest entries.

Facts that change (hours, prices, phone...) are never stored in the answers: they are {placeholders} filled from the database on every call.
"""
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


def normalize(text):
    s = _APOS.sub("", str(text or "").lower()).replace("ё", "е")
    return _NONWORD.sub(" ", s).strip()


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
    return [stem(w) for w in normalize(text).split()]


# ------------------------------------------------------------------ the compiled keyword index
_INDEX = None  # list of (entry, [(stems tuple, weight)])


def _index():
    global _INDEX
    if _INDEX is None:
        idx = []
        for e in kb.ENTRIES:
            seen, kws = set(), []
            for lang in kb.LANGS:
                for raw in e["kw"][lang]:
                    strong = raw.startswith("!")
                    st = tuple(tokens(raw.lstrip("!")))
                    if not st or st in seen:
                        continue
                    seen.add(st)
                    kws.append((st, 2.0 if (strong or len(st[0]) >= 6) else 1.0) if len(st) == 1 else (st, 2.0 * len(st)))
            idx.append((e, kws))
        _INDEX = idx
    return _INDEX


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


def score_all(text):
    """[(score, entry)] for every entry that shares at least one keyword with the text, best first."""
    qlist = tokens(text)
    qset = set(qlist)
    if not qset:
        return []
    out = []
    for order, (e, kws) in enumerate(_index()):
        if e["topic"] == "chat" and len(qlist) > CHAT_MAX_WORDS:
            continue
        hits = []
        for st, w in kws:
            if all(_has(s, qset) for s in st):
                hits.append(w + (1.0 if len(st) > 1 and _contiguous(st, qlist) else 0.0))
        if hits:
            hits.sort(reverse=True)
            sc = hits[0] + 0.25 * min(sum(hits[1:]), 4.0)
            chat = e["topic"] == "chat"
            if chat:
                sc = THRESHOLD  # small talk always clears the bar but loses every tie, so a real question wins over "salom"
            out.append((sc, 0 if chat else 1, -order, e))
    out.sort(key=lambda t: t[:3], reverse=True)
    return [(t[0], t[3]) for t in out]


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
def detect_lang(text, lang):
    """The language of the answer: the site language, except that a question written in Cyrillic is answered in Russian."""
    lang = lang if lang in kb.LANGS else "uz"
    letters = [c for c in text if c.isalpha()]
    if letters and lang != "ru" and sum(1 for c in letters if _CYR.match(c)) * 2 > len(letters):
        return "ru"
    return lang


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


def suggestions(scored, lang, skip=None, n=4):
    ids = [e["id"] for _, e in scored if e["id"] != skip and e["topic"] != "chat"][:n]
    for pid in kb.POPULAR:
        if len(ids) >= n:
            break
        if pid not in ids and pid != skip:
            ids.append(pid)
    return [title_of(kb.BY_ID[i], lang) for i in ids[:n]]


def answer(text, lang="uz", user=None):
    text = str(text or "").strip()[:MAX_QUERY]
    lang = detect_lang(text, lang)
    scored = score_all(text)
    authed = user is not None and user.is_authenticated
    best = scored[0][1] if scored and scored[0][0] >= THRESHOLD else None
    if best is None:
        return {"matched": False, "answer": _t(lang, "asst_unknown"), "links": [], "suggest": suggestions(scored, lang), "id": None, "topic": None}
    if best["id"] in kb.PERSONAL and not authed:
        return {"matched": True, "answer": _t(lang, "asst_login"), "links": [{"label": _t(lang, "login"), "url": reverse("login")}],
                "suggest": suggestions(scored, lang, skip=best["id"]), "id": best["id"], "topic": best["topic"]}
    facts = Facts(lang, user)
    return {"matched": True, "answer": fill(best["a"][lang], facts), "links": _links(best, lang),
            "suggest": suggestions(scored, lang, skip=best["id"]), "id": best["id"], "topic": best["topic"]}
