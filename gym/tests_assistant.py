"""The offline assistant: knowledge-base matching in three languages, facts from the database, unknown questions, personal answers,
the /assistant/ask/ endpoint (CSRF, rate limit) and the rule-based workout plan."""
import json
from datetime import timedelta

from django.core.cache import cache
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from . import assistant, assistant_kb, assistant_plan, calories
from .models import BodyLog, FoodEntry, GymSettings, Membership, Plan, User, WorkoutPlan

# (question, expected entry id) in Uzbek, Russian and English: site, training, nutrition
CASES = [
    ("Ish vaqti qanday?", "uz", "hours"), ("Какой график работы зала?", "ru", "hours"), ("What time do you open?", "en", "hours"),
    ("Manzilingiz qayerda?", "uz", "address"), ("Какой у вас адрес?", "ru", "address"), ("where is the gym", "en", "address"),
    ("Abonement narxi qancha?", "uz", "prices"), ("Сколько стоит абонемент?", "ru", "prices"), ("how much does a membership cost", "en", "prices"),
    ("Qanday to'lov usullari bor?", "uz", "pay_methods"), ("чем можно оплатить", "ru", "pay_methods"), ("payment methods", "en", "pay_methods"),
    ("muzlatish mumkinmi", "uz", "freeze"), ("заморозить абонемент", "ru", "freeze"), ("can I freeze my membership", "en", "freeze"),
    ("parolni unutdim", "uz", "password_reset"), ("забыл пароль", "ru", "password_reset"), ("forgot password", "en", "password_reset"),
    ("Boshlovchi uchun mashq rejasi", "uz", "beginner_plan"), ("программа для новичка", "ru", "beginner_plan"), ("beginner workout plan", "en", "beginner_plan"),
    ("ozish uchun qanday mashq qilish kerak", "uz", "fat_loss_train"), ("как похудеть тренировками", "ru", "fat_loss_train"), ("workout for fat loss", "en", "fat_loss_train"),
    ("squat qanday qilinadi", "uz", "squat"), ("Как правильно делать присед?", "ru", "squat"), ("how do I squat properly", "en", "squat"),
    ("deadlift texnikasi", "uz", "deadlift"), ("жим лёжа", "ru", "bench_press"), ("how to do push ups", "en", "pushups"),
    ("Kuniga qancha oqsil kerak", "uz", "protein_need"), ("сколько белка нужно в день", "ru", "protein_need"), ("how much protein do I need", "en", "protein_need"),
    ("osh necha kaloriya", "uz", "osh_cal"), ("сколько калорий в плове", "ru", "osh_cal"), ("how many calories in plov", "en", "osh_cal"),
    ("mashqdan keyin nima yeyish kerak", "uz", "post_workout_meal"), ("что есть перед тренировкой", "ru", "pre_workout_meal"), ("what should I eat after training", "en", "post_workout_meal"),
    ("kreatin zararlimi", "uz", "creatine"), ("is creatine safe", "en", "creatine"), ("o'tirib turish texnikasi", "uz", "squat"),
    ("Belim og'riyapti", "uz", "pain_doctor"), ("my knee hurts", "en", "pain_doctor"),
    ("Salom", "uz", "hello"), ("привет", "ru", "hello"), ("rahmat", "uz", "thanks"),
]


# (question, expected entry id) - realistic questions in Uzbek (Latin and Cyrillic), Russian and English across every area of the knowledge base
REGRESSION = [
    # ---- exercise library
    ("front squat qanday qilinadi", "ex_front_squat"), ("фронтальный присед техника", "ex_front_squat"), ("how to do a front squat", "ex_front_squat"),
    ("goblet squat nima", "ex_goblet_squat"), ("кубковый присед для новичков", "ex_goblet_squat"), ("goblet squat form", "ex_goblet_squat"),
    ("bolgar split squat texnikasi", "ex_bulgarian"), ("болгарские выпады как делать", "ex_bulgarian"), ("bulgarian split squat", "ex_bulgarian"),
    ("leg press qanday qilinadi", "ex_hack_leg_press"), ("жим ногами в тренажёре", "ex_hack_leg_press"), ("how to leg press", "ex_hack_leg_press"),
    ("romanian deadlift texnikasi", "ex_rdl"), ("румынская тяга", "ex_rdl"), ("romanian deadlift form", "ex_rdl"),
    ("sumo deadlift", "ex_sumo_dl"), ("становая сумо", "ex_sumo_dl"), ("trap bar deadlift", "ex_trap_bar"),
    ("incline bench press", "ex_incline_bench"), ("жим на наклонной скамье", "ex_incline_bench"), ("qiya skameykada surish", "ex_incline_bench"),
    ("gantel bilan yotib surish", "ex_db_press"), ("жим гантелей лёжа", "ex_db_press"), ("dumbbell bench press", "ex_db_press"),
    ("gantel yoyish", "ex_db_fly"), ("разводка гантелей", "ex_db_fly"), ("dumbbell fly", "ex_db_fly"),
    ("cable crossover", "ex_cable_cross"), ("кроссовер", "ex_cable_cross"),
    ("arnold press", "ex_arnold"), ("жим арнольда", "ex_arnold"),
    ("barbell row qanday", "ex_barbell_row"), ("тяга штанги в наклоне", "ex_barbell_row"), ("how to do a bent over row", "ex_barbell_row"),
    ("one arm dumbbell row", "ex_db_row"), ("тяга гантели одной рукой", "ex_db_row"),
    ("seated cable row", "ex_seated_row"), ("горизонтальная тяга блока", "ex_seated_row"),
    ("chin-up nima", "ex_chinups"), ("подтягивания обратным хватом", "ex_chinups"),
    ("tortila olmayman", "ex_assisted_pull"), ("не могу подтянуться", "ex_assisted_pull"), ("how to get my first pull up", "ex_assisted_pull"),
    ("lat pulldown", "ex_lat_pulldown"), ("тяга верхнего блока", "ex_lat_pulldown"),
    ("dips qanday qilinadi", "ex_dips"), ("отжимания на брусьях", "ex_dips"), ("parallel bar dips", "ex_dips"),
    ("tizzada otjimaniya", "ex_pushup_var"), ("отжимания с колен", "ex_pushup_var"), ("knee push ups", "ex_pushup_var"),
    ("hip thrust", "ex_hip_thrust"), ("ягодичный мостик со штангой", "ex_hip_thrust"),
    ("glute bridge", "ex_glute_bridge"), ("ягодичный мостик", "ex_glute_bridge"),
    ("leg curl", "ex_leg_curl"), ("сгибание ног в тренажёре", "ex_leg_curl"),
    ("leg extension", "ex_leg_ext"), ("разгибание ног сидя", "ex_leg_ext"),
    ("calf raise", "ex_calf_raise"), ("подъём на носки", "ex_calf_raise"), ("boldir mashqi", "ex_calf_raise"),
    ("biceps curl qanday", "ex_biceps_curl"), ("сгибание рук на бицепс", "ex_biceps_curl"),
    ("hammer curl", "ex_hammer_curl"), ("молотковые сгибания", "ex_hammer_curl"),
    ("triceps pushdown", "ex_tri_pushdown"), ("разгибание рук на блоке", "ex_tri_pushdown"),
    ("skullcrusher", "ex_skullcrusher"), ("французский жим лёжа", "ex_skullcrusher"),
    ("lateral raise", "ex_lateral_raise"), ("махи гантелей в стороны", "ex_lateral_raise"),
    ("face pull", "ex_face_pull"), ("тяга к лицу", "ex_face_pull"),
    ("shrugs", "ex_shrugs"), ("шраги", "ex_shrugs"),
    ("side plank", "ex_side_plank"), ("боковая планка", "ex_side_plank"),
    ("crunch qanday qilinadi", "ex_crunch"), ("скручивания на пресс", "ex_crunch"),
    ("hanging leg raise", "ex_leg_raise"), ("подъём ног в висе", "ex_leg_raise"),
    ("ab wheel", "ex_ab_wheel"), ("ролик для пресса", "ex_ab_wheel"),
    ("russian twist", "ex_russian_twist"), ("mountain climber", "ex_mountain_climber"),
    ("burpee qanday", "ex_burpee"), ("как делать бёрпи", "ex_burpee"), ("how to do a burpee", "ex_burpee"),
    ("kettlebell swing", "ex_kb_swing"), ("махи гирей", "ex_kb_swing"),
    ("farmer carry", "ex_farmer_carry"), ("box jump", "ex_box_jump"), ("прыжки на тумбу", "ex_box_jump"),
    ("yugurish texnikasi", "ex_run_tech"), ("техника бега", "ex_run_tech"), ("running technique", "ex_run_tech"),
    ("rowing machine", "ex_rowing_machine"), ("гребной тренажёр", "ex_rowing_machine"),
    ("velotrenajyor", "ex_cycling"), ("велотренажёр", "ex_cycling"),
    ("suzish foydasi", "ex_swimming"), ("плавание для похудения", "ex_swimming"),
    ("jump rope", "ex_jump_rope"), ("скакалка", "ex_jump_rope"), ("arqon sakrash", "ex_jump_rope"),
    ("hamstring stretch", "ex_stretch_hamstring"), ("hip flexor stretch", "ex_stretch_quad_hip"),
    ("cat cow", "ex_cat_cow"), ("yoga boshlovchi uchun", "ex_yoga_basics"), ("йога для начинающих", "ex_yoga_basics"),
    ("wall sit", "ex_wall_sit"), ("bird dog", "ex_bird_dog"), ("dead bug", "ex_dead_bug"),
    ("giperekstenziya", "ex_back_extension"), ("гиперэкстензия", "ex_back_extension"),
    ("squat xatolari", "ex_squat_mistakes"), ("ошибки в приседе", "ex_squat_mistakes"),
    ("bench press xatolari", "ex_bench_mistakes"), ("deadlift xatolari", "ex_deadlift_mistakes"), ("ошибки в становой", "ex_deadlift_mistakes"),
    ("yugurish yo'lakchasi", "ex_cardio_machines"), ("беговая дорожка", "ex_cardio_machines"), ("how to use a treadmill", "ex_cardio_machines"),
    # ---- programming and body parts
    ("rpe nima", "pg_rpe"), ("what is rpe", "pg_rpe"), ("rir nima", "pg_rir"), ("что такое rir", "pg_rir"),
    ("superset nima", "pg_superset"), ("drop set", "pg_dropset"), ("periodizatsiya", "pg_periodization"), ("периодизация", "pg_periodization"),
    ("full body workout", "pg_fullbody"), ("тренировка на всё тело", "pg_fullbody"), ("push pull legs", "pg_ppl"), ("upper lower split", "pg_upper_lower"),
    ("haftasiga 2 kun mashq", "pg_two_days"), ("two days a week workout", "pg_two_days"),
    ("tabata", "pg_hiit_protocols"), ("табата", "pg_hiit_protocols"), ("zona 2 kardio", "pg_zone2"), ("zone 2 cardio", "pg_zone2"),
    ("recomp nima", "pg_recomp"), ("рекомпозиция тела", "pg_recomp"), ("bulking and cutting", "pg_bulk_cut"),
    ("ozg'in odam massa olish", "pg_skinny"), ("эктоморф хочет массу", "pg_skinny"), ("hardgainer", "pg_skinny"),
    ("boshlovchilar xatolari", "pg_beginner_mistakes"), ("ошибки новичков", "pg_beginner_mistakes"),
    ("mashq kundaligi", "pg_workout_log"), ("workout log", "pg_workout_log"),
    ("lifting belt", "pg_belt_straps"), ("атлетический пояс", "pg_belt_straps"),
    ("qaysi mashq birinchi", "pg_order_exercises"), ("order of exercises", "pg_order_exercises"),
    ("ko'krak mushaklarini katta qilish", "pg_bp_chest"), ("как накачать грудь", "pg_bp_chest"), ("how to build chest", "pg_bp_chest"),
    ("keng orqa", "pg_bp_back"), ("как накачать спину", "pg_bp_back"), ("how to build a bigger back", "pg_bp_back"),
    ("yelka mushaklarini o'stirish", "pg_bp_shoulders"), ("широкие плечи", "pg_bp_shoulders"),
    ("dumbani qanday katta qilaman", "pg_bp_glutes"), ("как накачать ягодицы", "pg_bp_glutes"), ("how to grow glutes", "pg_bp_glutes"),
    ("qorin kubiklari qanday paydo bo'ladi", "pg_bp_abs_six"), ("как сделать кубики на прессе", "pg_bp_abs_six"), ("how to get a six pack", "pg_bp_abs_six"),
    ("qorin yog'ini qanday yo'qotaman", "pg_bp_belly_fat"), ("как убрать жир с живота", "pg_bp_belly_fat"), ("how to lose belly fat", "pg_bp_belly_fat"),
    ("kor nima", "pg_bp_core"), ("что такое кор", "pg_bp_core"), ("v shakl tana", "pg_bp_vtaper"),
    ("ayollar uchun tarang tana", "pg_bp_women_toning"), ("как подтянуть тело", "pg_bp_women_toning"),
    # ---- health, recovery, mindset
    ("necha soat uxlash kerak", "hl_sleep_hours"), ("сколько нужно спать", "hl_sleep_hours"), ("how many hours of sleep do i need", "hl_sleep_hours"),
    ("uxlay olmayapman", "hl_sleep_tips"), ("не могу уснуть", "hl_sleep_tips"), ("trouble sleeping", "hl_sleep_tips"),
    ("stress va mashq", "hl_stress"), ("как снять стресс", "hl_stress"),
    ("tizza og'rig'i", "hl_knee_pain"), ("болят колени при приседе", "hl_knee_pain"), ("knee pain", "hl_knee_pain"),
    ("bel og'rig'i mashq", "hl_back_pain"), ("боль в пояснице упражнения", "hl_back_pain"), ("lower back pain exercises", "hl_back_pain"),
    ("yelka og'rig'i", "hl_shoulder_pain"), ("боль в плече", "hl_shoulder_pain"), ("shoulder pain", "hl_shoulder_pain"),
    ("bilak og'rig'i", "hl_wrist_pain"), ("sprained ankle", "hl_ankle_sprain"), ("подвернул ногу", "hl_ankle_sprain"),
    ("mushak tortishishi", "hl_cramps"), ("судороги", "hl_cramps"), ("muscle cramps", "hl_cramps"),
    ("foam roller", "hl_foam_roll_massage"), ("сауна после тренировки", "hl_sauna_cold"),
    ("suvsizlanish belgilari", "hl_hydration_signs"), ("признаки обезвоживания", "hl_hydration_signs"),
    ("issiqda mashq", "hl_hot_weather"), ("тренировка в жару", "hl_hot_weather"),
    ("chekish va sport", "hl_smoking"), ("курение и спорт", "hl_smoking"),
    ("qon bosimi baland", "hl_high_bp"), ("высокое давление и тренировки", "hl_high_bp"), ("high blood pressure and exercise", "hl_high_bp"),
    ("diabet va mashq", "hl_diabetes_ex"), ("диабет и тренировки", "hl_diabetes_ex"),
    ("yurak kasalligi va mashq", "hl_heart_condition"), ("боль в груди при тренировке", "hl_heart_condition"), ("chest pain during workout", "hl_heart_condition"),
    ("astma va mashq", "hl_asthma"), ("ortiqcha vazn bilan boshlash", "hl_obesity_start"), ("начать тренироваться с лишним весом", "hl_obesity_start"),
    ("osteoporoz", "hl_osteoporosis"), ("остеопороз", "hl_osteoporosis"),
    ("puls me'yori", "hl_heart_rate"), ("максимальный пульс", "hl_heart_rate"), ("max heart rate", "hl_heart_rate"),
    ("tug'ruqdan keyin mashq", "hl_pregnancy_post"), ("тренировки после родов", "hl_pregnancy_post"),
    ("hayz paytida mashq", "hl_cycle"), ("тренировки в месячные", "hl_cycle"), ("workout on period", "hl_cycle"),
    ("menopauza va mashq", "hl_menopause"), ("40 yoshdan keyin mashq", "hl_age_40_plus"), ("тренировки после 40", "hl_age_40_plus"),
    ("working out after 40", "hl_age_40_plus"),
    ("60 yoshdan keyin mashq", "hl_age_60_plus"), ("exercise over 60", "hl_age_60_plus"),
    ("o'smir va og'irlik ko'tarish", "hl_teen_safety"), ("kasallikdan keyin qaytish", "hl_illness_return"), ("как вернуться после перерыва", "hl_illness_return"),
    ("tez yordam", "hl_emergency"), ("вызвать скорую", "hl_emergency"),
    ("steroidlar", "hl_steroids"), ("стероиды", "hl_steroids"), ("anabolic steroids", "hl_steroids"), ("steroid dozasi", "hl_steroids"),
    ("fat burner", "hl_fat_burners"), ("жиросжигатели", "hl_fat_burners"),
    ("odat shakllantirish", "hl_habits"), ("как выработать привычку тренироваться", "hl_habits"), ("how to stay consistent", "hl_habits"),
    ("maqsad qo'yish", "hl_goal_setting"), ("постановка целей", "hl_goal_setting"),
    ("progressni qanday kuzataman", "hl_track_progress"), ("фото прогресса", "hl_track_progress"), ("progress photos", "hl_track_progress"),
    ("vazn tez o'zgaradi", "hl_scale_fluctuation"), ("вес скачет", "hl_scale_fluctuation"), ("scale jumps", "hl_scale_fluctuation"),
    ("tanamdan norozi bo'lish", "hl_body_image"), ("mashqni o'tkazib yubordim", "hl_missed_workouts"), ("пропустил тренировку", "hl_missed_workouts"),
    ("zaldan uyalish", "hl_gym_anxiety"), ("стесняюсь идти в зал", "hl_gym_anxiety"), ("gym anxiety", "hl_gym_anxiety"),
    ("qancha vaqtda ko'rinadi", "hl_patience_timeline"), ("how long until i see results", "hl_patience_timeline"),
    ("mashq qilsam ham ozmayapman", "hl_diet_vs_exercise"), ("why am i not losing weight", "hl_diet_vs_exercise"), ("тренируюсь но не худею", "hl_diet_vs_exercise"),
    # ---- nutrition
    ("ozish uchun makrolar", "nu_macros_fat_loss"), ("бжу для похудения", "nu_macros_fat_loss"), ("macros for fat loss", "nu_macros_fat_loss"),
    ("massa uchun makrolar", "nu_macros_muscle"), ("macros for muscle gain", "nu_macros_muscle"),
    ("kaloriyani qanday sanayman", "nu_count_calories"), ("как считать калории", "nu_count_calories"), ("how to count calories", "nu_count_calories"),
    ("tovuq ko'kragi", "nu_chicken"), ("куриная грудка", "nu_chicken"), ("chicken breast", "nu_chicken"),
    ("guruch kaloriyasi", "nu_rice_cal"), ("калории риса", "nu_rice_cal"), ("rice calories", "nu_rice_cal"),
    ("suli bo'tqasi", "nu_oats"), ("овсянка", "nu_oats"), ("oatmeal", "nu_oats"),
    ("banan kaloriyasi", "nu_banana_apple"), ("mosh loviya no'xat", "nu_legumes"), ("бобовые польза", "nu_legumes"),
    ("arzon menyu bir hafta", "nu_budget_menu"), ("бюджетное меню на неделю", "nu_budget_menu"), ("budget meal plan", "nu_budget_menu"),
    ("meal prep", "nu_meal_prep"), ("iftorlik menyu", "nu_ramadan_iftar"), ("что есть на сухур", "nu_ramadan_iftar"),
    ("16/8 intervalli ochlik", "nu_if_16_8"), ("интервальное голодание 16/8", "nu_if_16_8"),
    ("keto dieta", "nu_keto"), ("кето диета", "nu_keto"), ("keto diet", "nu_keto"),
    ("vegan sportchi", "nu_vegan_gym"), ("tuz me'yori", "nu_salt"), ("норма соли", "nu_salt"),
    ("d vitamini", "nu_vitamin_d"), ("витамин д", "nu_vitamin_d"), ("vitamin d", "nu_vitamin_d"),
    ("temir yetishmasligi", "nu_iron"), ("железо дефицит", "nu_iron"), ("magniy", "nu_magnesium"), ("магний", "nu_magnesium"),
    ("omega-3", "nu_omega3_b12"), ("рыбий жир", "nu_omega3_b12"), ("bcaa kerakmi", "nu_bcaa"), ("bcaa нужны ли", "nu_bcaa"),
    ("pre workout", "nu_preworkout_supp"), ("предтреник", "nu_preworkout_supp"), ("mass gainer", "nu_mass_gainer"), ("гейнер", "nu_mass_gainer"),
    ("kollagen", "nu_collagen_joint"), ("etiketka o'qish", "nu_read_labels"), ("как читать этикетки", "nu_read_labels"), ("nutrition label", "nu_read_labels"),
    ("dietik osh", "nu_plov_light"), ("лёгкий плов", "nu_plov_light"), ("chuchvara kaloriyasi", "nu_chuchvara_norin"),
    ("pitsa kaloriyasi", "nu_pizza_burger"), ("калории пиццы", "nu_pizza_burger"), ("pizza calories", "nu_pizza_burger"),
    ("shirinlikka ishtiyoq", "nu_sweets_craving"), ("тяга к сладкому", "nu_sweets_craving"), ("sugar cravings", "nu_sweets_craving"),
    ("stress bilan yeyish", "nu_emotional_eating"), ("эмоциональное переедание", "nu_emotional_eating"),
    ("qorin dam bo'lishi", "nu_bloating_digestion"), ("вздутие живота", "nu_bloating_digestion"), ("bloating", "nu_bloating_digestion"),
    ("detoks", "nu_detox_myth"), ("детокс", "nu_detox_myth"), ("glikemik indeks", "nu_glycemic"), ("гликемический индекс", "nu_glycemic"),
    ("anabolik oyna", "nu_anabolic_window"), ("анаболическое окно", "nu_anabolic_window"),
    ("energetik ichimlik", "nu_energy_drinks"), ("энергетики вред", "nu_energy_drinks"), ("are energy drinks bad", "nu_energy_drinks"),
    ("restoranda nima buyurtma qilish", "nu_eating_out"), ("что заказать в ресторане", "nu_eating_out"),
    # ---- site
    ("sms kod kelmayapti", "st_login_code"), ("код не приходит", "st_login_code"), ("code not arriving", "st_login_code"),
    ("google bilan kirish", "st_login_google_apple"), ("вход через google", "st_login_google_apple"),
    ("boshqa qurilmalardan chiqish", "st_logout_others"), ("telefon raqamni o'zgartirish", "st_change_contact"), ("сменить номер телефона", "st_change_contact"),
    ("change my password", "st_change_contact"),
    ("akkauntni o'chirish", "st_delete_account"), ("удалить аккаунт", "st_delete_account"), ("delete my account", "st_delete_account"),
    ("kvitansiya", "st_receipt"), ("квитанция об оплате", "st_receipt"), ("payment receipt", "st_receipt"),
    ("to'lov qildim lekin abonement yo'q", "st_pay_done_report"), ("оплатил но абонемента нет", "st_pay_done_report"),
    ("i paid but no membership", "st_pay_done_report"),
    ("abonementni uzaytirish", "st_renew"), ("продлить абонемент", "st_renew"), ("renew membership", "st_renew"),
    ("qaysi abonementni tanlash kerak", "st_plan_choose"), ("какой абонемент выбрать", "st_plan_choose"),
    ("sinov mashg'uloti", "st_trial_visit"), ("пробное занятие", "st_trial_visit"), ("free trial", "st_trial_visit"),
    ("talabalar uchun chegirma", "st_student_discount"), ("скидка студентам", "st_student_discount"),
    ("parkovka", "st_lockers_parking"), ("есть ли шкафчики", "st_lockers_parking"), ("where to park", "st_lockers_parking"),
    ("darsga qanday yozilaman", "st_book_class_how"), ("как записаться на занятие", "st_book_class_how"), ("how to book a class", "st_book_class_how"),
    ("qaysi murabbiy yaxshi", "st_pick_trainer"), ("как выбрать тренера", "st_pick_trainer"), ("how to choose a trainer", "st_pick_trainer"),
    ("shaxsiy mashg'ulotni bekor qilish", "st_pt_cancel"), ("men murabbiyman", "st_i_am_trainer"),
    ("do'konda nima sotiladi", "st_shop_items"), ("что продаётся в магазине", "st_shop_items"),
    ("buyurtma berish qadamlari", "st_cart_checkout"), ("как оформить заказ", "st_cart_checkout"), ("how to place an order", "st_cart_checkout"),
    ("buyurtmani bekor qilish", "st_order_cancel_return"), ("отменить заказ", "st_order_cancel_return"),
    ("o'z ovqatimni qo'shish", "st_custom_food"), ("добавить своё блюдо", "st_custom_food"), ("add my own food", "st_custom_food"),
    ("matn bilan ovqat qo'shish", "st_calorie_text_entry"), ("ovqatni o'chirish", "st_calorie_delete"),
    ("tayyor dasturni boshlash", "st_start_program"), ("vazn qo'shish", "st_progress_add"), ("добавить вес", "st_progress_add"),
    ("shaxsiy rekord qo'shish", "st_pr_log"), ("sharh yozish", "st_review_write"),
    ("shikoyat qilish qayerga", "st_complaint"), ("куда жаловаться", "st_complaint"), ("make a complaint", "st_complaint"),
    ("xabarni o'chirish chatda", "st_chat_block_delete"), ("internetsiz ishlaydimi", "st_offline_pwa"), ("telefonga o'rnatish", "st_offline_pwa"),
    ("tilni qanday o'zgartiraman", "st_language_switch"), ("как сменить язык", "st_language_switch"),
    ("ma'lumotlarim xavfsizmi", "st_data_privacy_safe"),
    # ---- small talk / myths / quick answers
    ("hazil ayt", "mx_joke"), ("расскажи шутку", "mx_joke"), ("tell me a joke", "mx_joke"),
    ("seni kim yaratgan", "mx_made_by"), ("кто тебя создал", "mx_made_by"), ("who made you", "mx_made_by"),
    ("xayrli tun", "mx_goodnight"), ("спокойной ночи", "mx_goodnight"), ("good night", "mx_goodnight"),
    ("yog' mushakka aylanadimi", "mx_myth_fat_muscle"), ("жир превращается в мышцы", "mx_myth_fat_muscle"),
    ("ko'p terlash yog' yoqadimi", "mx_myth_sweat"), ("does sweating burn fat", "mx_myth_sweat"),
    ("ayollar katta mushak bo'lib ketadimi", "mx_myth_women_bulky"), ("will lifting make women bulky", "mx_myth_women_bulky"),
    ("protein buyrakka zararlimi", "mx_myth_protein_kidney"), ("белок вреден для почек", "mx_myth_protein_kidney"),
    ("is protein bad for kidneys", "mx_myth_protein_kidney"),
    ("kardio mushakni yeydimi", "mx_myth_cardio_muscle"), ("kech emasmi boshlash uchun", "mx_myth_age_start"), ("is it too late to start", "mx_myth_age_start"),
    ("mashqdan oldin cho'zilish kerakmi", "mx_myth_stretch_before"),
    ("zalga nima kiyish kerak", "mx_q_gym_clothes"), ("что надеть в зал", "mx_q_gym_clothes"), ("what to wear to the gym", "mx_q_gym_clothes"),
    ("spotter nima", "mx_q_spotter"), ("что такое страхующий", "mx_q_spotter"),
    ("kreatin dozasi qancha", "mx_q_mass_water_creatine"), ("креатин дозировка", "mx_q_mass_water_creatine"),
    ("creatine dose", "mx_q_mass_water_creatine"),
    ("tez ozish", "qa_lose_weight_fast"), ("быстро похудеть", "qa_lose_weight_fast"), ("lose weight fast", "qa_lose_weight_fast"),
    ("och qoringa mashq", "qa_empty_stomach_gym"), ("тренировка на голодный желудок", "qa_empty_stomach_gym"),
    ("kuniga ikki marta mashq", "qa_two_workouts_day"), ("две тренировки в день", "qa_two_workouts_day"),
    ("sut kislotasi", "qa_lactic_acid"), ("молочная кислота", "qa_lactic_acid"), ("лактат", "qa_lactic_acid"),
    ("somatotip", "qa_body_type"), ("типы телосложения", "qa_body_type"),
    # ---- Uzbek written in Cyrillic
    ("оқсил қанча керак", "protein_need"), ("иш вақти қандай", "hours"), ("абонемент нархи қанча", "prices"), ("манзилингиз қаерда", "address"),
    ("ўтириб туриш техникаси", "squat"), ("креатин зарарлими", "creatine"), ("белим оғрияпти", "pain_doctor"),
    ("қорин ёғини қандай йўқотаман", "pg_bp_belly_fat"), ("ҳафтасига 2 кун машқ", "pg_two_days"), ("кунига неча қадам", "steps"),
    # ---- typos
    ("protien qancha kerak", "protein_need"), ("kreatin zararlimi", "creatine"), ("abonemet narxi", "prices"),
    ("how much protien do i need", "protein_need"), ("dedlift texnikasi", "deadlift"), ("kaloria hisoblash usuli", "nu_count_calories"),
]


# Added with the knowledge base growth (900+ entries): ex2 machines/cable/bodyweight/stretching, sport and rehab, nutrition deep dive, myths,
# beginners' Q&A, equipment, glossary, site features and small talk. (question, expected entry id), Uzbek (Latin and Cyrillic), Russian, English.
REGRESSION2 = [
    ('chest press mashinasi qanday ishlatiladi', 'ex_chest_press_machine'), ('жим от груди в тренажёре как делать', 'ex_chest_press_machine'), ('how to use the machine chest press', 'ex_chest_press_machine'),
    ('pec deck nima uchun', 'ex_pec_deck'), ('бабочка тренажёр техника', 'ex_pec_deck'), ('how to use the pec deck', 'ex_pec_deck'),
    ('yelka press trenajyori', 'ex_shoulder_press_machine'), ('жим плеч в тренажёре', 'ex_shoulder_press_machine'), ('shoulder press machine setup', 'ex_shoulder_press_machine'),
    ('hack squat trenajyori', 'ex_hack_squat'), ('гакк присед', 'ex_hack_squat'), ('what is a hack squat machine', 'ex_hack_squat'),
    ('smith mashinasi bilan skvat', 'ex_smith_machine'), ('присед в смите', 'ex_smith_machine'), ('smith machine squat safe', 'ex_smith_machine'),
    ('abduktor trenajyori', 'ex_hip_abduction_adduction'), ('разведение ног в тренажёре', 'ex_hip_abduction_adduction'), ('inner thigh machine', 'ex_hip_abduction_adduction'),
    ('preacher curl qanday', 'ex_preacher_curl'), ('сгибания на скамье скотта', 'ex_preacher_curl'), ('scott curl', 'ex_preacher_curl'),
    ("o'tirib boldir ko'tarish", 'ex_seated_calf'), ('икры сидя', 'ex_seated_calf'), ('soleus exercise', 'ex_seated_calf'),
    ('tor tutim tortish', 'ex_lat_pulldown_close'), ('тяга узким хватом', 'ex_lat_pulldown_close'), ('v-bar pulldown', 'ex_lat_pulldown_close'),
    ('reverse pec deck', 'ex_reverse_pec_machine'), ('обратная бабочка', 'ex_reverse_pec_machine'), ('gravitron', 'ex_assisted_dip_machine'),
    ('гравитрон', 'ex_assisted_dip_machine'), ('assisted dip machine', 'ex_assisted_dip_machine'), ('leg pressda oyoq joylashuvi', 'ex_leg_press_foot'),
    ('положение ног в жиме ногами', 'ex_leg_press_foot'), ('leg press foot placement', 'ex_leg_press_foot'), ('landmine press', 'ex_landmine_press'),
    ('лэндмайн жим', 'ex_landmine_press'), ('tor tutim bilan yotib surish', 'ex_close_grip_bench'), ('жим узким хватом', 'ex_close_grip_bench'),
    ('close grip bench press', 'ex_close_grip_bench'), ('floor press', 'ex_floor_press_decline'), ('decline bench', 'ex_floor_press_decline'),
    ('жим с пола', 'ex_floor_press_decline'), ('push press va thruster', 'ex_push_press_thruster'), ('трастер', 'ex_push_press_thruster'),
    ('what is a thruster', 'ex_push_press_thruster'), ('power clean', 'ex_power_clean_basics'), ('олимпийские упражнения', 'ex_power_clean_basics'),
    ('sled push', 'ex_sled_push'), ('толкание саней', 'ex_sled_push'), ('battle rope mashqi', 'ex_battle_ropes'),
    ('боевые канаты', 'ex_battle_ropes'), ('battle ropes workout', 'ex_battle_ropes'), ('medbol bilan mashq', 'ex_medicine_ball'),
    ('медбол упражнения', 'ex_medicine_ball'), ('medicine ball slam', 'ex_medicine_ball'), ('TRX mashqlari', 'ex_trx_suspension'),
    ('TRX петли', 'ex_trx_suspension'), ('trx workout', 'ex_trx_suspension'), ('rezina lenta bilan mashq', 'ex_resistance_bands'),
    ('резинки для фитнеса', 'ex_resistance_bands'), ('resistance bands workout', 'ex_resistance_bands'), ('kabel trenajyori nima', 'ex_cable_curl_pushdown_basics'),
    ('блочный тренажёр', 'ex_cable_curl_pushdown_basics'), ("kabelda yon ko'tarish", 'ex_cable_lateral_raise'), ('махи в сторону на блоке', 'ex_cable_lateral_raise'),
    ('cable lateral raise', 'ex_cable_lateral_raise'), ('pallof press', 'ex_woodchop_pallof'), ('паллоф пресс', 'ex_woodchop_pallof'),
    ('cable woodchop', 'ex_woodchop_pallof'), ('cable kickback', 'ex_cable_kickback_glute'), ('отведение ноги на блоке', 'ex_cable_kickback_glute'),
    ('straight arm pulldown', 'ex_straight_arm_pulldown'), ('пулловер на блоке', 'ex_straight_arm_pulldown'), ('cable crunch', 'ex_cable_crunch_fly'),
    ('скручивания на блоке', 'ex_cable_crunch_fly'), ('turkish get-up', 'ex_turkish_get_up'), ('турецкий подъём', 'ex_turkish_get_up'),
    ('what is the turkish get up', 'ex_turkish_get_up'), ('girya clean va press', 'ex_kb_clean_press'), ('взятие гири на грудь', 'ex_kb_clean_press'),
    ('kettlebell clean', 'ex_kb_clean_press'), ('girya snatch', 'ex_kb_snatch_windmill'), ('рывок гири', 'ex_kb_snatch_windmill'),
    ('girya vazni qancha tanlash', 'ex_kb_weight_choose'), ('какую гирю выбрать', 'ex_kb_weight_choose'), ('what kettlebell weight for beginners', 'ex_kb_weight_choose'),
    ('girya bilan uy mashqi', 'ex_kb_circuit_home'), ('тренировка с гирей дома', 'ex_kb_circuit_home'), ('kettlebell home workout', 'ex_kb_circuit_home'),
    ('otjimaniya qilolmayman', 'ex_pushup_progression'), ('не могу отжаться', 'ex_pushup_progression'), ('push up progression', 'ex_pushup_progression'),
    ('программа подтягиваний', 'ex_pullup_progression'), ('pull up progression', 'ex_pullup_progression'), ("bir oyoqda o'tirish pistol", 'ex_squat_progression_pistol'),
    ('пистолетик', 'ex_squat_progression_pistol'), ('pistol squat', 'ex_squat_progression_pistol'), ('inverted row', 'ex_inverted_row'),
    ('австралийские подтягивания', 'ex_inverted_row'), ("qo'lda turish o'rganish", 'ex_handstand_progression'), ('стойка на руках как научиться', 'ex_handstand_progression'),
    ('how to learn a handstand', 'ex_handstand_progression'), ('pike otjimaniya', 'ex_hspu_progression'), ('пайк отжимания', 'ex_hspu_progression'),
    ('plank qiyinlashtirish', 'ex_plank_progression'), ('варианты планки', 'ex_plank_progression'), ('harder plank variations', 'ex_plank_progression'),
    ('hollow hold', 'ex_hollow_hold_l_sit'), ('l-sit', 'ex_hollow_hold_l_sit'), ('nordic curl', 'ex_nordic_curl'),
    ('нордический сгиб', 'ex_nordic_curl'), ('dead hang foydasi', 'ex_hanging_progression'), ('вис на перекладине польза', 'ex_hanging_progression'),
    ('benefits of dead hang', 'ex_hanging_progression'), ('lunge bosqichlari', 'ex_lunge_progression'), ('выпады назад', 'ex_lunge_progression'),
    ('reverse lunge', 'ex_lunge_progression'), ('hip hinge nima', 'ex_hip_hinge_learn'), ('тазовый шарнир', 'ex_hip_hinge_learn'),
    ('how to learn the hip hinge', 'ex_hip_hinge_learn'), ('muscle-up', 'ex_muscle_up'), ('выход силой', 'ex_muscle_up'),
    ('how to do a muscle up', 'ex_muscle_up'), ('front lever', 'ex_front_lever'), ('фронтлевер', 'ex_front_lever'),
    ('human flag', 'ex_planche_human_flag'), ('человеческий флаг', 'ex_planche_human_flag'), ('dragon flag', 'ex_dragon_flag_one_arm'),
    ('драгон флаг', 'ex_dragon_flag_one_arm'), ('kalistenika boshlovchi', 'ex_calisthenics_beginner'), ('калистеника для новичков', 'ex_calisthenics_beginner'),
    ('calisthenics for beginners', 'ex_calisthenics_beginner'), ("bo'yin cho'zilishi", 'ex_stretch_neck'), ('растяжка шеи', 'ex_stretch_neck'),
    ('neck stretch', 'ex_stretch_neck'), ("yuqori orqa cho'zish", 'ex_stretch_upper_back'), ('растяжка верха спины', 'ex_stretch_upper_back'),
    ('upper back stretch', 'ex_stretch_upper_back'), ("bel cho'zish mashqi", 'ex_stretch_lower_back'), ('растяжка поясницы', 'ex_stretch_lower_back'),
    ('lower back stretch', 'ex_stretch_lower_back'), ("kaptar holati cho'zilish", 'ex_stretch_hips_glutes'), ('поза голубя', 'ex_stretch_hips_glutes'),
    ('pigeon pose', 'ex_stretch_hips_glutes'), ("boldir cho'zish", 'ex_stretch_calves_ankles'), ('растяжка икр', 'ex_stretch_calves_ankles'),
    ('calf stretch', 'ex_stretch_calves_ankles'), ("ichki son cho'zish", 'ex_stretch_adductors_groin'), ('растяжка внутренней поверхности бедра', 'ex_stretch_adductors_groin'),
    ('groin stretch', 'ex_stretch_adductors_groin'), ("bilak cho'zish", 'ex_stretch_wrists_forearms'), ('растяжка запястий', 'ex_stretch_wrists_forearms'),
    ('wrist stretch', 'ex_stretch_wrists_forearms'), ("butun tana cho'zilish tartibi", 'ex_stretch_full_body_routine'), ('растяжка всего тела комплекс', 'ex_stretch_full_body_routine'),
    ('full body stretching routine', 'ex_stretch_full_body_routine'), ("ofisda cho'zilish", 'ex_stretch_desk_office'), ('растяжка в офисе', 'ex_stretch_desk_office'),
    ('desk stretches', 'ex_stretch_desk_office'), ("shpagat qanday o'tirish", 'ex_pigeon_splits_flexibility'), ('как сесть на шпагат', 'ex_pigeon_splits_flexibility'),
    ('how to do the splits', 'ex_pigeon_splits_flexibility'), ('dinamik isitish', 'ex_dynamic_warmup_routine'), ('динамическая разминка', 'ex_dynamic_warmup_routine'),
    ('dynamic warm up routine', 'ex_dynamic_warmup_routine'), ('band pull apart', 'ex_band_pull_apart_face'), ('agility ladder', 'ex_agility_ladder'),
    ('координационная лестница', 'ex_agility_ladder'), ('pliometrika boshlovchi', 'ex_plyometrics_beginner'), ('плиометрика для новичков', 'ex_plyometrics_beginner'),
    ('suitcase carry', 'ex_zercher_front_rack_carry'), ('futbolchi uchun jismoniy tayyorgarlik', 'sp_football_conditioning'), ('физподготовка футболиста', 'sp_football_conditioning'),
    ('football conditioning', 'sp_football_conditioning'), ('fifa 11+ isinish', 'sp_football_injury_prevention'), ('профилактика травм в футболе', 'sp_football_injury_prevention'),
    ('football injury prevention', 'sp_football_injury_prevention'), ('boks uchun jismoniy tayyorgarlik', 'sp_boxing_conditioning'), ('тренировки боксёра', 'sp_boxing_conditioning'),
    ('boxing workout', 'sp_boxing_conditioning'), ('boksda vazn tushirish', 'sp_boxing_weight_cut'), ('сгонка веса бокс', 'sp_boxing_weight_cut'),
    ('cutting weight for a fight', 'sp_boxing_weight_cut'), ('kurash uchun kuch mashqlari', 'sp_wrestling_kurash_strength'), ('тренировки для борьбы', 'sp_wrestling_kurash_strength'),
    ('mma conditioning', 'sp_wrestling_kurash_strength'), ("jang san'ati uchun mashq", 'sp_martial_arts_general'), ('физподготовка карате', 'sp_martial_arts_general'),
    ('5 km yugurish rejasi', 'sp_couch_to_5k'), ('план бега на 5 км', 'sp_couch_to_5k'), ('couch to 5k', 'sp_couch_to_5k'),
    ('10 km yugurish rejasi', 'sp_running_10k_plan'), ('план на 10 км', 'sp_running_10k_plan'), ('10k training plan', 'sp_running_10k_plan'),
    ('yarim marafon tayyorgarlik', 'sp_half_marathon_marathon'), ('подготовка к полумарафону', 'sp_half_marathon_marathon'), ('marathon training plan', 'sp_half_marathon_marathon'),
    ('interval yugurish', 'sp_run_intervals_tempo'), ('темповый бег', 'sp_run_intervals_tempo'), ('tempo run', 'sp_run_intervals_tempo'),
    ('yugurish poyabzali tanlash', 'sp_running_shoes_surface'), ('кроссовки для бега', 'sp_running_shoes_surface'), ('how to choose running shoes', 'sp_running_shoes_surface'),
    ("yugurganda tizza og'rishi", 'sp_running_knee_shin_prevent'), ('болят колени при беге', 'sp_running_knee_shin_prevent'), ("runner's knee", 'sp_running_knee_shin_prevent'),
    ('12-3-30', 'sp_treadmill_incline_walk'), ('incline treadmill walking', 'sp_treadmill_incline_walk'), ("suzishni o'rganish", 'sp_swimming_technique_beginner'),
    ('как научиться плавать', 'sp_swimming_technique_beginner'), ('learn to swim', 'sp_swimming_technique_beginner'), ('план тренировки в бассейне', 'sp_swimming_workout_plan'),
    ('pool workout plan', 'sp_swimming_workout_plan'), ('velosiped bilan ozish', 'sp_cycling_road_gym'), ('велотренировки', 'sp_cycling_road_gym'),
    ('sakrash balandligini oshirish', 'sp_basketball_volleyball_jump'), ('как прыгать выше', 'sp_basketball_volleyball_jump'), ('increase vertical jump', 'sp_basketball_volleyball_jump'),
    ('tennis uchun fizika', 'sp_tennis_badminton_conditioning'), ('бадминтон тренировки', 'sp_tennis_badminton_conditioning'), ('toshga chiqish uchun mashq', 'sp_climbing_basics'),
    ('скалолазание тренировки', 'sp_climbing_basics'), ('bouldering fitness', 'sp_climbing_basics'), ("tog'ga chiqishga tayyorgarlik", 'sp_hiking_trekking_prep'),
    ('подготовка к походу в горы', 'sp_hiking_trekking_prep'), ('hiking fitness prep', 'sp_hiking_trekking_prep'), ('crossfit nima', 'sp_crossfit_style_wod'),
    ('что такое кроссфит', 'sp_crossfit_style_wod'), ('what is crossfit', 'sp_crossfit_style_wod'), ('musobaqa kuni ovqat', 'sp_sport_nutrition_gameday'),
    ('питание в день соревнований', 'sp_sport_nutrition_gameday'), ('game day nutrition', 'sp_sport_nutrition_gameday'), ('bolaga kuch mashqi mumkinmi', 'sp_young_athlete_training'),
    ('тренировки для детей', 'sp_young_athlete_training'), ('strength training for children', 'sp_young_athlete_training'), ('sport lifchik tanlash', 'sp_women_sports_bra_gear'),
    ('как выбрать спортивный бюстгальтер', 'sp_women_sports_bra_gear'), ('how to choose a sports bra', 'sp_women_sports_bra_gear'), ('qizlar uchun zal dasturi', 'sp_women_strength_myth_plan'),
    ('силовая программа для женщин', 'sp_women_strength_myth_plan'), ("women's strength program", 'sp_women_strength_myth_plan'), ('kegel mashqi', 'sp_pelvic_floor_kegel'),
    ('упражнения кегеля', 'sp_pelvic_floor_kegel'), ('pelvic floor exercises', 'sp_pelvic_floor_kegel'), ('stulda bajariladigan mashqlar', 'sp_chair_exercises_seniors'),
    ('зарядка для пожилых', 'sp_chair_exercises_seniors'), ('как укрепить хват', 'sp_grip_strength_aging'), ('improve grip strength', 'sp_grip_strength_aging'),
    ('yurish dasturi', 'sp_walking_program_start'), ('программа ходьбы', 'sp_walking_program_start'), ('walking program', 'sp_walking_program_start'),
    ("tovon og'rig'i", 'hl_plantar_fasciitis'), ('боль в пятке', 'hl_plantar_fasciitis'), ('heel pain', 'hl_plantar_fasciitis'),
    ('churra bel', 'hl_sciatica_disc'), ('ишиас', 'hl_sciatica_disc'), ('herniated disc', 'hl_sciatica_disc'),
    ('orqa son tortilishi', 'hl_hamstring_strain'), ('потянул заднюю поверхность бедра', 'hl_hamstring_strain'), ('pulled hamstring', 'hl_hamstring_strain'),
    ('tizza operatsiyasidan keyin', 'hl_acl_meniscus_post_surgery'), ('после операции на колене', 'hl_acl_meniscus_post_surgery'), ('acl rehab', 'hl_acl_meniscus_post_surgery'),
    ('miya chayqalishi', 'hl_concussion_head'), ('сотрясение мозга', 'hl_concussion_head'), ('concussion', 'hl_concussion_head'),
    ("bo'g'imlar qarsillashi", 'hl_joint_cracking'), ('хруст в суставах', 'hl_joint_cracking'), ('joints cracking', 'hl_joint_cracking'),
    ('uvishish', 'hl_numbness_tingling'), ('онемение рук и ног', 'hl_numbness_tingling'), ('numbness', 'hl_numbness_tingling'),
    ("og'irlik ko'targanda bosh og'rig'i", 'hl_headache_lifting'), ('головная боль при подъёме веса', 'hl_headache_lifting'), ('headache when lifting', 'hl_headache_lifting'),
    ('PCOS va ozish', 'hl_pcos_thyroid_weight'), ('щитовидка и вес', 'hl_pcos_thyroid_weight'), ('thyroid and weight', 'hl_pcos_thyroid_weight'),
    ('kamqonlik', 'hl_anemia_low_energy'), ('анемия', 'hl_anemia_low_energy'), ('после ковида тренировки', 'hl_covid_post_viral'),
    ('returning to the gym after flu', 'hl_covid_post_viral'), ('varikoz va mashq', 'hl_varicose_veins'), ('варикоз и тренировки', 'hl_varicose_veins'),
    ('varicose veins and exercise', 'hl_varicose_veins'), ('xolesterin va mashq', 'hl_cholesterol_exercise'), ('холестерин и спорт', 'hl_cholesterol_exercise'),
    ('cholesterol and exercise', 'hl_cholesterol_exercise'), ('kefir kaloriyasi', 'fd_qatiq_kefir'), ('калории кефира', 'fd_qatiq_kefir'),
    ('kefir vs yogurt', 'fd_qatiq_kefir'), ('suzma oqsil', 'fd_suzma_tvorog'), ('калории творога', 'fd_suzma_tvorog'),
    ("qaymoq sariyog' kaloriyasi", 'fd_milk_cream_butter'), ('калории айрана', 'fd_milk_cream_butter'), ('butter cream calories', 'fd_milk_cream_butter'),
    ('pishloq kaloriyasi', 'fd_cheese_calories'), ('калории сыра', 'fd_cheese_calories'), ('cheese calories', 'fd_cheese_calories'),
    ("mol go'shti kaloriyasi", 'fd_beef_lamb_calories'), ('калории говядины', 'fd_beef_lamb_calories'), ('jigar foydasi', 'fd_liver_offal'),
    ('польза печени', 'fd_liver_offal'), ('liver benefits', 'fd_liver_offal'), ('losos kaloriyasi', 'fd_fish_tuna_salmon'),
    ('тунец консервированный', 'fd_fish_tuna_salmon'), ('canned tuna', 'fd_fish_tuna_salmon'), ('qazi kaloriyasi', 'fd_qazi_sausage'),
    ('сосиски вредны', 'fd_qazi_sausage'), ('are sausages unhealthy', 'fd_qazi_sausage'), ('grechka kaloriyasi', 'fd_buckwheat_cal'),
    ('калории гречки', 'fd_buckwheat_cal'), ('buckwheat calories', 'fd_buckwheat_cal'), ('makaron semirtiradimi', 'fd_pasta_macaroni'),
    ('от макарон толстеют', 'fd_pasta_macaroni'), ('does pasta make you fat', 'fd_pasta_macaroni'), ('kartoshka fri kaloriyasi', 'fd_potato_fried_boiled'),
    ('картофель фри калорийность', 'fd_potato_fried_boiled'), ('french fries calories', 'fd_potato_fried_boiled'), ('kinoa nima', 'fd_bulgur_couscous_quinoa'),
    ('булгур калории', 'fd_bulgur_couscous_quinoa'), ('what is quinoa', 'fd_bulgur_couscous_quinoa'), ('patir kaloriyasi', 'fd_lepyoshka_patir'),
    ('калории лепёшки', 'fd_lepyoshka_patir'), ('loviya kaloriyasi', 'fd_beans_chickpea_lentil'), ('нут калорийность', 'fd_beans_chickpea_lentil'),
    ('lentils and mung beans', 'fd_beans_chickpea_lentil'), ('bodom kaloriyasi', 'fd_nuts_almond_walnut'), ('грецкие орехи калорийность', 'fd_nuts_almond_walnut'),
    ('almond calories', 'fd_nuts_almond_walnut'), ('mayiz kaloriyasi', 'fd_dried_fruit_raisins'), ('курага калории', 'fd_dried_fruit_raisins'),
    ('dates calories', 'fd_dried_fruit_raisins'), ('anor kaloriyasi', 'fd_fruit_calories_list'), ('калорийность винограда', 'fd_fruit_calories_list'),
    ('pomegranate calories', 'fd_fruit_calories_list'), ('pomidor bodring kaloriyasi', 'fd_vegetables_calories'), ('калории моркови', 'fd_vegetables_calories'),
    ('vegetable calories', 'fd_vegetables_calories'), ('achichuk salat kaloriyasi', 'fd_greens_herbs_salad'), ('зелень польза', 'fd_greens_herbs_salad'),
    ('zaytun moyi kaloriyasi', 'fd_avocado_olive_oil'), ('калории оливкового масла', 'fd_avocado_olive_oil'), ('olive oil calories', 'fd_avocado_olive_oil'),
    ('asal kaloriyasi', 'fd_honey_sugar_halva'), ('халва калорийность', 'fd_honey_sugar_halva'), ('honey calories', 'fd_honey_sugar_halva'),
    ('kola kaloriyasi', 'fd_soda_cola_drinks'), ('газировка сахар', 'fd_soda_cola_drinks'), ('is soda bad', 'fd_soda_cola_drinks'),
    ('are chips bad', 'fd_chips_snacks'), ('shaurma kaloriyasi', 'fd_shawarma_doner_hotdog'), ('калории шаурмы', 'fd_shawarma_doner_hotdog'),
    ('shawarma calories', 'fd_shawarma_doner_hotdog'), ('chebureki kaloriyasi', 'fd_fried_pastries'), ('беляши калорийность', 'fd_fried_pastries'),
    ('mastava kaloriyasi', 'fd_mastava_moshxorda_soups'), ('калории маставы', 'fd_mastava_moshxorda_soups'), ('mastava calories', 'fd_mastava_moshxorda_soups'),
    ('qozon kabob kaloriyasi', 'fd_qozon_kabob_qovurma'), ('калории казан-кебаба', 'fd_qozon_kabob_qovurma'), ('meal prep necha kun turadi', 'fd_mealprep_storage'),
    ('сколько хранится готовая еда', 'fd_mealprep_storage'), ('how long does cooked food last', 'fd_mealprep_storage'), ('yakshanba kuni ovqat tayyorlash', 'fd_mealprep_sunday_plan'),
    ('заготовка еды на неделю', 'fd_mealprep_sunday_plan'), ('weekly meal prep plan', 'fd_mealprep_sunday_plan'), ('talaba uchun arzon ovqat', 'fd_budget_student_week'),
    ('дёшево питаться студенту', 'fd_budget_student_week'), ('budget grocery list', 'fd_budget_student_week'), ('eng arzon oqsil manbai', 'fd_budget_protein_per_som'),
    ('самый дешёвый белок', 'fd_budget_protein_per_som'), ('cheapest protein sources', 'fd_budget_protein_per_som'), ('halol oqsil kukuni', 'fd_halal_nutrition_notes'),
    ('халяльный протеин', 'fd_halal_nutrition_notes'), ('gelatin capsules halal', 'fd_halal_nutrition_notes'), ("o'smir sportchi oqsil", 'fd_kids_teens_protein'),
    ('белок для подростков', 'fd_kids_teens_protein'), ('protein for teenagers', 'fd_kids_teens_protein'), ("maktab o'quvchisi nonushta", 'fd_kids_breakfast_school'),
    ('завтрак школьнику', 'fd_kids_breakfast_school'), ("o'smirlar ozishi", 'fd_teen_weight_loss_warning'), ('диета для подростка', 'fd_teen_weight_loss_warning'),
    ("to'yda ovqatlanish", 'fd_toy_wedding_feast'), ('питание на свадьбе', 'fd_toy_wedding_feast'), ('party food tips', 'fd_toy_wedding_feast'),
    ('kafe va fast food tanlovi', 'fd_eating_out_fast_choices'), ('что выбрать в фастфуде', 'fd_eating_out_fast_choices'), ('healthy fast food choices', 'fd_eating_out_fast_choices'),
    ('pivo kaloriyasi', 'fd_alcohol_calories_muscle'), ('калории алкоголя', 'fd_alcohol_calories_muscle'), ('alcohol calories', 'fd_alcohol_calories_muscle'),
    ('ichgandan keyin mashq', 'fd_hangover_training'), ('похмелье и зал', 'fd_hangover_training'), ('exercise with a hangover', 'fd_hangover_training'),
    ('5:2 ochlik', 'fd_if_variants_5_2_omad'), ('диета 5:2', 'fd_if_variants_5_2_omad'), ('OMAD', 'fd_if_variants_5_2_omad'),
    ('ochlik va mushak', 'fd_intermittent_fasting_muscle'), ('голодание и мышцы', 'fd_intermittent_fasting_muscle'), ('refeed nima', 'fd_refeed_diet_break'),
    ('что такое рефид', 'fd_refeed_diet_break'), ('diet break', 'fd_refeed_diet_break'), ('reverse diet', 'fd_reverse_diet_maintenance'),
    ('обратная диета', 'fd_reverse_diet_maintenance'), ('7700 kkal', 'fd_kcal_in_kg_fat'), ('сколько калорий в 1 кг жира', 'fd_kcal_in_kg_fat'),
    ('calories in a kilogram of fat', 'fd_kcal_in_kg_fat'), ('bir mahalda qancha oqsil', 'fd_protein_per_meal_distribution'), ('сколько белка за один приём', 'fd_protein_per_meal_distribution'),
    ('how much protein per meal', 'fd_protein_per_meal_distribution'), ('uglevod yuklash', 'fd_carb_loading_glycogen'), ('углеводная загрузка', 'fd_carb_loading_glycogen'),
    ('carb loading', 'fd_carb_loading_glycogen'), ('NEAT nima', 'fd_neat_daily_movement'), ('что такое neat', 'fd_neat_daily_movement'),
    ('ovqatning termik effekti', 'fd_thermic_effect_food'), ('термический эффект пищи', 'fd_thermic_effect_food'), ('thermic effect of food', 'fd_thermic_effect_food'),
    ("qo'shimchalar A dan Z gacha", 'fd_supp_evidence_overview'), ('какие добавки работают', 'fd_supp_evidence_overview'), ('which supplements actually work', 'fd_supp_evidence_overview'),
    ('beta-alanin', 'fd_supp_beta_alanine'), ('бета-аланин', 'fd_supp_beta_alanine'), ('beta alanine', 'fd_supp_beta_alanine'),
    ('sitrullin', 'fd_supp_citrulline_nitrate'), ('цитруллин', 'fd_supp_citrulline_nitrate'), ('citrulline', 'fd_supp_citrulline_nitrate'),
    ('ashvagandxa', 'fd_supp_ashwagandha_adaptogens'), ('ашваганда', 'fd_supp_ashwagandha_adaptogens'), ('ashwagandha', 'fd_supp_ashwagandha_adaptogens'),
    ('glutamin', 'fd_supp_glutamine_hmb_carnitine'), ('глютамин нужен ли', 'fd_supp_glutamine_hmb_carnitine'), ('l carnitine does it work', 'fd_supp_glutamine_hmb_carnitine'),
    ('testosteron booster', 'fd_supp_testosterone_boosters'), ('бустер тестостерона', 'fd_supp_testosterone_boosters'), ('tribulus', 'fd_supp_testosterone_boosters'),
    ('multivitamin kerakmi', 'fd_supp_multivitamin_zinc_c'), ('нужны ли мультивитамины', 'fd_supp_multivitamin_zinc_c'), ('zinc supplement', 'fd_supp_multivitamin_zinc_c'),
    ('elektrolitlar kerakmi', 'fd_supp_electrolytes_eaa'), ('электролиты нужны ли', 'fd_supp_electrolytes_eaa'), ('eaa vs bcaa', 'fd_supp_electrolytes_eaa'),
    ('melatonin', 'fd_supp_melatonin_sleep'), ('мелатонин', 'fd_supp_melatonin_sleep'), ('whey izolyat kontsentrat farqi', 'fd_supp_whey_types'),
    ('изолят или концентрат сывороточного', 'fd_supp_whey_types'), ('casein vs whey', 'fd_supp_whey_types'), ("qo'shimchaning asliyligini tekshirish", 'fd_supp_check_authentic'),
    ('подделка протеина', 'fd_supp_check_authentic'), ('fake protein', 'fd_supp_check_authentic'), ("homiladorlik qo'shimcha", 'fd_supp_who_should_avoid'),
    ('добавки подросткам', 'fd_supp_who_should_avoid'), ('supplements during pregnancy', 'fd_supp_who_should_avoid'), ('energiya gel', 'fd_supp_sodium_bicarb_gels'),
    ('энергетические гели', 'fd_supp_sodium_bicarb_gels'), ('energy gels', 'fd_supp_sodium_bicarb_gels'), ('no pain no gain', 'mx_m_no_pain_no_gain'),
    ('без боли нет результата', 'mx_m_no_pain_no_gain'), ('is pain needed for results', 'mx_m_no_pain_no_gain'), ("og'irlik ko'tarish bo'yni to'xtatadi", 'mx_m_lifting_stunts_growth'),
    ('силовые тормозят рост', 'mx_m_lifting_stunts_growth'), ('does lifting stunt growth', 'mx_m_lifting_stunts_growth'), ("mushak yog'dan og'irroqmi", 'mx_m_muscle_weighs_more'),
    ('мышцы тяжелее жира', 'mx_m_muscle_weighs_more'), ('muscle weighs more than fat', 'mx_m_muscle_weighs_more'), ("yog' yoqish zonasi", 'mx_m_fat_burning_zone'),
    ('зона жиросжигания', 'mx_m_fat_burning_zone'), ('fat burning zone', 'mx_m_fat_burning_zone'), ("crunch qorin yog'ini yo'qotadimi", 'mx_m_crunches_flat_stomach'),
    ('пресс убирает жир с живота', 'mx_m_crunches_flat_stomach'), ('do crunches burn belly fat', 'mx_m_crunches_flat_stomach'), ("o'tirib turish tizzaga zararlimi", 'mx_m_squats_bad_knees'),
    ('приседания вредны для коленей', 'mx_m_squats_bad_knees'), ('are squats bad for knees', 'mx_m_squats_bad_knees'), ('deadlift belga zararlimi', 'mx_m_deadlift_bad_back'),
    ('становая тяга вредна для спины', 'mx_m_deadlift_bad_back'), ('is deadlifting bad for your back', 'mx_m_deadlift_bad_back'), ("kardio va kuch mashqini birga qilsa bo'ladimi", 'mx_m_cardio_and_muscle_together'),
    ('можно ли совмещать кардио и силовые', 'mx_m_cardio_and_muscle_together'), ('can you do cardio and weights together', 'mx_m_cardio_and_muscle_together'), ('har kuni mashq qilgan yaxshimi', 'mx_m_train_everyday_better'),
    ('чем больше тренировок тем лучше', 'mx_m_train_everyday_better'), ('is more training always better', 'mx_m_train_everyday_better'), ('trenajyorlar foydasiz', 'mx_m_machines_vs_free_myth'),
    ('only free weights work', 'mx_m_machines_vs_free_myth'), ("cho'zilish jarohatdan saqlaydimi", 'mx_m_stretching_prevents_all_injury'), ('does stretching prevent injury', 'mx_m_stretching_prevents_all_injury'),
    ('растяжка защищает от травм', 'mx_m_stretching_prevents_all_injury'), ('genetika hammasini hal qiladi', 'mx_m_genetics_decide_all'), ('генетика решает всё', 'mx_m_genetics_decide_all'),
    ('genetics decide everything', 'mx_m_genetics_decide_all'), ('30 yoshdan keyin metabolizm sekinlashadi', 'mx_m_slow_metabolism_after_30'), ('после 30 метаболизм замедляется', 'mx_m_slow_metabolism_after_30'),
    ('metabolism slows after 30', 'mx_m_slow_metabolism_after_30'), ("ayollar og'ir ko'tarmasligi kerakmi", 'mx_m_women_dont_lift_heavy'), ('женщинам нельзя тяжёлые веса', 'mx_m_women_dont_lift_heavy'),
    ('heavy lifting is bad for women', 'mx_m_women_dont_lift_heavy'), ('terlatuvchi kamar', 'mx_m_sauna_suit_belly_belt'), ('пояс для похудения', 'mx_m_sauna_suit_belly_belt'),
    ('waist trainer burns fat', 'mx_m_sauna_suit_belly_belt'), ('titrash platformasi ozdiradimi', 'mx_m_vibration_machines_ems'), ('виброплатформа для похудения', 'mx_m_vibration_machines_ems'),
    ('vibration plate weight loss', 'mx_m_vibration_machines_ems'), ('soat 8 dan keyin ovqat yemaslik', 'mx_m_eating_after_8pm'), ('после 18 не есть', 'mx_m_eating_after_8pm'),
    ('no eating after 8pm', 'mx_m_eating_after_8pm'), ('ochlik rejimi metabolizm', 'mx_m_starvation_mode'), ('режим голодания метаболизм', 'mx_m_starvation_mode'),
    ('starvation mode', 'mx_m_starvation_mode'), ("ko'p mahal ovqat metabolizmni tezlashtiradimi", 'mx_m_small_meals_boost_metabolism'), ('дробное питание ускоряет обмен', 'mx_m_small_meals_boost_metabolism'),
    ('eating 6 times a day', 'mx_m_small_meals_boost_metabolism'), ('nonushta eng muhim ovqatmi', 'mx_m_breakfast_most_important'), ('завтрак самый важный приём', 'mx_m_breakfast_most_important'),
    ('is breakfast the most important meal', 'mx_m_breakfast_most_important'), ('uglevod semirtiradimi', 'mx_m_carbs_make_fat'), ('углеводы делают толстым', 'mx_m_carbs_make_fat'),
    ('do carbs make you fat', 'mx_m_carbs_make_fat'), ("yog' yeysam semiraman", 'mx_m_fat_makes_fat'), ('does eating fat make you fat', 'mx_m_fat_makes_fat'),
    ('tuxum xolesterinni oshiradimi', 'mx_m_eggs_cholesterol'), ('яйца повышают холестерин', 'mx_m_eggs_cholesterol'), ('do eggs raise cholesterol', 'mx_m_eggs_cholesterol'),
    ("yashil choy yog' yoqadimi", 'mx_m_green_tea_lemon_vinegar'), ('зелёный чай сжигает жир', 'mx_m_green_tea_lemon_vinegar'), ('apple cider vinegar weight loss', 'mx_m_green_tea_lemon_vinegar'),
    ("glutensiz sog'lomroqmi", 'mx_m_gluten_free_organic'), ('безглютеновая диета полезнее', 'mx_m_gluten_free_organic'), ('is gluten free healthier', 'mx_m_gluten_free_organic'),
    ('белок строго через 30 минут', 'mx_m_30_min_protein_window'), ('protein within 30 minutes of training', 'mx_m_30_min_protein_window'), ("kofe bo'yni to'xtatadimi", 'mx_m_coffee_stunts_growth_dehydrates'),
    ('кофе тормозит рост', 'mx_m_coffee_stunts_growth_dehydrates'), ('does coffee dehydrate', 'mx_m_coffee_stunts_growth_dehydrates'), ('kreatin steroidmi', 'mx_m_creatine_steroid_dehydrates'),
    ('креатин это стероид', 'mx_m_creatine_steroid_dehydrates'), ('is creatine a steroid', 'mx_m_creatine_steroid_dehydrates'), ('shakarsiz degani kaloriyasiz', 'mx_m_sugar_free_means_calorie_free'),
    ('без сахара значит без калорий', 'mx_m_sugar_free_means_calorie_free'), ('sugar free means no calories', 'mx_m_sugar_free_means_calorie_free'), ('meva sharbati ozdiradimi', 'mx_m_juice_cleanse_fruit_sugar'),
    ('соковая диета', 'mx_m_juice_cleanse_fruit_sugar'), ('juice cleanse weight loss', 'mx_m_juice_cleanse_fruit_sugar'), ("ko'p oqsil ko'p mushak", 'mx_m_protein_more_equals_more'),
    ('слишком много белка', 'mx_m_protein_more_equals_more'), ('can you eat too much protein', 'mx_m_protein_more_equals_more'), ("qo'shimcha ichmasam o'smayman", 'mx_m_supplements_required'),
    ('без добавок мышцы не растут', 'mx_m_supplements_required'), ('do I need supplements to grow', 'mx_m_supplements_required'), ('tuzsiz ovqat yaxshimi', 'mx_m_salt_free_always'),
    ('совсем без соли полезно', 'mx_m_salt_free_always'), ("bir kun ko'p yesam hamma narsa buziladimi", 'mx_m_cheat_day_ruins'), ('один срыв всё портит', 'mx_m_cheat_day_ruins'),
    ('one bad day ruins everything', 'mx_m_cheat_day_ruins'), ("ozg'in odam sog'lommi", 'mx_m_thin_means_healthy'), ('худой значит здоровый', 'mx_m_thin_means_healthy'),
    ('skinny fat', 'mx_m_thin_means_healthy'), ('sellyulit kremlar', 'mx_m_cellulite_creams'), ('целлюлит кремы', 'mx_m_cellulite_creams'),
    ('cellulite creams', 'mx_m_cellulite_creams'), ('ortiqcha ovqatni mashq bilan yoqish', 'mx_m_exercise_cancels_junk_food'), ('тренировка отработает любую еду', 'mx_m_exercise_cancels_junk_food'),
    ('exercise burns off any food', 'mx_m_exercise_cancels_junk_food'), ('ozish uchun tabletkalar', 'mx_m_diet_pills_wraps'), ('sut mahsulotlari zararlimi', 'mx_m_dairy_bad_for_you'),
    ('молочное вредно', 'mx_m_dairy_bad_for_you'), ('is dairy bad for you', 'mx_m_dairy_bad_for_you'), ("yog'siz mahsulot ozdiradi", 'mx_m_fat_free_means_slim'),
    ('обезжиренные продукты худеют', 'mx_m_fat_free_means_slim'), ('fat free helps you slim', 'mx_m_fat_free_means_slim'), ('oqsil faqat bodibildinglar uchunmi', 'mx_m_bodybuilders_only_protein'),
    ('протеин только для бодибилдеров', 'mx_m_bodybuilders_only_protein'), ('is protein only for athletes', 'mx_m_bodybuilders_only_protein'), ("BMI to'liq haqiqatmi", 'mx_m_bmi_only_truth'),
    ('ИМТ показывает всё', 'mx_m_bmi_only_truth'), ('bmi is the whole truth', 'mx_m_bmi_only_truth'), ('vazn turib qoldi nima qilay', 'mx_m_wl_stall_plateau_steps'),
    ('вес встал что делать', 'mx_m_wl_stall_plateau_steps'), ('weight loss stalled what to do', 'mx_m_wl_stall_plateau_steps'), ('kaloriyani qancha kamaytirish kerak', 'mx_m_wl_how_many_kcal_cut'),
    ('сколько калорий убрать для похудения', 'mx_m_wl_how_many_kcal_cut'), ('how many calories to cut', 'mx_m_wl_how_many_kcal_cut'), ('10 kg ozish uchun qancha vaqt', 'mx_m_wl_10kg_timeline'),
    ('сколько времени похудеть на 10 кг', 'mx_m_wl_10kg_timeline'), ('how long to lose 10 kg', 'mx_m_wl_10kg_timeline'), ("yuzdagi yog'ni yo'qotish", 'mx_m_wl_face_arms_thighs'),
    ('как убрать жир с лица', 'mx_m_wl_face_arms_thighs'), ('lose face fat', 'mx_m_wl_face_arms_thighs'), ('40 yoshdan keyin ozish', 'mx_m_wl_after_40_women'),
    ('похудение после 40', 'mx_m_wl_after_40_women'), ('weight loss after 40', 'mx_m_wl_after_40_women'), ("stress qorin yog'i", 'mx_m_wl_stress_belly_cortisol'),
    ('кортизол и вес', 'mx_m_wl_stress_belly_cortisol'), ('cortisol and weight', 'mx_m_wl_stress_belly_cortisol'), ('mashqdan keyin vazn oshdi', 'mx_m_wl_scale_up_after_workout'),
    ('вес вырос после тренировок', 'mx_m_wl_scale_up_after_workout'), ('weight went up after starting exercise', 'mx_m_wl_scale_up_after_workout'), ('5 kg massa olish', 'mx_m_wg_gain_5kg_plan'),
    ('набрать 5 кг', 'mx_m_wg_gain_5kg_plan'), ('gain 5 kg', 'mx_m_wg_gain_5kg_plan'), ("ko'p yeyman lekin semirmayman", 'mx_m_wg_eat_lot_not_gaining'),
    ('много ем но не поправляюсь', 'mx_m_wg_eat_lot_not_gaining'), ('i eat a lot but cannot gain weight', 'mx_m_wg_eat_lot_not_gaining'), ('lean bulk nima', 'mx_m_wg_lean_bulk_belly'),
    ('чистая масса', 'mx_m_wg_lean_bulk_belly'), ('kunduzgi uyqu mashqqa foydali mi', 'mx_m_rc_nap_power'), ('дневной сон и тренировки', 'mx_m_rc_nap_power'),
    ('does napping help training', 'mx_m_rc_nap_power'), ("kofeinni qachon to'xtatish", 'mx_m_rc_caffeine_cutoff_sleep'), ('когда прекратить кофе', 'mx_m_rc_caffeine_cutoff_sleep'),
    ('caffeine cutoff time', 'mx_m_rc_caffeine_cutoff_sleep'), ('ortiqcha charchash belgilari', 'mx_m_rc_overreaching_signs'), ('признаки перетренированности', 'mx_m_rc_overreaching_signs'),
    ('signs of overtraining', 'mx_m_rc_overreaching_signs'), ('quti nafasi', 'mx_m_rc_breathing_stress_box'), ('квадратное дыхание', 'mx_m_rc_breathing_stress_box'),
    ('box breathing', 'mx_m_rc_breathing_stress_box'), ('smenali ish uyqu', 'mx_m_rc_shift_work_sleep'), ('посменная работа сон', 'mx_m_rc_shift_work_sleep'),
    ('night shift and training', 'mx_m_rc_shift_work_sleep'), ("alkogol uyquga ta'siri", 'mx_m_rc_alcohol_sleep_recovery'), ('алкоголь и сон', 'mx_m_rc_alcohol_sleep_recovery'),
    ('alcohol and sleep', 'mx_m_rc_alcohol_sleep_recovery'), ("birinchi og'irlikni qanday tanlash", 'fq_first_weight_pick'), ('как выбрать начальный вес', 'fq_first_weight_pick'),
    ('how to pick a starting weight', 'fq_first_weight_pick'), ("qachon og'irlikni oshirish kerak", 'fq_when_add_weight'), ('когда повышать вес', 'fq_when_add_weight'),
    ('when to increase weight', 'fq_when_add_weight'), ("bir mashg'ulotda nechta mashq", 'fq_exercises_per_workout'), ('сколько упражнений за тренировку', 'fq_exercises_per_workout'),
    ('how many exercises per workout', 'fq_exercises_per_workout'), ('kardio avval yoki keyin', 'fq_cardio_before_after'), ('кардио до или после силовых', 'fq_cardio_before_after'),
    ('cardio before or after weights', 'fq_cardio_before_after'), ('zalga sochiq kerakmi', 'fq_towel_needed'), ('нужно ли полотенце в зал', 'fq_towel_needed'),
    ('do i need a towel at the gym', 'fq_towel_needed'), ("qo'lqop kerakmi", 'fq_gloves_needed'), ('нужны ли перчатки в зале', 'fq_gloves_needed'),
    ('do i need gym gloves', 'fq_gloves_needed'), ("mushak og'rig'i necha kun davom etadi", 'fq_soreness_duration'), ('сколько длится крепатура', 'fq_soreness_duration'),
    ('how long does muscle soreness last', 'fq_soreness_duration'), ('mushaklar titraydi', 'fq_muscles_shaking'), ('дрожат мышцы', 'fq_muscles_shaking'),
    ('why do my arms shake', 'fq_muscles_shaking'), ('mushak uchishi', 'fq_muscle_twitch'), ('подёргивание мышц', 'fq_muscle_twitch'),
    ('muscle twitching', 'fq_muscle_twitch'), ('bir tomon kuchliroq', 'fq_one_side_stronger'), ('правая рука сильнее левой', 'fq_one_side_stronger'),
    ('one side stronger than the other', 'fq_one_side_stronger'), ('murabbiy kerakmi', 'fq_need_trainer'), ('нужен ли тренер', 'fq_need_trainer'),
    ('do i need a personal trainer', 'fq_need_trainer'), ("qorinni har kuni qilsa bo'ladimi", 'fq_abs_every_day'), ('можно ли качать пресс каждый день', 'fq_abs_every_day'),
    ('can i train abs every day', 'fq_abs_every_day'), ('bir mushakka necha kun dam', 'fq_rest_between_same_muscle'), ('через сколько снова качать мышцу', 'fq_rest_between_same_muscle'),
    ('how soon to train a muscle again', 'fq_rest_between_same_muscle'), ('terlamasam mashq foydasizmi', 'fq_no_sweat_no_workout'), ('если не потею тренировка зря', 'fq_no_sweat_no_workout'),
    ('no sweat means no workout', 'fq_no_sweat_no_workout'), ('ovqatdan keyin qachon mashq', 'fq_after_big_meal_wait'), ('через сколько тренироваться после еды', 'fq_after_big_meal_wait'),
    ('how long after eating can i work out', 'fq_after_big_meal_wait'), ('bir soat mashqda necha kaloriya yoqiladi', 'fq_calories_per_hour_gym'), ('сколько калорий сжигается за час тренировки', 'fq_calories_per_hour_gym'),
    ('how many calories does an hour workout burn', 'fq_calories_per_hour_gym'), ("tarozimi yoki ko'zgu", 'fq_scale_or_mirror'), ('весы или зеркало что точнее', 'fq_scale_or_mirror'),
    ('pre-workout shartmi', 'fq_pre_workout_not_needed'), ('обязателен ли предтреник', 'fq_pre_workout_not_needed'), ('is pre workout necessary', 'fq_pre_workout_not_needed'),
    ('tanaffusdan keyin qaytish', 'fq_break_return_week'), ('возвращение после перерыва', 'fq_break_return_week'), ('returning after a break', 'fq_break_return_week'),
    ("zalda yolg'iz mashq xavfsizmi", 'fq_training_alone_safety'), ('тренироваться одному безопасно', 'fq_training_alone_safety'), ('is it safe to train alone', 'fq_training_alone_safety'),
    ('texnikani videoga olish', 'fq_record_form_video'), ('снять технику на видео', 'fq_record_form_video'), ('record your form on video', 'fq_record_form_video'),
    ('nafasni qachon chiqarish', 'fq_exhale_when_effort'), ('когда выдыхать при подъёме', 'fq_exhale_when_effort'), ('when to breathe out when lifting', 'fq_exhale_when_effort'),
    ('16 yoshda zalga borish mumkinmi', 'fq_age_16_start_gym'), ('с какого возраста можно в зал', 'fq_age_16_start_gym'), ('what age can you start the gym', 'fq_age_16_start_gym'),
    ('squat sonni kattalashtiradimi', 'fq_squats_big_thighs'), ('приседания накачают огромные ноги', 'fq_squats_big_thighs'), ('do squats make legs bulky', 'fq_squats_big_thighs'),
    ("har kuni otjimaniya qilsa bo'ladimi", 'fq_pushups_daily_ok'), ('можно ли отжиматься каждый день', 'fq_pushups_daily_ok'), ('can i do push ups every day', 'fq_pushups_daily_ok'),
    ("yugurish yo'lakchasida qanday tezlik", 'fq_treadmill_beginner_speed'), ('какая скорость на дорожке для новичка', 'fq_treadmill_beginner_speed'), ('treadmill speed for beginners', 'fq_treadmill_beginner_speed'),
    ('elliptik trenajyor foydasi', 'fq_elliptical_low_impact'), ('эллиптический тренажёр польза', 'fq_elliptical_low_impact'), ('elliptical trainer benefits', 'fq_elliptical_low_impact'),
    ("oyoq kuni o'tkazib yuborish", 'fq_skip_leg_day'), ('пропускать день ног', 'fq_skip_leg_day'), ('skipping leg day', 'fq_skip_leg_day'),
    ('dasturni qachon almashtirish', 'fq_change_program_when'), ('когда менять программу', 'fq_change_program_when'), ('when to change my program', 'fq_change_program_when'),
    ("zal qachon bo'sh", 'fq_gym_busy_times'), ('когда в зале меньше людей', 'fq_gym_busy_times'), ('when is the gym least busy', 'fq_gym_busy_times'),
    ("haftasiga mushakka necha to'plam", 'fq_how_many_sets_week_muscle'), ('сколько подходов в неделю на мышцу', 'fq_how_many_sets_week_muscle'), ('how many sets per muscle per week', 'fq_how_many_sets_week_muscle'),
    ("vaqt yo'q qanday mashq qilish", 'fq_keep_training_while_busy'), ('нет времени на тренировки', 'fq_keep_training_while_busy'), ('no time to train', 'fq_keep_training_while_busy'),
    ('zal sumkasiga nima solish', 'fq_gym_bag_packing'), ('что взять в спортивную сумку', 'fq_gym_bag_packing'), ('what to pack in a gym bag', 'fq_gym_bag_packing'),
    ('yoga yoki zal qaysi yaxshi', 'fq_yoga_vs_gym'), ('йога или зал что лучше', 'fq_yoga_vs_gym'), ('yoga or gym which is better', 'fq_yoga_vs_gym'),
    ('pilates nima', 'fq_pilates_basics'), ('что такое пилатес', 'fq_pilates_basics'), ('what is pilates', 'fq_pilates_basics'),
    ('birinchi oyda nima kutish kerak', 'fq_first_month_expect'), ('чего ждать за первый месяц', 'fq_first_month_expect'), ('what to expect in the first month', 'fq_first_month_expect'),
    ("qomatni tez to'g'rilash", 'fq_quick_posture_fix'), ('убрать сутулость', 'fq_quick_posture_fix'), ('fix posture quickly', 'fq_quick_posture_fix'),
    ("otjimaniyada qo'l joylashuvi", 'fq_pushup_hand_position'), ('положение рук в отжиманиях', 'fq_pushup_hand_position'), ('push up hand position', 'fq_pushup_hand_position'),
    ("tizza oyoq uchidan o'tsa zararlimi", 'fq_knees_over_toes'), ('колени за носки опасно ли', 'fq_knees_over_toes'), ('knees over toes dangerous', 'fq_knees_over_toes'),
    ("yugurganda yon og'riq", 'fq_side_stitch_running'), ('колет в боку при беге', 'fq_side_stitch_running'), ('side stitch while running', 'fq_side_stitch_running'),
    ('порвалась мозоль', 'fq_hand_blisters'), ('torn callus', 'fq_hand_blisters'), ("tomoq og'rig'ida mashq", 'fq_sore_throat_training'),
    ('тренировка при боли в горле', 'fq_sore_throat_training'), ('workout with a sore throat', 'fq_sore_throat_training'), ("tos qotib qolishi o'tirishdan", 'fq_tight_hips_sitting'),
    ('зажаты бёдра от сидения', 'fq_tight_hips_sitting'), ('tight hips from sitting', 'fq_tight_hips_sitting'), ('odat shakllanishi necha kun', 'fq_habit_how_long'),
    ('сколько дней формируется привычка', 'fq_habit_how_long'), ('how long to form a habit', 'fq_habit_how_long'), ('faqat gantel bilan reja', 'fq_dumbbells_only_plan'),
    ('программа только с гантелями', 'fq_dumbbells_only_plan'), ('plan with only dumbbells', 'fq_dumbbells_only_plan'), ('uy zali uchun nima olish', 'fq_home_gym_starter_kit'),
    ('что купить для домашних тренировок', 'fq_home_gym_starter_kit'), ('what to buy for a home gym', 'fq_home_gym_starter_kit'), ("velotrenajyor o'rindiq balandligi", 'fq_bike_seat_height'),
    ('высота седла велотренажёра', 'fq_bike_seat_height'), ('exercise bike seat height', 'fq_bike_seat_height'), ('zina trenajyori', 'fq_stairmaster_machine'),
    ('лестничный тренажёр', 'fq_stairmaster_machine'), ('stair climber machine', 'fq_stairmaster_machine'), ("yo'lakchada yoki ko'chada yugurish", 'fq_treadmill_vs_outdoor'),
    ('бег на дорожке или на улице', 'fq_treadmill_vs_outdoor'), ('treadmill or outdoor running', 'fq_treadmill_vs_outdoor'), ("og'ir mashqdan oldin isinish to'plamlari", 'fq_warmup_sets_for_heavy'),
    ('разминочные подходы перед тяжёлым', 'fq_warmup_sets_for_heavy'), ('warm up sets before heavy lifts', 'fq_warmup_sets_for_heavy'), ("og'riq va noqulaylik farqi", 'fq_pain_vs_discomfort'),
    ('боль или дискомфорт разница', 'fq_pain_vs_discomfort'), ('pain vs discomfort', 'fq_pain_vs_discomfort'), ('abonement muddatini tanlash', 'fq_choose_membership_length'),
    ('какой срок абонемента выбрать', 'fq_choose_membership_length'), ('eski jarohat bilan mashq', 'fq_train_with_old_injury'), ('тренировки со старой травмой', 'fq_train_with_old_injury'),
    ('training with an old injury', 'fq_train_with_old_injury'), ("mashq kayfiyatga ta'siri", 'fq_exercise_and_mood'), ('тренировки и настроение', 'fq_exercise_and_mood'),
    ('exercise and mood', 'fq_exercise_and_mood'), ('yotishdan oldin ovqat mushak', 'fq_meal_before_bed_muscle'), ('белок на ночь', 'fq_meal_before_bed_muscle'),
    ("og'irlikni joyiga qo'yish", 'fq_et_rerack'), ('возвращать веса на место', 'fq_et_rerack'), ('re-rack your weights', 'fq_et_rerack'),
    ('skameykani artish', 'fq_et_wipe_bench'), ('протирать скамью', 'fq_et_wipe_bench'), ('wipe down the bench', 'fq_et_wipe_bench'),
    ('boshqalarni suratga olish zalda', 'fq_et_filming_others'), ('снимать других в зале', 'fq_et_filming_others'), ('filming others in the gym', 'fq_et_filming_others'),
    ('zalga atir sepish', 'fq_et_perfume_hygiene'), ('духи в зале', 'fq_et_perfume_hygiene'), ('perfume in the gym', 'fq_et_perfume_hygiene'),
    ('shtanga necha kg', 'fq_eq_olympic_barbell'), ('сколько весит гриф', 'fq_eq_olympic_barbell'), ('how much does a barbell weigh', 'fq_eq_olympic_barbell'),
    ('EZ shtanga nima', 'fq_eq_ez_bar'), ('что такое ez гриф', 'fq_eq_ez_bar'), ('what is an ez bar', 'fq_eq_ez_bar'),
    ('power rack nima', 'fq_eq_power_rack'), ('что такое силовая рама', 'fq_eq_power_rack'), ('what is a power rack', 'fq_eq_power_rack'),
    ('skameyka turlari', 'fq_eq_bench_types'), ('виды скамеек', 'fq_eq_bench_types'), ('types of benches', 'fq_eq_bench_types'),
    ('shtanga qulfi', 'fq_eq_weight_plate_collar'), ('замки для грифа', 'fq_eq_weight_plate_collar'), ('barbell collars', 'fq_eq_weight_plate_collar'),
    ('magnezium chalk nima', 'fq_eq_chalk_magnesium'), ('магнезия в зале', 'fq_eq_chalk_magnesium'), ('gym chalk', 'fq_eq_chalk_magnesium'),
    ('assault bike', 'fq_eq_assault_air_bike'), ('эйр байк', 'fq_eq_assault_air_bike'), ('ролик для пресса безопасен', 'fq_eq_ab_roller_wheel'),
    ('ab wheel safe', 'fq_eq_ab_roller_wheel'), ('smith yoki erkin shtanga tanlash', 'fq_eq_smith_vs_rack'), ('смит или свободная штанга что выбрать', 'fq_eq_smith_vs_rack'),
    ('AMRAP nima', 'fq_gl_amrap'), ('что такое amrap', 'fq_gl_amrap'), ('what is amrap', 'fq_gl_amrap'),
    ('EMOM nima', 'fq_gl_emom'), ('что такое emom', 'fq_gl_emom'), ('what is emom', 'fq_gl_emom'),
    ('PR nima', 'fq_gl_pr_pb'), ('что такое пр в зале', 'fq_gl_pr_pb'), ('what is a pr', 'fq_gl_pr_pb'),
    ('rep va set nima', 'fq_gl_rep_set'), ('что такое повторение и подход', 'fq_gl_rep_set'), ('what is a rep and a set', 'fq_gl_rep_set'),
    ('konsentrik ekssentrik izometrik', 'fq_gl_concentric_eccentric'), ('эксцентрическая фаза', 'fq_gl_concentric_eccentric'), ('kompleks va izolyatsiya mashq farqi', 'fq_gl_compound_isolation'),
    ('базовые и изолирующие упражнения разница', 'fq_gl_compound_isolation'), ('compound vs isolation exercises', 'fq_gl_compound_isolation'), ('HIIT va LISS farqi', 'fq_gl_hiit_liss'),
    ('hiit и liss разница', 'fq_gl_hiit_liss'), ('hiit vs liss', 'fq_gl_hiit_liss'), ('sirk mashq nima', 'fq_gl_circuit_giant_set'),
    ('круговая тренировка что это', 'fq_gl_circuit_giant_set'), ('what is a circuit workout', 'fq_gl_circuit_giant_set'), ('gipertrofiya nima', 'fq_gl_hypertrophy_strength_endurance'),
    ('что такое гипертрофия', 'fq_gl_hypertrophy_strength_endurance'), ('what is hypertrophy', 'fq_gl_hypertrophy_strength_endurance'), ('BMR nima', 'fq_gl_bmr_maintenance'),
    ('что такое bmr', 'fq_gl_bmr_maintenance'), ('what is bmr', 'fq_gl_bmr_maintenance'), ('tutim turlari', 'fq_gl_grip_types'),
    ('виды хвата', 'fq_gl_grip_types'), ('grip types', 'fq_gl_grip_types'), ("funksional mashg'ulot nima", 'fq_gl_functional_training'),
    ('что такое функциональный тренинг', 'fq_gl_functional_training'), ('what is functional training', 'fq_gl_functional_training'), ('harakatchanlik va egiluvchanlik farqi', 'fq_gl_mobility_vs_flexibility'),
    ('подвижность и гибкость разница', 'fq_gl_mobility_vs_flexibility'), ('mobility vs flexibility', 'fq_gl_mobility_vs_flexibility'), ('kipping nima', 'fq_gl_kipping_strict'),
    ('что такое киппинг', 'fq_gl_kipping_strict'), ('what is kipping', 'fq_gl_kipping_strict'), ('Rx nima', 'fq_gl_rx_wod_cf_terms'),
    ('что значит rx', 'fq_gl_rx_wod_cf_terms'), ('словарь терминов фитнеса', 'fq_gl_deficit_surplus_maintenance_terms'), ('fitness glossary', 'fq_gl_deficit_surplus_maintenance_terms'),
    ('mehmon taklifnomasi qanday', 'st_guest_pass'), ('гостевое приглашение', 'st_guest_pass'), ('how to invite a guest', 'st_guest_pass'),
    ("sovg'a sertifikati", 'st_gift_certificate'), ('подарочный сертификат', 'st_gift_certificate'), ('gift certificate', 'st_gift_certificate'),
    ('darsga navbat', 'st_class_waitlist'), ('лист ожидания на занятие', 'st_class_waitlist'), ('class waitlist', 'st_class_waitlist'),
    ('oylik eng faollar reytingi', 'st_leaderboard_how'), ('рейтинг активности', 'st_leaderboard_how'), ('join the leaderboard', 'st_leaderboard_how'),
    ("kalendarga qo'shish darslarni", 'st_calendar_feed_ics'), ('добавить занятия в календарь', 'st_calendar_feed_ics'), ('add classes to my calendar', 'st_calendar_feed_ics'),
    ('kirish tarixi', 'st_entry_history_page'), ('история посещений', 'st_entry_history_page'), ('entry history', 'st_entry_history_page'),
    ('murabbiyni baholash', 'st_rate_trainer'), ('поставить оценку тренеру', 'st_rate_trainer'), ('give a trainer a rating', 'st_rate_trainer'),
    ('abonementni bir bosishda yangilash', 'st_one_click_renew'), ('продлить в один клик', 'st_one_click_renew'), ('renew in one click', 'st_one_click_renew'),
    ('muzlatish qoidalari', 'st_freeze_rules_detail'), ('правила заморозки', 'st_freeze_rules_detail'), ('freeze rules', 'st_freeze_rules_detail'),
    ('yordam tugmasi saytda', 'st_support_widget'), ('кнопка помощи на сайте', 'st_support_widget'), ('support widget', 'st_support_widget'),
    ('push bildirishnoma', 'st_push_notifications_how'), ('уведомления в браузере', 'st_push_notifications_how'), ('browser notifications', 'st_push_notifications_how'),
    ('instagram orqali savol', 'st_instagram_bot_dm'), ('бот в инстаграм', 'st_instagram_bot_dm'), ('instagram bot', 'st_instagram_bot_dm'),
    ('qabulxonada kirish tartibi', 'st_desk_checkin_how'), ('что такое fz номер', 'st_desk_checkin_how'), ('how front desk check in works', 'st_desk_checkin_how'),
    ('VIP abonement afzalliklari', 'st_vip_perks'), ('преимущества vip', 'st_vip_perks'), ('vip membership perks', 'st_vip_perks'),
    ('oferta va maxfiylik siyosati', 'st_legal_pages'), ('terms and privacy policy', 'st_legal_pages'), ('tez-tez beriladigan savollar sahifasi', 'st_faq_page'),
    ('страница частых вопросов', 'st_faq_page'), ('faq page', 'st_faq_page'), ('progress sahifasi imkoniyatlari', 'st_tracker_features'),
    ('график веса', 'st_tracker_features'), ('export my results', 'st_tracker_features'), ("tayyor dasturlar ro'yxati", 'st_programs_ready'),
    ('готовые программы список', 'st_programs_ready'), ('stop my program', 'st_programs_ready'), ('murabbiy yordamchi sahifasi nima', 'st_ai_page_what'),
    ('раздел составить план', 'st_ai_page_what'), ('ai coach page', 'st_ai_page_what'), ("to'lovlar tarixi", 'st_payments_history_page'),
    ('история платежей', 'st_payments_history_page'), ('payment history', 'st_payments_history_page'), ("do'kondagi chegirma", 'st_shop_discount_vip'),
    ('скидка в магазине', 'st_shop_discount_vip'), ('shop discount', 'st_shop_discount_vip'), ('akkauntni himoya qilish', 'st_two_factor_security_basics'),
    ('защита аккаунта', 'st_two_factor_security_basics'), ('account security', 'st_two_factor_security_basics'), ('qaysi tillarda ishlaysan', 'st_languages_voice_scope'),
    ('на каких языках ты отвечаешь', 'st_languages_voice_scope'), ('which languages do you speak', 'st_languages_voice_scope'), ('sen qanday ishlaysan', 'st_how_assistant_works'),
    ('откуда твои ответы', 'st_how_assistant_works'), ('where do your answers come from', 'st_how_assistant_works'), ("javob noto'g'ri bo'lsa", 'st_report_wrong_answer'),
    ('ты ошибся', 'st_report_wrong_answer'), ('report a mistake', 'st_report_wrong_answer'), ('profilga nima kiritish kerak', 'st_birthday_goal_profile'),
    ('что заполнить в профиле', 'st_birthday_goal_profile'), ('complete my profile', 'st_birthday_goal_profile'), ('xayrli kun', 'mx_good_morning'),
    ('добрый день', 'mx_good_morning'), ('ismingiz nima', 'mx_what_is_name'), ('как тебя зовут', 'mx_what_is_name'),
    ('sen robotmisan', 'mx_are_robot'), ('ты робот', 'mx_are_robot'), ('are you a robot', 'mx_are_robot'),
    ("seni yaxshi ko'raman", 'mx_love_you'), ('i love you', 'mx_love_you'), ('charchadim', 'mx_feeling_tired'),
    ('я устал', 'mx_feeling_tired'), ('i am tired', 'mx_feeling_tired'), ('tabriklayman', 'mx_congrats_birthday'),
    ('happy birthday', 'mx_congrats_birthday'), ('yordam bering', 'mx_help_me'), ('помогите мне', 'mx_help_me'),
    ('help me', 'mx_help_me'), ('necha yoshdasan', 'mx_age_you'), ('how old are you', 'mx_age_you'),
]


class MatchingTests(TestCase):
    def setUp(self):
        cache.clear()
        GymSettings.load()
        GymSettings.objects.get(pk=1).save()

    def test_kb_size_and_shape(self):
        self.assertGreaterEqual(len(assistant_kb.ENTRIES), 900)
        for e in assistant_kb.ENTRIES:
            for lang in assistant_kb.LANGS:
                self.assertTrue(e["kw"][lang] and e["a"][lang].strip(), (e["id"], lang))

    def test_representative_questions(self):
        for q, lang, want in CASES:
            scored = assistant.score_all(q)
            got = scored[0][1]["id"] if scored and scored[0][0] >= assistant.THRESHOLD else None
            self.assertEqual(got, want, (q, lang))

    def test_wrong_topic_regressions(self):
        """Questions that used to land on the wrong topic (or nowhere) after the audit: the entry that must answer them."""
        want = [
            ("болят мышцы после тренировки что делать", "doms"),  # not the generic "what to do after training" cool-down
            ("how do I cancel my membership", "refund"),  # not "my membership" (the personal status)
            ("is it ok to train every day", "frequency"),  # "train" is not the coach entry "trainers"
            ("what supplements should I take", "supplements"),  # "should" is not "shoulder"
            ("до скольки вы работаете в субботу", "hours"),  # Russian "-ете" and "-ет" forms share one stem
            ("yakshanba kuni zal ishlaydimi", "hours"),
            ("что лучше кардио или силовые", "fat_loss_train"),
            ("можно ли тренироваться при простуде", "sick_train"),
            ("can I bring a guest", "facilities"),
            ("kechqurun ovqat yesam semiraman?", "meal_timing"),
            ("what is a good breakfast for muscle building", "breakfast"),
            ("men 80 kg man, necha kaloriya yeyishim kerak", "tdee"),
            ("Qaysi mashqlar bilan elka rivojlanadi", "overhead_press"),
            ("kartaga pul o'tkazdim", "card_transfer"),
        ]
        for q, eid in want:
            scored = assistant.score_all(q)
            got = scored[0][1]["id"] if scored and scored[0][0] >= assistant.THRESHOLD else None
            self.assertEqual(got, eid, q)

    def test_every_suggested_question_is_answered(self):
        """The coach page offers three example questions in each language: each must get a real answer (the Uzbek 'abs' and 'squat' ones did not)."""
        from .i18n import T
        for lang in ("uz", "ru", "en"):
            for key in ("ai_q1", "ai_q2", "ai_q3"):
                res = assistant.answer(T[lang][key], lang)
                self.assertTrue(res["matched"], (lang, key, T[lang][key]))
        for q in ("Abonementlar narxi", "Ish vaqti"):  # the voice panel's examples
            self.assertTrue(assistant.answer(q, "uz")["matched"], q)

    def test_stemmer_agent_ending(self):
        self.assertEqual(assistant.stem("работаете"), assistant.stem("работает"))
        self.assertFalse(assistant._has("trainer", {"train"}))
        self.assertTrue(assistant._has("kaloriya", {"kaloriyali"}))

    def test_every_language_answers(self):
        for lang in ("uz", "ru", "en"):
            res = assistant.answer("protein", lang)
            self.assertTrue(res["matched"] or res["suggest"])
        self.assertIn("белка", assistant.answer("сколько белка нужно в день", "uz")["answer"])  # Cyrillic question gets a Russian answer
        self.assertIn("protein", assistant.answer("how much protein do I need", "en")["answer"])

    def test_dynamic_facts_come_from_database(self):
        gs = GymSettings.load()
        gs.address, gs.phone = "Toshkent, Sinov ko'chasi 5", "91 111 22 33"
        gs.save()
        Plan.objects.create(code="zz1", name="Maxsus", months=2, price=250000)
        self.assertIn("Sinov ko'chasi 5", assistant.answer("manzil", "uz")["answer"])
        self.assertIn("+998 91 111 22 33", assistant.answer("telefon raqamingiz?", "uz")["answer"])
        self.assertIn("250 000", assistant.answer("abonement narxi qancha", "uz")["answer"])
        self.assertIn("Maxsus", assistant.answer("how much does a membership cost", "en")["answer"])
        gs.open_time, gs.close_time = "07:00", "21:30"
        gs.save()
        self.assertIn("07:00", assistant.answer("ish vaqti", "uz")["answer"])
        self.assertIn("21:30", assistant.answer("ish vaqti", "uz")["answer"])
        self.assertNotIn("{", assistant.answer("ish vaqti", "uz")["answer"])

    def test_no_placeholder_leaks_anywhere(self):
        for e in assistant_kb.ENTRIES:
            for lang in assistant_kb.LANGS:
                if e["id"] in assistant_kb.PERSONAL:
                    continue
                text = assistant.fill(e["a"][lang], assistant.Facts(lang))
                self.assertNotRegex(text, r"\{\w+\}", (e["id"], lang))

    def test_unknown_gives_suggestions(self):
        for q in ("basketbol qoidalari haqida gapirib ber", "what is the capital of france", "", "asdf qwer zxcv"):
            res = assistant.answer(q, "en")
            self.assertFalse(res["matched"])
            self.assertTrue(3 <= len(res["suggest"]) <= 4)
        close = assistant.answer("qaysi mashqlar yaxshi", "uz")
        self.assertFalse(close["matched"])

    def test_regression_set(self):
        """700+ realistic questions in uz (Latin and Cyrillic), ru and en: the entry that must answer each."""
        self.assertGreaterEqual(len(REGRESSION) + len(REGRESSION2), 700)
        wrong = []
        for q, eid in REGRESSION + REGRESSION2:
            scored = assistant.score_all(q)
            got = scored[0][1]["id"] if scored and scored[0][0] >= assistant.THRESHOLD else None
            if got != eid:
                wrong.append((q, eid, got))
        self.assertEqual(wrong, [])

    def test_regression_ids_exist_and_all_areas_covered(self):
        for _, eid in REGRESSION + REGRESSION2:
            self.assertIn(eid, assistant_kb.BY_ID, eid)
        prefixes = {eid.split("_")[0] for _, eid in REGRESSION + REGRESSION2}
        self.assertTrue({"ex", "pg", "hl", "nu", "st", "mx", "qa", "sp", "fd", "fq"} <= prefixes)

    def test_answer_language_follows_the_question(self):
        self.assertIn("Zal har kuni", assistant.answer("Ish vaqti qanday?", "en")["answer"])  # Uzbek question on the English site
        self.assertIn("The gym is open", assistant.answer("what time do you open", "uz")["answer"])
        self.assertIn("Зал работает", assistant.answer("какой график работы зала", "en")["answer"])
        self.assertIn("Zal har kuni", assistant.answer("иш вақти қандай", "ru")["answer"])  # Uzbek written in Cyrillic is answered in Uzbek

    def test_cyrillic_uzbek_and_typos(self):
        self.assertEqual(assistant.translit("Ўтириб туриш қанча"), "otirib turish qancha")
        self.assertEqual(assistant.answer("оқсил қанча керак", "ru")["id"], "protein_need")
        self.assertEqual(assistant.answer("how much protien do i need", "en")["id"], "protein_need")
        self.assertEqual(assistant.answer("kreatinn zararlimi", "uz")["id"], "creatine")

    def test_calculators(self):
        a = lambda q, lang="uz": assistant.answer(q, lang)
        self.assertEqual(a("100 kg necha funt")["id"], "calc_units")
        self.assertIn("220.46 lb", a("100 kg necha funt")["answer"])
        self.assertIn("62.14 mile", a("100 km in miles", "en")["answer"])
        self.assertIn("45.36 kg", a("100 lb kg")["answer"])
        self.assertIn("4", a("2+2")["answer"])
        self.assertEqual(a("15*3")["answer"], "15*3 = 45")
        self.assertEqual(a("сколько будет 100/4", "ru")["answer"], "100/4 = 25")
        self.assertNotEqual(a("__import__('os').system(1+1)")["id"], "calc_math")  # never evaluates code
        self.assertIn("BMI = 24.7", a("vaznim 80 bo'yim 180")["answer"])
        self.assertEqual(a("weight 80 height 180", "en")["id"], "calc_bmi")
        self.assertIn("ИМТ = 24.7", a("вес 80 рост 180", "ru")["answer"])
        self.assertIn("Mifflin", a("men 30 yoshli erkak, vazn 80 kg, bo'y 180 sm")["answer"])
        rm = a("100 kg 5 marta")
        self.assertEqual(rm["id"], "calc_1rm")
        self.assertIn("116.7", rm["answer"])
        self.assertEqual(a("bench 80 kg x 8", "en")["id"], "calc_1rm")
        self.assertNotEqual(a("3-4 kunlik reja")["id"], "calc_math")  # a range is not a subtraction

    def test_time_and_date_come_from_the_server(self):
        now = timezone.localtime()
        self.assertIn(f"{now:%H:%M}", assistant.answer("hozir soat nechchi", "uz")["answer"])
        self.assertEqual(assistant.answer("soat nechchi", "uz")["id"], "calc_time")
        self.assertEqual(assistant.answer("который час", "ru")["id"], "calc_time")
        self.assertEqual(assistant.answer("what is the date today", "en")["id"], "calc_date")
        self.assertIn(str(now.year), assistant.answer("bugungi sana", "uz")["answer"])
        self.assertEqual(assistant.answer("soat nechada ochiladi", "uz")["id"], "hours")  # opening time is not "what time is it"

    def test_fallback_is_honest_and_helpful(self):
        gs = GymSettings.load()
        gs.phone = "90 123 45 67"
        gs.save()
        res = assistant.answer("qwertyuiop asdfgh", "uz")
        self.assertFalse(res["matched"])
        self.assertIsNone(res["id"])
        self.assertIn("+998 90 123 45 67", res["answer"])
        self.assertIn("aniq javobim yo'q", res["answer"])
        self.assertEqual(res["links"][0]["url"], reverse("chat"))
        self.assertTrue(3 <= len(res["suggest"]) <= 4)
        self.assertNotIn("{", res["answer"])
        ru = assistant.answer("какая столица франции", "ru")
        self.assertFalse(ru["matched"])
        self.assertIn("Чат", ru["links"][0]["label"])

    def test_related_chips_for_a_match(self):
        res = assistant.answer("front squat qanday qilinadi", "uz")
        self.assertEqual(len(res["suggest"]), 4)
        self.assertEqual(len(set(res["suggest"])), 4)

    def test_dangerous_topics_never_give_doses(self):
        for q in ("steroid dozasi qancha", "сколько стероидов колоть", "how much steroids should i take"):
            res = assistant.answer(q, "uz")
            self.assertEqual(res["id"], "hl_steroids", q)
            self.assertNotRegex(res["answer"], r"\d+\s?(mg|мг)")

    def test_every_entry_has_a_title_per_language(self):
        for e in assistant_kb.ENTRIES:
            for lang in assistant_kb.LANGS:
                self.assertTrue(assistant.title_of(e, lang).strip())

    def test_small_talk_does_not_hijack_questions(self):
        self.assertEqual(assistant.answer("salom, ish vaqti qanday?", "uz")["id"], "hours")

    def test_personal_answers(self):
        guest = assistant.answer("abonementim qachon tugaydi", "uz")
        self.assertIn("kiring", guest["answer"])
        self.assertEqual(guest["links"][0]["url"], reverse("login"))
        u = User.objects.create_user(username="pers", email="p@x.uz", password="pw12345678", first_name="P")
        self.assertIn("yo'q", assistant.answer("abonementim qachon tugaydi", "uz", u)["answer"])
        plan = Plan.objects.create(code="pp", name="Oylik", months=1, price=100000)
        now = timezone.now()
        Membership.objects.create(user=u, plan=plan, starts=now - timedelta(days=5), expires=now + timedelta(days=10, hours=1))
        self.assertIn("10 kun", assistant.answer("abonementim qachon tugaydi", "uz", u)["answer"])
        self.assertIn("10", assistant.answer("when does my membership expire", "en", u)["answer"])
        FoodEntry.objects.create(user=u, name="Osh", grams=200, kcal=400, protein=12)
        ans = assistant.answer("bugun qancha kaloriya yedim", "uz", u)["answer"]
        self.assertIn("400", ans)
        u.goal = "lose"
        u.save()
        BodyLog.objects.create(user=u, weight=80, height_cm=180)
        prof = assistant.answer("mening vaznim", "uz", u)["answer"]
        self.assertIn("80", prof)
        self.assertIn("BMI 24.7", prof)
        self.assertIn("Ozish", prof)
        self.assertIn("ozish", assistant.answer("menga qanday reja mos", "uz", u)["answer"].lower())


class EndpointTests(TestCase):
    def setUp(self):
        cache.clear()
        GymSettings.load()
        GymSettings.objects.get(pk=1).save()

    def ask(self, client, q, **extra):
        return client.post("/assistant/ask/", data=json.dumps({"q": q}), content_type="application/json", **extra)

    def test_contract_json_and_form(self):
        c = Client()
        d = self.ask(c, "Ish vaqti qanday?").json()
        self.assertEqual(set(d), {"ok", "answer", "links", "matched", "suggest", "approx"})
        self.assertFalse(d["approx"])
        self.assertTrue(d["ok"] and d["matched"])
        d = c.post("/assistant/ask/", {"q": "abonement narxi", "lang": "ru"}).json()  # what voice.js sends
        self.assertTrue(d["matched"])
        self.assertEqual(d["links"][0]["url"], reverse("plans"))
        self.assertEqual(c.post("/assistant/ask/", {"q": "  "}).status_code, 400)
        self.assertEqual(c.get("/assistant/ask/").status_code, 405)
        self.assertFalse(self.ask(c, "qwerty zxcv").json()["matched"])

    def test_csrf_is_enforced(self):
        c = Client(enforce_csrf_checks=True)
        self.assertEqual(self.ask(c, "salom").status_code, 403)
        c.get("/")  # sets the CSRF cookie
        token = c.cookies["csrftoken"].value
        r = self.ask(c, "salom", HTTP_X_CSRFTOKEN=token)
        self.assertEqual(r.status_code, 200)

    def test_rate_limit(self):
        c = Client()
        codes = [self.ask(c, "salom").status_code for _ in range(32)]
        self.assertEqual(codes[:30], [200] * 30)
        self.assertEqual(codes[30:], [429, 429])
        self.assertFalse(self.ask(c, "salom").json()["ok"])

    def test_personal_only_when_logged_in(self):
        u = User.objects.create_user(username="ep", email="e@x.uz", password="pw12345678")
        self.assertIn("kiring", self.ask(Client(), "abonementim qachon tugaydi").json()["answer"])
        c = Client()
        c.force_login(u)
        self.assertIn("yo'q", self.ask(c, "abonementim qachon tugaydi").json()["answer"])

    def test_voice_js_contract(self):
        js = open("gym/static/js/voice.js", encoding="utf-8").read()
        for needle in ("d.ok", "d.answer", "d.links", "d.matched"):
            self.assertIn(needle, js)


class PlanTests(TestCase):
    def test_shapes(self):
        for goal in assistant_plan.GOALS:
            for level in assistant_plan.LEVELS:
                for days in range(2, 7):
                    for eq in assistant_plan.EQUIPMENT:
                        for lang in ("uz", "ru", "en"):
                            p = assistant_plan.build_plan(goal, level, days, eq, lang)
                            self.assertEqual([d["weekday"] for d in p["days"]], list(range(7)))
                            work = [d for d in p["days"] if not d["rest"]]
                            self.assertEqual(len(work), days)
                            for d in work:
                                self.assertTrue(4 <= len(d["exercises"]) <= 8)
                                for ex in d["exercises"]:
                                    self.assertTrue(1 <= ex["sets"] <= 5 and ex["reps"] and ex["name"] and len(ex["note"]) <= 120)
                            for a, b in zip(p["days"], p["days"][1:]):  # no two hard days in a row for 2-3 day plans
                                if days <= 3:
                                    self.assertTrue(a["rest"] or b["rest"])

    def test_goal_changes_scheme(self):
        main = lambda g: assistant_plan.build_plan(g, "intermediate", 3, "gym")["days"][0]["exercises"][0]
        self.assertEqual(main("strength")["reps"], "3-5")
        self.assertEqual(main("muscle")["reps"], "6-10")
        self.assertEqual(main("fat_loss")["reps"], "10-12")
        fat = assistant_plan.build_plan("fat_loss", "beginner", 3, "home")["days"][0]["exercises"]
        self.assertIn("cardio", fat[-1]["key"])
        self.assertEqual(assistant_plan.build_plan("muscle", "beginner", 4, "gym")["days"][0]["label"], "Yuqori tana")

    def test_bad_input_falls_back(self):
        p = assistant_plan.build_plan("zzz", "zzz", "abc", "zzz", "xx")
        self.assertEqual((p["goal"], p["level"], p["days_per_week"], p["equipment"]), ("general", "beginner", 3, "gym"))
        self.assertEqual(assistant_plan.build_plan("muscle", "beginner", 99, "gym")["days_per_week"], 6)

    def test_saved_plan(self):
        u = User.objects.create_user(username="pl", email="pl@x.uz", password="pw12345678")
        WorkoutPlan.objects.create(user=u, title="Eski", active=True)
        obj = assistant_plan.make_plan(u, "fat_loss", "intermediate", 4, "home", "ru")
        self.assertFalse(WorkoutPlan.objects.get(title="Eski").active)
        self.assertEqual(sorted({e.weekday for e in obj.exercises.all()}), [0, 1, 3, 4])
        self.assertTrue(obj.notes)


class CalorieTextTests(TestCase):
    def test_text_examples(self):
        r = calories.parse_text("2 ta somsa va choy")
        self.assertEqual([(i["grams"]) for i in r], [240, 200])
        self.assertAlmostEqual(r[0]["kcal"], 696.0)
        self.assertEqual(calories.parse_text("200 g osh")[0]["grams"], 200)
        self.assertEqual(calories.parse_text("3 tuxum")[0]["grams"], 165)
        self.assertEqual(calories.parse_text("osh va non")[1]["grams"], 150)  # usual portions when no amount is given
        self.assertEqual(calories.parse_text("no food words"), [])


class FallbackTests(TestCase):
    """The nearest-answer fallback (approx), the off-topic and medical guards, the honest unknown answer, and the matching helpers."""

    def setUp(self):
        cache.clear()
        GymSettings.load()
        GymSettings.objects.get(pk=1).save()

    def test_approx_answers_the_closest_topic_with_an_honest_note(self):
        cases = [("mening qo'llarim juda ozg'in nima qilsam bo'ladi", "pg_skinny", "Savolingizni to'liq tushunmadim, ehtimol bu haqida so'ragandirsiz: «"),
                 ("после тренировки трясутся ноги и руки сильно", "fq_muscles_shaking", "Я не до конца понял вопрос, возможно, вы спрашивали про: «"),
                 ("why are my fingers tingling when I lift", "hl_numbness_tingling", "I did not fully understand your question; you may be asking about:")]
        for q, eid, prefix in cases:
            res = assistant.answer(q, "uz")
            self.assertTrue(res["matched"], q)
            self.assertTrue(res["approx"], q)
            self.assertEqual((res["id"], res["kind"]), (eid, "approx"), q)
            self.assertTrue(res["answer"].startswith(prefix), (q, res["answer"][:80]))
            entry = assistant_kb.BY_ID[eid]
            lang = "uz" if "Savolingizni" in prefix else "ru" if "Я не" in prefix else "en"
            self.assertIn(assistant.fill(entry["a"][lang], assistant.Facts(lang))[:40], res["answer"])  # the body is the entry's own text: nothing invented
            self.assertTrue(2 <= len(res["suggest"]) <= 3, (q, res["suggest"]))
            self.assertNotIn("{", res["answer"])

    def test_confident_answers_are_not_approx(self):
        for q in ("Ish vaqti qanday?", "protein qancha kerak", "100 kg necha funt", "salom"):
            res = assistant.answer(q, "uz")
            self.assertTrue(res["matched"])
            self.assertFalse(res["approx"], q)
            self.assertNotIn("tushunmadim", res["answer"])

    def test_old_response_shape_is_kept(self):
        res = assistant.answer("qwertyuiop asdfgh", "uz")
        for key in ("matched", "answer", "links", "suggest", "id", "topic"):
            self.assertIn(key, res)
        self.assertEqual(set(self.client.post("/assistant/ask/", {"q": "abonement narxi"}).json()), {"ok", "answer", "links", "matched", "suggest", "approx"})

    def test_off_topic_questions_are_declined_politely(self):
        for q, word in (("what is the capital of france", "fitness"), ("какая столица франции", "фитнес"), ("python dasturlash o'rgat", "fitnes"),
                        ("solve the equation x squared", "fitness"), ("kim kashf qildi telefonni", "fitnes"), ("write my essay about napoleon", "fitness")):
            res = assistant.answer(q, "uz")
            self.assertFalse(res["matched"], q)
            self.assertEqual(res["kind"], "offtopic", q)
            self.assertFalse(res["approx"])
            self.assertIn(word, res["answer"], q)
            self.assertTrue(3 <= len(res["suggest"]) <= 4)
            self.assertEqual(res["links"][0]["url"], reverse("chat"))

    def test_medicine_doses_are_never_given(self):
        for q in ("ibuprofen necha mg ichsam", "сколько таблеток парацетамола пить", "how many mg of paracetamol should I take"):
            res = assistant.answer(q, "uz")
            self.assertFalse(res["matched"], q)
            self.assertEqual(res["kind"], "medical", q)
            self.assertNotRegex(res["answer"], r"\d+\s?(mg|мг)")
            self.assertTrue(any(w in res["answer"] for w in ("shifokor", "врач", "doctor")))
        self.assertEqual(assistant.answer("kreatin dozasi qancha", "uz")["id"], "mx_q_mass_water_creatine")  # a supplement is not a medicine

    def test_nothing_related_is_honestly_unknown(self):
        gs = GymSettings.load()
        gs.phone = "90 123 45 67"
        gs.save()
        for q in ("qwertyuiop asdfgh", "asdf qwer zxcv", "how to play chess", "щцкгшо жэдлорп"):
            res = assistant.answer(q, "uz")
            self.assertFalse(res["matched"], q)
            self.assertFalse(res["approx"], q)
            self.assertEqual(res["kind"], "unknown", q)
            self.assertIsNone(res["id"])
            self.assertIn("+998 90 123 45 67", res["answer"])
            self.assertTrue(3 <= len(res["suggest"]) <= 4)

    def test_vague_generic_questions_do_not_get_a_random_answer(self):
        for q in ("qaysi mashqlar yaxshi", "basketbol qoidalari haqida gapirib ber", "voleybol o'ynash foydalimi"):
            self.assertFalse(assistant.answer(q, "uz")["matched"], q)

    def test_approx_prefix_follows_the_question_language(self):
        self.assertIn("не до конца", assistant.answer("после тренировки трясутся ноги и руки сильно", "en")["answer"])
        self.assertIn("tushunmadim", assistant.answer("mening qo'llarim juda ozg'in nima qilsam bo'ladi", "en")["answer"])

    def test_stemming_synonyms_and_numbers(self):
        self.assertEqual(assistant.stem("running"), assistant.stem("run"))
        self.assertEqual(assistant.stem("swimming"), "swim")
        self.assertEqual(assistant.tokens("trenirovka"), assistant.tokens("mashq"))
        self.assertEqual(assistant.tokens("30kg"), ["30", "kg"])
        self.assertEqual(assistant.tokens("haftasiga 3kun"), assistant.tokens("xaftasiga 3 kun"))
        self.assertEqual(assistant.translit("Ҳафтасига 3 кун"), "haftasiga 3 kun")

    def test_typo_tolerance(self):
        for q, eid in (("pelvik floor exercises", "sp_pelvic_floor_kegel"), ("plyometrcs for beginners", "ex_plyometrics_beginner"),
                       ("protien qancha kerak", "protein_need"), ("kreatinn zararlimi", "creatine"), ("hamstrng stretch", "ex_stretch_hamstring")):
            scored = assistant.score_all(q)
            got = scored[0][1]["id"] if scored and scored[0][0] >= assistant.THRESHOLD else None
            self.assertEqual(got, eid, q)
        self.assertTrue(assistant._lev2("ashvagandha", "ashwagandha"))
        self.assertFalse(assistant._lev2("squat", "deadlift"))

    def test_site_questions_beat_training_topics_when_the_gym_is_meant(self):
        self.assertEqual(assistant.answer("sizda mehmon taklifnomasi bormi", "uz")["id"], "st_guest_pass")
        self.assertEqual(assistant.answer("is there a waitlist for classes on your site", "en")["id"], "st_class_waitlist")

    def test_new_areas_are_big_enough(self):
        by = {}
        for e in assistant_kb.ENTRIES:
            by[e["id"].split("_")[0]] = by.get(e["id"].split("_")[0], 0) + 1
        self.assertGreaterEqual(by["fq"], 100)  # beginners' short Q&A, etiquette, equipment, glossary
        self.assertGreaterEqual(sum(1 for e in assistant_kb.ENTRIES if e["id"].startswith("mx_m_")), 50)  # myths and weight FAQs
        self.assertGreaterEqual(by["sp"], 30)
        self.assertGreaterEqual(by["fd"], 50)
