"""Rule-based weekly workout plan: goal + level + days per week + equipment -> a 7-day plan built from fixed templates.

No AI and no network: the day templates, set/rep schemes and exercise names below are plain data. build_plan() returns the structure,
make_plan() saves it as the member's current WorkoutPlan (the same plan page the old generator filled).
"""
GOALS = ("fat_loss", "muscle", "strength", "general")
LEVELS = ("beginner", "intermediate", "advanced")
EQUIPMENT = ("gym", "home")
LANGS = ("uz", "ru", "en")

# training weekdays (0 = Monday) for 2..6 days a week, with rest days spread between hard sessions
SCHEDULE = {2: [0, 3], 3: [0, 2, 4], 4: [0, 1, 3, 4], 5: [0, 1, 2, 4, 5], 6: [0, 1, 2, 3, 4, 5]}
SPLITS = {2: ["full_a", "full_b"], 3: ["full_a", "full_b", "full_a"], 4: ["upper", "lower", "upper", "lower"],
          5: ["push", "pull", "legs", "upper", "lower"], 6: ["push", "pull", "legs", "push", "pull", "legs"]}
DAY_NAMES = {
    "full_a": ("Butun tana A", "Всё тело A", "Full body A"), "full_b": ("Butun tana B", "Всё тело B", "Full body B"),
    "upper": ("Yuqori tana", "Верх тела", "Upper body"), "lower": ("Pastki tana", "Низ тела", "Lower body"),
    "push": ("Itarish (ko'krak, yelka, triceps)", "Жимы (грудь, плечи, трицепс)", "Push (chest, shoulders, triceps)"),
    "pull": ("Tortish (orqa, biceps)", "Тяги (спина, бицепс)", "Pull (back, biceps)"), "legs": ("Oyoq va dumba", "Ноги и ягодицы", "Legs and glutes"),
}
REST_DAY = ("Dam kuni (yengil yurish yoki cho'zilish)", "День отдыха (лёгкая ходьба или растяжка)", "Rest day (easy walk or stretching)")

# key -> (name uz, name ru, name en, tip uz, tip ru, tip en); tips stay short because they are stored in a 120-character note
EX = {
    "squat": ("O'tirib turish (Squat)", "Присед со штангой (Squat)", "Barbell squat", "Orqa tekis, tovonga tayaning", "Спина ровная, упор в пятки", "Flat back, push through heels"),
    "leg_press": ("Leg press", "Жим ногами (Leg press)", "Leg press", "Tizzani oxirigacha yozmang", "Колени до конца не выпрямляйте", "Do not lock the knees"),
    "rdl": ("Rumin deadlift (RDL)", "Румынская тяга (RDL)", "Romanian deadlift", "Tos orqaga, orqa tekis", "Таз назад, спина ровная", "Hips back, back flat"),
    "deadlift": ("Deadlift", "Становая тяга (Deadlift)", "Deadlift", "Shtanga tanaga yaqin, orqa tekis", "Штанга близко, спина ровная", "Bar close, back flat"),
    "lunges": ("Chiqish (Lunge)", "Выпады (Lunge)", "Lunges", "Har oyoqqa, nazoratli qadam", "На каждую ногу, шаг под контролем", "Each leg, controlled steps"),
    "leg_curl": ("Oyoq bukish (trenajyor)", "Сгибание ног (тренажёр)", "Leg curl", "Sekin qaytaring", "Возвращайте медленно", "Lower slowly"),
    "calf_raise": ("Boldir ko'tarish", "Подъёмы на носки", "Calf raise", "Tepada 1 soniya ushlang", "Задержка вверху 1 секунда", "Hold 1 second at the top"),
    "bench": ("Yotib surish (Bench press)", "Жим лёжа (Bench press)", "Bench press", "Kuraklar birlashgan, oyoq yerda", "Лопатки сведены, ноги в пол", "Shoulder blades pinched, feet down"),
    "incline_db": ("Qiya skameykada gantel surish", "Жим гантелей на наклонной", "Incline dumbbell press", "Tirsaklar tanadan 45-70 daraja", "Локти 45-70 градусов к корпусу", "Elbows 45-70 degrees from the body"),
    "ohp": ("Yelka surish (Overhead press)", "Жим стоя (Overhead press)", "Overhead press", "Belni bukmang, qorin tarang", "Не прогибайте поясницу", "Do not arch the lower back"),
    "lateral_raise": ("Gantel yon ko'tarish", "Махи гантелями в стороны", "Lateral raise", "Yengil og'irlik, silkinmasdan", "Лёгкий вес, без рывков", "Light weight, no swinging"),
    "triceps_push": ("Triceps blokda cho'zish", "Разгибание на трицепс на блоке", "Triceps pushdown", "Tirsaklar tanaga yopishgan", "Локти прижаты к корпусу", "Elbows pinned to the sides"),
    "chest_fly": ("Kabel yig'ish", "Сведения на блоках", "Cable fly", "Ko'krak mushagini his qiling", "Чувствуйте грудные мышцы", "Feel the chest working"),
    "lat_pulldown": ("Yuqori blok tortish (Lat pulldown)", "Тяга верхнего блока (Lat pulldown)", "Lat pulldown", "Ko'krakka qarab torting", "Тяните к груди", "Pull toward the chest"),
    "seated_row": ("Gorizontal blok tortish", "Горизонтальная тяга на блоке", "Seated cable row", "Kuraklarni birlashtiring", "Сводите лопатки", "Squeeze the shoulder blades"),
    "face_pull": ("Face pull", "Тяга к лицу (Face pull)", "Face pull", "Yelka sog'ligi uchun foydali", "Полезно для здоровья плеч", "Good for shoulder health"),
    "biceps_curl": ("Gantel bilan biceps", "Сгибания на бицепс с гантелями", "Dumbbell curl", "Tirsaklar qimirlamasin", "Локти неподвижны", "Keep the elbows still"),
    "hammer_curl": ("Bolg'a uslubida biceps", "Молотковые сгибания", "Hammer curl", "Sekin tushiring", "Опускайте медленно", "Lower slowly"),
    "plank": ("Plank", "Планка (Plank)", "Plank", "Tana tekis chiziq", "Тело ровной линией", "Body in one straight line"),
    "hanging_knee": ("Osilib tizza ko'tarish", "Подъём коленей в висе", "Hanging knee raise", "Silkinmasdan", "Без раскачивания", "No swinging"),
    "cardio_hiit": ("Intervalli kardio (yugurish yoki velotrenajyor)", "Интервальное кардио (дорожка или велотренажёр)", "Interval cardio (treadmill or bike)",
                    "30 soniya tez, 60 soniya sekin", "30 секунд быстро, 60 секунд медленно", "30 seconds fast, 60 seconds easy"),
    "cardio_easy": ("Yengil kardio", "Лёгкое кардио", "Easy cardio", "Suhbatlashish mumkin bo'lgan temp", "Темп, при котором можно говорить", "A pace where you can talk"),
    # at home
    "pushup": ("Otjimaniya", "Отжимания", "Push-ups", "Tana tekis; qiyin bo'lsa tizzada", "Тело ровно; тяжело — с колен", "Straight body; knees if too hard"),
    "pike_pushup": ("Burchakli otjimaniya (yelka)", "Отжимания углом (плечи)", "Pike push-ups", "Dumba yuqorida, boshni polga yaqinlashtiring", "Таз вверху, голова к полу", "Hips high, head toward the floor"),
    "diamond_pushup": ("Tor otjimaniya (triceps)", "Узкие отжимания (трицепс)", "Close-grip push-ups", "Tirsaklar tanaga yaqin", "Локти близко к корпусу", "Elbows close to the body"),
    "dips_chair": ("Stulda triceps otjimaniya", "Обратные отжимания от стула", "Chair dips", "Yelkani ortiqcha tushirmang", "Плечи не опускайте слишком глубоко", "Do not drop the shoulders too deep"),
    "bw_squat": ("O'tirib turish (o'z vazni bilan)", "Приседания (свой вес)", "Bodyweight squat", "Tovonga tayaning, sekin tushing", "Упор в пятки, спуск медленно", "Heels down, lower slowly"),
    "goblet": ("Goblet squat (ryukzak yoki gantel)", "Гоблет-присед (рюкзак или гантель)", "Goblet squat (backpack or dumbbell)", "Yukni ko'krak oldida ushlang", "Груз держите у груди", "Hold the weight at the chest"),
    "glute_bridge": ("Dumba ko'prigi (Glute bridge)", "Ягодичный мостик (Glute bridge)", "Glute bridge", "Tepada dumbani qisib 1 soniya", "Вверху сожмите ягодицы на 1 секунду", "Squeeze the glutes for 1 second at the top"),
    "step_up": ("Stulga chiqish (Step-up)", "Зашагивания на стул (Step-up)", "Step-ups", "Barqaror tayanch tanlang", "Выберите устойчивую опору", "Use a stable step"),
    "wall_sit": ("Devorga suyanib o'tirish", "Стульчик у стены", "Wall sit", "Tizza 90 daraja", "Колени под 90 градусов", "Knees at 90 degrees"),
    "calf_home": ("Boldir ko'tarish (poyda)", "Подъёмы на носки (на ступеньке)", "Calf raise (on a step)", "Sekin va to'liq amplituda", "Медленно и в полную амплитуду", "Slow and full range"),
    "backpack_row": ("Ryukzak bilan tortish", "Тяга рюкзака в наклоне", "Backpack row", "Orqa tekis, tirsakni orqaga torting", "Спина ровная, тяните локоть назад", "Flat back, pull the elbow back"),
    "superman": ("Superman (orqa mushaklari)", "Супермен (мышцы спины)", "Superman", "Tepada 2 soniya ushlang", "Задержка вверху 2 секунды", "Hold 2 seconds at the top"),
    "bird_dog": ("Bird-dog", "Птица-собака (Bird-dog)", "Bird-dog", "Belni tekis ushlang", "Держите поясницу ровно", "Keep the lower back level"),
    "good_morning": ("Egilish (Good morning)", "Наклоны (Good morning)", "Good morning hinge", "Tos orqaga, orqa tekis", "Таз назад, спина ровная", "Hips back, back flat"),
    "bicycle_crunch": ("Velosiped (qorin)", "Велосипед (пресс)", "Bicycle crunch", "Sekin, bo'yinni tortmang", "Медленно, шею не тяните", "Slow, do not pull the neck"),
    "mountain": ("Tog'ga chiqish (Mountain climbers)", "Скалолаз (Mountain climbers)", "Mountain climbers", "Tana tekis, tez-tez qadam", "Тело ровно, частые шаги", "Straight body, quick steps"),
    "cardio_home": ("Uyda intervalli kardio (sakrash, burpee)", "Домашнее интервальное кардио (прыжки, бёрпи)", "Home interval cardio (jumping jacks, burpees)",
                    "30 soniya ish, 30 soniya dam", "30 секунд работа, 30 секунд отдых", "30 seconds on, 30 seconds off"),
}

# exercise keys of each day type; the first two are the "main" (compound) exercises, the rest are accessories
DAYS = {
    "gym": {
        "full_a": ["squat", "bench", "lat_pulldown", "ohp", "leg_curl", "plank"],
        "full_b": ["rdl", "incline_db", "seated_row", "lunges", "lateral_raise", "hanging_knee"],
        "upper": ["bench", "lat_pulldown", "ohp", "seated_row", "biceps_curl", "triceps_push"],
        "lower": ["squat", "rdl", "leg_press", "leg_curl", "calf_raise", "plank"],
        "push": ["bench", "ohp", "incline_db", "lateral_raise", "triceps_push", "chest_fly"],
        "pull": ["lat_pulldown", "seated_row", "face_pull", "biceps_curl", "hammer_curl", "hanging_knee"],
        "legs": ["squat", "rdl", "leg_press", "lunges", "leg_curl", "calf_raise"],
    },
    "home": {
        "full_a": ["bw_squat", "pushup", "backpack_row", "glute_bridge", "plank", "mountain"],
        "full_b": ["lunges", "pike_pushup", "good_morning", "dips_chair", "bicycle_crunch", "superman"],
        "upper": ["pushup", "backpack_row", "pike_pushup", "dips_chair", "superman", "plank"],
        "lower": ["bw_squat", "lunges", "glute_bridge", "step_up", "calf_home", "wall_sit"],
        "push": ["pushup", "pike_pushup", "diamond_pushup", "dips_chair", "plank", "mountain"],
        "pull": ["backpack_row", "superman", "bird_dog", "good_morning", "glute_bridge", "plank"],
        "legs": ["goblet", "lunges", "glute_bridge", "step_up", "calf_home", "wall_sit"],
    },
}
TIMED = {"plank": "30-60 s", "wall_sit": "30-45 s", "cardio_hiit": "8-10 min", "cardio_easy": "15-20 min", "cardio_home": "8-10 min",
         "superman": "10-12", "bird_dog": "10 / 10"}

# goal -> (main sets, main reps, main rest, accessory sets, accessory reps, accessory rest); home work uses its own reps (no heavy load)
SCHEMES = {
    "fat_loss": (3, "10-12", "60-75 s", 3, "12-15", "45-60 s"),
    "muscle": (4, "6-10", "90-120 s", 3, "10-15", "60-90 s"),
    "strength": (5, "3-5", "2-3 min", 3, "6-8", "90 s"),
    "general": (3, "8-12", "60-90 s", 2, "12-15", "45-60 s"),
}
HOME_REPS = {"fat_loss": ("15-20", "15-20"), "muscle": ("10-15", "12-20"), "strength": ("6-10", "10-15"), "general": ("10-15", "12-15")}
REST_WORD = ("Dam", "Отдых", "Rest")
CAP = {"beginner": 5, "intermediate": 6, "advanced": 6}

TITLES = {
    "fat_loss": ("Ozish rejasi", "План для похудения", "Fat loss plan"), "muscle": ("Mushak o'stirish rejasi", "План на рост мышц", "Muscle gain plan"),
    "strength": ("Kuch rejasi", "Силовой план", "Strength plan"), "general": ("Umumiy fitnes rejasi", "План общей формы", "General fitness plan"),
}
NOTES = {
    "fat_loss": ("Mashqni 5-10 daqiqa razminka bilan boshlang. Ozish asosan kaloriya tanqisligidan keladi: ovqatni nazorat qiling, kuniga 7-10 ming qadam yuring. Har 2 haftada takrorni yoki og'irlikni ozgina oshiring.",
                 "Начинайте с разминки 5-10 минут. Похудение в основном даёт дефицит калорий: следите за питанием и проходите 7-10 тысяч шагов в день. Каждые 2 недели чуть увеличивайте повторы или вес.",
                 "Start with a 5-10 minute warm-up. Fat loss mostly comes from a calorie deficit, so watch your food and walk 7-10 thousand steps a day. Every 2 weeks add a few reps or a little weight."),
    "muscle": ("Mashqni 5-10 daqiqa razminka bilan boshlang. Oxirgi takrorlar og'ir bo'lsin, texnika buzilmasin. Takror yuqori chegaraga yetsa, og'irlikni 2,5-5% oshiring; oqsil 1,6-2,2 g/kg va 7-9 soat uyqu.",
               "Начинайте с разминки 5-10 минут. Последние повторы должны быть тяжёлыми, но техника не ломается. Дошли до верхней границы повторов, добавьте вес на 2,5-5%; белок 1,6-2,2 г/кг и 7-9 часов сна.",
               "Start with a 5-10 minute warm-up. The last reps should be hard while the form holds. When you reach the top of the rep range add 2.5-5% weight; eat 1.6-2.2 g/kg protein and sleep 7-9 hours."),
    "strength": ("Mashqni 10 daqiqa razminka va yengil yondashuvlar bilan boshlang. Asosiy mashqlarda dam 2-3 daqiqa, texnika birinchi o'rinda. Og'irlikni haftada 2,5 kg gacha oshiring, 6-8 haftadan keyin bir yengil hafta qiling.",
                 "Начинайте с разминки 10 минут и лёгких подходов. В базовых упражнениях отдых 2-3 минуты, техника на первом месте. Прибавляйте вес до 2,5 кг в неделю, через 6-8 недель устройте лёгкую неделю.",
                 "Start with a 10 minute warm-up and light sets. Rest 2-3 minutes on the main lifts and put technique first. Add up to 2.5 kg a week and take a light week after 6-8 weeks."),
    "general": ("Mashqni 5-10 daqiqa razminka bilan boshlang. Qulay og'irlik tanlang, texnikani o'rganing. Har hafta bir-ikki takror qo'shing; kunlar orasida yurish va cho'zilish foydali.",
                "Начинайте с разминки 5-10 минут. Выберите комфортный вес и осваивайте технику. Каждую неделю добавляйте по одному-двум повторам; ходьба и растяжка между днями полезны.",
                "Start with a 5-10 minute warm-up. Choose a comfortable weight and learn the technique. Add a rep or two each week; walking and stretching between days help."),
}
LEVEL_NOTE = {
    "beginner": ("Boshlovchi uchun hajm kamaytirilgan: avval texnika.", "Для новичка объём уменьшен: сначала техника.", "Volume is lower for beginners: technique first."),
    "intermediate": ("", "", ""),
    "advanced": ("Asosiy mashqlarda bitta qo'shimcha yondashuv bor.", "В базовых упражнениях добавлен один подход.", "Main lifts carry one extra set."),
}


class PlanError(Exception):
    """Carries a translation key shown to the member."""
    def __init__(self, key):
        super().__init__(key)
        self.key = key


def _li(lang):
    return LANGS.index(lang) if lang in LANGS else 0


def clean(goal, level, days, equipment):
    goal = goal if goal in GOALS else "general"
    level = level if level in LEVELS else "beginner"
    equipment = equipment if equipment in EQUIPMENT else "gym"
    try:
        days = max(2, min(6, int(days)))
    except (TypeError, ValueError):
        days = 3
    return goal, level, days, equipment


def _exercise(key, role, goal, level, equipment, lang):
    i = _li(lang)
    ms, mr, mrest, as_, ar, arest = SCHEMES[goal]
    if key in TIMED:
        sets, reps, rest = (1 if key.startswith("cardio") else 3), TIMED[key], ""
    elif role == "main":
        sets, reps, rest = ms, mr, mrest
        if equipment == "home":
            reps = HOME_REPS[goal][0]
            sets = min(sets, 4)
        if level == "beginner":
            sets = max(2, sets - 1)
            if goal == "strength":
                reps = "5-8" if equipment == "gym" else reps
        elif level == "advanced":
            sets = min(sets + 1, 5)
    else:
        sets, reps, rest = as_, ar, arest
        if equipment == "home":
            reps = HOME_REPS[goal][1]
        if level == "beginner":
            sets = max(2, sets - 1)
    name, tip = EX[key][i], EX[key][3 + i]
    note = tip if not rest else f"{REST_WORD[i]}: {rest}. {tip}"
    return {"key": key, "name": name[:80], "sets": sets, "reps": reps[:20], "rest": rest, "note": note[:120]}


def build_plan(goal="general", level="beginner", days=3, equipment="gym", lang="uz"):
    """The structured plan: {"title", "notes", "goal", "level", "days_per_week", "equipment", "days": [7 x {weekday, rest, label, exercises}]}.
    Each exercise is {key, name, sets, reps, rest, note}; rest days have an empty list."""
    goal, level, days, equipment = clean(goal, level, days, equipment)
    lang = lang if lang in LANGS else "uz"
    i = _li(lang)
    schedule, split = SCHEDULE[days], SPLITS[days]
    by_weekday = {wd: kind for wd, kind in zip(schedule, split)}
    week = []
    for wd in range(7):
        kind = by_weekday.get(wd)
        if kind is None:
            week.append({"weekday": wd, "rest": True, "label": REST_DAY[i], "exercises": []})
            continue
        keys = list(DAYS[equipment][kind])
        if goal == "strength" and equipment == "gym" and level != "beginner" and "rdl" in keys and kind in ("lower", "legs"):
            keys[keys.index("rdl")] = "deadlift"
        keys = keys[:CAP[level]]
        rows = [_exercise(k, "main" if n < 2 else "acc", goal, level, equipment, lang) for n, k in enumerate(keys)]
        if goal == "fat_loss":  # a short interval finisher on every training day
            rows.append(_exercise("cardio_hiit" if equipment == "gym" else "cardio_home", "acc", goal, level, equipment, lang))
        elif goal == "general" and len([w for w in week if not w["rest"]]) % 2 == 1:  # easy cardio on every second training day
            rows.append(_exercise("cardio_easy", "acc", goal, level, equipment, lang))
        week.append({"weekday": wd, "rest": False, "label": DAY_NAMES[kind][i], "exercises": rows})
    notes = NOTES[goal][i] + (" " + LEVEL_NOTE[level][i] if LEVEL_NOTE[level][i] else "")
    suffix = {"uz": f"{days} kun", "ru": f"{days} дн.", "en": f"{days} days"}[lang]
    return {"title": f"{TITLES[goal][i]}: {suffix}", "notes": notes[:2000], "goal": goal, "level": level, "days_per_week": days,
            "equipment": equipment, "days": week}


def make_plan(user, goal, level, days, equipment, lang="uz"):
    """Builds the plan and saves it as the member's current plan. A plan written by the member's trainer is never replaced."""
    from .models import WorkoutPlan
    if user.workout_plans.filter(active=True, trainer__isnull=False).exists():
        raise PlanError("program_trainer")
    plan = build_plan(goal, level, days, equipment, lang)
    user.workout_plans.filter(active=True).update(active=False)
    obj = WorkoutPlan.objects.create(user=user, title=("✦ " + plan["title"])[:80], notes=plan["notes"], active=True)
    order = 0
    for day in plan["days"]:
        for ex in day["exercises"]:
            obj.exercises.create(weekday=day["weekday"], name=ex["name"], sets=ex["sets"], reps=ex["reps"], note=ex["note"], order=order)
            order += 1
    return obj
