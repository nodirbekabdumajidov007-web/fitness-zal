"""Extra keywords for existing knowledge base entries: the everyday ways members actually ask (short, spoken, often without the "key" noun).

{entry id: (uz, ru, en)} - "|" separates keywords, a leading "!" makes a single word strong enough on its own (see assistant._index).
Only keywords live here: every answer stays in its own assistant_kb_*.py row, so nothing about the gym is invented. Merged by assistant_kb.
"""

ALIAS = {
    # ---- the gym: payment, place, hours
    "pay_methods": ("to'lov qanday qilinadi|qanday to'lasam bo'ladi|qanday to'lash mumkin|to'lov qilish|qayerga to'layman|qanday to'lanadi|to'lov qanday",
                    "как оплатить|как можно оплатить|как платить|способ оплаты|оплатить картой|можно ли оплатить картой",
                    "how to pay|how can i pay|pay by card|can i pay by card|payment options"),
    "pay_online": ("click orqali to'lash|payme orqali to'lash|onlayn to'lov|telefondan to'lash", "оплата через click|оплата онлайн", "pay online|pay with click"),
    "address": ("!qayerdasiz|!qayerdasizlar|qayerda joylashgansizlar|manzil qayer|zal qayerda joylashgan|qanday borsam bo'ladi",
                "где вы находитесь|где находится зал|ваш адрес|как добраться", "where are you located|where are you|how to get there"),
    "hours": ("zal qachon ochiladi|soat nechada ochilasiz|soat nechagacha ishlaysiz|yakshanba kuni ishlaysizlarmi|dam olish kunlari ochiqmi|shanba kuni ishlaysizmi|bayramda ishlaysizmi",
              "во сколько открывается зал|до скольки работаете|работаете в воскресенье|режим работы", "what time do you open|when do you close|are you open on sunday"),
    "facilities": ("sauna bormi|basseyn bormi|suzish havzasi bormi|parkovka bormi|mashina qo'yish joyi|kiyim almashtirish xonasi|dush bormi|shkaf bormi",
                   "есть ли сауна|есть ли бассейн|есть парковка|раздевалка", "is there a sauna|is there a pool|parking|locker room"),
    "classes": ("yoga bormi|boks bormi|guruh mashg'ulotlari bormi|qanday mashg'ulotlar bor|guruh mashg'ulotlariga yozilish",
                "есть ли йога|есть ли бокс|групповые занятия", "is there yoga|is there boxing|group classes"),
    "st_guest_pass": ("mehmon olib kelsa bo'ladimi|do'stimni olib kelsam bo'ladimi|mehmon olib kelish|bir kunlik kirish",
                      "можно привести друга|гостевой визит|гостевой пропуск", "can i bring a friend|guest pass|bring a guest"),
    "st_gift_certificate": ("abonementni boshqa odamga berish|abonementni sovg'a qilish|sovg'a qilsam bo'ladimi",
                            "подарить абонемент|подарочный сертификат", "gift a membership|gift card"),
    "refund": ("pulni qaytarish mumkinmi|pulimni qaytarib berasizmi|pul qaytariladimi", "можно ли вернуть деньги|возврат денег", "can i get a refund|money back"),
    # ---- losing / gaining weight
    "fat_loss_train": ("!ozish|ozish uchun nima qilish kerak|qanday ozsam bo'ladi|qanday ozaman|ozmoqchiman|vazn tashlamoqchiman|ozishni xohlayman|ozish yo'llari|qanday qilib ozish",
                       "!похудеть|как похудеть|хочу похудеть|как сбросить вес", "how to lose weight|i want to lose weight|lose weight|weight loss"),
    "surplus": ("!semirish|semirish uchun nima yeyish kerak|qanday semiraman|vazn olish|vazn olmoqchiman|semirmoqchiman|ozg'inman qanday semiraman",
                "как набрать вес|хочу набрать вес|набор веса", "how to gain weight|i want to gain weight|gain weight"),
    "muscle_gain_train": ("muskul qanday o'stiraman|mushak massasini oshirish|mushak qanday o'stiriladi|muskul o'stirish|massa yig'ish|qanday qilib mushak o'stiraman",
                          "как накачать мышцы|набрать мышечную массу|как нарастить мышцы", "how to build muscle|build muscle|gain muscle"),
    "abs": ("qorin muskullarini chiqarish|press qanday chiqaraman|press chiqarish|qorin mushaklarini chiqarish|press qilish",
            "как накачать пресс|кубики пресса", "how to get abs|abs workout"),
    "arms": ("qo'l mushaklarini kattalashtirish|qo'lni katta qilish|bitseps o'stirish", "как накачать руки|как накачать бицепс", "how to get bigger arms"),
    # ---- training basics
    "frequency": ("haftada necha marta mashq qilish kerak|haftasiga necha kun mashq|necha kunda bir mashq qilish|har kuni zalga borsa bo'ladimi",
                  "сколько раз в неделю тренироваться|как часто тренироваться", "how often should i train|how many times a week"),
    "running": ("ertalab yugurish foydalimi|yugurish foydasi|yugurish foydalimi|har kuni yugurish|yugurishni qanday boshlash",
                "польза бега|бегать по утрам|утренняя пробежка", "is running good|benefits of running|morning run"),
    "hl_sleep_hours": ("uyqu qancha bo'lishi kerak|qancha uxlash kerak|kam uxlayman|uyqu muhimmi|!uyqu", "сколько спать спортсмену", "how much sleep"),
    "first_gym_day": ("birinchi marta zalga boraman|zalga birinchi marta boraman nima qilay|zalga endi boshladim", "первый раз в зале|первая тренировка", "first time at the gym"),
    "beginner_plan": ("yangi boshlovchi uchun mashq|boshlovchilar uchun mashq|endi boshlayapman qanday mashq", "программа для новичка|тренировки для начинающих",
                      "workout for beginners|beginner workout"),
    "osh_cal": ("osh kaloriyasi|oshning kaloriyasi|palov kaloriyasi", "калорийность плова", "plov calories"),
    "warmup": ("qizdirish mashqlari|qizish mashqlari|mashqdan oldin qizish shartmi", "разминка перед тренировкой", "warm up exercises"),
    # ---- food
    "protein_need": ("oqsil qayerda ko'p|oqsilga boy mahsulotlar|qaysi ovqatda oqsil ko'p|oqsilli ovqatlar|protein qayerda bor",
                     "где много белка|продукты с белком|в чём много белка", "foods high in protein|where to get protein|protein foods"),
    "tdee": ("kaloriya qancha kerak|kuniga necha kaloriya kerak|menga qancha kaloriya kerak|kaloriya me'yori",
             "сколько калорий нужно в день|норма калорий", "how many calories do i need|daily calories"),
    "menu_fat_loss": ("ovqatlanish rejasi|ozish uchun ovqatlanish rejasi|nima yesam ozaman|ratsion tuzib bering",
                      "план питания|рацион для похудения|меню на день", "meal plan|diet plan|what should i eat to lose weight"),
    "non_cal": ("non yesam semiramanmi|non semirtiradimi|non yeyish mumkinmi", "хлеб полнит|можно ли есть хлеб", "does bread make you fat"),
    "late_night": ("kechqurun ovqatlansa bo'ladimi|kechasi ovqat yesam semiramanmi|soat 6 dan keyin ovqat|kechki ovqat zararlimi",
                   "можно ли есть после шести|есть на ночь", "eating late at night|eating after 6pm"),
    "sugar": ("shirinlik yesam bo'ladimi|shirinlik zararlimi|shokolad yesam bo'ladimi", "можно ли сладкое|сладкое на диете", "can i eat sweets"),
    "older_train": ("yoshi kattalar uchun mashq|keksa odam mashq qilsa bo'ladimi|60 yoshda mashq", "тренировки для пожилых", "exercise for older adults"),
}
