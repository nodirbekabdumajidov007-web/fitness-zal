"""Starting texts of the legal pages (public offer, privacy policy, refund rules) in three languages.

These are TEMPLATES, not legal advice, and they contain NO real company data: everything in [SQUARE BRACKETS] is a placeholder
that the owner must replace in the admin (Huquqiy sahifalar) before the site goes live. Have a lawyer check the final text.
Format: a blank line starts a paragraph, a line starting with "# " is a heading, a line starting with "- " is a list item."""
import re

PLACEHOLDER_RE = re.compile(r"\[[A-ZА-ЯЁ0-9'`’ ]{3,40}\]")


def find_placeholders(*texts):
    """Distinct [PLACEHOLDER] tokens still present in the given texts (order of first appearance)."""
    seen = []
    for text in texts:
        for token in PLACEHOLDER_RE.findall(text or ""):
            if token not in seen:
                seen.append(token)
    return seen


OFERTA_UZ = """# 1. Umumiy qoidalar
Ushbu ommaviy oferta (keyingi o'rinlarda — «Oferta») [YURIDIK NOM] (STIR: [STIR], manzil: [MANZIL], keyingi o'rinlarda — «Zal») tomonidan fitnes xizmatlarini ko'rsatish shartlarini belgilaydi. Saytda ro'yxatdan o'tish yoki to'lov qilish Oferta shartlarini to'liq qabul qilishni (O'zbekiston Respublikasi Fuqarolik kodeksining akseptga oid qoidalari) anglatadi.
Zalning rekvizitlari: bank — [BANK], hisob raqami — [BANK HISOBI], MFO — [MFO], telefon — [TELEFON], e-mail — [EMAIL].

# 2. Xizmat predmeti
- Zalning jihozlaridan va hududidan tanlangan abonement davrida foydalanish;
- guruh mashg'ulotlariga bron qilish, murabbiy bilan shaxsiy mashg'ulotlar (alohida to'lanadigan hollarda);
- do'kondagi mahsulotlarni sotib olish, sovg'a sertifikatlari va mehmon taklifnomalaridan foydalanish.
Xizmatlar ro'yxati, narxi va muddati saytdagi «Abonementlar» va «Do'kon» sahifalarida e'lon qilinadi. Narxlar so'mda ko'rsatiladi.

# 3. Abonement va undan foydalanish
Abonement to'lov tasdiqlangan paytdan e'tiboran amal qiladi va shaxsiy hisoblanadi: uni boshqa shaxsga berish mumkin emas. Zalga kirish a'zolik QR-kartasi orqali amalga oshiriladi. Zal ichki tartib qoidalariga va xavfsizlik talablariga rioya qilishga majbur etadi; qoidalarni qo'pol buzgan a'zoning kirishi cheklanishi mumkin.
Abonementni muzlatish saytdagi «Muzlatish» bo'limida ko'rsatilgan shartlar (eng kam va eng ko'p kun) bo'yicha amalga oshiriladi; muzlatilgan kunlar uchun abonement muddati shuncha kunga uzayadi.
Mehmon taklifnomasi abonement turida ko'zda tutilgan miqdorda beriladi, faqat ko'rsatilgan kunda va bir marta amal qiladi.

# 4. To'lov tartibi
To'lov saytda ko'rsatilgan usullardan biri bilan amalga oshiriladi (naqd pul, karta orqali o'tkazma yoki ulangan onlayn to'lov tizimi). Karta orqali o'tkazmalar Zal xodimi to'lov tushganini tasdiqlagandan keyin qabul qilinadi. To'lanmagan buyurtma [24] soatdan keyin bekor qilinishi mumkin.

# 5. Qaytarish va bekor qilish
Pulni qaytarish qoidalari alohida «Qaytarish qoidalari» sahifasida bayon etilgan va Ofertaning ajralmas qismi hisoblanadi.

# 6. Taraflarning javobgarligi
Zal xizmatlarni ko'rsatilgan sifatda taqdim etishga majbur. A'zo o'z sog'lig'i holati uchun javobgar: mashg'ulotlarni boshlashdan oldin shifokor bilan maslahatlashish tavsiya etiladi. Zal a'zoning qimmatbaho buyumlari uchun, ular shaxsiy shkafda qulflanmagan bo'lsa, javobgar emas. Majburiy holatlar (fors-major) vaqtida taraflar javobgarlikdan ozod etiladi.

# 7. Shaxsiy ma'lumotlar
A'zoning shaxsiy ma'lumotlari «Maxfiylik siyosati»ga muvofiq, O'zbekiston Respublikasining «Shaxsga doir ma'lumotlar to'g'risida»gi ZRU-547-son Qonuni talablariga rioya qilingan holda qayta ishlanadi.

# 8. Nizolarni hal qilish
Nizolar muzokaralar yo'li bilan hal etiladi. Kelishuvga erishilmasa, nizo O'zbekiston Respublikasi qonunchiligiga muvofiq [SUD NOMI] sudida ko'riladi.

# 9. Oferta o'zgarishi
Zal Ofertani bir tomonlama o'zgartirish huquqiga ega. Yangi tahrir saytda e'lon qilingan paytdan kuchga kiradi; to'langan abonement shartlari to'lov paytidagi tahrir bo'yicha saqlanadi.
"""

OFERTA_RU = """# 1. Общие положения
Настоящая публичная оферта (далее — «Оферта») определяет условия оказания фитнес-услуг компанией [YURIDIK NOM] (ИНН: [STIR], адрес: [MANZIL], далее — «Зал»). Регистрация на сайте или оплата означает полное принятие условий Оферты (акцепт).
Реквизиты Зала: банк — [BANK], расчётный счёт — [BANK HISOBI], МФО — [MFO], телефон — [TELEFON], e-mail — [EMAIL].

# 2. Предмет
- пользование оборудованием и территорией Зала в период действия выбранного абонемента;
- запись на групповые занятия, персональные тренировки с тренером (если они оплачиваются отдельно);
- покупка товаров в магазине, использование подарочных сертификатов и гостевых приглашений.
Перечень услуг, цены и сроки публикуются на страницах «Абонементы» и «Магазин». Цены указаны в сумах.

# 3. Абонемент и его использование
Абонемент действует с момента подтверждения оплаты и является персональным: передавать его другому лицу нельзя. Вход в Зал осуществляется по QR-карте участника. Участник обязан соблюдать правила внутреннего распорядка и требования безопасности; при грубом нарушении вход может быть ограничен.
Заморозка абонемента выполняется в разделе «Заморозка» на условиях, указанных там (минимальный и максимальный срок); срок абонемента продлевается на количество замороженных дней.
Гостевое приглашение выдаётся в количестве, предусмотренном видом абонемента, действует один раз и только в указанную дату.

# 4. Порядок оплаты
Оплата производится одним из способов, указанных на сайте (наличные, перевод на карту или подключённая онлайн-система). Переводы на карту принимаются после подтверждения сотрудником Зала поступления средств. Неоплаченный заказ может быть отменён через [24] часа.

# 5. Возврат и отмена
Правила возврата денежных средств изложены на отдельной странице «Правила возврата» и являются неотъемлемой частью Оферты.

# 6. Ответственность сторон
Зал обязан предоставлять услуги надлежащего качества. Участник отвечает за состояние своего здоровья: перед началом занятий рекомендуется проконсультироваться с врачом. Зал не отвечает за ценные вещи участника, не запертые в личном шкафчике. При обстоятельствах непреодолимой силы стороны освобождаются от ответственности.

# 7. Персональные данные
Персональные данные участника обрабатываются согласно «Политике конфиденциальности» с соблюдением Закона Республики Узбекистан «О персональных данных» № ЗРУ-547.

# 8. Разрешение споров
Споры решаются путём переговоров. При недостижении согласия спор рассматривается в [SUD NOMI] суде в соответствии с законодательством Республики Узбекистан.

# 9. Изменение Оферты
Зал вправе изменять Оферту в одностороннем порядке. Новая редакция вступает в силу с момента публикации на сайте; условия оплаченного абонемента сохраняются в редакции на момент оплаты.
"""

OFERTA_EN = """# 1. General
This public offer (the "Offer") sets out the terms on which [YURIDIK NOM] (tax ID: [STIR], address: [MANZIL], the "Gym") provides fitness services. Registering on the site or paying means you accept the Offer in full.
Gym details: bank — [BANK], account — [BANK HISOBI], bank code — [MFO], phone — [TELEFON], e-mail — [EMAIL].

# 2. Subject
- use of the Gym's equipment and premises during the chosen membership period;
- booking group classes and personal training with a trainer (where paid separately);
- buying products in the shop, using gift certificates and guest passes.
The list of services, prices and terms is published on the Memberships and Shop pages. Prices are in UZS.

# 3. Membership and its use
A membership starts when payment is confirmed and is personal: it cannot be passed to another person. Entry is by the member's QR card. Members must follow the house rules and safety requirements; entry may be restricted after a serious breach.
Freezing is done in the Freeze section on the terms shown there (minimum and maximum days); the membership is extended by the number of frozen days.
A guest pass is issued in the number set by the membership type, works once and only on the stated date.

# 4. Payment
Payment is made by one of the methods shown on the site (cash, card transfer or a connected online system). Card transfers are accepted once Gym staff confirm the money has arrived. An unpaid order may be cancelled after [24] hours.

# 5. Refunds and cancellation
Refund rules are set out on the separate Refund rules page and form an integral part of the Offer.

# 6. Liability
The Gym provides services of proper quality. The member is responsible for their own health: consult a doctor before you start training. The Gym is not responsible for valuables not locked in a personal locker. Neither party is liable in cases of force majeure.

# 7. Personal data
The member's personal data is processed under the Privacy policy and the Law of the Republic of Uzbekistan "On personal data" No. ZRU-547.

# 8. Disputes
Disputes are settled by negotiation. If no agreement is reached, the dispute goes to the [SUD NOMI] court under the law of the Republic of Uzbekistan.

# 9. Changes to the Offer
The Gym may change the Offer unilaterally. The new version applies from its publication on the site; a paid membership keeps the terms in force at the time of payment.
"""

PRIVACY_UZ = """# 1. Umumiy ma'lumot
Ushbu Maxfiylik siyosati [YURIDIK NOM] (STIR: [STIR], manzil: [MANZIL], keyingi o'rinlarda — «Operator») saytda to'plangan shaxsiy ma'lumotlarni qanday qayta ishlashini tushuntiradi. U O'zbekiston Respublikasining «Shaxsga doir ma'lumotlar to'g'risida»gi 2019-yil 2-iyuldagi ZRU-547-son Qonuniga muvofiq tuzilgan. Saytda ro'yxatdan o'tish va oferta bilan birga ushbu siyosatga rozilik berilganda ma'lumotlarni qayta ishlashga roziligingiz olingan hisoblanadi.

# 2. Qanday ma'lumotlar to'planadi
- identifikatsiya: login, ism, familiya, telefon raqami, e-mail, tug'ilgan sana (ixtiyoriy);
- a'zolik: abonementlar, to'lovlar (summa, usul, sana; karta raqami to'liq saqlanmaydi), buyurtmalar, zalga kirish (tashrif) vaqtlari, mashg'ulotlarga bronlar;
- sog'liq va natijalar (faqat siz kiritsangiz): vazn, bo'y, maqsad, mashq rekordlari, ovqat va kaloriya yozuvlari;
- aloqa: Telegram chat identifikatori (agar ulasangiz), saytdagi xabarlar va chat yozishmalari;
- texnik: IP-manzil, brauzer turi, sessiya cookie-lari (kirish va xavfsizlik uchun zarur).

# 3. Maqsadlar va asos
Ma'lumotlar quyidagi maqsadlarda qayta ishlanadi: akkauntni yuritish va kirishni tasdiqlash; abonementlar, to'lovlar va zalga kirishni boshqarish; mashg'ulotlarga bron va murabbiy bilan ishlash; abonement tugashi va mashg'ulotlar haqida eslatmalar yuborish; xavfsizlik va firibgarlikning oldini olish; qonunchilik talablarini (shu jumladan buxgalteriya hisobini) bajarish. Asos — sizning roziligingiz va shartnomani (ofertani) bajarish zarurati.

# 4. Uchinchi shaxslarga berish
Ma'lumotlar sotilmaydi va reklama maqsadida uchinchi shaxslarga berilmaydi. Faqat xizmatni ko'rsatish uchun zarur bo'lgan hollarda ular quyidagilarga ochilishi mumkin: to'lov va SMS/e-mail xizmatlari provayderlari, xosting va fayl saqlash provayderlari, Telegram (agar siz botni ulagan bo'lsangiz), shuningdek qonun talab qilganda vakolatli davlat organlari.

# 5. Saqlash joyi va muddati
Ma'lumotlar saqlanadigan joy: [MA'LUMOTLAR SAQLANADIGAN JOY]. Operator shaxsga doir ma'lumotlar bazalarini qonunchilik talab qilgan tartibda saqlashni ta'minlaydi.
Akkaunt faol bo'lgan davrda ma'lumotlar saqlanadi. Akkauntni o'chirgandan keyin shaxsiy ma'lumotlar (ism, telefon, e-mail, rasm, tana o'lchamlari, ovqat yozuvlari, xabarlar) o'chiriladi yoki shaxsni aniqlab bo'lmaydigan holga keltiriladi. Moliyaviy yozuvlar (to'lovlar, buyurtmalar) buxgalteriya va soliq qonunchiligi talab qilgan muddat davomida — [SAQLASH MUDDATI] yil — shaxsni aniqlamaydigan tarzda saqlanadi.

# 6. Sizning huquqlaringiz
- o'zingiz haqingizda qanday ma'lumot saqlanishini bilish va uning nusxasini olish («Profil» → «Ma'lumotlarimni yuklab olish»);
- noto'g'ri ma'lumotni tuzatish («Profil»);
- roziligingizni qaytarib olish va ma'lumotlaringiz o'chirilishini talab qilish («Profil» → «Akkauntni o'chirish»);
- qayta ishlashga e'tiroz bildirish va vakolatli organga shikoyat qilish.
So'rovlar [EMAIL] manziliga yoki [TELEFON] raqamiga yuboriladi; javob qonunda belgilangan muddatda beriladi.

# 7. Xavfsizlik
Parollar bir tomonlama shifrlangan ko'rinishda saqlanadi, sessiyalar himoyalangan cookie orqali yuritiladi. Hech bir usul to'liq xavfsizlikni kafolatlay olmaydi; ma'lumotlar sizib chiqqan taqdirda Operator qonunda belgilangan tartibda xabar beradi.

# 8. Cookie
Sayt faqat zarur cookie-lardan foydalanadi: sessiya, til va mavzu tanlovi. Reklama cookie-lari ishlatilmaydi.

# 9. Aloqa va o'zgarishlar
Savollar bo'yicha: [YURIDIK NOM], [MANZIL], [TELEFON], [EMAIL]. Siyosat o'zgarsa, yangi tahrir shu sahifada e'lon qilinadi.
"""

PRIVACY_RU = """# 1. Общие сведения
Настоящая Политика конфиденциальности объясняет, как [YURIDIK NOM] (ИНН: [STIR], адрес: [MANZIL], далее — «Оператор») обрабатывает персональные данные, собранные на сайте. Она составлена в соответствии с Законом Республики Узбекистан «О персональных данных» от 2 июля 2019 года № ЗРУ-547. Регистрируясь на сайте и принимая оферту вместе с этой политикой, вы даёте согласие на обработку данных.

# 2. Какие данные собираются
- идентификация: логин, имя, фамилия, номер телефона, e-mail, дата рождения (по желанию);
- членство: абонементы, платежи (сумма, способ, дата; номер карты целиком не хранится), заказы, время посещений зала, записи на занятия;
- здоровье и результаты (только если вы их вносите): вес, рост, цель, рекорды, записи о питании и калориях;
- связь: идентификатор чата Telegram (если вы его подключили), сообщения на сайте и переписка в чате;
- технические: IP-адрес, тип браузера, сессионные cookie (необходимы для входа и безопасности).

# 3. Цели и основания
Данные обрабатываются для: ведения аккаунта и подтверждения входа; управления абонементами, платежами и входом в зал; записи на занятия и работы с тренером; напоминаний об окончании абонемента и занятиях; безопасности и предотвращения мошенничества; выполнения требований законодательства (в том числе бухгалтерского учёта). Основание — ваше согласие и необходимость исполнения договора (оферты).

# 4. Передача третьим лицам
Данные не продаются и не передаются третьим лицам в рекламных целях. Они могут раскрываться только в той мере, в какой это нужно для услуги: провайдерам платежей и SMS/e-mail, хостинга и хранения файлов, Telegram (если вы подключили бота), а также уполномоченным государственным органам по требованию закона.

# 5. Место и срок хранения
Место хранения данных: [MA'LUMOTLAR SAQLANADIGAN JOY]. Оператор обеспечивает хранение баз персональных данных в порядке, требуемом законодательством.
Пока аккаунт активен, данные хранятся. После удаления аккаунта личные данные (имя, телефон, e-mail, фото, замеры тела, записи о питании, сообщения) удаляются или обезличиваются. Финансовые записи (платежи, заказы) хранятся в обезличенном виде в течение срока, требуемого бухгалтерским и налоговым законодательством, — [SAQLASH MUDDATI] лет.

# 6. Ваши права
- знать, какие данные о вас хранятся, и получить их копию («Профиль» → «Скачать мои данные»);
- исправить неверные данные («Профиль»);
- отозвать согласие и потребовать удаления данных («Профиль» → «Удалить аккаунт»);
- возразить против обработки и пожаловаться в уполномоченный орган.
Запросы направляйте на [EMAIL] или по телефону [TELEFON]; ответ даётся в срок, установленный законом.

# 7. Безопасность
Пароли хранятся в необратимо зашифрованном виде, сессии защищены cookie. Ни один способ не гарантирует абсолютной безопасности; при утечке данных Оператор уведомит об этом в порядке, установленном законом.

# 8. Cookie
Сайт использует только необходимые cookie: сессия, выбор языка и темы. Рекламные cookie не используются.

# 9. Контакты и изменения
По вопросам: [YURIDIK NOM], [MANZIL], [TELEFON], [EMAIL]. При изменении политики новая редакция публикуется на этой странице.
"""

PRIVACY_EN = """# 1. Overview
This Privacy policy explains how [YURIDIK NOM] (tax ID: [STIR], address: [MANZIL], the "Operator") processes personal data collected on the site. It follows the Law of the Republic of Uzbekistan "On personal data" of 2 July 2019, No. ZRU-547. By registering and accepting the offer together with this policy you consent to the processing.

# 2. What data is collected
- identity: username, first and last name, phone number, e-mail, date of birth (optional);
- membership: memberships, payments (amount, method, date; the full card number is not stored), orders, gym entry times, class bookings;
- health and progress (only what you enter): weight, height, goal, lifting records, food and calorie entries;
- contact: Telegram chat ID (if you link it), site messages and chat;
- technical: IP address, browser type, session cookies (needed for sign-in and security).

# 3. Purposes and basis
Data is processed to: run your account and confirm sign-in; manage memberships, payments and entry; book classes and work with trainers; send reminders about expiring memberships and classes; keep the site secure and prevent fraud; meet legal duties (including bookkeeping). The basis is your consent and the need to perform the contract (the offer).

# 4. Sharing
Data is not sold or shared with third parties for advertising. It is disclosed only as far as the service needs: payment, SMS and e-mail providers, hosting and file-storage providers, Telegram (if you linked the bot), and public authorities where the law requires it.

# 5. Where and how long
Where data is stored: [MA'LUMOTLAR SAQLANADIGAN JOY]. The Operator keeps personal-data databases as the law requires.
Data is kept while your account is active. After you delete the account, personal data (name, phone, e-mail, photo, body measurements, food entries, messages) is deleted or anonymised. Financial records (payments, orders) are kept without identifying you for as long as accounting and tax law require — [SAQLASH MUDDATI] years.

# 6. Your rights
- to know what data is stored about you and get a copy (Profile → Download my data);
- to correct wrong data (Profile);
- to withdraw consent and ask for deletion (Profile → Delete account);
- to object to processing and complain to the authorised body.
Send requests to [EMAIL] or call [TELEFON]; we reply within the period set by law.

# 7. Security
Passwords are stored irreversibly hashed and sessions use protected cookies. No method is perfectly secure; if data is leaked the Operator will notify as the law requires.

# 8. Cookies
The site uses only necessary cookies: session, language and theme choice. No advertising cookies.

# 9. Contact and changes
Questions: [YURIDIK NOM], [MANZIL], [TELEFON], [EMAIL]. A changed policy is published on this page.
"""

REFUND_UZ = """# 1. Umumiy qoida
To'langan xizmat uchun pul quyida bayon etilgan hollarda va tartibda qaytariladi. Qaytarish so'rovi [EMAIL] manziliga, [TELEFON] raqamiga yoki Zal qabulxonasiga beriladi; so'rovda a'zo kodi (FZ-…) va to'lov raqami (P…) ko'rsatiladi.

# 2. Abonement
- abonement hali boshlanmagan va zalga kirilmagan bo'lsa — to'lov qilingan kundan boshlab [14] kun ichida to'liq summa qaytariladi;
- foydalanish boshlangan bo'lsa — ishlatilgan kunlar va chegirmalar (bonus kunlar, promokod) hisobga olinib, qolgan muddat uchun pul qaytariladi, [10]% xizmat haqi ushlab qolinishi mumkin;
- Zal xizmatni ko'rsata olmasa (ta'mir, yopilish) yoki a'zo tibbiy ma'lumotnoma bilan mashq qila olmasligini tasdiqlasa — qolgan muddat uchun to'liq qaytariladi yoki abonement muzlatiladi;
- muzlatilgan kunlar uchun pul qaytarilmaydi: ular abonement muddatiga qo'shiladi.

# 3. Do'kon mahsulotlari
Sifatsiz yoki noto'g'ri mahsulot olingan kundan [3] kun ichida almashtiriladi yoki pul qaytariladi. Ochilgan oziq-ovqat, sport ovqatlanishi va gigiena mahsulotlari qaytarilmaydi (sifatsiz bo'lsa — istisno). Yetkazib berish haqi, agar xato Zal tomonidan bo'lmasa, qaytarilmaydi.

# 4. Sovg'a sertifikati va mehmon taklifnomasi
Ishlatilmagan sovg'a sertifikati amal qilish muddati tugaguncha [14] kun ichida qaytarilishi mumkin; ishlatilgan yoki muddati o'tgan sertifikat va ishlatilgan mehmon taklifnomasi uchun pul qaytarilmaydi. Sertifikat summasi abonement narxidan oshsa, qoldiq qaytarilmaydi.

# 5. Qaytarish usuli va muddati
Pul to'lov qilingan usulda (karta, onlayn to'lov tizimi yoki naqd) qaytariladi. So'rov qabul qilingandan keyin [10] ish kuni ichida ko'rib chiqiladi; bank tomonidan o'tkazish muddati qo'shimcha [5] kungacha davom etishi mumkin.

# 6. Bekor qilingan to'lovlar
Tasdiqlanmagan (pul tushmagan) to'lov [24] soatdan keyin avtomatik bekor qilinadi; bunda hech qanday pul yechilmaydi. Promokod yoki sertifikat bekor qilingan to'lovda qayta tiklanadi.

# 7. Aloqa
[YURIDIK NOM], [MANZIL], [TELEFON], [EMAIL].
"""

REFUND_RU = """# 1. Общие правила
Деньги за оплаченную услугу возвращаются в случаях и порядке, описанных ниже. Запрос на возврат направляется на [EMAIL], по телефону [TELEFON] или на ресепшен Зала; укажите код участника (FZ-…) и номер платежа (P…).

# 2. Абонемент
- абонемент ещё не начался и входов не было — полная сумма возвращается в течение [14] дней с даты оплаты;
- если пользование началось — возвращается стоимость оставшегося срока с учётом использованных дней и скидок (бонусные дни, промокод), может удерживаться [10]% за обработку;
- если Зал не может оказать услугу (ремонт, закрытие) или участник подтверждает справкой невозможность заниматься — полный возврат за оставшийся срок либо заморозка;
- за замороженные дни деньги не возвращаются: они добавляются к сроку абонемента.

# 3. Товары магазина
Товар ненадлежащего качества или не тот заменяется либо деньги возвращаются в течение [3] дней с получения. Вскрытое питание, спортивное питание и гигиенические товары возврату не подлежат (кроме случаев брака). Стоимость доставки не возвращается, если ошибка не на стороне Зала.

# 4. Подарочный сертификат и гостевое приглашение
Неиспользованный сертификат можно вернуть в течение [14] дней, но не позже срока его действия; использованный или просроченный сертификат и использованное гостевое приглашение не возвращаются. Если сумма сертификата больше цены абонемента, остаток не возвращается.

# 5. Способ и срок возврата
Деньги возвращаются тем способом, которым была оплата (карта, онлайн-система или наличные). Запрос рассматривается в течение [10] рабочих дней; перевод банком может занять ещё до [5] дней.

# 6. Отменённые платежи
Неподтверждённый платёж (деньги не поступили) автоматически отменяется через [24] часа; при этом деньги не списываются. Промокод или сертификат при отмене платежа восстанавливается.

# 7. Контакты
[YURIDIK NOM], [MANZIL], [TELEFON], [EMAIL].
"""

REFUND_EN = """# 1. General rule
Money for a paid service is returned in the cases and the way described below. Send the refund request to [EMAIL], call [TELEFON] or ask at the Gym front desk; give your member code (FZ-…) and payment number (P…).

# 2. Membership
- the membership has not started and there were no entries — the full amount is returned within [14] days of payment;
- if use has begun — the value of the remaining period is returned after deducting days used and discounts (bonus days, promo code); a [10]% processing fee may be kept;
- if the Gym cannot provide the service (repairs, closure) or the member proves with a medical note that they cannot train — full refund for the remaining period, or a freeze;
- frozen days are not refunded: they are added to the membership.

# 3. Shop products
A faulty or wrong product is replaced or refunded within [3] days of receipt. Opened food, sports nutrition and hygiene products cannot be returned (unless faulty). Delivery fees are not refunded unless the mistake was the Gym's.

# 4. Gift certificate and guest pass
An unused certificate can be refunded within [14] days and before it expires; a used or expired certificate and a used guest pass are not refunded. If a certificate is worth more than the membership price, the rest is not refunded.

# 5. How and when
Money goes back the way it was paid (card, online system or cash). A request is reviewed within [10] working days; the bank transfer can take up to [5] more days.

# 6. Cancelled payments
An unconfirmed payment (money not received) is cancelled automatically after [24] hours; nothing is charged. A promo code or certificate is restored when a payment is cancelled.

# 7. Contact
[YURIDIK NOM], [MANZIL], [TELEFON], [EMAIL].
"""

DEFAULTS = {
    "oferta": {"title_uz": "Ommaviy oferta", "title_ru": "Публичная оферта", "title_en": "Public offer",
               "body_uz": OFERTA_UZ, "body_ru": OFERTA_RU, "body_en": OFERTA_EN},
    "privacy": {"title_uz": "Maxfiylik siyosati", "title_ru": "Политика конфиденциальности", "title_en": "Privacy policy",
                "body_uz": PRIVACY_UZ, "body_ru": PRIVACY_RU, "body_en": PRIVACY_EN},
    "refund": {"title_uz": "Qaytarish qoidalari", "title_ru": "Правила возврата", "title_en": "Refund rules",
               "body_uz": REFUND_UZ, "body_ru": REFUND_RU, "body_en": REFUND_EN},
}
