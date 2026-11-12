"""Strings of the polished /progress/ and /records/ pages that are not in gym/i18n.py yet. Each value is (uz, ru, en); Turkish / Kyrgyz / Tajik are in TX_X below; any other
language falls back to English. Moving them to i18n.py later is a mechanical change (see tx_for())."""

TX = {
    "history": ("Tarix", "История", "History"),
    "export": ("Eksport", "Экспорт", "Export"),
    "bmi_need_height": ("Bo'yni kiriting", "Укажите рост", "Enter height"),
    "bf_need": ("O'lchamlar kerak", "Нужны замеры", "Measurements needed"),
    "bf_lean": ("Quruq", "Сухой", "Lean"),
    "bf_ok": ("Me'yor", "Норма", "Normal"),
    "bf_high": ("Yuqori", "Повышенный", "High"),
    "d7": ("7 kun", "7 дн.", "7 d"),
    "d30": ("30 kun", "30 дн.", "30 d"),
    "visits_n": ("tashrif", "посещений", "visits"),
    "goal_prompt": ("Maqsad qo'ying — masalan 75 kg gacha", "Поставьте цель — например, до 75 кг", "Set a goal — e.g. down to 75 kg"),
    "goal_remove": ("O'chirish", "Удалить", "Remove"),
    "v_weight": ("Vazn 20–400 kg oralig'ida bo'lsin", "Вес должен быть от 20 до 400 кг", "Weight must be 20–400 kg"),
    "v_height": ("Bo'y 100–250 sm oralig'ida bo'lsin", "Рост должен быть от 100 до 250 см", "Height must be 100–250 cm"),
    "v_date": ("Sana kelajakda bo'lmasin", "Дата не может быть в будущем", "The date cannot be in the future"),
    "empty_weight": ("2 ta o'lchov kiritilsa grafik paydo bo'ladi", "График появится после двух замеров", "The chart appears after 2 measurements"),
    "empty_measures": ("Bel, ko'krak va boshqa o'lchamlar kiritilsa grafik paydo bo'ladi", "График появится, когда вы добавите талию, грудь и другие замеры",
                       "The chart appears once you log waist, chest or other measurements"),
    "empty_fat": ("Tana yog'i yoki puls kiritilsa grafik paydo bo'ladi", "График появится после ввода жира или пульса", "The chart appears once you log body fat or pulse"),
    "empty_strength": ("Mashg'ulot qo'shsangiz kuch grafigi paydo bo'ladi", "График силы появится после первой тренировки", "The strength chart appears after your first workout"),
    "empty_volume": ("Mashg'ulot qo'shsangiz hajm grafigi paydo bo'ladi", "График объёма появится после первой тренировки", "The volume chart appears after your first workout"),
    "empty_activity": ("Mashg'ulot yoki zal tashrifi bo'lsa grafik paydo bo'ladi", "График появится после тренировки или визита в зал", "The chart appears after a workout or a gym visit"),
    "empty_calories": ("Ovqat kundaligiga kaloriya yozilsa grafik paydo bo'ladi", "График появится, когда вы начнёте вести дневник питания", "The chart appears once you log meals"),
    # records page
    "rc_first": ("Birinchi natijani yozing", "Запишите первый результат", "Log your first result"),
    "rc_best": ("Eng yaxshi", "Лучший", "Best"),
    "rc_vs_prev": ("oldingi rekorddan", "к прошлому рекорду", "vs previous best"),
    "rc_est": ("Taxminiy 1RM", "Расчётный 1ПМ", "Estimated 1RM"),
}

LIFT_NAMES = {  # key: (uz, ru, en)
    "bench": ("Jim yotib itarish", "Жим лёжа", "Bench press"),
    "squat": ("O'tirib turish", "Приседания", "Squat"),
    "deadlift": ("Stanovoy tortish", "Становая тяга", "Deadlift"),
    "ohp": ("Yelkaga itarish", "Жим стоя", "Overhead press"),
    "pullup": ("Turnikda tortilish", "Подтягивания", "Pull-up"),
    "row": ("Shtanga bilan eshkak", "Тяга штанги в наклоне", "Barbell row"),
}

_IDX = {"uz": 0, "ru": 1, "en": 2}

# Turkish / Kyrgyz / Tajik, same keys: (tr, ky, tg)
TX_X = {
    "history": ("Geçmiş", "Тарых", "Таърих"),
    "export": ("Dışa aktar", "Экспорт", "Содирот"),
    "bmi_need_height": ("Boyunuzu girin", "Бойду киргизиңиз", "Қадро ворид кунед"),
    "bf_need": ("Ölçümler gerekli", "Өлчөмдөр керек", "Андозаҳо лозиманд"),
    "bf_lean": ("Kuru", "Курғак", "Хушк"),
    "bf_ok": ("Normal", "Норма", "Муқаррарӣ"),
    "bf_high": ("Yüksek", "Жогору", "Баланд"),
    "d7": ("7 gün", "7 күн", "7 рӯз"),
    "d30": ("30 gün", "30 күн", "30 рӯз"),
    "visits_n": ("ziyaret", "визит", "ташриф"),
    "goal_prompt": ("Bir hedef belirleyin, örn. 75 kg'a kadar", "Максат коюңуз, мисалы 75 кгга чейин", "Ҳадаф гузоред, масалан то 75 кг"),
    "goal_remove": ("Sil", "Өчүрүү", "Нест кардан"),
    "v_weight": ("Kilo 20–400 kg arasında olmalı", "Салмак 20–400 кг аралыгында болушу керек", "Вазн бояд аз 20 то 400 кг бошад"),
    "v_height": ("Boy 100–250 cm arasında olmalı", "Бой 100–250 см аралыгында болушу керек", "Қад бояд аз 100 то 250 см бошад"),
    "v_date": ("Tarih gelecekte olamaz", "Дата келечекте болбошу керек", "Сана дар оянда набояд бошад"),
    "empty_weight": ("2 ölçüm girildiğinde grafik görünür", "2 өлчөм киргизилгенде график пайда болот", "Пас аз ворид кардани 2 андоза диаграмма пайдо мешавад"),
    "empty_measures": ("Bel, göğüs ve diğer ölçüler girildiğinde grafik görünür", "Бел, көкүрөк жана башка өлчөмдөр киргизилгенде график пайда болот",
                       "Вақте камар, сина ва андозаҳои дигарро ворид кунед, диаграмма пайдо мешавад"),
    "empty_fat": ("Vücut yağı veya nabız girildiğinde grafik görünür", "Дененин майы же пульс киргизилгенде график пайда болот", "Пас аз ворид кардани чарбуи бадан ё набз диаграмма пайдо мешавад"),
    "empty_strength": ("İlk antrenmandan sonra güç grafiği görünür", "Биринчи машыгуудан кийин күч графиги пайда болот", "Пас аз машқи аввал диаграммаи қувват пайдо мешавад"),
    "empty_volume": ("İlk antrenmandan sonra hacim grafiği görünür", "Биринчи машыгуудан кийин көлөм графиги пайда болот", "Пас аз машқи аввал диаграммаи ҳаҷм пайдо мешавад"),
    "empty_activity": ("Antrenman veya salon ziyaretinden sonra grafik görünür", "Машыгуу же залга визиттен кийин график пайда болот", "Пас аз машқ ё ташриф ба толор диаграмма пайдо мешавад"),
    "empty_calories": ("Yemek günlüğüne kayıt girildiğinde grafik görünür", "Тамак күнүмдүгүнө жазуу киргизилгенде график пайда болот", "Вақте ба рӯзномаи ғизо сабт ворид кунед, диаграмма пайдо мешавад"),
    "rc_first": ("İlk sonucu kaydedin", "Биринчи жыйынтыкты жазыңыз", "Натиҷаи аввалинро сабт кунед"),
    "rc_best": ("En iyi", "Эң мыкты", "Беҳтарин"),
    "rc_vs_prev": ("önceki rekora göre", "мурунку рекордго салыштырмалуу", "нисбат ба рекорди қаблӣ"),
    "rc_est": ("Tahmini 1RM", "Болжолдуу 1RM", "1RM-и тахминӣ"),
}
LIFT_X = {
    "bench": ("Bench press", "Скамейкада штанга түртүү", "Тела додани штанга дар скамя"),
    "squat": ("Squat", "Отуруп туруу (сквот)", "Нишаста хестан (сквот)"),
    "deadlift": ("Deadlift", "Дедлифт", "Дедлифт"),
    "ohp": ("Omuz press", "Ийинге штанга түртүү", "Тела додани штанга аз китф"),
    "pullup": ("Barfiks", "Турникте тартылуу", "Дар турник кашида шудан"),
    "row": ("Barbell row", "Штанга менен калак", "Калак бо штанга"),
}
_NEW = {"tr": 0, "ky": 1, "tg": 2}


def tx_for(lang):
    if lang in _NEW:
        return {k: TX_X[k][_NEW[lang]] for k in TX}
    i = _IDX.get(lang, 2)
    return {k: v[i] for k, v in TX.items()}


def lift_name(key, lang):
    names = LIFT_NAMES[key]
    if lang in _NEW:
        return LIFT_X[key][_NEW[lang]], names[2]
    return names[_IDX.get(lang, 2)], (names[2] if lang != "en" else "")
