"""Ready-made training programs shown on the "Mashq rejam" page.

Each program is a few sessions; a session is a label, the weekdays it runs on (0 = Monday) and its exercises
(name, sets, reps, rest in seconds). `build()` flattens them to the (weekday, name, sets, reps, rest) rows a WorkoutPlan needs.
Exercise names are written for members in Uzbek with the usual gym name in brackets. No emoji anywhere: the page draws line icons.
The data below is Uzbek; the Russian and English text of every title, description, tip, session label, exercise name and "30 s" / "20 daq" style
repetition is in TR (keyed by the Uzbek text), and `tr()`, `rows()`, `schedule()` give it in the member's language.
"""
import re

from .programs_x import RAW as _RAWX

GOALS = ("lose", "mass", "strength", "tone", "endurance")
LEVELS = ("beginner", "intermediate", "advanced")
PLACES = ("gym", "home")
# User.goal -> program goals that fit it best
GOAL_FIT = {"lose": ("lose",), "gain": ("mass",), "strength": ("strength",), "keep": ("tone", "endurance"), "health": ("tone", "endurance")}

COMMON_TIPS = ("Mashqdan oldin 5–10 daqiqa isinib oling, oxirida cho'zilish qiling.",
               "Og'riq (mushak charchog'idan boshqa) sezsangiz to'xtang; sog'lig'ingizda muammo bo'lsa, avval shifokor bilan maslahatlashing.")

PROGRAMS = {
    "beginner": {
        "title": "Boshlang'ich: butun tana", "goal": "tone", "level": "beginner", "place": "gym", "minutes": 50, "icon": "leaf",
        "about": "Haftasiga 3 marta. Asosiy harakatlarni o'rganish va kuchni bir tekis oshirish uchun.",
        "tips": ("Yengil vazn bilan boshlang: oxirgi takror qiyin, lekin texnika buzilmasin.", "Mashq kunlari orasida kamida 1 kun dam oling.",
                 "Har 2 haftada vaznni 2–5% oshiring."),
        "sessions": [("Butun tana", (0, 2, 4), [
            ("O'tirib turish (Squat)", 3, "12", 60), ("Polga tayanib ko'tarilish (Push-up)", 3, "10", 60),
            ("Yuqori blokni tortish (Lat pulldown)", 3, "12", 60), ("Gantel bilan eshkak (Dumbbell row)", 3, "12", 60),
            ("Planka (Plank)", 3, "30 s", 45)])]},
    "upper_lower": {
        "title": "Yuqori / Pastki tana", "goal": "mass", "level": "intermediate", "place": "gym", "minutes": 60, "icon": "dumbbell",
        "about": "Haftasiga 4 marta: yuqori va pastki tana navbatma-navbat. Massa uchun muvozanatli dastur.",
        "tips": ("Asosiy mashqlarda 8–10 takror, 90 s dam.", "Ovqatda protein yetarli bo'lsin (taxminan 1,6–2 g/kg).", "Uyqu kamida 7 soat."),
        "sessions": [
            ("Yuqori tana", (0, 3), [
                ("Shtanga bilan jim yotib itarish (Bench press)", 4, "8", 120), ("Shtanga bilan eshkak (Barbell row)", 4, "8", 120),
                ("Yelka uchun itarish (Shoulder press)", 3, "10", 90), ("Yuqori blokni tortish (Lat pulldown)", 3, "10", 90),
                ("Biceps (Curl)", 3, "12", 60), ("Triceps blokda (Pushdown)", 3, "12", 60)]),
            ("Pastki tana", (1, 4), [
                ("O'tirib turish (Squat)", 4, "8", 120), ("Rumincha stanovoy (RDL)", 3, "10", 120),
                ("Oyoq bilan itarish (Leg press)", 3, "12", 90), ("Son orqasi (Leg curl)", 3, "12", 60),
                ("Boldir (Calf raise)", 4, "15", 45), ("Planka (Plank)", 3, "45 s", 45)])]},
    "ppl": {
        "title": "Itarish · Tortish · Oyoq", "goal": "mass", "level": "advanced", "place": "gym", "minutes": 70, "icon": "trending-up",
        "about": "Push / Pull / Legs: har mushak guruhi haftasiga 2 marta. Massa va kuch uchun.",
        "tips": ("Faqat tajribali a'zolar uchun: haftasiga 6 kun yuk katta.", "Charchoq to'plansa, bir hafta yengil (deload) o'tkazing.",
                 "Og'ir to'plamlarda sherik yoki xavfsizlik tayanchidan foydalaning."),
        "sessions": [
            ("Itarish (Push)", (0, 3), [
                ("Shtanga bilan jim yotib itarish (Bench press)", 4, "8", 120), ("Qiya o'rindiqda gantel (Incline DB press)", 3, "10", 90),
                ("Yelka uchun itarish (Shoulder press)", 3, "10", 90), ("Yon tomonga ko'tarish (Lateral raise)", 3, "15", 45),
                ("Triceps blokda (Pushdown)", 3, "12", 60)]),
            ("Tortish (Pull)", (1, 4), [
                ("Stanovoy (Deadlift)", 4, "6", 150), ("Turnikda tortilish (Pull-up)", 4, "8", 120),
                ("Shtanga bilan eshkak (Barbell row)", 3, "10", 90), ("Yuzga tortish (Face pull)", 3, "15", 45), ("Biceps (Curl)", 3, "12", 60)]),
            ("Oyoq (Legs)", (2, 5), [
                ("O'tirib turish (Squat)", 4, "8", 120), ("Rumincha stanovoy (RDL)", 3, "10", 120),
                ("Oyoq bilan itarish (Leg press)", 3, "12", 90), ("Son orqasi (Leg curl)", 3, "12", 60), ("Boldir (Calf raise)", 4, "15", 45)])]},
    "fatloss": {
        "title": "Yog' yoqish: circuit", "goal": "lose", "level": "intermediate", "place": "gym", "minutes": 45, "icon": "flame",
        "about": "Aylana (circuit) mashqlar va kardio: puls baland, dam olish qisqa (30–45 s).",
        "tips": ("Doira oxirigacha to'xtamasdan bajaring, doiralar orasida 1–2 daqiqa dam.", "Ko'proq suv iching.",
                 "Yog' yoqish uchun ovqatdagi kaloriya ham muhim: kunlik kaloriya hisoblagichidan foydalaning."),
        "sessions": [
            ("Kardio circuit", (0, 3), [
                ("Burpi (Burpee)", 4, "12", 40), ("Girya silkitish (Kettlebell swing)", 4, "15", 40), ("Arqon (Jump rope)", 4, "60 s", 30),
                ("Tog'ga chiqish (Mountain climber)", 4, "30 s", 30), ("Yugurish yo'lakchasi", 1, "20 daq", 0)]),
            ("Kuch circuit", (1, 4), [
                ("Gantel bilan o'tirib turish (Goblet squat)", 4, "15", 40), ("Polga tayanib ko'tarilish (Push-up)", 4, "12", 40),
                ("Hamla (Lunges)", 3, "12", 40), ("Eshkak trenajyori (Rowing)", 1, "15 daq", 0), ("Planka (Plank)", 3, "45 s", 30)])]},
    "home": {
        "title": "Uyda: jihozsiz", "goal": "lose", "level": "beginner", "place": "home", "minutes": 35, "icon": "home",
        "about": "Haftasiga 3 marta, faqat o'z vazningiz bilan. Zalga bora olmaganlar uchun.",
        "tips": ("Sirpanmaydigan gilam yoki yumshoq sirt tanlang.", "Takrorlar oson bo'lsa, sekinlashtiring yoki bitta oyoqda bajaring.",
                 "Qo'shnilarni bezovta qilmaslik uchun sakrashsiz variantlarni tanlang."),
        "sessions": [("Uy aylanasi", (0, 2, 4), [
            ("Havodagi o'tirib turish (Bodyweight squat)", 3, "15", 45), ("Tizzada turib itarilish (Push-up)", 3, "10", 45),
            ("Hamla (Lunges)", 3, "10", 45), ("Ko'prik (Glute bridge)", 3, "15", 45), ("Planka (Plank)", 3, "30 s", 30),
            ("Joyida yugurish (High knees)", 3, "30 s", 30)])]},
    "strength5x5": {
        "title": "Kuch: 5×5", "goal": "strength", "level": "intermediate", "place": "gym", "minutes": 60, "icon": "zap",
        "about": "Haftasiga 3 marta: A va B mashg'ulotlar navbatma-navbat, og'ir asosiy harakatlar 5×5.",
        "tips": ("Texnika avval: vaznni faqat toza bajarilganda oshiring.", "Og'ir to'plamlar orasida 2–3 daqiqa dam oling.", "Squat va stanovoyda xavfsizlik kamari yoki sherik tavsiya etiladi."),
        "sessions": [
            ("Mashg'ulot A", (0, 4), [
                ("O'tirib turish (Squat)", 5, "5", 180), ("Shtanga bilan jim yotib itarish (Bench press)", 5, "5", 180),
                ("Shtanga bilan eshkak (Barbell row)", 5, "5", 180)]),
            ("Mashg'ulot B", (2,), [
                ("O'tirib turish (Squat)", 5, "5", 180), ("Tik shtanga itarish (Overhead press)", 5, "5", 180), ("Stanovoy (Deadlift)", 1, "5", 180)])]},
    "glute": {
        "title": "Tonus: son va dumba", "goal": "tone", "level": "intermediate", "place": "gym", "minutes": 55, "icon": "heart",
        "about": "Haftasiga 4 marta: dumba va oyoqqa urg'u, yuqori tana uchun yengil tonus. Ayollar uchun mashhur.",
        "tips": ("Dumbani siqishga e'tibor bering, belni egmang.", "Vaznni asta oshiring: 10–12 takror oxirgisi qiyin bo'lsin.", "Kardio kunini tez yurish bilan almashtirish mumkin."),
        "sessions": [
            ("Dumba A", (0,), [
                ("Dumba ko'prigi shtanga bilan (Hip thrust)", 4, "12", 90), ("Bolgar hamlasi (Bulgarian split squat)", 3, "10", 75),
                ("Rumincha stanovoy (RDL)", 3, "12", 90), ("Oyoqni yonga ko'tarish (Cable kickback)", 3, "15", 45)]),
            ("Yuqori tana tonusi", (2,), [
                ("Yuqori blokni tortish (Lat pulldown)", 3, "12", 60), ("Gantel bilan yelka itarish (DB shoulder press)", 3, "12", 60),
                ("Gantel bilan eshkak (Dumbbell row)", 3, "12", 60), ("Planka (Plank)", 3, "40 s", 30)]),
            ("Dumba B", (4,), [
                ("Gantel bilan o'tirib turish (Goblet squat)", 4, "12", 75), ("Hamla (Lunges)", 3, "12", 60),
                ("Oyoq bilan itarish (Leg press)", 3, "15", 75), ("Ko'prik (Glute bridge)", 3, "20", 45)]),
            ("Kardio va press", (5,), [
                ("Qiya yo'lakchada yurish (Incline walk)", 1, "25 daq", 0), ("Qorin buralishi (Crunch)", 3, "15", 30),
                ("Orqa tomonga ko'tarilish (Back extension)", 3, "12", 30)])]},
    "cardio": {
        "title": "Kardio va chidamlilik", "goal": "endurance", "level": "beginner", "place": "gym", "minutes": 40, "icon": "activity",
        "about": "Haftasiga 3 marta: yurak va nafas chidamliligini bosqichma-bosqich oshirish.",
        "tips": ("Suhbatlasha oladigan sur'atda boshlang (puls ~60–70%).", "Haftada davomiylikni 5 daqiqadan oshirib boring.", "Yurak bilan bog'liq kasallik bo'lsa, avval shifokorga murojaat qiling."),
        "sessions": [
            ("Tekis kardio", (0, 4), [("Yugurish yo'lakchasi (Treadmill)", 1, "25 daq", 0), ("Planka (Plank)", 3, "30 s", 30)]),
            ("Intervallar", (2,), [("Velotrenajyor: 1 daq tez, 1 daq sekin", 8, "1 daq tez", 0), ("Eshkak trenajyori (Rowing)", 1, "10 daq", 0)]),
        ]},
}


LANGS = ("uz", "ru", "en", "tr", "ky", "tg")
REST_LABEL = {"uz": "Dam", "ru": "Отдых", "en": "Rest", "tr": "Dinlenme", "ky": "Эс алуу", "tg": "Истироҳат"}  # the start of the "Dam: 60 s" note on an exercise
_UNITS = {"uz": ("s", "daq"), "ru": ("с", "мин"), "en": ("s", "min"), "tr": ("sn", "dk"), "ky": ("сек", "мүн"), "tg": ("сон", "дақ")}  # seconds, minutes
_TIMED = re.compile(r"(\d+) (s|daq)")  # a repetition value such as "30 s" or "20 daq"


TRX = {}  # English text -> (Turkish, Kyrgyz, Tajik)
for _line in _RAWX.strip().splitlines():
    _en, *_cells = _line.split("||")
    TRX[_en] = tuple(_cells)


def tr(text, lang="uz"):
    """`text` (written in Uzbek, as in PROGRAMS) in `lang`; the Uzbek text itself for uz, an unknown language or an unknown text."""
    pair = TR.get(text) if lang in ("ru", "en", "tr", "ky", "tg") else None
    if not pair:
        return text
    if lang in ("ru", "en"):
        return pair[0] if lang == "ru" else pair[1]
    own = TRX.get(pair[1])  # Turkish / Kyrgyz / Tajik: keyed by the English text; a missing one falls back (tr -> en, ky/tg -> ru)
    got = own[("tr", "ky", "tg").index(lang)] if own else ""
    return got or (pair[1] if lang == "tr" else pair[0])


def rest_label(lang="uz"):
    return REST_LABEL.get(lang, REST_LABEL["uz"])


def all_titles(prog):
    """The title of a program in every language (a started plan keeps the title of the language it was started in)."""
    return {tr(prog["title"], lang) for lang in LANGS}


def tips(prog, lang="uz"):
    return tuple(tr(t, lang) for t in prog["tips"] + COMMON_TIPS)


def fmt_rest(sec, lang="uz"):
    if not sec:
        return ""
    s, m = _UNITS.get(lang, _UNITS["uz"])
    if sec < 90:
        return f"{sec} {s}"
    if sec % 60 == 0:
        return f"{sec // 60} {m}"
    n = f"{sec / 60:.1f}"
    return f"{n if lang == 'en' else n.replace('.', ',')} {m}"


def fmt_reps(reps, lang="uz"):
    m = _TIMED.fullmatch(reps)
    if m and lang in ("ru", "en", "tr", "ky", "tg"):
        return f"{m.group(1)} {_UNITS[lang][0 if m.group(2) == 's' else 1]}"
    return tr(reps, lang)


def rows(prog, lang="uz"):
    """Flat (weekday, name, sets, reps, rest_text) in `lang`, ordered by weekday then by position in the session."""
    out = []
    for _label, days, exs in prog["sessions"]:
        for wd in days:
            out += [(wd, tr(n, lang), s, fmt_reps(r, lang), fmt_rest(rest, lang)) for n, s, r, rest in exs]
    return sorted(out, key=lambda x: x[0])  # sorted() is stable, so the in-session order is kept


def schedule(prog, lang="uz"):
    """[{wd, label, ex: [{name, sets, reps, rest}]}] for the preview, one entry per training day, in `lang`."""
    days = []
    for label, wds, exs in prog["sessions"]:
        for wd in wds:
            days.append({"wd": str(wd), "label": tr(label, lang),
                         "ex": [{"name": tr(n, lang), "sets": s, "reps": fmt_reps(r, lang), "rest": fmt_rest(rest, lang)} for n, s, r, rest in exs]})
    return sorted(days, key=lambda d: int(d["wd"]))


def days_list(prog):
    return sorted({wd for _l, wds, _e in prog["sessions"] for wd in wds})


def recommended(user_goal, done_count):
    """The key of the program that suits the member's profile goal (and rough experience), or None."""
    fit = GOAL_FIT.get(user_goal or "")
    if not fit:
        return None
    pool = [(k, p) for k, p in PROGRAMS.items() if p["goal"] in fit]
    if not pool:
        return None
    want = "beginner" if done_count < 20 else "intermediate"
    for k, p in pool:
        if p["level"] == want:
            return k
    return pool[0][0]


# ---------------------------------------------------------------- Russian and English text, keyed by the Uzbek text above: (ru, en)
# gym/tests_programs.py checks that every string of PROGRAMS and COMMON_TIPS has an entry here, so a new program needs its translations too.
TR = {
    # titles
    "Boshlang'ich: butun tana": ("Для начинающих: всё тело", "Beginner: full body"),
    "Yuqori / Pastki tana": ("Верх / низ тела", "Upper / lower body"),
    "Itarish · Tortish · Oyoq": ("Жим · Тяга · Ноги", "Push · Pull · Legs"),
    "Yog' yoqish: circuit": ("Жиросжигание: круговая", "Fat loss: circuit"),
    "Uyda: jihozsiz": ("Дома: без оборудования", "At home: no equipment"),
    "Kuch: 5×5": ("Сила: 5×5", "Strength: 5×5"),
    "Tonus: son va dumba": ("Тонус: бёдра и ягодицы", "Toning: thighs and glutes"),
    "Kardio va chidamlilik": ("Кардио и выносливость", "Cardio and endurance"),
    # descriptions
    "Haftasiga 3 marta. Asosiy harakatlarni o'rganish va kuchni bir tekis oshirish uchun.": (
        "3 раза в неделю. Чтобы освоить базовые движения и равномерно наращивать силу.",
        "3 times a week. To learn the basic movements and build strength steadily."),
    "Haftasiga 4 marta: yuqori va pastki tana navbatma-navbat. Massa uchun muvozanatli dastur.": (
        "4 раза в неделю: верх и низ тела по очереди. Сбалансированная программа на набор массы.",
        "4 times a week, alternating upper and lower body. A balanced program for building muscle."),
    "Push / Pull / Legs: har mushak guruhi haftasiga 2 marta. Massa va kuch uchun.": (
        "Push / Pull / Legs: каждая группа мышц 2 раза в неделю. Для массы и силы.",
        "Push / Pull / Legs: each muscle group twice a week. For muscle and strength."),
    "Aylana (circuit) mashqlar va kardio: puls baland, dam olish qisqa (30–45 s).": (
        "Круговые упражнения и кардио: пульс высокий, отдых короткий (30–45 с).",
        "Circuit exercises and cardio: high heart rate, short rests (30–45 s)."),
    "Haftasiga 3 marta, faqat o'z vazningiz bilan. Zalga bora olmaganlar uchun.": (
        "3 раза в неделю, только с собственным весом. Для тех, кто не может ходить в зал.",
        "3 times a week with your own body weight only. For those who can't get to the gym."),
    "Haftasiga 3 marta: A va B mashg'ulotlar navbatma-navbat, og'ir asosiy harakatlar 5×5.": (
        "3 раза в неделю: тренировки A и B по очереди, тяжёлые базовые движения 5×5.",
        "3 times a week: workouts A and B alternate, heavy compound lifts at 5×5."),
    "Haftasiga 4 marta: dumba va oyoqqa urg'u, yuqori tana uchun yengil tonus. Ayollar uchun mashhur.": (
        "4 раза в неделю: акцент на ягодицы и ноги, лёгкий тонус для верха тела. Популярна среди женщин.",
        "4 times a week: focus on glutes and legs, light toning for the upper body. Popular with women."),
    "Haftasiga 3 marta: yurak va nafas chidamliligini bosqichma-bosqich oshirish.": (
        "3 раза в неделю: постепенное повышение выносливости сердца и дыхания.",
        "3 times a week: build heart and lung endurance step by step."),
    # tips
    "Yengil vazn bilan boshlang: oxirgi takror qiyin, lekin texnika buzilmasin.": (
        "Начинайте с лёгкого веса: последнее повторение даётся трудно, но техника не страдает.",
        "Start light: the last rep should be hard, but your form should hold."),
    "Mashq kunlari orasida kamida 1 kun dam oling.": (
        "Между тренировочными днями отдыхайте не менее 1 дня.", "Rest at least 1 day between training days."),
    "Har 2 haftada vaznni 2–5% oshiring.": ("Каждые 2 недели увеличивайте вес на 2–5%.", "Add 2–5% to the weight every 2 weeks."),
    "Asosiy mashqlarda 8–10 takror, 90 s dam.": ("В базовых упражнениях 8–10 повторений, отдых 90 с.", "8–10 reps on the main lifts, 90 s rest."),
    "Ovqatda protein yetarli bo'lsin (taxminan 1,6–2 g/kg).": (
        "Белка в рационе должно хватать (примерно 1,6–2 г/кг).", "Eat enough protein (about 1.6–2 g/kg)."),
    "Uyqu kamida 7 soat.": ("Спите не менее 7 часов.", "Sleep at least 7 hours."),
    "Faqat tajribali a'zolar uchun: haftasiga 6 kun yuk katta.": (
        "Только для опытных: 6 тренировок в неделю — большая нагрузка.", "For experienced members only: 6 days a week is a heavy load."),
    "Charchoq to'plansa, bir hafta yengil (deload) o'tkazing.": (
        "Если накопилась усталость, проведите лёгкую неделю (deload).", "If fatigue builds up, take an easy week (deload)."),
    "Og'ir to'plamlarda sherik yoki xavfsizlik tayanchidan foydalaning.": (
        "В тяжёлых подходах используйте страховщика или страховочные упоры.", "Use a spotter or safety pins on heavy sets."),
    "Doira oxirigacha to'xtamasdan bajaring, doiralar orasida 1–2 daqiqa dam.": (
        "Выполняйте круг до конца без остановок, между кругами отдыхайте 1–2 минуты.",
        "Go through each circuit without stopping, then rest 1–2 minutes between circuits."),
    "Ko'proq suv iching.": ("Пейте больше воды.", "Drink more water."),
    "Yog' yoqish uchun ovqatdagi kaloriya ham muhim: kunlik kaloriya hisoblagichidan foydalaning.": (
        "Для жиросжигания важны и калории в еде: пользуйтесь счётчиком калорий.",
        "For fat loss the calories you eat matter too: use the daily calorie tracker."),
    "Sirpanmaydigan gilam yoki yumshoq sirt tanlang.": ("Выберите нескользящий коврик или мягкую поверхность.", "Use a non-slip mat or a soft surface."),
    "Takrorlar oson bo'lsa, sekinlashtiring yoki bitta oyoqda bajaring.": (
        "Если повторения даются легко, замедлите темп или выполняйте на одной ноге.", "If reps feel easy, slow them down or do them on one leg."),
    "Qo'shnilarni bezovta qilmaslik uchun sakrashsiz variantlarni tanlang.": (
        "Чтобы не мешать соседям, выбирайте варианты без прыжков.", "To avoid disturbing the neighbours, choose no-jump variations."),
    "Texnika avval: vaznni faqat toza bajarilganda oshiring.": (
        "Сначала техника: увеличивайте вес только при чистом выполнении.", "Form first: add weight only when the reps are clean."),
    "Og'ir to'plamlar orasida 2–3 daqiqa dam oling.": ("Между тяжёлыми подходами отдыхайте 2–3 минуты.", "Rest 2–3 minutes between heavy sets."),
    "Squat va stanovoyda xavfsizlik kamari yoki sherik tavsiya etiladi.": (
        "В приседе и становой тяге рекомендуются страховочный пояс или партнёр.",
        "A lifting belt or a spotter is recommended for squats and deadlifts."),
    "Dumbani siqishga e'tibor bering, belni egmang.": (
        "Следите за сокращением ягодиц, не прогибайте поясницу.", "Focus on squeezing the glutes and don't arch your lower back."),
    "Vaznni asta oshiring: 10–12 takror oxirgisi qiyin bo'lsin.": (
        "Повышайте вес постепенно: последнее из 10–12 повторений должно быть тяжёлым.",
        "Increase the weight gradually: the last of 10–12 reps should be hard."),
    "Kardio kunini tez yurish bilan almashtirish mumkin.": ("День кардио можно заменить быстрой ходьбой.", "You can swap the cardio day for brisk walking."),
    "Suhbatlasha oladigan sur'atda boshlang (puls ~60–70%).": (
        "Начинайте в темпе, при котором можно разговаривать (пульс ~60–70%).", "Start at a pace where you can still talk (heart rate ~60–70%)."),
    "Haftada davomiylikni 5 daqiqadan oshirib boring.": (
        "Каждую неделю увеличивайте длительность на 5 минут.", "Add 5 minutes to the duration each week."),
    "Yurak bilan bog'liq kasallik bo'lsa, avval shifokorga murojaat qiling.": (
        "При заболеваниях сердца сначала обратитесь к врачу.", "If you have a heart condition, see a doctor first."),
    "Mashqdan oldin 5–10 daqiqa isinib oling, oxirida cho'zilish qiling.": (
        "Перед тренировкой разминайтесь 5–10 минут, в конце сделайте растяжку.", "Warm up for 5–10 minutes before training and stretch at the end."),
    "Og'riq (mushak charchog'idan boshqa) sezsangiz to'xtang; sog'lig'ingizda muammo bo'lsa, avval shifokor bilan maslahatlashing.": (
        "Если чувствуете боль (не мышечную усталость), остановитесь; при проблемах со здоровьем сначала проконсультируйтесь с врачом.",
        "Stop if you feel pain (other than muscle fatigue); if you have health issues, talk to a doctor first."),
    # session labels
    "Butun tana": ("Всё тело", "Full body"),
    "Yuqori tana": ("Верх тела", "Upper body"),
    "Pastki tana": ("Низ тела", "Lower body"),
    "Itarish (Push)": ("Жим (Push)", "Push"),
    "Tortish (Pull)": ("Тяга (Pull)", "Pull"),
    "Oyoq (Legs)": ("Ноги (Legs)", "Legs"),
    "Kardio circuit": ("Кардио-круг", "Cardio circuit"),
    "Kuch circuit": ("Силовой круг", "Strength circuit"),
    "Uy aylanasi": ("Домашний круг", "Home circuit"),
    "Mashg'ulot A": ("Тренировка A", "Workout A"),
    "Mashg'ulot B": ("Тренировка B", "Workout B"),
    "Dumba A": ("Ягодицы A", "Glutes A"),
    "Dumba B": ("Ягодицы B", "Glutes B"),
    "Yuqori tana tonusi": ("Тонус верха тела", "Upper body toning"),
    "Kardio va press": ("Кардио и пресс", "Cardio and abs"),
    "Tekis kardio": ("Равномерное кардио", "Steady cardio"),
    "Intervallar": ("Интервалы", "Intervals"),
    # exercises
    "O'tirib turish (Squat)": ("Приседания (Squat)", "Squat"),
    "Polga tayanib ko'tarilish (Push-up)": ("Отжимания от пола (Push-up)", "Push-up"),
    "Yuqori blokni tortish (Lat pulldown)": ("Тяга верхнего блока (Lat pulldown)", "Lat pulldown"),
    "Gantel bilan eshkak (Dumbbell row)": ("Тяга гантели в наклоне (Dumbbell row)", "Dumbbell row"),
    "Planka (Plank)": ("Планка (Plank)", "Plank"),
    "Shtanga bilan jim yotib itarish (Bench press)": ("Жим штанги лёжа (Bench press)", "Bench press"),
    "Shtanga bilan eshkak (Barbell row)": ("Тяга штанги в наклоне (Barbell row)", "Barbell row"),
    "Yelka uchun itarish (Shoulder press)": ("Жим на плечи (Shoulder press)", "Shoulder press"),
    "Biceps (Curl)": ("Сгибания на бицепс (Curl)", "Biceps curl"),
    "Triceps blokda (Pushdown)": ("Разгибания на трицепс в блоке (Pushdown)", "Triceps pushdown"),
    "Rumincha stanovoy (RDL)": ("Румынская тяга (RDL)", "Romanian deadlift (RDL)"),
    "Oyoq bilan itarish (Leg press)": ("Жим ногами (Leg press)", "Leg press"),
    "Son orqasi (Leg curl)": ("Сгибания ног (Leg curl)", "Leg curl"),
    "Boldir (Calf raise)": ("Подъём на икры (Calf raise)", "Calf raise"),
    "Qiya o'rindiqda gantel (Incline DB press)": ("Жим гантелей на наклонной скамье (Incline DB press)", "Incline dumbbell press"),
    "Yon tomonga ko'tarish (Lateral raise)": ("Подъём гантелей в стороны (Lateral raise)", "Lateral raise"),
    "Stanovoy (Deadlift)": ("Становая тяга (Deadlift)", "Deadlift"),
    "Turnikda tortilish (Pull-up)": ("Подтягивания на перекладине (Pull-up)", "Pull-up"),
    "Yuzga tortish (Face pull)": ("Тяга к лицу (Face pull)", "Face pull"),
    "Burpi (Burpee)": ("Бёрпи (Burpee)", "Burpee"),
    "Girya silkitish (Kettlebell swing)": ("Махи гирей (Kettlebell swing)", "Kettlebell swing"),
    "Arqon (Jump rope)": ("Скакалка (Jump rope)", "Jump rope"),
    "Tog'ga chiqish (Mountain climber)": ("Скалолаз (Mountain climber)", "Mountain climber"),
    "Yugurish yo'lakchasi": ("Беговая дорожка", "Treadmill"),
    "Gantel bilan o'tirib turish (Goblet squat)": ("Гоблет-приседания (Goblet squat)", "Goblet squat"),
    "Hamla (Lunges)": ("Выпады (Lunges)", "Lunges"),
    "Eshkak trenajyori (Rowing)": ("Гребной тренажёр (Rowing)", "Rowing machine"),
    "Havodagi o'tirib turish (Bodyweight squat)": ("Приседания без веса (Bodyweight squat)", "Bodyweight squat"),
    "Tizzada turib itarilish (Push-up)": ("Отжимания с колен (Push-up)", "Knee push-up"),
    "Ko'prik (Glute bridge)": ("Ягодичный мостик (Glute bridge)", "Glute bridge"),
    "Joyida yugurish (High knees)": ("Бег на месте, колени вверх (High knees)", "High knees"),
    "Tik shtanga itarish (Overhead press)": ("Жим штанги стоя (Overhead press)", "Overhead press"),
    "Dumba ko'prigi shtanga bilan (Hip thrust)": ("Ягодичный мостик со штангой (Hip thrust)", "Hip thrust"),
    "Bolgar hamlasi (Bulgarian split squat)": ("Болгарские сплит-приседания (Bulgarian split squat)", "Bulgarian split squat"),
    "Oyoqni yonga ko'tarish (Cable kickback)": ("Отведение ноги в блоке (Cable kickback)", "Cable kickback"),
    "Gantel bilan yelka itarish (DB shoulder press)": ("Жим гантелей на плечи (DB shoulder press)", "Dumbbell shoulder press"),
    "Qiya yo'lakchada yurish (Incline walk)": ("Ходьба по наклонной дорожке (Incline walk)", "Incline walk"),
    "Qorin buralishi (Crunch)": ("Скручивания на пресс (Crunch)", "Crunch"),
    "Orqa tomonga ko'tarilish (Back extension)": ("Гиперэкстензия (Back extension)", "Back extension"),
    "Yugurish yo'lakchasi (Treadmill)": ("Беговая дорожка (Treadmill)", "Treadmill"),
    "Velotrenajyor: 1 daq tez, 1 daq sekin": ("Велотренажёр: 1 мин быстро, 1 мин медленно", "Exercise bike: 1 min fast, 1 min slow"),
    # repetitions that are words ("30 s" / "20 daq" are converted by fmt_reps)
    "1 daq tez": ("1 мин быстро", "1 min fast"),
}
