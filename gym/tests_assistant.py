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


class MatchingTests(TestCase):
    def setUp(self):
        cache.clear()
        GymSettings.load()
        GymSettings.objects.get(pk=1).save()

    def test_kb_size_and_shape(self):
        self.assertGreaterEqual(len(assistant_kb.ENTRIES), 500)
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
        """200+ realistic questions in uz (Latin and Cyrillic), ru and en: the entry that must answer each."""
        self.assertGreaterEqual(len(REGRESSION), 200)
        wrong = []
        for q, eid in REGRESSION:
            scored = assistant.score_all(q)
            got = scored[0][1]["id"] if scored and scored[0][0] >= assistant.THRESHOLD else None
            if got != eid:
                wrong.append((q, eid, got))
        self.assertEqual(wrong, [])

    def test_regression_ids_exist_and_all_areas_covered(self):
        for _, eid in REGRESSION:
            self.assertIn(eid, assistant_kb.BY_ID, eid)
        prefixes = {eid.split("_")[0] for _, eid in REGRESSION}
        self.assertTrue({"ex", "pg", "hl", "nu", "st", "mx", "qa"} <= prefixes)

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
        self.assertEqual(set(d), {"ok", "answer", "links", "matched", "suggest"})
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
