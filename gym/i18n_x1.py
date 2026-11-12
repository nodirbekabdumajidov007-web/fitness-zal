"""Turkish / Kyrgyz / Tajik UI text, part 1. Line: key||Turkish||Kyrgyz||Tajik (see gym/i18n.py)."""

RAW = """
brand||Fitnes Zal||Fitnes Zal||Fitnes Zal
tag||Yeni sen bugün başlıyor||Жаңы сен бүгүн башталат||Шахси нав аз имрӯз оғоз мешавад
tag_sub||Her antrenman, daha güçlü, daha sağlıklı ve kendine daha güvenen sana bir adım.||Ар бир машыгуу — күчтүүрөөк, дени сак жана өзүнө ишенген сенге карай бир кадам.||Ҳар машқ як қадам ба сӯи шахси тавоно, солим ва боэътимод аст.
nav_home||Ana sayfa||Башкы бет||Саҳифаи асосӣ
nav_dash||Panelim||Кабинет||Кабинет
nav_plans||Üyelikler||Абонементтер||Абонементҳо
nav_shop||Mağaza||Дүкөн||Мағоза
nav_classes||Dersler||Сабактар||Машғулиятҳо
nav_trainers||Antrenörler||Машыктыруучулар||Мураббиён
nav_progress||Sonuçlarım||Жыйынтыктарым||Натиҷаҳои ман
nav_reviews||Yorumlar||Пикирлер||Фикрҳо
nav_profile||Profil||Профиль||Профил
nav_desk||Resepsiyon||Кабыл алуу||Қабулгоҳ
nav_admin||Yönetim paneli||Башкаруу панели||Панели идора
login||Giriş yap||Кирүү||Ворид шудан
register||Kayıt ol||Катталуу||Сабти ном
logout||Çıkış||Чыгуу||Баромад
open||Açık||Ачык||Кушода
closed||Kapalı||Жабык||Баста
hours||Çalışma saatleri||Иш убактысы||Соатҳои корӣ
first_name||Ad||Аты||Ном
last_name||Soyad||Фамилиясы||Насаб
phone||Telefon numarası||Телефон номери||Рақами телефон
password||Şifre||Сырсөз||Рамз
show||Göster||Көрсөтүү||Нишон додан
hide||Gizle||Жашыруу||Пинҳон кардан
or||veya||же||ё
google_off||Google ile giriş yapılandırılmamış (sunucuda GOOGLE_CLIENT_ID gerekir).||Google менен кирүү жөндөлгөн эмес (серверде GOOGLE_CLIENT_ID керек).||Воридшавӣ тавассути Google танзим нашудааст (дар сервер GOOGLE_CLIENT_ID лозим аст).
no_account||Hesabınız yok mu?||Аккаунтуңуз жокпу?||Аккаунт надоред?
have_account||Zaten hesabınız var mı?||Аккаунтуңуз барбы?||Аллакай аккаунт доред?
err_fields||Alanları doğru doldurun||Талааларды туура толтуруңуз||Майдонҳоро дуруст пур кунед
err_phone||Numara +998 ile başlamalı ve 9 haneden oluşmalı||Номер +998 менен башталып, 9 санден турушу керек||Рақам бояд бо +998 оғоз шавад ва аз 9 рақам иборат бошад
err_pass||Şifre 6 ile 128 karakter arasında olmalı||Сырсөз 6дан 128 белгиге чейин болушу керек||Рамз бояд аз 6 то 128 аломат бошад
err_exists||Bu numara zaten kayıtlı||Бул номер мурунтан катталган||Ин рақам аллакай сабт шудааст
err_cred||Numara veya şifre hatalı||Номер же сырсөз туура эмес||Рақам ё рамз нодуруст аст
err_blocked||Hesabınız engellendi. Yönetici ile iletişime geçin||Аккаунтуңуз бөгөттөлдү. Администратор менен байланышыңыз||Аккаунти шумо масдуд шудааст. Бо администратор тамос гиред
err_rate||Çok fazla deneme. 10 dakika sonra tekrar deneyin||Өтө көп аракет. 10 мүнөттөн кийин кайра аракет кылыңыз||Кӯшишҳо аз ҳад зиёд. Баъди 10 дақиқа дубора кӯшиш кунед
err_stock||Yeterli stok yok||Запас жетишсиз||Захира кофӣ нест
err_method||Bu ödeme yöntemi kullanılamıyor||Бул төлөм ыкмасы жеткиликсиз||Ин усули пардохт дастнорас аст
err_member||Önce aktif bir üyelik gerekir||Адегенде активдүү абонемент керек||Аввал абонементи фаъол лозим аст
err_frozen||Üyeliğiniz dondurulmuş: dondurma bitene kadar giriş kapalı||Абонементиңиз тоңдурулган: тоңдуруу бүтмөйүнчө кирүү жабык||Абонементи шумо яхбандӣ шудааст: то анҷоми яхбандӣ воридшавӣ баста аст
err_google||Google hesabı doğrulanamadı||Google аккаунту текшерилген жок||Аккаунти Google тасдиқ нашуд
promo_bad||Promosyon kodu geçersiz veya süresi dolmuş||Промокод жараксыз же мөөнөтү бүткөн||Промокод нодуруст ё муҳлати он гузаштааст
cart_bad||Sepetteki bir ürün bulunamadı||Себеттеги бир буюм табылган жок||Яке аз ашёи сабад ёфт нашуд
welcome||Hoş geldiniz!||Кош келиңиз!||Хуш омадед!
saved||Kaydedildi||Сакталды||Захира шуд
hello||Merhaba||Салам||Салом
membership||Üyelik||Абонемент||Абонемент
no_membership||Üyelik yok||Абонемент жок||Абонемент нест
active||Aktif||Активдүү||Фаъол
expired||Süresi doldu||Мөөнөтү бүттү||Муҳлаташ гузашт
frozen||Dondurulmuş||Тоңдурулган||Яхбандишуда
upcoming||Başlamadı||Башталган жок||Оғоз нашудааст
until||şuna kadar||чейин||то
days_left||gün kaldı||күн калды||рӯз монд
checkin||Salondayım||Мен залдамын||Ман дар толорам
checked_in||Bugün giriş yapıldı||Бүгүн кирүү белгиленди||Имрӯз воридшавӣ қайд шуд
check_ok||Ziyaret kaydedildi. İyi antrenmanlar!||Визит катталды. Жакшы машыгыңыз!||Ташриф сабт шуд. Машқи хуб!
visits_month||Bu ayki ziyaretler||Ушул айдагы визиттер||Ташрифҳои ин моҳ
streak||Gün serisi||Күндөр сериясы||Силсилаи рӯзҳо
member_id||Üye numarası||Мүчө номери||Рақами аъзо
expiring||Üyeliğiniz {days} gün sonra bitiyor. Önceden yenileyin.||Абонементиңиз {days} күндөн кийин бүтөт. Алдын ала узартыңыз.||Абонементи шумо баъди {days} рӯз тамом мешавад. Пешакӣ тамдид кунед.
pending_note||Ödemeniz onay bekliyor. Salonda ödeyin, yönetici onaylayacak.||Төлөмүңүз ырастоону күтүүдө. Залда төлөңүз, администратор ырастайт.||Пардохти шумо мунтазири тасдиқ аст. Дар толор пардохт кунед, администратор тасдиқ мекунад.
announcements||Duyurular||Жарыялар||Эълонҳо
my_bookings||Rezervasyonlarım||Брондорум||Брони ман
none_yet||Henüz yok||Азырынча жок||Ҳоло нест
contacts||İletişim||Байланыш||Тамос
address||Adres||Дарек||Суроға
price_unit||UZS||UZS||сӯм
months_n||{n} ay||{n} ай||{n} моҳ
buy||Satın al||Сатып алуу||Харидан
pay||Ödeme||Төлөм||Пардохт
pay_method||Ödeme yöntemi||Төлөм ыкмасы||Усули пардохт
cash||Salonda nakit||Залда накталай||Нақд дар толор
promo||Promosyon kodu||Промокод||Промокод
bought_paid||Üyelik etkinleştirildi.||Абонемент иштетилди.||Абонемент фаъол шуд.
bought_pending||Salonda ödeyin. Üyelik yönetici onayladığında başlar.||Залда төлөңүз. Абонемент администратор ырастаганда башталат.||Дар толор пардохт кунед. Абонемент пас аз тасдиқи администратор оғоз мешавад.
demo_note||Ödeme yöntemleri test modunda: gerçek bir ödeme geçidi bağlı değil.||Төлөм ыкмалары сыноо режиминде: чыныгы төлөм шлюзу туташтырылган эмес.||Усулҳои пардохт дар ҳолати санҷишӣ ҳастанд: шлюзи воқеии пардохт пайваст нашудааст.
perk_all||Tüm alanlar||Бардык зоналар||Ҳамаи минтақаҳо
perk_save||200.000 UZS tasarruf||200 000 UZS үнөмдөө||200 000 UZS сарфа
perk_consult||Antrenör danışmanlığı||Машыктыруучунун кеңеши||Машварати мураббӣ
perk_locker||Kişisel dolap||Жеке шкаф||Шкафи шахсӣ
perk_sauna||Sauna||Сауна||Сауна
perk_vip||VIP alan||VIP зона||Минтақаи VIP
plan_m1||1 aylık||1 айлык||1 моҳа
plan_m3||3 aylık||3 айлык||3 моҳа
plan_vip||VIP 1 aylık||VIP 1 айлык||VIP 1 моҳа
freeze||Üyeliği dondur||Абонементти тоңдуруу||Абонементро яхбандӣ кардан
freeze_help||Bir kez, en fazla {max} gün. Bitiş tarihiniz aynı gün sayısı kadar ileri kayar.||Бир жолу, {max} күнгө чейин. Бүтүү күнүңүз ошончо күнгө жылат.||Як маротиба, то {max} рӯз. Санаи анҷоми шумо ба ҳамон қадар рӯз ба пеш мегузарад.
freeze_do||Dondur||Тоңдуруу||Яхбандӣ кардан
freeze_days||Gün||Күн||Рӯз
freeze_ok||Üyelik donduruldu: {until} tarihinde geri dönüyorsunuz.||Абонемент тоңдурулду: {until} күнү кайтасыз.||Абонемент яхбандӣ шуд: шумо дар {until} бармегардед.
freeze_fail||Dondurulamadı (zaten kullanıldı veya üyelik yok).||Тоңдурулган жок (мурун колдонулган же абонемент жок).||Яхбандӣ нашуд (аллакай истифода шудааст ё абонемент нест).
frozen_until||Şu tarihe kadar donduruldu:||Чейин тоңдурулган:||То ин сана яхбандӣ шудааст:
shop||Mağaza||Дүкөн||Мағоза
all||Tümü||Баары||Ҳама
search||Ara||Издөө||Ҷустуҷӯ
in_stock||Stokta||Бар||Мавҷуд аст
sold_out||Tükendi||Түгөндү||Тамом шуд
add||Ekle||Кошуу||Илова кардан
cart||Sepet||Себет||Сабад
cart_empty||Sepetiniz boş||Себетиңиз бош||Сабади шумо холӣ аст
remove||Kaldır||Өчүрүү||Бардоштан
update||Güncelle||Жаңыртуу||Навсозӣ
total||Toplam||Жалпы||Ҷамъ
discount||İndirim||Арзандатуу||Тахфиф
checkout||Sipariş ver||Заказ берүү||Фармоиш додан
order_ok||Sipariş verildi. Salondan teslim alın.||Заказ кабыл алынды. Залдан алып кетиңиз.||Фармоиш қабул шуд. Онро аз толор гиред.
login_first||Devam etmek için lütfen giriş yapın||Улантуу үчүн кириңиз||Барои идома додан лутфан ворид шавед
orders||Siparişlerim||Заказдарым||Фармоишҳои ман
payments||Ödemeler||Төлөмдөр||Пардохтҳо
receipt||Makbuz||Чек||Квитансия
print||Yazdır||Басып чыгаруу||Чоп кардан
user||Üye||Мүчө||Аъзо
date||Tarih||Дата||Сана
type||Tür||Түрү||Навъ
amount||Tutar||Сумма||Маблағ
status||Durum||Статус||Ҳолат
item||Ürün||Буюм||Ашё
qty||Adet||Саны||Миқдор
st_pending||Onay bekliyor||Ырастоону күтүүдө||Мунтазири тасдиқ
st_paid||Ödendi||Төлөндү||Пардохт шуд
st_cancelled||İptal edildi||Жокко чыгарылды||Бекор шуд
st_new||Yeni||Жаңы||Нав
st_done||Teslim edildi||Тапшырылды||Супорида шуд
kind_plan||Üyelik||Абонемент||Абонемент
kind_shop||Mağaza||Дүкөн||Мағоза
classes||Grup dersleri||Топтук сабактар||Машғулиятҳои гурӯҳӣ
next_session||Sıradaki:||Кийинки:||Навбатӣ:
seats_left||{n} yer kaldı||{n} орун калды||{n} ҷой монд
full||Dolu||Толук||Пур
book||Yer ayırt||Жазылуу||Ном навиштан
booked||Yer ayrıldı||Жазылды||Сабт шуд
cancel_booking||İptal||Жокко чыгаруу||Бекор кардан
book_ok||Yer ayrıldı.||Жазылдыңыз.||Номнавис шуд.
book_fail||Yer ayrılamadı.||Жазылуу мүмкүн болбоду.||Ном навиштан имкон надошт.
cancel_ok||Rezervasyon iptal edildi.||Брондоо жокко чыгарылды.||Брон бекор шуд.
trainer||Antrenör||Машыктыруучу||Мураббӣ
trainers||Antrenörler||Машыктыруучулар||Мураббиён
years_exp||yıl deneyim||жыл тажрыйба||соли таҷриба
weekday_0||Pazartesi||Дүйшөмбү||Душанбе
weekday_1||Salı||Шейшемби||Сешанбе
weekday_2||Çarşamba||Шаршемби||Чоршанбе
weekday_3||Perşembe||Бейшемби||Панҷшанбе
weekday_4||Cuma||Жума||Ҷумъа
weekday_5||Cumartesi||Ишемби||Шанбе
weekday_6||Pazar||Жекшемби||Якшанбе
progress||İlerlemem||Менин жыйынтыгым||Пешрафти ман
progress_help||Kilonuzu ve boyunuzu girin, grafik kendiliğinden çizilir.||Салмагыңыз менен бойуңузду жазыңыз, график өзү тартылат.||Вазн ва қади худро қайд кунед, диаграмма худ кашида мешавад.
weight||Kilo (kg)||Салмак (кг)||Вазн (кг)
height||Boy (cm)||Бой (см)||Қад (см)
note||Not||Эскертүү||Эзоҳ
bmi||VKİ||БМИ||ИМТ
bmi_low||Zayıf||Салмак жетишсиз||Вазни кам
bmi_ok||Normal||Нормалдуу||Муқаррарӣ
bmi_high||Fazla kilolu||Ашыкча салмак||Вазни зиёд
bmi_obese||Obez||Семирүү||Фарбеҳӣ
change||Değiştir||Өзгөртүү||Тағйир додан
delete||Sil||Өчүрүү||Нест кардан
sure||Emin misiniz?||Ишенимдүүсүзбү?||Боварӣ доред?
reviews||Yorumlar||Пикирлер||Фикрҳо
review_help||Yorumunuz yönetici onayladıktan sonra görünür.||Пикириңиз администратор ырастагандан кийин көрүнөт.||Фикри шумо пас аз тасдиқи администратор намоён мешавад.
rating||Puan||Баа||Баҳо
comment||Yorum||Комментарий||Шарҳ
send||Gönder||Жөнөтүү||Фиристодан
review_ok||Teşekkürler! Yorumunuz onaya gönderildi.||Рахмат! Пикириңиз ырастоого жөнөтүлдү.||Ташаккур! Фикри шумо барои тасдиқ фиристода шуд.
profile||Profil||Профиль||Профил
save||Kaydet||Сактоо||Захира кардан
language||Dil||Тил||Забон
theme||Tema||Тема||Мавзӯъ
light||Açık||Жарык||Равшан
dark||Koyu||Караңгы||Торик
auto||Otomatik||Авто||Худкор
change_pass||Şifreyi değiştir||Сырсөздү өзгөртүү||Рамзро тағйир додан
cur_pass||Mevcut şifre||Учурдагы сырсөз||Рамзи ҷорӣ
new_pass||Yeni şifre||Жаңы сырсөз||Рамзи нав
err_wrong_pass||Mevcut şifre yanlış||Учурдагы сырсөз туура эмес||Рамзи ҷорӣ нодуруст аст
desk||Resepsiyon||Кабыл алуу||Қабулгоҳ
desk_find||Üye bul (telefon, ad veya FZ numarası)||Мүчөнү табуу (телефон, аты же FZ номери)||Ёфтани аъзо (телефон, ном ё рақами FZ)
desk_checkin||Giriş kaydet||Кирүүнү белгилөө||Воридшавиро қайд кардан
desk_sell||Nakit sat||Накталай сатуу||Бо нақд фурӯхтан
desk_pending||Onay bekleyen ödemeler||Ырастоону күткөн төлөмдөр||Пардохтҳои мунтазири тасдиқ
desk_orders||Teslim edilecek siparişler||Тапшырыла турган заказдар||Фармоишҳои супоридашаванда
confirm||Onayla||Ырастоо||Тасдиқ кардан
hand_over||Teslim edildi||Тапшырылды||Супорида шуд
block||Engelle||Бөгөттөө||Масдуд кардан
unblock||Engeli kaldır||Бөгөттөн чыгаруу||Масдудиятро бардоштан
visits_today||Bugünkü ziyaretler||Бүгүнкү визиттер||Ташрифҳои имрӯз
active_members||Aktif üyeler||Активдүү мүчөлөр||Аъзоёни фаъол
done_ok||Tamam.||Даяр.||Тайёр.
rating_avg||Ortalama puan||Орточо баа||Баҳои миёна
footer_demo||Bu proje örnek veriyle çalışır.||Бул долбоор үлгү маалыматтар менен иштейт.||Ин лоиҳа бо маълумоти намунавӣ кор мекунад.
no_results||Hiçbir şey bulunamadı||Эчтеке табылган жок||Ҳеҷ чиз ёфт нашуд
forgot||Şifrenizi mi unuttunuz?||Сырсөздү унутуп калдыңызбы?||Рамзро фаромӯш кардед?
forgot_help||Telefon numaranızı girin, size bir kod gönderelim.||Телефон номериңизди киргизиңиз, биз сизге код жөнөтөбүз.||Рақами телефонатонро ворид кунед, мо ба шумо рамз мефиристем.
send_code||Kod gönder||Код жөнөтүү||Фиристодани рамз
sms_code||SMS kodu||SMS коду||Рамзи SMS
otp_sent||Numara kayıtlıysa bir kod gönderildi.||Номер катталган болсо, код жөнөтүлдү.||Агар рақам сабт бошад, рамз фиристода шуд.
otp_bad||Kod yanlış veya süresi dolmuş||Код туура эмес же мөөнөтү бүткөн||Рамз нодуруст ё муҳлати он гузаштааст
sms_fail||SMS gönderilemedi. Daha sonra tekrar deneyin.||SMS жөнөтүлгөн жок. Кийинчерээк аракет кылыңыз.||SMS фиристода нашуд. Баъдтар дубора кӯшиш кунед.
reset_ok||Şifre güncellendi. Artık giriş yapabilirsiniz.||Сырсөз жаңыртылды. Эми кире аласыз.||Рамз навсозӣ шуд. Акнун ворид шуда метавонед.
verify_needed||Devam etmek için lütfen telefon numaranızı doğrulayın.||Улантуу үчүн телефон номериңизди ырастаңыз.||Барои идома додан лутфан рақами телефонатонро тасдиқ кунед.
verify_phone||Telefonu doğrula||Телефонду ырастоо||Тасдиқи телефон
verify_help||Kod şu numaraya gönderilir:||Код төмөнкү номерге жөнөтүлөт:||Рамз ба ин рақам фиристода мешавад:
verified||Doğrulandı||Ырасталды||Тасдиқ шуд
verified_ok||Telefon doğrulandı.||Телефон ырасталды.||Телефон тасдиқ шуд.
add_phone_first||Önce profilinize telefon numaranızı ekleyin.||Адегенде профилиңизге телефон номериңизди кошуңуз.||Аввал рақами телефонатонро ба профил илова кунед.
member_card||Üye kartı||Мүчө картасы||Корти аъзо
card_help||Bu QR kodu resepsiyonda gösterin.||Бул QR кодду кабыл алууда көрсөтүңүз.||Ин QR-кодро дар қабулгоҳ нишон диҳед.
achievements||Başarılar||Жетишкендиктер||Дастовардҳо
points||Puan||Упай||Хол
points_help||Her ziyaret 10, her rezervasyon 5, her sipariş 2, davet edilen her arkadaş 50 puan.||Ар бир визит үчүн 10, брондоо үчүн 5, заказ үчүн 2, чакырылган дос үчүн 50 упай.||Барои ҳар ташриф 10, брон 5, фармоиш 2, барои ҳар дӯсти даъватшуда 50 хол.
leaderboard||Bu ayın en aktifleri||Айдын эң активдүүлөрү||Фаъолтаринҳои ин моҳ
leaderboard_help||Yalnızca adınız ve soyadınızın baş harfi görünür. Profilinizden çıkabilirsiniz.||Аты-жөнүңүздүн аты жана фамилиянын биринчи тамгасы гана көрүнөт. Профилден чыксаңыз болот.||Танҳо номи шумо ва ҳарфи аввали насаб намоён мешавад. Дар профил метавонед аз он баромад кунед.
show_board||Beni liderlik tablosunda göster||Мени лидерборддо көрсөтүү||Маро дар ҷадвали пешсафон нишон диҳед
ach_visits_1||İlk ziyaret||Биринчи визит||Ташрифи аввал
ach_visits_10||10 ziyaret||10 визит||10 ташриф
ach_visits_25||25 ziyaret||25 визит||25 ташриф
ach_visits_50||50 ziyaret||50 визит||50 ташриф
ach_visits_100||100 ziyaret||100 визит||100 ташриф
ach_visits_250||250 ziyaret||250 визит||250 ташриф
ach_streak_7||7 günlük seri||7 күндүк серия||Силсилаи 7-рӯза
ach_streak_30||30 günlük seri||30 күндүк серия||Силсилаи 30-рӯза
ach_classes_5||5 grup dersi||5 топтук сабак||5 машғулияти гурӯҳӣ
ach_first_order||İlk alışveriş||Биринчи сатып алуу||Харидони аввал
ach_tracker_3||3 vücut ölçümü||Дененин 3 өлчөмү||3 андозаи бадан
ach_reviewer||Yorum bıraktı||Пикир калтырды||Фикр гузошт
ach_referrer||Arkadaş getirdi||Дос алып келди||Дӯст овард
workouts||Antrenman planım||Менин машыгуу планым||Нақшаи машқи ман
today||bugün||бүгүн||имрӯз
mark_done||Tamamlandı işaretle||Аткарылды деп белгилөө||Иҷро шуд қайд кунед
done_mark||Tamamlandı||Аткарылды||Иҷро шуд
no_plan||Antrenörünüz henüz bir plan belirlemedi. Resepsiyondan sorun.||Машыктыруучуңуз азырынча план түзө элек. Кабыл алуудан сураңыз.||Мураббии шумо ҳанӯз нақша тартиб надодааст. Дар қабулгоҳ пурсед.
today_ex||Bugün: {done} / {total} egzersiz||Бүгүн: {done} / {total} көнүгүү||Имрӯз: {done} / {total} машқ
rest_day||Bugün dinlenme günü||Бүгүн эс алуу күнү||Имрӯз рӯзи истироҳат
offline_title||Çevrimdışısınız||Интернет жок||Шумо оффлайн ҳастед
offline_text||Bağlantı geri geldiğinde sayfa tekrar çalışır.||Байланыш кайтканда барак кайра иштейт.||Пас аз барқарор шудани алоқа саҳифа боз кор мекунад.
retry||Tekrar dene||Кайра аракет кылуу||Дубора кӯшиш кунед
scan||QR tarayıcı||QR сканер||Скенери QR
scan_start||Kamerayı başlat||Камераны иштетүү||Оғози камера
scan_manual||Kodu yazın veya tarayıcı kullanın||Кодду териңиз же сканерди колдонуңуз||Рамзро ворид кунед ё скенер истифода баред
scan_help||USB tarayıcı kodu bu alana yazar. Kamera yalnızca Chrome ve Edge'de çalışır.||USB сканер кодду ушул талаага жазат. Камера Chrome жана Edge'де гана иштейт.||Скенери USB рамзро ба ин майдон ворид мекунад. Камера танҳо дар Chrome ва Edge кор мекунад.
scan_err||Sunucuya ulaşılamıyor||Серверге жетүү мүмкүн эмес||Ба сервер дастрасӣ нест
scan_nocam||Bu tarayıcıda kamerayla tarama kullanılamıyor. Kodu elle yazın.||Бул браузерде камера менен сканерлөө жеткиликсиз. Кодду кол менен териңиз.||Дар ин браузер скенкунии камера дастнорас аст. Рамзро дастӣ ворид кунед.
scan_bad||Geçersiz kod||Жараксыз код||Рамзи нодуруст
scan_ok||Giriş kaydedildi||Кирүү катталды||Воридшавӣ сабт шуд
invite||Arkadaşını davet et||Досуңду чакыр||Дӯстатонро даъват кунед
invite_help||Arkadaşınız bu bağlantıyla kaydolup ilk üyeliğini aldığında ikiniz de {days} bonus gün kazanırsınız.||Досуңуз бул шилтеме менен катталып, биринчи абонементин алганда экөөңүз тең {days} бонус күн аласыздар.||Вақте дӯстатон бо ин пайванд сабти ном карда, абонементи аввалро мегирад, ҳар дуятон {days} рӯзи бонус мегиред.
copy||Kopyala||Көчүрүү||Нусха бардоштан
copied||Kopyalandı||Көчүрүлдү||Нусха бардошта шуд
invited_n||Davet edilen: {n}, ödüllendirilen: {ok}||Чакырылган: {n}, сыйлык алган: {ok}||Даъватшуда: {n}, мукофот гирифтааст: {ok}
invited_by||{name} sizi davet etti. İlk üyeliğinizle bonus gün kazanacaksınız.||{name} сизди чакырды. Биринчи абонементиңиз менен бонус күн аласыз.||{name} шуморо даъват кард. Бо абонементи аввалини худ рӯзи бонус мегиред.
pt||Kişisel antrenman||Жеке машыгуу||Машқи шахсӣ
pt_time||Tercih edilen saat||Ыңгайлуу убакыт||Вақти дилхоҳ
pt_request||İstek gönder||Өтүнүч жөнөтүү||Фиристодани дархост
pt_mine||Kişisel seanslarım||Менин жеке машыгууларым||Машқҳои шахсии ман
pt_requested||İstendi||Суралды||Дархост шуд
pt_confirmed||Onaylandı||Ырасталды||Тасдиқ шуд
pt_cancelled||İptal edildi||Жокко чыгарылды||Бекор шуд
pt_bad||Geçersiz saat: en az 1 saat sonrası, 60 gün içinde ve çalışma saatlerinde olmalı (en fazla 3 bekleyen istek).||Жараксыз убакыт: кеминде 1 саатан кийин, 60 күндүн ичинде жана иш убактысында болушу керек (күтүүдөгү өтүнүч эң көбү 3).||Вақти нодуруст: на камтар аз 1 соат баъд, дар доираи 60 рӯз ва дар соатҳои корӣ (ҳадди аксар 3 дархости мунтазир).
"""
