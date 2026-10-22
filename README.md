# Fitnes Zal (Django)

Django 5.2: server shablonlari, formalar, Django admin (dashboard va hisobotlar bilan), qabulxona, QR skaner, Telegram bot, SMS, Click. Til: o'zbek, rus, ingliz. Yorug' va qorong'i rejim. Telefonga o'rnatiladigan ilova (PWA).

## Ishga tushirish (kompyuterda)

`start.bat` ni ikki marta bosing: `.venv` yaratadi, Django va segno'ni o'rnatadi, bazani tayyorlaydi, namuna ma'lumot qo'shadi va serverni ochadi.
Sayt: http://127.0.0.1:8000. Admin paroli terminalda **bir marta** chiqadi. Oynani yopsangiz sayt to'xtaydi.

Testlar (42 ta): `.venv\Scripts\python manage.py test gym`

## Admin kirishi

Telefon `+998 90 877 55 05`, parol oxiriga `.admin` qo'shing (`parolim.admin`). `.admin`siz kirsangiz oddiy a'zo bo'lasiz, admin sahifalar esa a'zolarga 404 ko'rinadi.

- `/django-admin/`: dashboard, a'zolar, to'lovlar, buyurtmalar, mahsulotlar, mashq rejalari, shaxsiy mashg'ulotlar, sozlamalar va amallar (+30 kun, bloklash, tasdiqlash, CSV).
- `/django-admin/reports/`: hisobotlar (oylik tushum, yangi a'zolar, gavjum kun va soatlar, eng ko'p sotilgan mahsulot, qayta obuna).
- `/staff/`: qabulxona. `/staff/scan/`: QR skaner (telefon kamerasi yoki USB skaner).

## Funksiyalar

A'zo: ro'yxatdan o'tish, abonement (promokod, muzlatish), "Zalga kirdim", do'kon va savat, guruh mashg'ulotlariga bron, **shaxsiy mashg'ulot so'rovi**,
**mashq rejasi** (murabbiy admin paneldan yozadi, a'zo kunma-kun belgilaydi), tana o'lchami va BMI grafigi, **yutuqlar, ball va oylik reyting**,
**QR a'zo kartasi**, **do'stni taklif qilish** (ikkalasiga bonus kunlar), fikr qoldirish, kvitansiya, **parolni SMS bilan tiklash**, **telefonni tasdiqlash**, **Telegram eslatmalari**.

## Mashq darslari (`/training/`)

Har kun uchun mashg'ulotlar: hafta kunini tanlaysiz, tur (kuch, kardio, yoga...) va daraja bo'yicha filtrlaysiz. Har darsda video, "qanday bajariladi" qadamlari, ishlaydigan mushaklar, jihoz va xatolar/maslahatlar bor. Hafta kuni bo'sh qoldirilgan dars **har kuni** ko'rinadi (masalan qizdirish).

Admin panel → **Mashg'ulot turlari** va **Darslar**. Video qo'shishning ikki yo'li:
1. **Faylni yuklash** (`.mp4` yoki `.webm`, standart chegara 500 MB, `FZ_MAX_VIDEO_MB`): "Video fayl" maydoni. Fayl `media/` papkasiga tushadi va faqat dastur orqali beriladi (to'g'ridan-to'g'ri havolasi yo'q). **VIP darsning videosini faqat VIP a'zolar ko'ra oladi**, videoni o'tkazib ko'rish (seek) ham ishlaydi.
2. **Havola:** YouTube, Vimeo yoki `.mp4` havolasi (faqat `https://`). YouTube/Vimeo sahifa ichida ko'rinadi.
Yuklangan fayl havoladan ustun turadi. **Internetga chiqarganda:** bepul hostingning diski vaqtincha, yuklangan videolar yo'qolib qoladi. Doimiy disk yoki YouTube (Unlisted) ishlating. Katta videolar uchun YouTube qulayroq. YouTube havolasi VIP bo'lsa ham, havola biladigan odam uni ochishi mumkin, shuning uchun to'liq yopiq VIP video kerak bo'lsa faylni yuklang.
`setup_gym --demo` 16 ta **namuna** dars qo'shadi (umumiy tavsiyalar, video yo'q): ularni o'z murabbiylaringiz darslari bilan almashtiring.

## Chat (`/chat/`)

- **Shaxsiy yozishmalar:** a'zoni ism yoki a'zo raqami (FZ-0012) bilan topasiz va yozasiz. Telefon raqam bilan **qidirib bo'lmaydi** va hech kimga ko'rinmaydi. Boshqalar sizni "Aziz K." ko'rinishida ko'radi.
- **Umumiy xona:** barcha kirgan a'zolar. **VIP xona:** faqat VIP a'zolar (va xodimlar).
- Yangi xabarlar har 3 soniyada o'zi keladi (WebSocket yo'q, oddiy so'rov). Menyuda o'qilmagan shaxsiy xabarlar soni chiqadi.
- **Himoya:** bloklash (ikki tomonlama), xabarga shikoyat, o'z xabarini o'chirish, daqiqasiga 15 ta xabar chegarasi, 1000 belgi, profilda "qidiruvda ko'rinmayman" tanlovi. Xabarlar faqat matn: havolalar bosiladigan qilinmaydi, HTML ishlamaydi.
- **Moderatsiya:** admin panel → **Chat shikoyatlari** (xabar atrofidagi suhbat bilan): yashirish, yuboruvchini chetlatish. Shaxsiy yozishmalarni xodimlar **ro'yxatdan ko'ra olmaydi**: ular admin panelda faqat shikoyat qilinganda ko'rinadi. Umumiy va VIP xonalar to'liq ko'rinadi.
- A'zolarga chatda "telefon so'rash taqiqlanadi" deb ogohlantirilgan. Chat uchun kimdir shikoyat qilsa, xodim ko'rib chiqishi kerak: shikoyatlar sonini admin bosh sahifasida ko'rasiz.

## VIP obuna (`/vip/`): oyiga 50 000 so'm

Gym abonementidan alohida sotib olinadi (karta, naqd, Click). Imkoniyatlari: faqat VIP uchun darslar (dasturlar, ovqatlanish, yog' yoqish), do'kondan 10% chegirma, ikki baravar ball, profilda VIP belgisi.
Narx, muddat va chegirma foizi admin panelda: **Zal sozlamalari**. Narxni brauzer o'zgartira olmaydi, u serverdan olinadi. Qayta sotib olsangiz kunlar ustiga qo'shiladi.
**"VIP 1 oylik" (600 000 so'm) gym abonementi** egalari VIP imkoniyatlarini avtomatik oladi. Admin "A'zolar" ro'yxatida **"VIP ni sovg'a qilish"** amali bor.

### VIP'ning qo'shimcha imkoniyatlari
- **Ajratilgan joylar:** har guruh mashg'ulotida 2 ta joy faqat VIP uchun (sozlanadi, joylarning yarmidan oshmaydi). Mashg'ulot to'lsa ham VIP joy topadi.
- **Bepul konsultatsiya:** oyiga 1 ta shaxsiy mashg'ulot so'rovi avtomatik "VIP bepul" bo'ladi (xodim qabulxonada belgini ko'radi). Bekor qilinsa, imkoniyat qaytadi.
- **Mehmon taklifnomasi:** oyiga 1 ta. VIP sahifasida mehmon ismi va kunini yozasiz, QR va 8 belgili kod chiqadi. Qabulxonada QR skaner yoki qidiruv orqali **faqat o'sha kuni, bir marta** ishlaydi.
- Bular hammasi admin panel → **Zal sozlamalari**da o'zgartiriladi.

## Rasmlar
- Admin panel → **Mahsulotlar** va **Murabbiylar** → "Rasm" maydoniga jpg/png/webp yuklang (5 MB gacha, `FZ_MAX_IMAGE_MB`). Fayl turi nomidan emas, ichidagi baytlardan tekshiriladi, SVG/HTML qabul qilinmaydi.
- Rasm yuklanmaguncha mahsulotlarda nomiga qarab chizilgan illyustratsiya (suv, protein, ichimlik, batonchik, sheyker), murabbiylarda siluet chiqadi.
- Har mahsulotning alohida sahifasi bor (`/shop/<id>/`): katta rasm, tavsif, VIP narxi, o'xshash mahsulotlar. "Ommabop" (so'nggi 60 kunda eng ko'p sotilgan 3 ta) va "Kam qoldi" (5 tadan kam) belgilari o'zi chiqadi.
- Har murabbiyning sahifasi (`/trainers/<id>/`): rasm, tanishtiruv, olib boradigan mashg'ulotlari, shaxsiy mashg'ulotga yozilish.
- Rasmlar ham `media/` papkasida turadi: internetga chiqarganda doimiy disk kerak.

## Karta orqali to'lov (pul sizning kartangizga tushadi)

Admin panel → **To'lov kartalari** → qo'shish: bank, 16 raqamli karta, egasi, "Asosiy karta" belgisi. Karta raqami tekshiruv raqami bilan tekshiriladi (xato yozilsa qabul qilinmaydi).
**Kartani almashtirish:** yangi karta qo'shib "Asosiy" qiling. Eskilari o'chirilmaydi, chunki oldingi to'lovlar o'z kartasini eslab turadi.

Jarayon (abonement ham, do'kon ham bir xil):
1. A'zo "Karta orqali o'tkazma"ni tanlaydi → sahifada karta raqami, aniq summa va izohga yoziladigan kod (masalan `P57`) chiqadi (nusxalash tugmalari bilan).
2. A'zo o'tkazadi, jo'natgan kartasining **oxirgi 4 raqamini** yozib "To'ladim"ni bosadi. To'liq karta raqami so'ralmaydi.
3. Xodim bank ilovasida pulni ko'rib, qabulxonada (`/staff/`) yoki admin panelda **Tasdiqlash**ni bosadi. Faqat shundan keyin abonement faollashadi / buyurtma tayyor bo'ladi. Pul tushmagan bo'lsa **Rad etish** (mahsulot omborga qaytadi).
4. 24 soat ichida "To'ladim" bosilmagan o'tkazmalar o'zi bekor bo'ladi: `python manage.py expire_pending` (har soatda ishga tushiring).

Banklar bilan avtomatik bog'lanish yo'q: pulni tekshirish xodim qo'lida. Bu soxta "to'ladim" bilan aldashdan himoya qiladi, lekin xodim e'tiborli bo'lishi kerak.
Sinov (Payme/Click/Uzum "to'landi") tugmalari faqat `DJANGO_DEBUG=1` bo'lganda va admin paneldan yoqilganda chiqadi, internetda hech qachon.

## Sozlash

| Xizmat | Nima uchun | Qanday |
|---|---|---|
| SMS | Parolni tiklash, telefon tasdig'i | `SMS_BACKEND=eskiz`, `ESKIZ_EMAIL`, `ESKIZ_PASSWORD` (`ESKIZ_FROM`). Standart `console`: kod serverning terminalida chiqadi |
| Telegram | Eslatmalar va xodimga xabar | `TELEGRAM_BOT_TOKEN` (@BotFather), `TELEGRAM_ADMIN_CHAT_ID` (ixtiyoriy). Bot username'ini admin paneldagi "Zal sozlamalari"ga yozing. `python manage.py run_bot` botni ishga tushiradi, `python manage.py send_reminders` eslatma yuboradi (har soatda ishga tushiring) |
| Click | Onlayn to'lov | `CLICK_SERVICE_ID`, `CLICK_MERCHANT_ID`, `CLICK_SECRET_KEY`. Click kabinetida callback manzili: `https://SAYTINGIZ/pay/click/` |
| Google | Google bilan kirish | `GOOGLE_CLIENT_ID` |
| Zaxira | Baza nusxasi | `python manage.py backup_db` (oxirgi 14 tasi saqlanadi). PostgreSQL uchun `pg_dump` kerak |
| Loglar | Xatolarni kuzatish | `FZ_LOG_DIR=logs` fayl yozadi. Telegram sozlangan bo'lsa server xatolari admin chatga ketadi |

Boshqa o'zgaruvchilar: `DJANGO_DEBUG` (internetda `0`), `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS`, `DATABASE_URL`, `FZ_ADMIN_PASSWORD`, `FZ_SECURE_COOKIE`.

## Nima sinalgan va nima sinalmagan

Testlar (42 ta) Click imzosini (soxta kalit bilan), Telegram mantiqini (soxta transport bilan), SMS kodlarini, QR imzosini, referal, yutuqlar, PT, zaxira va admin sahifalarini qamraydi.
**Haqiqiy tashqi xizmatlarga ulanib sinalmagan:** Eskiz (SMS), Telegram API, Click serverlari, Google. Ularni ishlatishdan oldin o'z akkauntingiz bilan sinang. Click uchun avval ularning sandbox muhitida.
Kamera orqali QR o'qish faqat Chrome/Edge'da ishlaydi (boshqa brauzerda qo'lda kiritish yoki USB skaner).

## Internetga chiqarish

`render.yaml`, `build.sh` va `Procfile` tayyor (Render.com):
1. Loyihani GitHub'ga yuklang (`.venv`, baza, `.secret_key` yuklanmaydi).
2. Render → New → Blueprint → repozitoriy. `FZ_ADMIN_PASSWORD` ni kiriting.
3. Deploy tugagach `https://....onrender.com` havolasi chiqadi.

Internetda SQLite emas, PostgreSQL ishlatiladi (`DATABASE_URL`). Render'ning bepul diski vaqtincha, shuning uchun `backup_db` fayllarini boshqa joyga ko'chirib turing yoki hostingning o'z zaxira xizmatidan foydalaning. Telegram bot (`run_bot`) va eslatmalar (`send_reminders`) alohida doimiy jarayon yoki cron talab qiladi: bu odatda pullik tarifda bo'ladi.
