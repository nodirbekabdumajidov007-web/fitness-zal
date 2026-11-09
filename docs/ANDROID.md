# Google Play uchun Android ilova (TWA)

Sayt to'liq PWA. Google Play uchun uni **Trusted Web Activity (TWA)** qilib o'raymiz: ilova ichida Chrome to'liq ekranda saytni ochadi (manzil satrisiz). Alohida kod yozilmaydi, ilova saytning o'zi bilan yangilanib turadi.

Tayyor narsalar (kodda bor): `manifest.webmanifest`, `sw.js`, ikonkalar (192/512, maskable, monochrome), `/offline/` sahifa, `/.well-known/assetlinks.json` (env orqali), `/privacy/` sahifa.

## 0. Boshlashdan oldin

- Sayt internetda **HTTPS** bilan ishlashi kerak (Render: `https://fitness-zal-ji76.onrender.com` yoki o'z domeningiz). Domenni keyin almashtirsangiz, ilovani qayta yig'ishga to'g'ri keladi, shuning uchun avval domenni tanlang.
- Google Play Developer akkaunti kerak (bir martalik to'lov bor; amaldagi narx va shartlarni Play Console'da tekshiring).
- Ilova identifikatori (package id) tavsiyasi: `uz.fitneszal.app`. **Bir marta tanlanadi va keyin o'zgartirib bo'lmaydi.**

## 1. PWABuilder bilan .aab yig'ish

1. https://www.pwabuilder.com oching va sayt manzilini kiriting. U manifest va service worker'ni tekshiradi (hammasi yashil bo'lishi kerak).
2. **Package for stores** -> **Android** -> **Generate package**.
3. Maydonlar:
   - **Package ID**: `uz.fitneszal.app`
   - **App name**: Fitnes Zal; **Short name**: Fitnes Zal
   - **App version**: 1 (har yangi yuklashda oshiring: 2, 3, ...); **Version code** ham oshib borishi shart
   - **Start URL**: `/?source=pwa`
   - **Signing key**: **"Create new"** ni tanlang (yoki bor keystore'ingizni yuklang)
   - **Notifications / Location billing** kabi qo'shimcha funksiyalar kerak bo'lmasa o'chiq qoldiring
4. **Download package**. ZIP ichida: `*.aab` (Play'ga yuklanadi), `*.apk` (telefonda sinash uchun), **`signing.keystore`**, `signing-key-info.txt` (parollar) va `assetlinks.json`.

### Imzo kaliti (keystore) bilan ehtiyot bo'ling

- `signing.keystore` va `signing-key-info.txt` dagi parollarni **parol menejerida va 2 ta joyda** (masalan, shifrlangan flesh va yopiq bulut) saqlang.
- **Hech qachon gitga qo'shmang**, chatga yoki ommaviy joyga tashlamang.
- Play App Signing yoqilgan bo'lsa (yangi ilovalar uchun odatiy), siz yuklash kalitini yo'qotsangiz Google yordam bilan almashtirish mumkin; lekin baribir saqlab qo'ying.

## 2. SHA-256 barmoq izi (fingerprint)

Android saytni ilovaga bog'liq deb tan olishi uchun `assetlinks.json` ichida ilova imzosining SHA-256 izi bo'lishi kerak. Izni olish joylari:

- **PWABuilder** yuklagan ZIP ichidagi `assetlinks.json` (yoki `signing-key-info.txt`): `SHA-256 fingerprint` qatori.
- **Play Console** -> ilovangiz -> **Test and release** -> **App integrity** (yoki Setup -> App signing) -> **App signing key certificate** -> **SHA-256 certificate fingerprint**.

Muhim: Play App Signing yoqilgan bo'lsa, foydalanuvchilar qurilmasidagi ilovani **Google'ning imzo kaliti** bilan imzolaydi, shuning uchun Play Console'dagi *App signing key* izini ishlating. Eng ishonchlisi: **ikkala izni ham** (yuklash kaliti + Google imzo kaliti) vergul bilan yozing; keraksizi zarar qilmaydi.

Iz shunday ko'rinadi: `AB:CD:12:...` (32 juft, ikki nuqta bilan).

## 3. Render'da ikkita o'zgaruvchi

Render -> servisingiz -> **Environment**:

| Kalit | Qiymat |
|---|---|
| `ANDROID_PACKAGE_NAME` | `uz.fitneszal.app` |
| `ANDROID_SHA256_FINGERPRINTS` | `AB:CD:...:99,11:22:...:FF` (vergul bilan, bo'sh joysiz yoki bo'sh joy bilan, farqi yo'q) |

Saqlang va servis qayta ishga tushishini kuting. Tekshirish: brauzerda `https://SAYT/.well-known/assetlinks.json` oching, quyidagiga o'xshash JSON ko'rinishi kerak (sozlanmagan bo'lsa `[]` qaytadi):

```json
[{"relation": ["delegate_permission/common.handle_all_urls"],
  "target": {"namespace": "android_app", "package_name": "uz.fitneszal.app",
             "sha256_cert_fingerprints": ["AB:CD:..."]}}]
```

Agar ilova ochilganda tepada manzil satri ko'rinib qolsa: assetlinks noto'g'ri (izi yoki package id mos emas). Google tekshiruvchisi: https://developers.google.com/digital-asset-links/tools/generator

## 4. Play Console'ga yuklash

1. https://play.google.com/console -> **Create app** (til: Uzbek yoki English, App/Free, deklaratsiyalarni qabul qiling).
2. **Test and release -> Production** (yoki avval Internal/Closed testing) -> **Create new release** -> `.aab` faylni yuklang.
3. Play App Signing so'ralsa **Continue** qiling.
4. Release notes yozing va **Save -> Review release**.

### Yopiq sinov (closed testing) talabi

Yangi **shaxsiy** (personal) developer akkauntlar uchun Google production'ga chiqishdan oldin yopiq sinov o'tkazishni **talab qilishi mumkin** (masalan, ma'lum miqdordagi sinovchi, ma'lum muddat davomida). Bu qoidalar o'zgarib turadi: **amaldagi Play siyosatini Play Console'dagi "Production" bo'limidan yoki Google'ning rasmiy yordam sahifasidan tekshiring.** Tashkilot (organization) akkaunti uchun talab boshqacha bo'lishi mumkin.

## 5. Do'kon sahifasi (store listing) materiallari

| Material | Fayl / qiymat |
|---|---|
| Ilova ikonkasi 512x512 PNG | `docs/play/icon-512.png` |
| Feature graphic 1024x500 | `docs/play/feature-graphic-1024x500.png` |
| Telefon skrinshotlari (kamida 2) | `gym/static/img/shots/*-375.png` (750x1624) |
| Qisqa tavsif (80 belgigacha) | Fitnes Zal: abonement, jadval, QR karta va do'kon bir ilovada |
| Maxfiylik siyosati (Privacy policy) URL | `https://SAYT/privacy/` |
| Kategoriya | Health & Fitness |

Qo'shimcha: **Data safety** anketasini to'ldiring (ism, telefon, e-mail, to'lov tarixi kabi nimalar yig'ilishini sayt maxfiylik siyosatiga mos yozing), **Content rating** so'rovnomasi, **Target audience** (13+ yoki 18+ ni tanlang) va **Ads**: "No ads".

Ikonka/grafikani qayta yaratish: `.venv/Scripts/python.exe tools/make_pwa_assets.py` (faqat lokalda, Pillow kerak).

## 6. Yangilash

- Sayt o'zgarishi ilovada **avtomatik** ko'rinadi (qayta yuklash shart emas).
- Faqat ilova ichki sozlamalari (ikonka, nom, package, imzo) o'zgarsa PWABuilder'da yangi paket yig'ib, **o'sha keystore bilan** imzolang, versiyani oshiring.

## 7. Push va iPhone

- **Android (TWA)**: Chrome push'ni qo'llaydi; `VAPID_*` o'zgaruvchilari qo'yilgach, a'zo "Akkaunt -> Bildirishnomalar" dan yoqadi. Kalit yaratish: `python manage.py generate_vapid`.
- **iPhone**: Play Store yo'q. Safari -> **Ulashish -> Uy ekraniga qo'shish**. Sayt buni sidebar'dagi "Ilovani o'rnatish" tugmasi orqali ko'rsatadi. iOS'da push faqat ilova bosh ekranga qo'shilgach (iOS 16.4+) ishlaydi.
