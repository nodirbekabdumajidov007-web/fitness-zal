"""Ready-made training programs shown on the "Mashq rejam" page.

Each program is a few sessions; a session is a label, the weekdays it runs on (0 = Monday) and its exercises
(name, sets, reps, rest in seconds). `build()` flattens them to the (weekday, name, sets, reps, rest) rows a WorkoutPlan needs.
Exercise names are written for members in Uzbek with the usual gym name in brackets. No emoji anywhere: the page draws line icons.
"""

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


def fmt_rest(sec):
    if not sec:
        return ""
    return f"{sec} s" if sec < 90 else (f"{sec // 60} daq" if sec % 60 == 0 else f"{sec / 60:.1f} daq".replace(".", ","))


def rows(prog):
    """Flat (weekday, name, sets, reps, rest_text), ordered by weekday then by position in the session."""
    out = []
    for _label, days, exs in prog["sessions"]:
        for wd in days:
            out += [(wd, n, s, r, fmt_rest(rest)) for n, s, r, rest in exs]
    return sorted(out, key=lambda x: x[0])  # sorted() is stable, so the in-session order is kept


def schedule(prog):
    """[{wd, label, ex: [{name, sets, reps, rest}]}] for the preview, one entry per training day."""
    days = []
    for label, wds, exs in prog["sessions"]:
        for wd in wds:
            days.append({"wd": str(wd), "label": label,
                         "ex": [{"name": n, "sets": s, "reps": r, "rest": fmt_rest(rest)} for n, s, r, rest in exs]})
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
