"""UI strings in three languages. One line per key: key||Uzbek||Russian||English"""

RAW = """
brand||Fitnes Zal||Fitnes Zal||Fitnes Zal
tag||Kuch temirdan boshlanadi||Сила начинается с железа||Strength starts with iron
tag_sub||Zamonaviy jihozlar, tajribali murabbiylar va qulay abonementlar.||Современное оборудование, опытные тренеры и удобные абонементы.||Modern equipment, experienced trainers and flexible memberships.
nav_home||Bosh sahifa||Главная||Home
nav_dash||Kabinet||Кабинет||Dashboard
nav_plans||Abonementlar||Абонементы||Memberships
nav_shop||Do'kon||Магазин||Shop
nav_classes||Mashg'ulotlar||Занятия||Classes
nav_trainers||Murabbiylar||Тренеры||Trainers
nav_progress||Natijalarim||Мои результаты||Progress
nav_reviews||Fikrlar||Отзывы||Reviews
nav_profile||Profil||Профиль||Profile
nav_desk||Qabulxona||Ресепшен||Front desk
nav_admin||Admin panel||Админ-панель||Admin panel
login||Kirish||Войти||Sign in
register||Ro'yxatdan o'tish||Регистрация||Sign up
logout||Chiqish||Выйти||Log out
open||Ochiq||Открыто||Open
closed||Yopiq||Закрыто||Closed
hours||Ish vaqti||Часы работы||Opening hours
first_name||Ism||Имя||First name
last_name||Familiya||Фамилия||Last name
phone||Telefon raqam||Номер телефона||Phone number
password||Parol||Пароль||Password
show||Ko'rsatish||Показать||Show
hide||Yashirish||Скрыть||Hide
or||yoki||или||or
google_off||Google bilan kirish sozlanmagan (serverda GOOGLE_CLIENT_ID kerak).||Вход через Google не настроен (нужен GOOGLE_CLIENT_ID на сервере).||Google sign-in is not configured (the server needs GOOGLE_CLIENT_ID).
no_account||Akkauntingiz yo'qmi?||Нет аккаунта?||No account yet?
have_account||Akkauntingiz bormi?||Уже есть аккаунт?||Already have an account?
err_fields||Maydonlarni to'g'ri to'ldiring||Заполните поля правильно||Please fill in the fields correctly
err_phone||Telefon +998 bilan boshlanib, 9 ta raqamdan iborat bo'lsin||Номер: +998 и 9 цифр||Phone must be +998 followed by 9 digits
err_pass||Parol 6 dan 128 gacha belgi bo'lsin||Пароль от 6 до 128 символов||Password must be 6 to 128 characters
err_exists||Bu raqam allaqachon ro'yxatdan o'tgan||Этот номер уже зарегистрирован||This number is already registered
err_cred||Raqam yoki parol noto'g'ri||Неверный номер или пароль||Wrong number or password
err_blocked||Akkauntingiz bloklangan. Administrator bilan bog'laning||Аккаунт заблокирован. Свяжитесь с администратором||Your account is blocked. Contact the admin
err_rate||Juda ko'p urinish. 10 daqiqadan keyin qayta urining||Слишком много попыток. Повторите через 10 минут||Too many attempts. Try again in 10 minutes
err_stock||Omborda yetarli mahsulot yo'q||Недостаточно товара на складе||Not enough stock
err_method||Bu to'lov usuli hozir ishlamaydi||Этот способ оплаты сейчас недоступен||This payment method is unavailable
err_member||Avval faol abonement kerak||Сначала нужен активный абонемент||You need an active membership first
err_frozen||Abonement muzlatilgan||Абонемент заморожен||Your membership is frozen
err_google||Google akkauntni tekshirib bo'lmadi||Не удалось проверить аккаунт Google||Could not verify the Google account
promo_bad||Promokod noto'g'ri yoki muddati o'tgan||Промокод неверный или просрочен||Promo code is invalid or expired
cart_bad||Savatdagi mahsulot topilmadi||Товар из корзины не найден||A cart item was not found
welcome||Xush kelibsiz!||Добро пожаловать!||Welcome!
saved||Saqlandi||Сохранено||Saved
hello||Salom||Привет||Hi
membership||Abonement||Абонемент||Membership
no_membership||Abonement yo'q||Нет абонемента||No membership
active||Faol||Активен||Active
expired||Tugagan||Истёк||Expired
frozen||Muzlatilgan||Заморожен||Frozen
upcoming||Boshlanmagan||Ещё не начат||Not started
until||gacha||до||until
days_left||kun qoldi||дн. осталось||days left
checkin||Zalga kirdim||Я в зале||I'm at the gym
checked_in||Bugun belgilangan||Сегодня отмечено||Checked in today
check_ok||Tashrif belgilandi. Mashg'ulotingiz samarali o'tsin!||Визит отмечен. Продуктивной тренировки!||Visit recorded. Have a great workout!
visits_month||Shu oydagi tashriflar||Визитов в этом месяце||Visits this month
streak||Ketma-ket kunlar||Дней подряд||Day streak
member_id||A'zo raqami||Номер члена клуба||Member ID
expiring||Abonement {days} kundan keyin tugaydi. Uzaytirib qo'ying.||Абонемент закончится через {days} дн. Продлите заранее.||Your membership ends in {days} days. Renew in advance.
pending_note||To'lovingiz tasdiq kutmoqda. Zalda to'lang, administrator tasdiqlaydi.||Ваш платёж ждёт подтверждения. Оплатите в зале, администратор подтвердит.||Your payment awaits confirmation. Pay at the gym and the admin will confirm.
announcements||E'lonlar||Объявления||Announcements
my_bookings||Mening bronlarim||Мои записи||My bookings
none_yet||Hozircha yo'q||Пока нет||Nothing yet
contacts||Aloqa||Контакты||Contact
address||Manzil||Адрес||Address
price_unit||so'm||сум||UZS
months_n||{n} oy||{n} мес.||{n} mo
buy||Sotib olish||Купить||Buy
pay||To'lov||Оплата||Payment
pay_method||To'lov usuli||Способ оплаты||Payment method
cash||Zalda naqd||Наличными в зале||Cash at the gym
promo||Promokod||Промокод||Promo code
bought_paid||Abonement faollashdi.||Абонемент активирован.||Membership activated.
bought_pending||Zalda to'lang. Administrator tasdiqlagach abonement faollashadi.||Оплатите в зале. Абонемент включится после подтверждения.||Pay at the gym. Your membership starts once the admin confirms.
demo_note||To'lov usullari sinov rejimida: haqiqiy to'lov tizimi ulanmagan.||Способы оплаты в тестовом режиме: платёжная система не подключена.||Payment methods are in test mode: no real gateway is connected.
perk_all||Barcha zonalar||Все зоны||All zones
perk_save||200 000 so'm tejaysiz||Экономия 200 000 сум||Save 200,000 UZS
perk_consult||Murabbiy konsultatsiyasi||Консультация тренера||Trainer consultation
perk_locker||Shaxsiy shkaf||Личный шкафчик||Personal locker
perk_sauna||Sauna||Сауна||Sauna
perk_vip||VIP zona||VIP-зона||VIP zone
plan_m1||1 oylik||1 месяц||1 month
plan_m3||3 oylik||3 месяца||3 months
plan_vip||VIP 1 oylik||VIP 1 месяц||VIP 1 month
freeze||Abonementni muzlatish||Заморозка абонемента||Freeze membership
freeze_help||Bir marta, {max} kungacha. Muddat shuncha kunga uzayadi.||Один раз, до {max} дн. Срок продлится на столько же дней.||Once, up to {max} days. Your end date moves by the same number of days.
freeze_do||Muzlatish||Заморозить||Freeze
freeze_days||Kunlar||Дни||Days
freeze_ok||Abonement muzlatildi.||Абонемент заморожен.||Membership frozen.
freeze_fail||Muzlatib bo'lmadi (allaqachon ishlatilgan yoki abonement yo'q).||Не удалось заморозить (уже использовано или нет абонемента).||Could not freeze (already used, or no membership).
frozen_until||Muzlatish tugaydi:||Заморозка до:||Frozen until:
shop||Do'kon||Магазин||Shop
all||Hammasi||Все||All
search||Qidirish||Поиск||Search
in_stock||Omborda||В наличии||In stock
sold_out||Tugagan||Нет в наличии||Sold out
add||Qo'shish||Добавить||Add
cart||Savat||Корзина||Cart
cart_empty||Savat bo'sh||Корзина пуста||Your cart is empty
remove||Olib tashlash||Убрать||Remove
update||Yangilash||Обновить||Update
total||Jami||Итого||Total
discount||Chegirma||Скидка||Discount
checkout||Buyurtma berish||Оформить заказ||Place order
order_ok||Buyurtma qabul qilindi. Zalda oling.||Заказ принят. Заберите в зале.||Order placed. Pick it up at the gym.
login_first||Davom etish uchun tizimga kiring||Войдите, чтобы продолжить||Please sign in to continue
orders||Buyurtmalarim||Мои заказы||My orders
payments||To'lovlar||Платежи||Payments
receipt||Kvitansiya||Квитанция||Receipt
print||Chop etish||Печать||Print
user||A'zo||Клиент||Member
date||Sana||Дата||Date
type||Turi||Тип||Type
amount||Summa||Сумма||Amount
status||Holat||Статус||Status
item||Mahsulot||Товар||Item
qty||Soni||Кол-во||Qty
st_pending||Tasdiq kutilmoqda||Ожидает подтверждения||Awaiting confirmation
st_paid||To'langan||Оплачено||Paid
st_cancelled||Bekor qilingan||Отменено||Cancelled
st_new||Yangi||Новый||New
st_done||Berildi||Выдан||Handed over
kind_plan||Abonement||Абонемент||Membership
kind_shop||Do'kon||Магазин||Shop
classes||Guruh mashg'ulotlari||Групповые занятия||Group classes
next_session||Navbatdagi:||Ближайшее:||Next:
seats_left||{n} ta joy||мест: {n}||{n} seats left
full||Joy qolmadi||Мест нет||Full
book||Bron qilish||Записаться||Book
booked||Bron qilingan||Вы записаны||Booked
cancel_booking||Bekor qilish||Отменить||Cancel
book_ok||Joy bron qilindi.||Вы записаны.||Booked.
book_fail||Bron qilib bo'lmadi.||Не удалось записаться.||Could not book.
cancel_ok||Bron bekor qilindi.||Запись отменена.||Booking cancelled.
trainer||Murabbiy||Тренер||Trainer
trainers||Murabbiylar||Тренеры||Trainers
years_exp||yil tajriba||лет опыта||years of experience
weekday_0||Dushanba||Понедельник||Monday
weekday_1||Seshanba||Вторник||Tuesday
weekday_2||Chorshanba||Среда||Wednesday
weekday_3||Payshanba||Четверг||Thursday
weekday_4||Juma||Пятница||Friday
weekday_5||Shanba||Суббота||Saturday
weekday_6||Yakshanba||Воскресенье||Sunday
progress||Natijalarim||Мои результаты||My progress
progress_help||Vazn va bo'yingizni yozib boring, grafik o'zi chiziladi.||Записывайте вес и рост, график построится сам.||Log your weight and height and the chart draws itself.
weight||Vazn (kg)||Вес (кг)||Weight (kg)
height||Bo'y (sm)||Рост (см)||Height (cm)
note||Izoh||Заметка||Note
bmi||BMI||ИМТ||BMI
bmi_low||Vazn yetishmaydi||Недостаток веса||Underweight
bmi_ok||Me'yoriy||Норма||Normal
bmi_high||Ortiqcha vazn||Избыточный вес||Overweight
bmi_obese||Semizlik||Ожирение||Obese
change||O'zgarish||Изменение||Change
delete||O'chirish||Удалить||Delete
sure||Aniqmi?||Точно?||Sure?
reviews||Fikrlar||Отзывы||Reviews
review_help||Fikringiz administrator ko'rib chiqqach saytda chiqadi.||Отзыв появится после проверки администратором.||Your review appears once the admin approves it.
rating||Baho||Оценка||Rating
comment||Fikr||Отзыв||Comment
send||Yuborish||Отправить||Send
review_ok||Rahmat! Fikringiz tekshiruvga yuborildi.||Спасибо! Отзыв отправлен на проверку.||Thanks! Your review was sent for approval.
profile||Profil||Профиль||Profile
save||Saqlash||Сохранить||Save
language||Til||Язык||Language
theme||Rejim||Режим||Theme
light||Yorug'||Светлый||Light
dark||Qorong'i||Тёмный||Dark
auto||Avto||Авто||Auto
change_pass||Parolni o'zgartirish||Сменить пароль||Change password
cur_pass||Joriy parol||Текущий пароль||Current password
new_pass||Yangi parol||Новый пароль||New password
err_wrong_pass||Joriy parol noto'g'ri||Текущий пароль неверный||Current password is wrong
desk||Qabulxona||Ресепшен||Front desk
desk_find||A'zoni qidirish (telefon, ism yoki FZ-raqam)||Поиск клиента (телефон, имя или FZ-номер)||Find a member (phone, name or FZ number)
desk_checkin||Kirishni belgilash||Отметить вход||Check in
desk_sell||Naqd sotish||Продать за наличные||Sell for cash
desk_pending||Tasdiq kutayotgan to'lovlar||Платежи на подтверждение||Payments awaiting confirmation
desk_orders||Berilishi kerak buyurtmalar||Заказы к выдаче||Orders to hand over
confirm||Tasdiqlash||Подтвердить||Confirm
hand_over||Berildi||Выдано||Handed over
block||Bloklash||Заблокировать||Block
unblock||Blokdan chiqarish||Разблокировать||Unblock
visits_today||Bugungi tashriflar||Визитов сегодня||Visits today
active_members||Faol a'zolar||Активных клиентов||Active members
done_ok||Bajarildi.||Готово.||Done.
rating_avg||O'rtacha baho||Средняя оценка||Average rating
footer_demo||Bu sinov ma'lumotlari bilan ishlaydigan loyiha.||Проект работает на тестовых данных.||This project runs on sample data.
no_results||Hech narsa topilmadi||Ничего не найдено||Nothing found
forgot||Parolni unutdingizmi?||Забыли пароль?||Forgot your password?
forgot_help||Telefon raqamingizni kiriting, SMS orqali kod yuboramiz.||Введите номер телефона, мы отправим код по SMS.||Enter your phone number and we'll text you a code.
send_code||Kod yuborish||Отправить код||Send code
sms_code||SMS kod||Код из SMS||SMS code
otp_sent||Agar raqam ro'yxatdan o'tgan bo'lsa, kod yuborildi.||Если номер зарегистрирован, код отправлен.||If the number is registered, a code was sent.
otp_bad||Kod noto'g'ri yoki muddati o'tgan||Код неверный или просрочен||The code is wrong or expired
sms_fail||SMS yuborib bo'lmadi. Keyinroq urinib ko'ring.||Не удалось отправить SMS. Попробуйте позже.||Could not send the SMS. Try again later.
reset_ok||Parol yangilandi. Endi kiring.||Пароль обновлён. Теперь войдите.||Password updated. You can sign in now.
verify_needed||Davom etish uchun telefon raqamingizni tasdiqlang.||Подтвердите номер телефона, чтобы продолжить.||Please verify your phone number to continue.
verify_phone||Telefonni tasdiqlash||Подтвердить телефон||Verify phone
verify_help||Kod quyidagi raqamga yuboriladi:||Код придёт на номер:||The code is sent to:
verified||Tasdiqlangan||Подтверждён||Verified
verified_ok||Telefon tasdiqlandi.||Телефон подтверждён.||Phone verified.
add_phone_first||Avval profilga telefon raqamingizni kiriting.||Сначала добавьте номер телефона в профиле.||Add your phone number in your profile first.
member_card||A'zo kartasi||Карта клиента||Member card
card_help||Qabulxonada shu QR kodni ko'rsating.||Покажите этот QR-код на ресепшене.||Show this QR code at the front desk.
achievements||Yutuqlar||Достижения||Achievements
points||Ball||Баллы||Points
points_help||Har tashrif 10 ball, har bron 5, har buyurtma 2, taklif qilingan do'st 50 ball beradi.||10 баллов за визит, 5 за запись, 2 за заказ, 50 за приглашённого друга.||10 points per visit, 5 per booking, 2 per order, 50 per invited friend.
leaderboard||Shu oyning eng faollari||Самые активные в этом месяце||Most active this month
leaderboard_help||Faqat ism va familiya bosh harfi ko'rinadi. Profilda o'chirib qo'yish mumkin.||Видны только имя и первая буква фамилии. Можно отключить в профиле.||Only your first name and last initial show. You can opt out in your profile.
show_board||Reytingda ko'rinishim||Показывать меня в рейтинге||Show me on the leaderboard
ach_visits_1||Birinchi tashrif||Первый визит||First visit
ach_visits_10||10 ta tashrif||10 визитов||10 visits
ach_visits_25||25 ta tashrif||25 визитов||25 visits
ach_visits_50||50 ta tashrif||50 визитов||50 visits
ach_visits_100||100 ta tashrif||100 визитов||100 visits
ach_visits_250||250 ta tashrif||250 визитов||250 visits
ach_streak_7||7 kun ketma-ket||7 дней подряд||7-day streak
ach_streak_30||30 kun ketma-ket||30 дней подряд||30-day streak
ach_classes_5||5 ta guruh mashg'uloti||5 групповых занятий||5 group classes
ach_first_order||Birinchi xarid||Первая покупка||First purchase
ach_tracker_3||3 marta o'lchash||3 замера тела||3 body measurements
ach_reviewer||Fikr qoldirdi||Оставил(а) отзыв||Left a review
ach_referrer||Do'st olib keldi||Привёл(а) друга||Brought a friend
workouts||Mashq rejam||Мой план тренировок||My workout plan
today||bugun||сегодня||today
mark_done||Bajardim||Выполнено||Mark done
done_mark||Bajarildi||Сделано||Done
no_plan||Hozircha murabbiy sizga reja bermagan. Qabulxonada so'rang.||Тренер пока не составил вам план. Спросите на ресепшене.||Your trainer hasn't set a plan yet. Ask at the front desk.
today_ex||Bugun: {done} / {total} mashq||Сегодня: {done} / {total} упражнений||Today: {done} / {total} exercises
rest_day||Bugun dam olish kuni||Сегодня день отдыха||Rest day today
offline_title||Internet yo'q||Нет интернета||You're offline
offline_text||Aloqa tiklangach sahifa o'zi ochiladi.||Страница откроется, когда появится связь.||The page will work again once you're back online.
retry||Qayta urinish||Повторить||Try again
scan||QR skaner||QR-сканер||QR scanner
scan_start||Kamerani yoqish||Включить камеру||Start camera
scan_manual||Kodni qo'lda kiriting yoki skanerdan o'tkazing||Введите код вручную или считайте сканером||Type the code or use a scanner
scan_help||USB skaner kodni shu maydonga yozadi. Telefon kamerasi faqat Chrome va Edge'da ishlaydi.||USB-сканер вводит код в это поле. Камера работает только в Chrome и Edge.||A USB scanner types the code into this field. The camera works in Chrome and Edge only.
scan_err||Server bilan aloqa yo'q||Нет связи с сервером||Can't reach the server
scan_nocam||Bu brauzerda kamera orqali skanerlash yo'q. Kodni qo'lda kiriting.||В этом браузере нет сканирования камерой. Введите код вручную.||Camera scanning isn't available in this browser. Type the code instead.
scan_bad||Kod noto'g'ri||Неверный код||Invalid code
scan_ok||Kirish belgilandi||Вход отмечен||Check-in recorded
invite||Do'stni taklif qiling||Пригласите друга||Invite a friend
invite_help||Do'stingiz shu havola orqali ro'yxatdan o'tib, birinchi abonementini olsa, ikkalangizga {days} kun bonus qo'shiladi.||Если друг зарегистрируется по этой ссылке и купит первый абонемент, вам обоим добавится по {days} дн.||When your friend signs up with this link and buys a first membership, you both get {days} bonus days.
copy||Nusxa olish||Копировать||Copy
copied||Nusxalandi||Скопировано||Copied
invited_n||Taklif qilinganlar: {n}, bonus olganlar: {ok}||Приглашено: {n}, получили бонус: {ok}||Invited: {n}, rewarded: {ok}
invited_by||{name} sizni taklif qildi. Birinchi abonementingizda bonus kunlar olasiz.||{name} пригласил(а) вас. За первый абонемент вы получите бонусные дни.||{name} invited you. You'll get bonus days with your first membership.
pt||Shaxsiy mashg'ulot||Персональная тренировка||Personal training
pt_time||Qulay vaqt||Удобное время||Preferred time
pt_request||So'rov yuborish||Отправить запрос||Send request
pt_mine||Mening shaxsiy mashg'ulotlarim||Мои персональные тренировки||My personal sessions
pt_requested||So'ralgan||Запрошено||Requested
pt_confirmed||Tasdiqlangan||Подтверждено||Confirmed
pt_cancelled||Bekor qilingan||Отменено||Cancelled
pt_bad||Vaqt noto'g'ri: kamida 1 soatdan keyin, 60 kun ichida, zal ish vaqtida bo'lsin (kutayotgan so'rov 3 tadan oshmasin).||Неверное время: не раньше чем через час, в пределах 60 дней и в часы работы (не больше 3 ожидающих запросов).||Invalid time: at least 1 hour ahead, within 60 days, during opening hours (max 3 pending requests).
pt_sent||So'rov yuborildi. Tasdiqlansa xabar olasiz.||Запрос отправлен. Вы получите сообщение после подтверждения.||Request sent. You'll hear back once it's confirmed.
pt_requests||Shaxsiy mashg'ulot so'rovlari||Запросы на персональные тренировки||Personal training requests
click_online||Click (onlayn)||Click (онлайн)||Click (online)
tg_help||Salom! Hisobingizni ulash uchun saytdagi profilingizdan Telegram tugmasini bosing.||Привет! Чтобы подключить аккаунт, нажмите кнопку Telegram в профиле на сайте.||Hi! To link your account, press the Telegram button in your profile on the website.
tg_linked||{name}, hisobingiz ulandi. Eslatmalarni shu yerda olasiz. /status, /stop||{name}, аккаунт подключён. Напоминания будут приходить сюда. /status, /stop||{name}, your account is linked. Reminders will arrive here. /status, /stop
tg_unlinked||Telegram uzildi.||Telegram отключён.||Telegram unlinked.
tg_status_active||Abonementingiz {date} gacha faol ({days} kun qoldi).||Абонемент активен до {date} (осталось {days} дн.).||Your membership is active until {date} ({days} days left).
tg_status_none||Hozir faol abonementingiz yo'q.||Сейчас нет активного абонемента.||You have no active membership right now.
tg_expiring||Abonementingiz {date} da tugaydi ({days} kun qoldi). Uzaytirib qo'ying.||Абонемент заканчивается {date} (осталось {days} дн.). Продлите заранее.||Your membership ends on {date} ({days} days left). Renew in advance.
tg_class_tomorrow||Ertaga {time} da "{name}" mashg'ulotiga bron qilgansiz.||Завтра в {time} у вас запись на «{name}».||Tomorrow at {time} you're booked for "{name}".
tg_pt_confirmed||Shaxsiy mashg'ulot tasdiqlandi: {trainer}, {time}.||Персональная тренировка подтверждена: {trainer}, {time}.||Personal training confirmed: {trainer}, {time}.
tg_pt_cancelled||Shaxsiy mashg'ulot bekor qilindi: {trainer}.||Персональная тренировка отменена: {trainer}.||Personal training cancelled: {trainer}.
tg_pt_soon||Yaqinda shaxsiy mashg'ulot: {trainer}, {time}.||Скоро персональная тренировка: {trainer}, {time}.||Personal training coming up: {trainer}, {time}.
tg_connect||Telegramni ulash||Подключить Telegram||Connect Telegram
tg_connected||Telegram ulangan||Telegram подключён||Telegram connected
tg_disconnect||Uzish||Отключить||Disconnect
card_transfer||Karta orqali o'tkazma||Перевод на карту||Card transfer
transfer_title||Karta orqali to'lov||Оплата переводом на карту||Pay by card transfer
transfer_step1||1-qadam. Quyidagi kartaga aynan shu summani o'tkazing (Payme, Click, Uzum yoki bank ilovasidan).||Шаг 1. Переведите ровно эту сумму на карту ниже (через Payme, Click, Uzum или приложение банка).||Step 1. Transfer exactly this amount to the card below (via Payme, Click, Uzum or your bank app).
transfer_step2||2-qadam. O'tkazgach, qaysi kartadan o'tkazganingizning oxirgi 4 raqamini yozib "To'ladim" tugmasini bosing.||Шаг 2. После перевода введите последние 4 цифры карты, с которой платили, и нажмите «Я оплатил».||Step 2. After transferring, enter the last 4 digits of the card you paid from and press "I've paid".
card_number||Karta raqami||Номер карты||Card number
card_holder||Karta egasi||Владелец карты||Card holder
transfer_amount||Summa||Сумма||Amount
transfer_comment||O'tkazma izohi (kodni yozing)||Комментарий к переводу (укажите код)||Transfer comment (write this code)
transfer_exact||Summa aynan shunday bo'lsin va izohga kodni yozing. Shunda to'lovingizni tez topamiz.||Сумма должна быть точной, а в комментарии укажите код. Так мы быстрее найдём ваш платёж.||The amount must match exactly, and put the code in the comment so we can find your payment quickly.
transfer_what||To'lov uchun||За что||For
transfer_reported||To'lov qilganingiz haqida xabar yuborildi (jo'natuvchi karta ••••{sender}). Xodim pulni ko'rib tasdiqlaydi, odatda tez.||Сообщение об оплате отправлено (карта отправителя ••••{sender}). Сотрудник проверит поступление и подтвердит.||Your payment notice was sent (sender card ••••{sender}). Staff will check the money arrived and confirm.
sender_last4||Kartangizning oxirgi 4 raqami||Последние 4 цифры вашей карты||Last 4 digits of your card
sender_last4_help||Faqat 4 ta raqam, to'liq karta raqamini yozmang.||Только 4 цифры, полный номер карты не вводите.||Only 4 digits. Never type your full card number.
i_paid||To'ladim||Я оплатил||I've paid
transfer_deadline||Muddat:||Срок:||Deadline:
pay_cancel||To'lovni bekor qilish||Отменить платёж||Cancel payment
pay_cancelled||To'lov bekor qilindi.||Платёж отменён.||Payment cancelled.
pay_now||To'lash||Оплатить||Pay now
no_card_note||Hozir karta ulanmagan. Zalda naqd to'lang yoki administrator bilan bog'laning.||Карта сейчас не подключена. Оплатите наличными в зале или свяжитесь с администратором.||No card is connected right now. Pay cash at the gym or contact the admin.
report_sent||Xabaringiz yuborildi. To'lov tasdiqlangach abonement/buyurtma faollashadi.||Сообщение отправлено. После подтверждения платежа абонемент/заказ активируется.||Notice sent. Your membership/order activates once the payment is confirmed.
err_last4||Kartaning oxirgi 4 raqamini yozing||Введите последние 4 цифры карты||Enter the last 4 digits of the card
proof_yes||To'ladim degan||Сообщил(а) об оплате||Says paid
proof_no||Hali xabar yo'q||Пока без сообщения||Not reported yet
confirm_money||Pul kartaga tushganini ko'rdingizmi?||Вы видите поступление на карту?||Did you see the money arrive?
reject||Rad etish||Отклонить||Reject
pending_card_note||Karta o'tkazmasi tugallanmagan yoki tasdiq kutmoqda. To'lovlar bo'limiga o'ting.||Перевод на карту не завершён или ждёт подтверждения. Откройте раздел «Платежи».||Your card transfer is unfinished or awaiting confirmation. Open Payments.
tg_payment_ok||To'lov tasdiqlandi: {amount} so'm ({ref}). Rahmat!||Платёж подтверждён: {amount} сум ({ref}). Спасибо!||Payment confirmed: {amount} UZS ({ref}). Thank you!
tg_payment_rejected||To'lov ({ref}) rad etildi yoki bekor qilindi. Savol bo'lsa qabulxonaga murojaat qiling.||Платёж ({ref}) отклонён или отменён. По вопросам обратитесь на ресепшен.||Payment ({ref}) was rejected or cancelled. Ask the front desk if you have questions.
nav_training||Mashq darslari||Видеоуроки||Lessons
training||Mashq darslari||Уроки тренировок||Training lessons
training_help||Har kun uchun mashg'ulotlar: video, qanday bajarilishi va maslahatlar.||Тренировки на каждый день: видео, техника выполнения и советы.||Workouts for every day: video, how to do them, and tips.
all_types||Barcha turlar||Все типы||All types
level||Daraja||Уровень||Level
level_beginner||Boshlang'ich||Начальный||Beginner
level_intermediate||O'rta||Средний||Intermediate
level_advanced||Yuqori||Продвинутый||Advanced
watch||Video||Видео||Video
every_day||Har kuni||Каждый день||Every day
how_to||Qanday bajariladi||Как выполнять||How to do it
muscles||Ishlaydigan mushaklar||Какие мышцы работают||Muscles worked
equipment||Jihoz||Инвентарь||Equipment
tips||Xatolar va maslahatlar||Ошибки и советы||Mistakes and tips
open_video||Videoni ochish||Открыть видео||Open video
no_video||Bu dars uchun video hali qo'shilmagan. Qadamlarni o'qing yoki murabbiydan so'rang.||Видео к этому уроку пока нет. Прочитайте шаги или спросите тренера.||No video for this lesson yet. Read the steps or ask a trainer.
related||Shu turdagi boshqa darslar||Другие уроки этого типа||More lessons of this type
safety_note||Mashqni boshlashdan oldin qizdiring. Og'riq sezsangiz to'xtang. Sog'lig'ingizda muammo bo'lsa, avval shifokor yoki murabbiy bilan maslahatlashing.||Перед тренировкой разомнитесь. При боли прекратите. Если есть проблемы со здоровьем, сначала посоветуйтесь с врачом или тренером.||Warm up first. Stop if you feel pain. If you have health issues, check with a doctor or trainer before you start.
vip_get||VIP sotib olish||Купить VIP||Get VIP
vip_extend||VIP ni uzaytirish||Продлить VIP||Extend VIP
vip_locked||Faqat VIP uchun||Только для VIP||VIP only
vip_unlock_text||Bu darsni ko'rish uchun VIP obuna oling. Narxi oyiga atigi 50 000 so'm.||Чтобы открыть этот урок, оформите VIP. Всего 50 000 сум в месяц.||Get VIP to open this lesson. Just 50,000 UZS a month.
vip_tag||Maxsus darslar, do'kon chegirmasi va ikki baravar ball.||Эксклюзивные уроки, скидка в магазине и двойные баллы.||Exclusive lessons, shop discount and double points.
vip_active||VIP faol||VIP активен||VIP active
vip_via_plan||VIP imkoniyatlari VIP abonementingiz bilan berilgan.||VIP-возможности даны вашим VIP-абонементом.||Your VIP-plan membership already includes VIP perks.
vip_perks||VIP imkoniyatlari||Возможности VIP||VIP perks
vip_perk_videos||{n} ta maxsus dars: haftalik dasturlar, ovqatlanish, yog' yoqish||{n} эксклюзивных уроков: недельные программы, питание, жиросжигание||{n} exclusive lessons: weekly programs, nutrition, fat burning
vip_perk_discount||Do'kondagi har bir xariddan {pct}% chegirma||Скидка {pct}% на каждую покупку в магазине||{pct}% off every shop purchase
vip_perk_points||Ball ikki baravar: reytingda tezroq ko'tarilasiz||Баллы x2: быстрее поднимаетесь в рейтинге||Double points: climb the leaderboard faster
vip_perk_badge||Profilingizda VIP belgisi||Значок VIP в профиле||A VIP badge on your profile
vip_days_note||Muddat: {days} kun. Qayta sotib olsangiz, kunlar ustiga qo'shiladi.||Срок: {days} дн. При повторной покупке дни суммируются.||Duration: {days} days. Buying again adds days on top.
vip_ok||VIP faollashdi. Xush kelibsiz!||VIP активирован. Добро пожаловать!||VIP activated. Welcome!
vip_pending||VIP to'lovi tasdiq kutmoqda. Tasdiqlangach faollashadi.||Оплата VIP ожидает подтверждения. После подтверждения VIP включится.||Your VIP payment awaits confirmation. VIP starts once it's confirmed.
kind_vip||VIP obuna||VIP-подписка||VIP pass
chat||Chat||Чат||Chat
chat_rules||A'zolar bilan yozishing. Hurmat bilan muomala qiling: haqorat, spam va telefon raqam so'rash taqiqlanadi. Shikoyat qilingan xabarlarni xodimlar ko'rib chiqadi.||Общайтесь с участниками. Будьте вежливы: оскорбления, спам и выпрашивание номеров запрещены. Жалобы на сообщения рассматривают сотрудники.||Chat with other members. Be respectful: no insults, spam or asking for phone numbers. Staff review reported messages.
chat_banned_notice||Siz chatda yozishdan chetlatilgansiz. Administrator bilan bog'laning.||Вам запрещено писать в чат. Свяжитесь с администратором.||You are not allowed to post in chat. Contact the admin.
room_general||Umumiy xona||Общая комната||General room
room_vip||VIP xona||VIP-комната||VIP room
room_general_help||Hamma a'zolar uchun ochiq suhbat||Открытый чат для всех участников||An open chat for every member
room_vip_help||Faqat VIP a'zolar uchun yopiq suhbat||Закрытый чат только для VIP||A private chat for VIP members only
chat_vip_only||Bu xona faqat VIP a'zolar uchun.||Эта комната только для VIP.||This room is for VIP members only.
chat_people||A'zoni topish||Найти участника||Find a member
chat_search||Ism yoki a'zo raqami||Имя или номер клиента||Name or member number
chat_min_search||Kamida 2 ta harf yozing.||Введите минимум 2 символа.||Type at least 2 characters.
chat_start_btn||Yozish||Написать||Message
chat_mine||Mening suhbatlarim||Мои переписки||My conversations
chat_blocked_tag||bloklangan||заблокирован||blocked
chat_deleted||Xabar o'chirilgan||Сообщение удалено||Message deleted
chat_blocked_list||Bloklaganlarim||Заблокированные мной||People I blocked
chat_block||Bloklash||Заблокировать||Block
chat_unblock||Blokdan chiqarish||Разблокировать||Unblock
chat_privacy_note||Sizni faqat ism va familiya bosh harfi bilan ko'rishadi, telefon raqamingiz hech kimga ko'rinmaydi. Qidiruvdan chiqib ketish:||Вас видят только по имени и первой букве фамилии, номер телефона никому не виден. Скрыться из поиска:||Others see only your first name and last initial; your phone number is never shown. To hide from search:
chat_you||Siz||Вы||You
chat_delete||O'chirish||Удалить||Delete
chat_report||Shikoyat||Пожаловаться||Report
chat_report_sent||Shikoyat yuborildi. Rahmat.||Жалоба отправлена. Спасибо.||Report sent. Thank you.
chat_empty_room||Hali xabar yo'q. Birinchi bo'lib yozing!||Сообщений пока нет. Напишите первым!||No messages yet. Be the first!
chat_blocked_notice||Bu suhbatda yozib bo'lmaydi (blok).||В этой переписке писать нельзя (блокировка).||You can't write in this conversation (blocked).
chat_type||Xabar yozing...||Напишите сообщение...||Write a message...
chat_send||Yuborish||Отправить||Send
chat_visible_label||Chatda a'zolar meni qidirib topa olsin||Разрешить участникам находить меня в чате||Let members find me in chat
chat_banned||Siz chatda yozishdan chetlatilgansiz.||Вам запрещено писать в чат.||You are not allowed to post in chat.
chat_forbidden||Bu xonaga ruxsat yo'q.||Нет доступа к этой комнате.||No access to this room.
chat_empty||Xabar bo'sh.||Сообщение пустое.||The message is empty.
chat_long||Xabar juda uzun (eng ko'pi 1000 belgi).||Сообщение слишком длинное (максимум 1000 символов).||The message is too long (1000 characters max).
chat_blocked||Bu a'zoga yozib bo'lmaydi.||Этому участнику писать нельзя.||You can't message this member.
vip_videos||VIP videolar||VIP-видео||VIP videos
vip_perk_chat||VIP xona: faqat VIP a'zolar uchun yopiq chat||VIP-комната: закрытый чат только для VIP||VIP room: a private chat for VIP members only
min_short||daq||мин||min
popular||Ommabop||Хит||Popular
low_stock||Kam qoldi||Мало осталось||Almost gone
vip_shop_note||VIP sifatida har bir xariddan {pct}% chegirma olasiz, u savatda avtomatik hisoblanadi.||Как VIP вы получаете скидку {pct}% на каждую покупку, она считается в корзине автоматически.||As VIP you get {pct}% off every purchase; it is applied in the cart automatically.
vip_price_hint||VIP a'zolar uchun {pct}% arzonroq →||Для VIP на {pct}% дешевле →||{pct}% cheaper for VIP members →
related_products||O'xshash mahsulotlar||Похожие товары||Related products
free_pt_note||Sizda shu oy {n} ta bepul shaxsiy konsultatsiya bor: keyingi so'rovingiz bepul bo'ladi.||У вас в этом месяце {n} бесплатная консультация: следующий запрос будет бесплатным.||You have {n} free consultation(s) this month: your next request is free.
vip_free||VIP bepul||VIP бесплатно||VIP free
trainer_open||Batafsil||Подробнее||Details
trainer_classes||Olib boradigan mashg'ulotlari||Ведёт занятия||Group classes
vip_tag2||Ko'proq imkoniyat, ko'proq natija: maxsus darslar, ajratilgan joylar, bepul konsultatsiya va mehmon olib kelish.||Больше возможностей, больше результата: эксклюзивные уроки, места за вами, бесплатная консультация и гость.||More access, better results: exclusive lessons, reserved spots, a free consultation and a guest pass.
vip_card||VIP kartasi||VIP-карта||VIP card
vip_not_active||Faol emas||Не активна||Not active
vip_guest_left||Mehmon taklifnomalari (shu oy)||Гостевые приглашения (этот месяц)||Guest passes (this month)
vip_pt_left||Bepul konsultatsiyalar (shu oy)||Бесплатные консультации (этот месяц)||Free consultations (this month)
vip_seats||Har mashg'ulotda siz uchun ajratilgan joylar||Мест за вами в каждом занятии||Seats held for you in each class
perk_t_videos||Maxsus video darslar||Эксклюзивные видеоуроки||Exclusive video lessons
perk_t_seats||Ajratilgan joylar||Места за вами||Reserved spots
vip_perk_seats||Har bir guruh mashg'ulotida {n} ta joy faqat VIP uchun: mashg'ulot to'lib qolsa ham joy topasiz.||В каждом групповом занятии {n} места только для VIP: место найдётся, даже когда всё занято.||{n} spots in every group class are kept for VIP, so you get in even when it fills up.
perk_t_pt||Bepul konsultatsiya||Бесплатная консультация||Free consultation
vip_perk_pt||Oyiga {n} ta shaxsiy mashg'ulot (konsultatsiya) murabbiy bilan bepul.||{n} персональная консультация с тренером в месяц бесплатно.||{n} free one-to-one consultation with a trainer every month.
perk_t_guest||Mehmon olib keling||Приводите гостя||Bring a guest
vip_perk_guest||Oyiga {n} ta mehmon taklifnomasi: do'stingiz bir kun bepul shug'ullanadi.||{n} гостевое приглашение в месяц: друг тренируется день бесплатно.||{n} guest pass a month: a friend trains free for a day.
perk_t_discount||Do'kon chegirmasi||Скидка в магазине||Shop discount
perk_t_points||Ikki baravar ball||Двойные баллы||Double points
perk_t_badge||VIP belgisi||Значок VIP||VIP badge
guest_invite||Mehmon taklifnomasi||Гостевое приглашение||Guest pass
guest_help||Mehmon ismini va kelish kunini yozing. Mehmon qabulxonada QR kod yoki 8 belgili kodni ko'rsatadi; taklifnoma faqat shu kuni bir marta ishlaydi.||Укажите имя гостя и дату. Гость показывает на ресепшене QR-код или 8-значный код; приглашение действует один раз и только в этот день.||Enter the guest's name and the day. The guest shows the QR or 8-character code at the desk; it works once, on that day only.
guest_name||Mehmon ismi||Имя гостя||Guest name
guest_create||Taklifnoma yaratish||Создать приглашение||Create pass
guest_limit||Shu oydagi taklifnomalar tugadi. Keyingi oy yana beriladi.||Приглашения на этот месяц закончились. В следующем месяце будут новые.||This month's passes are used up. New ones come next month.
guest_mine||Mening taklifnomalarim||Мои приглашения||My guest passes
guest_used_tag||Ishlatilgan||Использовано||Used
guest_valid||Amal qiladi||Действует||Valid
guest_host||Taklif qilgan||Пригласил(а)||Invited by
guest_rules||Mehmon shaxsini tasdiqlovchi hujjat bilan kelishi kerak. Zal qoidalari mehmonlarga ham taalluqli.||Гостю нужен документ, удостоверяющий личность. Правила зала действуют и для гостей.||The guest needs an ID. Gym rules apply to guests too.
guest||mehmon||гость||guest
guest_ok||Mehmon kirishi belgilandi||Вход гостя отмечен||Guest checked in
guest_used||Bu taklifnoma allaqachon ishlatilgan||Это приглашение уже использовано||This pass was already used
guest_wrong_day||Taklifnoma boshqa kun uchun||Приглашение на другой день||This pass is for another day
guest_name_bad||Mehmon ismini yozing (2-60 belgi)||Введите имя гостя (2-60 символов)||Enter the guest's name (2-60 characters)
guest_date_bad||Sana bugundan 30 kun ichida bo'lsin||Дата должна быть в течение 30 дней||Pick a date within the next 30 days
guests_today||Bugungi mehmonlar||Гости сегодня||Today's guests
vip_only_action||Bu faqat VIP a'zolar uchun||Это только для VIP||This is for VIP members only
vip_seats_note||Siz VIP: har mashg'ulotda siz uchun qo'shimcha joylar ajratilgan.||Вы VIP: в каждом занятии за вами дополнительные места.||You're VIP: extra spots are held for you in every class.
vip_seats_hint||Har mashg'ulotda bir nechta joy VIP a'zolar uchun ajratilgan. VIP haqida →||В каждом занятии несколько мест закреплено за VIP. О VIP →||A few spots in every class are kept for VIP members. About VIP →
pt_sent_free||So'rov yuborildi. Bu oyning bepul VIP konsultatsiyasi ishlatildi.||Запрос отправлен. Использована бесплатная VIP-консультация этого месяца.||Request sent. This month's free VIP consultation was used.
vip_how||Qanday ishlaydi||Как это работает||How it works
vip_how_1||To'lov usulini tanlab VIP sotib olasiz (karta, naqd yoki Click).||Выбираете способ оплаты и покупаете VIP (карта, наличные или Click).||Choose a payment method and buy VIP (card, cash or Click).
vip_how_2||To'lov tasdiqlangach VIP darhol yoqiladi va 30 kun amal qiladi.||После подтверждения оплаты VIP включается сразу и действует 30 дней.||Once the payment is confirmed, VIP starts right away and lasts 30 days.
vip_how_3||Qayta sotib olsangiz, kunlar tugash sanasiga qo'shiladi: hech narsa yo'qolmaydi.||При продлении дни добавляются к дате окончания: ничего не теряется.||Renew any time: the days are added to your end date, nothing is lost.
chat_rooms||Xonalar||Комнаты||Rooms
chat_no_dm||Hali shaxsiy suhbat yo'q. Pastda a'zoni topib yozing.||Личных переписок пока нет. Найдите участника ниже и напишите.||No private chats yet. Find a member below and say hi.
chat_photo||Rasm||Фото||Photo
chat_attach||Rasm biriktirish||Прикрепить фото||Attach a photo
chat_remove_photo||Rasmni olib tashlash||Убрать фото||Remove photo
chat_drop||Rasmni shu yerga tashlang||Перетащите фото сюда||Drop the photo here
chat_bad_image||Rasm jpg, png yoki webp bo'lsin, 5 MB gacha.||Фото: jpg, png или webp, до 5 МБ.||Photos must be jpg, png or webp, up to 5 MB.
chat_sent||Yuborildi||Отправлено||Sent
chat_read||O'qildi||Прочитано||Read
chat_rules_short||Hurmat bilan yozing. Rasm ham yuborishingiz mumkin.||Пишите вежливо. Можно отправлять и фото.||Be respectful. You can send photos too.
today_cap||Bugun||Сегодня||Today
yesterday||Kecha||Вчера||Yesterday
online||onlayn||в сети||online
last_seen_at||oxirgi marta {time} da||был(а) в {time}||last seen {time}
added_to_cart||Savatga qo'shildi||Добавлено в корзину||Added to cart
removed_from_cart||Savatdan olib tashlandi||Убрано из корзины||Removed from cart
cart_bar_items||{n} ta mahsulot||Товаров: {n}||{n} item(s)
go_to_cart||Savat||Корзина||Cart
cart_max||Omborda boshqa qolmagan||Больше нет на складе||No more in stock
cart_more||Bittaga ko'paytirish||Добавить ещё одну||Add one more
cart_less||Bittaga kamaytirish||Убрать одну||Remove one
continue_shopping||Xaridni davom ettirish||Продолжить покупки||Continue shopping
cart_empty_help||Suv, protein yoki energetikni tanlang: bir bosishda savatga tushadi.||Выберите воду, протеин или энергетик: добавляется одним нажатием.||Pick water, protein or an energy drink: one tap adds it.
tg_help_profile||Abonement tugashi, bron va mashg'ulot eslatmalarini Telegramda oling.||Получайте напоминания об абонементе, записях и тренировках в Telegram.||Get membership, booking and training reminders in Telegram.
otp_sent_to||{phone} raqamiga SMS kod yuborildi||SMS-код отправлен на {phone}||An SMS code was sent to {phone}
login_code_title||Telefoningizdagi kod||Код из SMS||Code from your phone
login_code_help||Xavfsizlik uchun: telefoningizga kelgan 6 xonali kodni kiriting. Kodsiz kirib bo'lmaydi.||Для безопасности введите 6-значный код из SMS. Без кода вход невозможен.||For security, enter the 6-digit code we texted you. You can't sign in without it.
resend_code||Kodni qayta yuborish||Отправить код ещё раз||Resend the code
login_expired||Kirish vaqti tugadi, qaytadan kiring||Время входа истекло, войдите снова||The sign-in timed out, please sign in again
google_required||Kirish faqat Google akkaunt orqali. Pastdagi Google tugmasini bosing.||Вход только через аккаунт Google. Нажмите кнопку Google ниже.||Sign-in is only with a Google account. Use the Google button below.
google_only_register||Ro'yxatdan o'tish faqat Google akkaunt orqali. Keyin telefon raqamingizni so'raymiz va SMS kod bilan tasdiqlaymiz.||Регистрация только через Google. Затем мы попросим номер телефона и подтвердим его SMS-кодом.||Sign-up is only with Google. Then we'll ask for your phone number and confirm it with an SMS code.
add_phone_title||Telefon raqamingiz||Ваш номер телефона||Your phone number
add_phone_help||Kirish kodi shu raqamga SMS orqali yuboriladi.||Код для входа придёт на этот номер по SMS.||Your sign-in code will be texted to this number.
admin_login||Administrator kirishi||Вход администратора||Administrator sign-in
start_now||Boshlash||Начать||Get started
days_short||kun||дн.||days
from_price||Oyiga||В месяц||Per month
home_vip_title||Keyingi darajangiz||Ваш следующий уровень||Your next level
scroll_more||Pastga||Вниз||Scroll down
ticker_1||Kuch||Сила||Strength
ticker_2||Intizom||Дисциплина||Discipline
ticker_3||Natija||Результат||Results
ticker_4||Har kuni||Каждый день||Every day
stat_members||faol a'zo||активных клиентов||active members
stat_classes||haftalik mashg'ulot||занятий в неделю||weekly classes
stat_lessons||video dars||видеоуроков||video lessons
feat_training||Video darslar||Видеоуроки||Video lessons
feat_training_sub||Har kunlik mashqlar: qanday bajarish, qaysi mushak ishlaydi.||Тренировки на каждый день: техника и какие мышцы работают.||Daily workouts: how to do them and which muscles work.
feat_classes_sub||Guruh mashg'ulotlariga bir bosishda yoziling.||Запись на групповые занятия в одно касание.||Book a group class in one tap.
feat_shop_sub||Suv, protein, energetik: zalda tayyor turadi.||Вода, протеин, энергетики: ждут вас в зале.||Water, protein, energy drinks: ready at the gym.
feat_card_sub||QR karta bilan kirish: navbat yo'q.||Вход по QR-карте: без очереди.||Walk in with your QR card: no queue.
home_plans_title||O'zingizga mos abonement||Абонемент под вас||A membership that fits you
home_trainers_title||Sizni kim olib boradi||Кто вас поведёт||Who will coach you
final_cta||Bugun boshlang. Ertaga farqni ko'rasiz.||Начните сегодня. Завтра увидите разницу.||Start today. See the difference tomorrow.
login_as||Kim bo'lib kirasiz||Войти как||Sign in as
role_member||A'zo||Клиент||Member
role_trainer||Murabbiy||Тренер||Trainer
role_trainer_note||Murabbiy paneli: mijozlaringiz, mashg'ulotlaringiz va reja tuzish.||Панель тренера: ваши клиенты, занятия и составление планов.||Trainer panel: your clients, classes and plan builder.
not_trainer||Bu raqam murabbiy sifatida ulanmagan. Admin «Murabbiylar» bo'limida akkauntingizni bog'lashi kerak.||Этот номер не привязан к тренеру. Админ должен связать аккаунт в разделе «Тренеры».||This number is not linked to a trainer. The admin must link your account under "Trainers".
coach_panel||Murabbiy paneli||Панель тренера||Trainer panel
coach_clients||mijoz||клиентов||clients
coach_attention||e'tibor kerak||требуют внимания||need attention
coach_week_bookings||shu hafta bron||записей за неделю||bookings this week
coach_month_pt||shu oy PT||PT за месяц||PT this month
coach_add_client||Mijoz qo'shish||Добавить клиента||Add a client
coach_add_help||A'zo raqami yoki telefoni aniq yoziladi||Точный номер клиента или телефон||Exact member code or phone
coach_today||Bugungi mashg'ulotlarim||Мои занятия сегодня||My classes today
coach_no_class_today||Bugun guruh mashg'ulotingiz yo'q||Сегодня групповых занятий нет||No group classes today
coach_upcoming||Tasdiqlangan seanslar||Подтверждённые сессии||Confirmed sessions
coach_attention_first||e'tibor kerak bo'lganlar tepada||сначала требующие внимания||those needing attention first
coach_other_plan||boshqa murabbiy rejasi||план другого тренера||another trainer's plan
coach_no_plan||Mashq rejasi yo'q||Нет плана тренировок||No workout plan
coach_never||hali kelmagan||ещё не приходил||never came
coach_days_away||kun kelmadi||дн. не был||days away
coach_needs_plan||reja kerak||нужен план||needs a plan
coach_today_in||bugun keldi||был сегодня||in today
coach_days_ago||kun oldin||дн. назад||days ago
coach_no_clients||Hali mijozlaringiz yo'q. Yuqoridan a'zo raqami bilan qo'shing.||Клиентов пока нет. Добавьте по номеру клиента выше.||No clients yet. Add one by member code above.
coach_week||Haftalik jadvalim||Моё расписание на неделю||My week
coach_visits_28||Oxirgi 4 hafta||Последние 4 недели||Last 4 weeks
coach_visits_total||jami tashrif||всего визитов||visits in total
coach_edit_plan||Rejani o'zgartirish||Изменить план||Edit the plan
coach_make_plan||Reja tuzish||Составить план||Build a plan
coach_plan_help||Har qatorda: kun, mashq, yondashuv, takror va izoh. Saqlanganda a'zoning faol rejasi shu bo'ladi va unga xabar boradi.||В каждой строке: день, упражнение, подходы, повторы и заметка. После сохранения план станет активным, клиент получит уведомление.||Each row: day, exercise, sets, reps and a note. On save it becomes the member's active plan and they are notified.
coach_start_from||Tayyor dasturdan boshlash:||Начать с готовой программы:||Start from a program:
coach_clear||Tozalash||Очистить||Clear
coach_plan_title||Reja nomi||Название плана||Plan name
coach_plan_notes||Umumiy izoh||Общая заметка||General note
coach_add_row||Mashq qo'shish||Добавить упражнение||Add exercise
coach_save_plan||Rejani saqlash||Сохранить план||Save the plan
client_not_found||Bunday a'zo topilmadi. A'zo raqami (FZ-0012) yoki telefonni aniq yozing.||Клиент не найден. Укажите точный номер (FZ-0012) или телефон.||Member not found. Use the exact code (FZ-0012) or phone.
plan_empty||Reja nomi va kamida bitta mashq kerak||Нужны название и хотя бы одно упражнение||A name and at least one exercise are needed
plan_saved||Reja saqlandi va a'zoga yuborildi! 💪||План сохранён и отправлен клиенту! 💪||Plan saved and sent to the member! 💪
tg_plan_new||📈 {trainer} sizga yangi mashq rejasi tuzdi: «{title}». Saytdagi «Mashq rejam» bo'limida.||📈 {trainer} составил вам новый план: «{title}». Смотрите «Мой план».||📈 {trainer} made you a new plan: "{title}". See "My plan".
day||Kun||День||Day
exercise||Mashq||Упражнение||Exercise
sets||Yondashuv||Подходы||Sets
reps||Takror||Повторы||Reps
min||daq||мин||min
tools||Kalkulyatorlar||Калькуляторы||Calculators
tools_sub||BMI, kaloriya, makrolar, 1RM, suv va puls zonalari: yozgan sari hisoblanadi.||ИМТ, калории, БЖУ, 1ПМ, вода и пульсовые зоны: считается на лету.||BMI, calories, macros, 1RM, water and heart-rate zones, live as you type.
tools_me||Ma'lumotlarim||Мои данные||About me
tools_sex||Jins||Пол||Sex
tools_male||Erkak||Мужчина||Male
tools_female||Ayol||Женщина||Female
tools_age||Yosh||Возраст||Age
tools_height||Bo'y||Рост||Height
tools_activity||Faollik||Активность||Activity
act_1||Kam harakat (ofis)||Минимальная (офис)||Sedentary (desk job)
act_2||Haftasiga 1–3 mashg'ulot||1–3 тренировки в неделю||1–3 workouts a week
act_3||Haftasiga 3–5 mashg'ulot||3–5 тренировок в неделю||3–5 workouts a week
act_4||Har kuni mashg'ulot||Каждый день||Every day
act_5||Juda faol (sportchi)||Очень активный (спортсмен)||Very active (athlete)
tools_goal||Maqsad||Цель||Goal
goal_lose||Ozish||Похудеть||Lose
goal_keep||Saqlash||Держать||Keep
goal_gain||Massa||Набрать||Gain
bmi_help||18.5–25 oralig'i sog'lom vazn hisoblanadi.||18,5–25 — здоровый вес.||18.5–25 is a healthy weight.
bmi_under||Vazn kam||Недостаток веса||Underweight
bmi_normal||Normal||Норма||Normal
bmi_over||Ortiqcha vazn||Избыточный вес||Overweight
tools_calories||Kunlik kaloriya||Калории в день||Daily calories
kcal_day||kkal / kun||ккал / день||kcal / day
tools_bmr||Bazal almashinuv (BMR)||Базальный обмен (BMR)||Basal rate (BMR)
tools_tdee||Faollik bilan (TDEE)||С активностью (TDEE)||With activity (TDEE)
tools_macros||Makrolar||БЖУ||Macros
protein||Oqsil||Белки||Protein
fat||Yog'||Жиры||Fat
carbs||Uglevod||Углеводы||Carbs
tools_lifted||Ko'tarilgan og'irlik||Поднятый вес||Weight lifted
tools_orm_help||bir martalik maksimum (taxminan)||разовый максимум (оценка)||estimated one-rep max
tools_train_min||Bugungi mashg'ulot (daqiqa)||Тренировка сегодня (мин)||Training today (min)
tools_liters||litr kuniga||литров в день||litres a day
tools_hr||Puls zonalari||Пульсовые зоны||Heart-rate zones
tools_rest_hr||Tinch holatdagi puls||Пульс в покое||Resting heart rate
tools_hr_help||Karvonen usuli: maksimal puls = 220 − yosh.||Метод Карвонена: максимум = 220 − возраст.||Karvonen method: max HR = 220 − age.
zone_1||1 · Tiklanish||1 · Восстановление||1 · Recovery
zone_2||2 · Yog' yoqish||2 · Жиросжигание||2 · Fat burn
zone_3||3 · Chidamlilik||3 · Выносливость||3 · Endurance
zone_4||4 · Kuch||4 · Сила||4 · Threshold
zone_5||5 · Maksimum||5 · Максимум||5 · Maximum
records||Rekordlarim||Мои рекорды||My records
records_sub||Har bir ko'tarishni yozing: eng yaxshi natija va 1RM avtomatik hisoblanadi, yangi rekordda konfetti!||Записывайте подходы: лучший результат и 1ПМ считаются сами, новый рекорд — конфетти!||Log your lifts: best result and 1RM are worked out, and a new record gets confetti!
record_add||Qo'shish||Добавить||Add
record_new||🏆 Yangi rekord! Tabriklaymiz!||🏆 Новый рекорд! Поздравляем!||🏆 New personal record! Congratulations!
record_saved||Natija saqlandi||Результат сохранён||Result saved
record_bad||Mashq, og'irlik (0–500 kg) va takror (1–30) to'g'ri bo'lsin||Проверьте упражнение, вес (0–500) и повторы (1–30)||Check the lift, weight (0–500 kg) and reps (1–30)
records_entries||ta yozuv||записей||entries
records_none||Hali yozuv yo'q||Записей пока нет||No entries yet
records_history||Oxirgi natijalar||Последние результаты||Recent results
desk_find_ph||Ism, telefon, FZ-0001 yoki QR kod…||Имя, телефон, FZ-0001 или QR-код…||Name, phone, FZ-0001 or QR code…
desk_all_clear||Hammasi bajarilgan, kutayotgan ish yo'q||Всё сделано, ничего не ждёт||All done, nothing is waiting
perk_pay||Naqd, karta o'tkazmasi yoki Click bilan to'lash||Оплата наличными, переводом на карту или Click||Pay in cash, by card transfer or Click
activity||Faollik (12 hafta)||Активность (12 недель)||Activity (12 weeks)
visits_total||jami {n} tashrif||всего {n} посещений||{n} visits in total
less||kam||меньше||less
more||ko'p||больше||more
water||Suv||Вода||Water
glass||stakan||стакан||glass
next_class||Keyingi mashg'ulot||Следующее занятие||Next class
starts_now||Hozir boshlanadi!||Начинается сейчас!||Starting now!
cd_labels||kun,soat,daq,son||дн,ч,мин,сек||d,h,min,s
weight_empty||Vazningizni yozib boring: grafik shu yerda chiziladi.||Записывайте вес: здесь появится график.||Log your weight and the trend appears here.
own_plan||O'zingiz tanlagan tayyor dastur||Выбранная вами готовая программа||A ready-made program you picked
week_progress||Shu haftadagi bajarilgan mashqlar||Выполнено за эту неделю||Done this week
this_week||shu hafta||эта неделя||this week
wd_short_0||Du||Пн||Mo
wd_short_1||Se||Вт||Tu
wd_short_2||Cho||Ср||We
wd_short_3||Pa||Чт||Th
wd_short_4||Ju||Пт||Fr
wd_short_5||Sha||Сб||Sa
wd_short_6||Ya||Вс||Su
rest_timer||Dam olish taymeri||Таймер отдыха||Rest timer
rest_timer_help||Yondashuvlar orasida bosing: vaqt tugaganda ovoz va tebranish beradi.||Нажимайте между подходами: по окончании прозвучит сигнал.||Tap between sets: it beeps and vibrates when time is up.
start||Boshlash||Старт||Start
plan_stop||Dasturni to'xtatish||Остановить программу||Stop this program
no_plan_title||Hali mashq rejangiz yo'q||Плана тренировок пока нет||No workout plan yet
no_plan_or||Yoki pastdan tayyor dasturni tanlab, bugunoq boshlang.||Или выберите готовую программу ниже и начните сегодня.||Or pick a ready-made program below and start today.
programs||Tayyor dasturlar||Готовые программы||Ready-made programs
programs_title||Bir bosishda boshlang||Начните в одно касание||Start in one tap
exercises_n||ta mashq||упражнений||exercises
program_start||Shu dasturni boshlash||Начать программу||Start this program
program_replace||Hozirgi dastur almashadi. Davom etamizmi?||Текущая программа будет заменена. Продолжить?||Your current program will be replaced. Continue?
program_started||Dastur boshlandi! Bugungi mashqlar ro'yxatda.||Программа запущена! Сегодняшние упражнения в списке.||Program started! Today's exercises are listed.
program_trainer||Sizda murabbiy bergan reja bor, u almashtirilmaydi.||У вас план от тренера, он не заменяется.||You have a plan from your trainer; it is kept.
workout_all_done||Bugungi mashq to'liq bajarildi! Zo'r! 💪||Сегодняшняя тренировка выполнена! Отлично! 💪||Today's workout is complete! Great job! 💪
chat_typing||{name} yozmoqda||{name} печатает||{name} is typing
find_route||Zalga yo'l||Маршрут до зала||Route to the gym
maps||xaritalar||Карты||Maps
crowd_now||Hozir zal||Сейчас в зале||Right now
crowd_calm||bo'sh||свободно||quiet
crowd_mid||o'rtacha||средне||moderate
crowd_busy||gavjum||многолюдно||busy
crowd_help||Oxirgi 2 soatda kelganlar soni bo'yicha||По числу посетителей за последние 2 часа||Based on check-ins in the last 2 hours
qr_2d||Skanerlash uchun||Для сканирования||To scan
qr_3d||3D ko'rinish||3D-вид||3D view
qr_theme||Rang||Цвет||Colour
qr_fire||Olov||Огонь||Fire
qr_gold||Oltin||Золото||Gold
qr_ice||Muz||Лёд||Ice
qr_3d_note||Sichqonchani bloklar ustida yurgizing. Kirishda «Skanerlash uchun» kodini ko'rsating.||Проведите мышкой по блокам. На входе показывайте код «Для сканирования».||Move the pointer over the blocks. At the door, show the "To scan" code.
step_delivery||Yetkazish||Доставка||Delivery
subtotal||Mahsulotlar||Товары||Items
free||Bepul||Бесплатно||Free
dlv_pickup||Zaldan olib ketaman||Заберу в зале||I'll pick it up at the gym
dlv_pickup_sub||Qabulxonada tayyor turadi||Будет готово на ресепшене||Ready at the front desk
dlv_courier||Yetkazib berish||Доставка курьером||Courier delivery
dlv_free_from||so'mdan bepul||сум — бесплатно||UZS and up: free
dlv_address_ph||Ko'cha, uy, xonadon, mo'ljal||Улица, дом, квартира, ориентир||Street, building, flat, landmark
dlv_note||Kuryerga izoh||Комментарий курьеру||Note for the courier
dlv_note_ph||Masalan: 3-qavat, domofon 25||Например: 3 этаж, домофон 25||e.g. 3rd floor, intercom 25
dlv_fee||Yetkazish||Доставка||Delivery
err_address||Yetkazish uchun manzilni to'liq yozing||Укажите полный адрес доставки||Please enter the full delivery address
delivery_off||Hozircha yetkazib berish yo'q, zaldan olib keting||Доставка сейчас недоступна, заберите в зале||Delivery is off for now; please pick up at the gym
st_shipping||Yo'lda||В пути||On the way
ship_do||Yo'lga chiqdi||Отправлен||Out for delivery
delivered_do||Yetkazildi||Доставлен||Delivered
track||Buyurtma holati||Статус заказа||Order status
trk_accepted||Qabul qilindi||Принят||Accepted
trk_shipping||Kuryer yo'lda||Курьер в пути||Courier on the way
trk_delivered||Yetkazildi||Доставлен||Delivered
trk_picked||Olib ketildi||Получен||Picked up
tg_order_shipping||🛵 Buyurtmangiz #{n} yo'lga chiqdi! Kuryer tez orada yetib boradi.||🛵 Ваш заказ #{n} в пути! Курьер скоро будет.||🛵 Your order #{n} is on the way! The courier will be there soon.
apple_soon||Apple (iCloud) bilan kirish tez orada||Вход через Apple (iCloud) скоро||Sign in with Apple (iCloud) coming soon
social_soon||Google va Apple (iCloud) bilan kirish tez orada||Вход через Google и Apple (iCloud) скоро||Google and Apple (iCloud) sign-in coming soon
apple_off||Apple bilan kirish sozlanmagan||Вход через Apple не настроен||Sign in with Apple is not set up
err_apple||Apple akkauntini tekshirib bo'lmadi||Не удалось проверить аккаунт Apple||Could not verify the Apple account
step_choose||Tanlov||Выбор||Choice
step_transfer||O'tkazma||Перевод||Transfer
step_confirm||Tasdiq kutilmoqda||Ожидает подтверждения||Awaiting confirmation
card_flip||Kartani aylantirish||Перевернуть карту||Flip the card
payment_details||To'lov ma'lumotlari||Данные для оплаты||Payment details
your_card||Sizning kartangiz||Ваша карта||Your card
reviews_sub||A'zolarimiz zal haqida nima deydi||Что говорят наши клиенты о зале||What our members say about the gym
reviews_count||{n} ta fikr||Отзывов: {n}||{n} reviews
review_write||Fikr qoldiring||Оставьте отзыв||Leave a review
review_edit||Fikringizni o'zgartirish||Изменить отзыв||Edit your review
review_ph||Zal, murabbiylar, jihozlar haqida yozing…||Напишите о зале, тренерах, оборудовании…||Tell us about the gym, trainers, equipment…
review_login||Fikr yozish uchun avval kiring.||Чтобы оставить отзыв, войдите.||Sign in to leave a review.
review_first||Birinchi bo'lib fikr qoldiring!||Оставьте отзыв первым!||Be the first to leave a review!
or_continue||yoki davom eting||или продолжите через||or continue with
google_soon||Google bilan kirish tez orada||Вход через Google скоро||Google sign-in coming soon
welcome_back||Qaytganingizdan xursandmiz||С возвращением||Welcome back
join_us||Jamoaga qo'shiling||Присоединяйтесь||Join the team
move_mouse||Sichqonchani qimirlatib ko'ring ✦||Подвигайте мышкой ✦||Move your mouse ✦
deleted_ok||Tayyor||Готово||Done
sms_login_note||Kirishda telefoningizga SMS kod keladi||При входе на телефон придёт SMS-код||You'll get an SMS code on your phone when signing in
inbox||Xabarlar||Сообщения||Inbox
inbox_sub||Zal ma'muriyati va tizimdan kelgan shaxsiy xabarlaringiz||Личные сообщения от администрации зала и системы||Personal messages from the gym team and the system
new||yangi||новое||new
from_admin||Ma'muriyatdan||От администрации||From the gym team
from_system||Tizim||Система||System
inbox_empty||Hozircha xabar yo'q||Сообщений пока нет||No messages yet
inbox_empty_help||Ma'muriyat sizga yozsa, xabar shu yerda paydo bo'ladi va qo'ng'iroqcha qizaradi.||Когда администрация напишет вам, сообщение появится здесь, а колокольчик загорится.||When the gym team writes to you, the message appears here and the bell lights up.
days_with_us||kun biz bilan||дней с нами||days with us
years_old||yosh||лет||years old
to_goal||Maqsadgacha||До цели||To goal
pf_tab_me||Shaxsiy||Личное||Personal
pf_tab_goals||Maqsad||Цель||Goal
pf_tab_security||Xavfsizlik||Безопасность||Security
pf_tab_connect||Ulanishlar||Подключения||Connections
pf_goal||Maqsadingiz||Ваша цель||Your goal
pf_target||Maqsad vazn||Целевой вес||Target weight
pf_birth||Tug'ilgan kun||Дата рождения||Birthday
pf_birth_help||Tug'ilgan kuningizda zal sizni tabriklaydi 🎂 Ma'lumot faqat ma'muriyatga ko'rinadi.||В день рождения зал вас поздравит 🎂 Видно только администрации.||The gym will greet you on your birthday 🎂 Only staff can see it.
pf_saved_goals||Maqsad saqlandi 🎯||Цель сохранена 🎯||Goal saved 🎯
sessions_title||Boshqa qurilmalardan chiqish||Выйти на других устройствах||Sign out other devices
sessions_help||Telefon yo'qolsa yoki birovning kompyuterida kirgan bo'lsangiz.||Если потеряли телефон или входили с чужого компьютера.||If you lost a phone or signed in on someone else's computer.
sessions_btn||Chiqarish||Выйти||Sign out
sessions_closed||{n} ta boshqa seans yopildi||Закрыто других сеансов: {n}||{n} other sessions closed
export_title||Ma'lumotlarimni yuklab olish||Скачать мои данные||Download my data
export_help||Tashriflar, to'lovlar, vazn va rekordlar bitta faylda.||Посещения, платежи, вес и рекорды одним файлом.||Visits, payments, weight and records in one file.
soon||tez orada||скоро||soon
invite_short||Do'stingiz shu havola orqali ro'yxatdan o'tsa, ikkalangizga bonus.||Если друг зарегистрируется по ссылке — бонус вам обоим.||If a friend signs up with this link, you both get a bonus.
find_us||Manzil||Адрес||Location
find_us_title||Zal qayerda joylashgan||Где находится зал||Where to find us
open_in_yandex||Yandex Xaritada ochish||Открыть в Яндекс Картах||Open in Yandex Maps
ft_cta_eyebrow||Birinchi qadam||Первый шаг||First step
ft_cta_title||Kuchli bo'lish bugundan boshlanadi||Сила начинается сегодня||Getting stronger starts today
ft_about||Zamonaviy jihozlar, tajribali murabbiylar va o'z natijangizni ko'rib boradigan shaxsiy kabinet — hammasi bitta zalda.||Современное оборудование, опытные тренеры и личный кабинет с вашим прогрессом — всё в одном зале.||Modern equipment, experienced trainers and a personal dashboard that tracks your progress, all in one gym.
ft_gym||Zal||Зал||The gym
ft_members||A'zolar uchun||Для клиентов||For members
ft_contact||Aloqa||Контакты||Contact
ft_rights||Barcha huquqlar himoyalangan||Все права защищены||All rights reserved
ft_made||Kuch · Intizom · Natija||Сила · Дисциплина · Результат||Strength · Discipline · Results
ft_top||Yuqoriga||Наверх||Back to top
tk_title||Kirish cheki||Чек входа||Entry receipt
tk_date||Sana va vaqt||Дата и время||Date & time
tk_member||A'zo||Клиент||Member
tk_host||Taklif qilgan||Пригласил||Invited by
tk_plan||Abonement||Абонемент||Membership
tk_guest_pass||mehmon chiptasi||гостевой пропуск||guest pass
tk_valid||Amal qiladi||Действует до||Valid until
tk_days_left||kun qoldi||дн. осталось||days left
tk_month_visits||Shu oy tashriflar||Визитов в этом месяце||Visits this month
tk_total_visits||Jami tashriflar||Всего визитов||Total visits
tk_allowed||KIRISH RUXSAT ETILDI||ВХОД РАЗРЕШЁН||ENTRY ALLOWED
tk_denied||KIRISH RAD ETILDI||ВХОД ЗАПРЕЩЁН||ENTRY DENIED
tk_again||Bugun allaqachon kirgan, birinchi kirish:||Сегодня уже входил, первый вход:||Already checked in today, first at
tk_stamp_ok||KIRDI||ВОШЁЛ||IN
tk_stamp_no||RAD||ОТКАЗ||DENIED
tk_wish||Mashg'ulotingiz samarali o'tsin! 💪||Продуктивной тренировки! 💪||Have a great workout! 💪
tk_help||Abonementni qabulxonada uzaytirish mumkin.||Продлить абонемент можно на ресепшене.||The membership can be renewed at the front desk.
tk_help_blocked||Akkaunt bloklangan: sababini zal rahbariyatidan aniqlang.||Аккаунт заблокирован: уточните причину у руководства зала.||The account is blocked: ask the gym management why.
tk_staff||Qabul qildi||Принял||Checked by
tk_today||ta kirish bugun||входов сегодня||check-ins today
tk_recent||Oxirgi skanerlar||Последние сканы||Recent scans
tk_wait||A'zo kartasidagi QR kodni skanerlang — kirish cheki shu yerda chiqadi.||Отсканируйте QR-код карты — чек входа появится здесь.||Scan the member card QR code and the entry receipt prints here.
tk_print||Chekni chop etish||Печать чека||Print receipt
caps_on||Caps Lock yoqilgan — parol katta harflar bilan yozilyapti||Включён Caps Lock — пароль вводится заглавными||Caps Lock is on, the password is being typed in capitals
remember_me||Meni eslab qol||Запомнить меня||Remember me
trust_encrypted||Parollar shifrlangan holda saqlanadi||Пароли хранятся в зашифрованном виде||Passwords are stored encrypted
trust_2fa||SMS bilan 2 bosqichli himoya||Двухэтапная защита по SMS||Two-step protection by SMS
trust_attempts||Ko'p xato urinish bloklanadi||Подбор пароля блокируется||Repeated wrong attempts are blocked
trust_free||Ro'yxatdan o'tish bepul||Регистрация бесплатна||Signing up is free
last_seen||Oldingi kirish: {when}. Bu siz bo'lmasangiz, parolni almashtiring.||Предыдущий вход: {when}. Если это были не вы, смените пароль.||Previous sign-in: {when}. If that wasn't you, change your password.
ai_coach||AI murabbiy||AI-тренер||AI coach
ai_coach_sub||Mashq va ovqatlanish bo'yicha savol bering||Спросите о тренировках и питании||Ask about training and nutrition
ai_sub||Maqsadingiz, vazningiz va mashq rejangizni biladigan shaxsiy yordamchi. Savol bering yoki haftalik reja tuzdiring.||Личный помощник, который знает вашу цель, вес и план тренировок. Задайте вопрос или составьте недельный план.||A personal assistant that knows your goal, weight and workout plan. Ask a question or get a weekly plan.
ai_home_title||AI murabbiy doim yoningizda||AI-тренер всегда рядом||An AI coach always at hand
ai_home_1||Texnika va mashq bo'yicha savollarga javob||Ответы о технике и упражнениях||Answers on technique and exercises
ai_home_2||Maqsadingizga mos haftalik reja||Недельный план под вашу цель||A weekly plan built for your goal
ai_home_3||Kun-u tun, o'zbek, rus va ingliz tilida||Круглосуточно, на узбекском, русском и английском||Day and night, in Uzbek, Russian and English
ai_try||Sinab ko'rish||Попробовать||Try it
ai_off||AI hali ulanmagan: administrator ANTHROPIC_API_KEY ni sozlashi kerak.||AI ещё не подключён: администратору нужно указать ANTHROPIC_API_KEY.||AI is not connected yet: the admin needs to set ANTHROPIC_API_KEY.
ai_login||AI murabbiy sizning ma'lumotlaringizga qarab javob beradi, shuning uchun avval kiring.||AI-тренер отвечает с учётом ваших данных, поэтому сначала войдите.||The AI coach answers using your own data, so please sign in first.
ai_chat_title||AI murabbiy bilan suhbat||Чат с AI-тренером||Chat with the AI coach
ai_today||bugun||сегодня||today
ai_clear||Suhbatni tozalash||Очистить чат||Clear chat
ai_try_title||Masalan, shunday so'rang:||Например, спросите:||For example, ask:
ai_q1||Qorin uchun eng yaxshi 5 ta mashq qaysi?||Какие 5 лучших упражнений для пресса?||What are the 5 best ab exercises?
ai_q2||Mashqdan keyin nima yeyish kerak?||Что есть после тренировки?||What should I eat after training?
ai_q3||Skvatni qanday to'g'ri bajaraman?||Как правильно делать присед?||How do I squat with good form?
ai_thinking||O'ylayapman…||Думаю…||Thinking…
ai_placeholder||Savolingizni yozing… (Enter — yuborish)||Напишите вопрос… (Enter — отправить)||Type your question… (Enter to send)
ai_send||Yuborish||Отправить||Send
ai_disclaimer||AI shifokor emas: og'riq yoki kasallikda shifokor va murabbiyga murojaat qiling.||AI не врач: при боли или болезни обратитесь к врачу и тренеру.||The AI is not a doctor: for pain or illness, see a doctor and a trainer.
ai_plan_title||AI mashq rejasi||AI-план тренировок||AI workout plan
ai_plan_sub||Darajangiz va vaqtingizni kiriting — AI sizga haftalik reja tuzib, «Mashq rejam» bo'limiga saqlaydi.||Укажите уровень и время — AI составит недельный план и сохранит его в «Мой план».||Enter your level and time — the AI builds a weekly plan and saves it to «My plan».
ai_level||Darajangiz||Ваш уровень||Your level
ai_days||Haftasiga necha kun||Дней в неделю||Days per week
ai_minutes||Bir mashg'ulot (daqiqa)||Одна тренировка (мин)||One session (min)
ai_notes||Qo'shimcha (ixtiyoriy)||Дополнительно (необязательно)||Extra (optional)
ai_notes_ph||Masalan: tizzam og'riydi, faqat gantel bor, qo'llarga urg'u…||Например: болит колено, только гантели, акцент на руки…||e.g. sore knee, dumbbells only, focus on arms…
ai_plan_btn||Reja tuzish||Составить план||Build my plan
ai_plan_busy||Tuzilmoqda… (1 daqiqagacha)||Составляю… (до 1 минуты)||Building… (up to a minute)
ai_plan_ok||✦ AI rejangiz tayyor! Pastda kunlar bo'yicha mashqlar.||✦ AI-план готов! Ниже упражнения по дням.||✦ Your AI plan is ready! The exercises by day are below.
ai_limit||Bugungi AI so'rovlar limiti tugadi. Ertaga yana urinib ko'ring.||Дневной лимит запросов к AI исчерпан. Попробуйте завтра.||Today's AI request limit is used up. Try again tomorrow.
ai_busy||AI hozir band. Bir daqiqadan keyin qayta urinib ko'ring.||AI сейчас занят. Попробуйте через минуту.||The AI is busy right now. Try again in a minute.
ai_error||AI javob bera olmadi. Qayta urinib ko'ring.||AI не смог ответить. Попробуйте ещё раз.||The AI could not answer. Please try again.
ai_refused||Bu savolga AI javob bera olmaydi. Boshqacha so'rab ko'ring yoki murabbiyga murojaat qiling.||На этот вопрос AI ответить не может. Переформулируйте или обратитесь к тренеру.||The AI can't answer this. Rephrase it or ask a trainer.
ai_empty||Savolni yozing||Напишите вопрос||Type a question
login_field||Login, email yoki telefon||Логин, email или телефон||Username, e-mail or phone
login_field_ph||masalan: aziz_karimov||например: aziz_karimov||e.g. aziz_karimov
username||Login (username)||Логин (username)||Username
username_help||3–30 belgi: lotin harflari, raqamlar, _ va . Kirishda shu yoki email ishlatiladi.||3–30 символов: латиница, цифры, _ и . Для входа подойдёт он или email.||3–30 characters: Latin letters, digits, _ and . You sign in with it or your e-mail.
password2||Parolni takrorlang||Повторите пароль||Repeat the password
reg_more||Ism va telefon (ixtiyoriy)||Имя и телефон (необязательно)||Name and phone (optional)
err_username||Login 3–30 belgi bo'lsin: lotin harflari, raqam, _ yoki .||Логин 3–30 символов: латиница, цифры, _ или .||Username: 3–30 characters, Latin letters, digits, _ or .
err_username_taken||Bu login band, boshqasini tanlang||Этот логин занят, выберите другой||This username is taken, pick another
err_email||Email manzil noto'g'ri||Неверный email||Invalid e-mail address
err_email_taken||Bu email bilan akkaunt bor. Kiring yoki parolni tiklang.||Аккаунт с этим email уже есть. Войдите или восстановите пароль.||An account with this e-mail exists. Sign in or reset the password.
err_pass_match||Parollar bir xil emas||Пароли не совпадают||The passwords do not match
pw_email_title||Parolni email orqali tiklash||Восстановление пароля по email||Reset the password by e-mail
pw_email_help||Ro'yxatdan o'tgan email manzilingizni yozing — yangi parol o'rnatish havolasini yuboramiz.||Введите email, указанный при регистрации — пришлём ссылку для нового пароля.||Enter the e-mail you signed up with and we'll send a link to set a new password.
pw_email_send||Havola yuborish||Отправить ссылку||Send the link
pw_email_sent||Agar bu email bilan akkaunt bo'lsa, xat yuborildi. Pochtangizni (va «Spam» papkasini) tekshiring.||Если аккаунт с таким email есть, письмо отправлено. Проверьте почту (и папку «Спам»).||If an account uses this e-mail, a message is on its way. Check your inbox (and the spam folder).
pw_link_bad||Havola eskirgan yoki allaqachon ishlatilgan.||Ссылка устарела или уже использована.||The link has expired or was already used.
pw_email_again||Yangi havola so'rash||Запросить новую ссылку||Request a new link
pw_by_sms||Telefon orqali (SMS) tiklash||Восстановить по SMS||Reset by SMS instead
pw_by_email||Email orqali tiklash||Восстановить по email||Reset by e-mail instead
cancel||Bekor qilish||Отмена||Cancel
rep_title||Nima uchun shikoyat qilyapsiz?||Почему вы жалуетесь?||Why are you reporting this?
rep_help||Sababni tanlang — administrator xabarni ko'rib chiqadi. Yozuvchi kim shikoyat qilganini bilmaydi.||Выберите причину — администратор проверит сообщение. Автор не узнает, кто пожаловался.||Pick a reason and the admin will review the message. The sender won't know who reported it.
rep_insult||Haqorat yoki so'kinish||Оскорбление или мат||Insults or swearing
rep_spam||Spam yoki reklama||Спам или реклама||Spam or advertising
rep_scam||Firibgarlik, pul so'rash||Мошенничество, просьба денег||Scam or asking for money
rep_photo||Noo'rin rasm||Неприемлемое фото||Inappropriate photo
rep_threat||Tahdid yoki bezovta qilish||Угрозы или преследование||Threats or harassment
rep_other||Boshqa sabab||Другая причина||Something else
rep_detail||Izoh («Boshqa» uchun majburiy)||Комментарий (обязателен для «Другое»)||Details (required for «Something else»)
rep_detail_ph||Qisqacha nima bo'lganini yozing||Коротко опишите, что случилось||Briefly say what happened
rep_send||Shikoyat yuborish||Отправить жалобу||Send report
chat_report_reason||Shikoyat sababini tanlang («Boshqa» bo'lsa, izoh yozing)||Выберите причину жалобы (для «Другое» напишите комментарий)||Pick a reason (for «Something else», add a few words)
avatar_change||Profil rasmini yuklash yoki almashtirish||Загрузить или сменить фото профиля||Upload or change your profile picture
avatar_remove||Rasmni o'chirish||Удалить фото||Remove the picture
avatar_saved||Profil rasmi saqlandi||Фото профиля сохранено||Profile picture saved
avatar_removed||Profil rasmi o'chirildi||Фото профиля удалено||Profile picture removed
err_avatar||Faqat jpg, png yoki webp rasm (5 MB gacha) yuklang||Загрузите jpg, png или webp (до 5 МБ)||Upload a jpg, png or webp image (up to 5 MB)
acc_title||Akkaunt sozlamalari||Настройки аккаунта||Account settings
acc_back||Kabinetga qaytish||Назад в кабинет||Back to dashboard
acc_pill||Akkaunt||Аккаунт||Account
acc_sub||Profil va kirish ma'lumotlarini yangilang.||Обновите профиль и данные для входа.||Update your profile and sign-in details.
acc_role_member||A'zo||Клиент||Member
acc_role_trainer||Murabbiy||Тренер||Trainer
acc_role_admin||Administrator||Администратор||Administrator
acc_photo||Profil rasmi||Фото профиля||Profile photo
acc_photo_now||Hozirgi||Сейчас||Currently
acc_photo_none||Rasm yuklanmagan||Фото не загружено||No photo yet
acc_photo_change||Almashtirish: fayl tanlang||Сменить: выберите файл||Change: choose a file
acc_no_file||Fayl tanlanmagan||Файл не выбран||No file chosen
acc_type||Hisob turi||Тип аккаунта||Account type
acc_pw_help||Parolni o'zgartirmoqchi bo'lmasangiz, ikkala maydonni bo'sh qoldiring.||Чтобы не менять пароль, оставьте оба поля пустыми.||Leave both fields empty to keep your password.
account_saved||Akkaunt sozlamalari saqlandi||Настройки аккаунта сохранены||Account settings saved
scan_session||Sessiya tugagan: sahifani yangilab, admin sifatida qayta kiring||Сессия истекла: обновите страницу и войдите снова как администратор||Session ended: reload the page and sign in again as admin
"""

T = {"uz": {}, "ru": {}, "en": {}}
for line in RAW.strip().splitlines():
    key, uz, ru, en = line.split("||")
    T["uz"][key], T["ru"][key], T["en"][key] = uz, ru, en
LANGS = ("uz", "ru", "en")
