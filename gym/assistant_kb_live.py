"""Knowledge base, part 10: answers built live (admin panel hint, "how long to train") and the assistant's own capability summary.
The weather entry (mx_weather, assistant_kb_misc.py) is live too: {weather} is filled from Open-Meteo (gym/assistant_live.py). Row format as in assistant_kb_site.py."""

CAP_UZ = ("Men Fitnes Zal saytining yordamchisiman. Nimalarni bilaman:\n"
          "• Zal: ish vaqti, narxlar, to'lov usullari, manzil, aloqa, muzlatish, sayt bo'limlari qayerda (masalan: \"ish vaqti qanday?\").\n"
          "• Mashq: texnika (squat, tortilish...), rejalar, haftalik tartib, tiklanish, jarohatdan saqlanish (\"squat qanday qilinadi?\").\n"
          "• Ovqatlanish: kaloriya, oqsil, taomlar, parhez (\"osh necha kaloriya?\").\n"
          "• Hisoblagichlar: BMI va kunlik kaloriya, 1RM (\"100 kg 5 marta\"), kg-lb, km-mile, oddiy arifmetika.\n"
          "• Bugungi sana, vaqt va zal joylashgan hududdagi ob-havo (mashq maslahati bilan).\n"
          "• Kirgan bo'lsangiz: abonementingiz, bugungi kaloriyangiz, profilingiz va maqsadingizga mos reja.\n"
          "Chegaralarim: men shifokor yoki murabbiy o'rnini bosmayman, tashxis qo'ymayman, dori va doza aytmayman, siyosat, dasturlash kabi mavzularda javob bermayman. Bilmasam, o'ylab topmayman va murabbiyga Chatda yozishni maslahat beraman.")
CAP_RU = ("Я помощник сайта Fitnes Zal. Что я умею:\n"
          "• Зал: часы работы, цены, способы оплаты, адрес, контакты, заморозка, где что на сайте (например: «какой график работы?»).\n"
          "• Тренировки: техника (присед, подтягивания...), программы, недельный режим, восстановление, профилактика травм («как делать присед?»).\n"
          "• Питание: калории, белок, блюда, диета («сколько калорий в плове?»).\n"
          "• Калькуляторы: ИМТ и дневная норма калорий, 1ПМ («100 кг 5 раз»), кг-фунты, км-мили, простая арифметика.\n"
          "• Сегодняшняя дата, время и погода в районе зала (с советом по тренировке).\n"
          "• Если вы вошли: ваш абонемент, сегодняшние калории, профиль и план под вашу цель.\n"
          "Мои ограничения: я не заменяю врача или тренера, не ставлю диагнозы, не называю лекарства и дозы, не отвечаю на темы вроде политики или программирования. Если не знаю, не выдумываю и советую написать тренеру в Чат.")
CAP_EN = ("I am the Fitnes Zal site assistant. What I can do:\n"
          "• The gym: opening hours, prices, payment methods, address, contacts, freezing, where things are on the site (e.g. \"what are your hours?\").\n"
          "• Training: exercise technique (squat, pull-ups...), programs, weekly structure, recovery, injury prevention (\"how do I squat?\").\n"
          "• Nutrition: calories, protein, dishes, diets (\"how many calories in plov?\").\n"
          "• Calculators: BMI and daily calories, 1RM (\"100 kg 5 reps\"), kg-lb, km-miles, simple arithmetic.\n"
          "• Today's date, the time and the weather around the gym (with a training tip).\n"
          "• If you are signed in: your membership, today's calories, your profile and a plan for your goal.\n"
          "My limits: I do not replace a doctor or a trainer, I do not diagnose, I do not name medicines or doses, and I do not answer topics like politics or programming. If I do not know, I will not make it up and will suggest writing to a trainer in Chat.")


def M(eid, kuz, kru, ken, uz, ru, en, topic="site", links=()):
    return ("mx_" + eid, topic, kuz, kru, ken, uz, ru, en, links)


LIVE = [
    M("admin_panel",
      "admin panelga kirish|admin panelga kir|admin panel qayerda|admin panelga qanday kiraman|admin panelni ochish|admin panel ochish|adminkaga kirish|admin sahifasi|admin paneli qayerda",
      "как зайти в админку|как войти в админ панель|где админ панель|где админка|вход в админку|открыть админ панель|админ панель",
      "how to open admin|how do i open the admin panel|where is the admin panel|admin panel|how to access admin|open admin panel|log in to admin",
      "{admin_help}", "{admin_help}", "{admin_help}", "site", (("nav_dash", "dashboard"), ("nav_profile", "account"))),
    M("train_hours",
      "kuniga necha soat mashq qilishim kerak|kuniga necha soat mashq qilish kerak|necha soat mashq qilish kerak|bir mashg'ulot necha soat|mashq qancha davom etishi kerak|zalda qancha vaqt o'tkazish kerak|kuniga qancha mashq qilish kerak|necha daqiqa mashq qilish kerak|haftasiga necha soat mashq",
      "сколько часов в день тренироваться|сколько часов нужно тренироваться|сколько должна длиться тренировка|сколько времени проводить в зале|сколько минут тренироваться|сколько часов в неделю тренироваться|как долго тренироваться",
      "how many hours a day should i train|how many hours should i train|how long should a workout be|how long should i work out|how long should i train|how much time should i spend in the gym|how many minutes should i exercise|hours per week of exercise",
      "{hours_per_day}", "{hours_per_day}", "{hours_per_day}", "train", (("nav_progress", "progress"), ("tools", "tools"))),
    M("capabilities",
      "sen nimani tushunasan|nimani tushunasan|nimalarni bilasan|nima qila olasan|siz nima qila olasiz|nimani bilasiz|nimaga yordam berasan|sen nimaga qodirsan|imkoniyatlaring qanday|sening imkoniyatlaring",
      "что ты умеешь|что ты можешь|что ты понимаешь|что вы умеете|что ты знаешь|на что ты способен|какие у тебя возможности|чем ты можешь помочь",
      "what can you do|what do you understand|what do you know|what are you able to do|what are your capabilities|what can i ask you|what can you help with|what do you know about",
      CAP_UZ, CAP_RU, CAP_EN, "site"),
]
