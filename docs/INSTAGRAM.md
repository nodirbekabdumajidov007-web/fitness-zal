# Instagram Direct bot: zal egasi uchun qo'llanma

Bot Instagram'dagi xabarlarga (Direct) avtomatik javob beradi: narxlar, ish vaqti, manzil, mashg'ulotlar va sayt bilimlar bazasidagi boshqa savollar. Bilmagan savolini «Administrator tez orada javob beradi» deb qaytaradi va suhbatni panelda **Javob kerak** deb belgilaydi. Siz javobni admin paneldagi **Mijozlar bilan aloqa → Instagram xabarlari** bo'limidan yozasiz.

Texnologiya: *Instagram API with Instagram Login* (Graph API v27.0). Facebook sahifasi **kerak emas**, o'z akkauntingiz uchun Meta tekshiruvi (App Review) ham **kerak emas**.

## 1. Instagram akkauntni tayyorlash

1. Instagram ilovasida **Sozlamalar → Akkaunt turi va asboblar → Professional akkauntga o'tish** (Business yoki Creator). Oddiy (Personal) akkaunt ishlamaydi.
2. **Sozlamalar → Xabarlar va hikoyaga javoblar → Ulangan asboblar (Connected tools) → Xabarlarga ruxsat berish (Allow access to messages)** ni yoqing. Bu yoqilmasa, xabarlar botga kelmaydi.

## 2. Meta ilovasini yaratish

1. https://developers.facebook.com saytiga kiring (shu Instagram bilan bog'langan Facebook akkaunt bilan), **My Apps → Create App**.
2. Use case: **Other** → turi **Business**. Ilovaga nom bering (masalan «Fitnes Zal Bot»).
3. Chap menyuda **Add product → Instagram** (yoki use case ichida **Instagram → API setup with Instagram login**).
4. **API setup with Instagram login** sahifasida:
   - **1. Generate access tokens** bo'limida **Add account** tugmasini bosing va o'z Instagram akkauntingizni qo'shing (Professional akkaunt bilan kiring, ruxsatlarni tasdiqlang).
   - Akkaunt yonida **Generate token** → chiqqan uzun matnni nusxalang. Bu **IG_ACCESS_TOKEN**. Ruxsatlar: `instagram_business_basic` va `instagram_business_manage_messages`.
5. **App settings → Basic** sahifasidan **App Secret** (Show tugmasi) ni nusxalang. Bu **IG_APP_SECRET**.
6. Akkaunt raqamini (Instagram user id) shu sahifada ko'rasiz. Bu ixtiyoriy **IG_ACCOUNT_ID**.

> Tokenlarni va App Secret'ni hech kimga bermang, chatga, skrinshotga yoki GitHub'ga qo'ymang. Faqat Render Environment'ga yozing. Agar sirli kalit ochilib qolsa, Meta'da darhol yangisini yarating.

## 3. Render'ga o'zgaruvchilarni kiritish

Render → **fitnes-zal** servisi → **Environment** → quyidagilarni qo'shing:

| Nomi | Qiymati |
|---|---|
| `IG_APP_SECRET` | App Secret (2.5-qadam) |
| `IG_VERIFY_TOKEN` | O'zingiz o'ylab topgan uzun tasodifiy matn (kamida 20 belgi), masalan `fz-ig-7Hk29xQpLm41vB` |
| `IG_ACCESS_TOKEN` | Token (2.4-qadam) |
| `IG_ACCOUNT_ID` | Ixtiyoriy: Instagram user id |
| `IG_API_VERSION` | Ixtiyoriy, odatda `v27.0` |
| `FZ_SITE_URL` | Saytingiz manzili, masalan `https://fitness-zal-ji76.onrender.com` (javoblardagi havolalar uchun) |

Saqlang: Render servisni qayta ishga tushiradi. Uchala asosiy qiymat (`IG_APP_SECRET`, `IG_VERIFY_TOKEN`, `IG_ACCESS_TOKEN`) bo'lmaguncha bot butunlay o'chiq turadi.

## 4. Webhook'ni ulash

1. Admin panelda **Instagram xabarlari** bo'limini oching: yuqorida **Webhook manzili** ko'rinadi, masalan `https://fitness-zal-ji76.onrender.com/webhooks/instagram/`.
2. Meta ilovasida **API setup with Instagram login → 2. Configure webhooks**:
   - **Callback URL**: yuqoridagi manzil.
   - **Verify token**: Render'dagi `IG_VERIFY_TOKEN` bilan bir xil matn.
   - **Verify and save** tugmasini bosing (sayt ishlab turgan bo'lishi kerak).
3. **Webhook fields** ro'yxatida **messages** ni (xohlasangiz `messaging_seen`, `message_reactions`, `message_edit` ni ham) **Subscribe** qiling.

## 5. Akkauntni obuna qilish (Render Shell)

Render → servis → **Shell** da bir marta ishga tushiring:

```
python manage.py ig_subscribe
```

`Obuna: {'success': True}` chiqsa, tayyor. Xato chiqsa, token va ruxsatlarni tekshiring.

## 6. Ilovani Live rejimga o'tkazish

Meta ilovasi **Development** rejimida webhook yubormaydi. **App settings → Basic** da:

- **Privacy Policy URL**: `https://<saytingiz>/privacy/` (sayt «Maxfiylik» sahifasi shu manzilda).
- Kategoriyani tanlang, so'ng yuqoridagi **App mode** kalitini **Live** ga o'tkazing.

O'z akkauntingiz uchun Standard Access yetarli: App Review va Business Verification **shart emas**.

## 7. Sinab ko'rish

1. **Boshqa** Instagram akkauntdan (do'stingiz telefonidan) zal akkauntiga «Salom» yozing: bot salomlashib, 4 ta tavsiya qaytaradi.
2. «Ish vaqti qanday?», «Narxlar», «Manzil» deb yozing.
3. Biror ma'nosiz matn yozing: bot «Administrator tez orada javob beradi» deydi, panelda suhbat **Javob kerak** bilan chiqadi.
4. Panelda suhbatni oching, javob yozing. Shundan keyin bot shu suhbatda bir necha soat (**Zal sozlamalari → Instagram Direct bot**, standart 12 soat) jim turadi.
5. Webhook ishlayotganini **Instagram xabarlari** sahifasidagi «Oxirgi webhook» qatoridan ko'rasiz. **Test yuborish** tugmasi eng oxirgi suhbatga qisqa xabar yuboradi.

Maslahat: o'z akkauntingizdan o'zingizga yozib sinab bo'lmaydi, boshqa akkaunt kerak. Ilova Development rejimida bo'lsa, faqat ilovaga rol berilgan akkauntlar (Roles → Instagram testers) sinay oladi.

## 8. Token yangilanishi

Token 60 kun yashaydi. Tizim uni o'zi yangilaydi (50 kundan keyin, webhook kelganda) va yangisini bazada saqlaydi. Qo'lda yangilash: `python manage.py ig_refresh_token --force`. Render'da kunlik Cron Job qo'shsangiz, ishonchliroq: `python manage.py ig_refresh_token` (muddati yetmagan bo'lsa hech narsa qilmaydi). Token muddati panelda ko'rinadi. Agar token muddati o'tib ketsa, Meta'da yangi token yarating va `IG_ACCESS_TOKEN` ga qo'ying: tizim yangisini avtomatik oladi.

Yuborilmay qolgan javoblarni qayta yuborish: `python manage.py ig_retry` (webhook kelganda ham avtomatik urinadi).

## 9. Cheklovlar

- **24 soat qoidasi**: faqat foydalanuvchining **oxirgi xabaridan keyingi 24 soat** ichida yozish mumkin. Undan keyin panel javob maydonini o'chirib qo'yadi va bot ham yubormaydi.
- **1000 bayt**: bitta xabar 1000 bayt (kirill harflar 2 bayt, ya'ni ~500 harf). Uzun javoblar avtomatik bir necha xabarga bo'linadi.
- Faqat matn: bot rasm, ovoz va stikerlarni o'qimaydi; shunday xabarga «faqat matn o'qiyman» deb javob berib, suhbatni sizga qoldiradi.
- Guruh chatlari qo'llab-quvvatlanmaydi. Obuna bo'lmagan odamlarning so'rovlari (message requests) 30 kundan keyin ko'rinmay qolishi mumkin.
- Bot bir suhbatda minutiga 5 tadan ortiq javob bermaydi (sikl bo'lib ketmasligi uchun).
- Bot o'chirish: **Zal sozlamalari → Instagram Direct bot** da «bot avtomatik javob bersin» ni o'chiring (xabarlar baribir panelda ko'rinadi). Bitta suhbat uchun: suhbat sahifasida **Botni to'xtatish**.
- Bot faqat o'z bilimlar bazasidan javob beradi (narxlar, vaqt, manzil real ma'lumotdan olinadi). Suhbatni a'zoga bog'lasangiz (telefon, login yoki FZ-kod), bot abonement va kaloriya haqidagi shaxsiy savollarga ham javob beradi; bog'lashni faqat odam aniq shu a'zo ekaniga ishonchingiz komil bo'lsa qiling.
