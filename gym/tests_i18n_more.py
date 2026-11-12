"""Turkish, Kyrgyz and Tajik next to Uzbek, Russian and English: coverage, placeholders, picker, switching, fallbacks, assistant, legal notice."""
import re
import unicodedata
from datetime import timedelta
from pathlib import Path

from django.core import mail
from django.test import Client, RequestFactory, TestCase
from django.utils import timezone

from . import assistant, assistant_kb, food_db, programs
from .food_names import NAMES
from .i18n import CHAIN, EXTRA_LANGS, FALLBACK, LANGS, OWN, T, pick
from .middleware import browser_lang
from .models import FaqItem, GymSettings, User
from .templatetags.gym_tags import translate
from .tests_full_smoke import FullSmokeTests

PH = re.compile(r"\{\w+\}")


def fresh_settings():
    """A saved settings row (its time fields become real times) and an empty cache."""
    from django.core.cache import cache
    cache.clear()
    GymSettings.load()
    GymSettings.objects.get(pk=1).save()


class CoverageTests(TestCase):
    def test_languages(self):
        self.assertEqual(LANGS, ("uz", "ru", "en", "tr", "ky", "tg"))
        self.assertEqual({len(T[lg]) for lg in LANGS}, {len(T["uz"])})
        self.assertEqual(CHAIN["tr"], ("tr", "en", "uz"))
        self.assertEqual(CHAIN["ky"], ("ky", "ru", "uz"))
        self.assertEqual(CHAIN["tg"], ("tg", "ru", "uz"))

    def test_every_key_has_its_own_text_in_tr_ky_tg(self):
        for lg in EXTRA_LANGS:
            self.assertEqual(sorted(k for k in T["uz"] if k not in OWN[lg]), [], f"{lg}: keys that fall back to another language")
            self.assertEqual(sorted(k for k in T["uz"] if not T[lg][k].strip()), [], lg)

    def test_placeholders_and_markup_preserved(self):
        for lg in EXTRA_LANGS:
            for k in T["uz"]:
                self.assertEqual(sorted(PH.findall(T[lg][k])), sorted(PH.findall(T["en"][k])), f"{lg}.{k}")
                if "||" in T[lg][k]:
                    self.fail(f"{lg}.{k} has the column separator")

    def test_brand_and_script(self):
        for lg in EXTRA_LANGS:
            self.assertEqual(T[lg]["brand"], "Fitnes Zal")
        for lg in ("ky", "tg"):  # Cyrillic script: no word mixes Latin and Cyrillic letters (brands with a suffix such as VIPти are the only exception)
            for k in T["uz"]:
                for w in re.findall(r"\w+", T[lg][k]):
                    scripts = {unicodedata.name(c, "?").split()[0] for c in w if c.isalpha()}
                    if scripts == {"CYRILLIC", "LATIN"} and not re.search(r"(?i)(vip|uzs|mail|sms|qr|usb|bcaa|rpe|fz|google|apple|telegram|instagram|safari|iphone|click|payme|uzum|chrome|edge|bmr|tdee|1rm)", w):
                        self.fail(f"{lg}.{k}: mixed-script word {w!r}")

    def test_pick_fallback_chain(self):
        vals = {"uz": "U", "ru": "R", "en": "E"}
        self.assertEqual(pick(vals, "tr"), "E")
        self.assertEqual(pick(vals, "ky"), "R")
        self.assertEqual(pick(vals, "tg"), "R")
        self.assertEqual(pick({"uz": "U"}, "tr"), "U")
        self.assertEqual(pick({"uz": "U", "tr": "T"}, "tr"), "T")
        self.assertEqual(pick({"uz": "U", "en": ""}, "tr"), "U")
        self.assertEqual(FALLBACK, {"uz": "uz", "ru": "ru", "en": "en", "tr": "en", "ky": "ru", "tg": "ru"})

    def test_translate_uses_new_languages(self):
        self.assertEqual(translate("tr", "nav_home"), "Ana sayfa")
        self.assertEqual(translate("ky", "nav_home"), "Башкы бет")
        self.assertEqual(translate("tg", "nav_home"), "Саҳифаи асосӣ")
        self.assertEqual(translate("xx", "nav_home"), T["uz"]["nav_home"])
        self.assertIn("5", translate("tr", "expiring", days=5))

    def test_weekdays_and_months_localised(self):
        for lg in EXTRA_LANGS:
            days = [T[lg][f"weekday_{i}"] for i in range(7)]
            self.assertEqual(len(set(days)), 7, lg)
            self.assertNotEqual(days, [T["en"][f"weekday_{i}"] for i in range(7)], lg)
            months = T[lg]["chat_months"].split(",")
            self.assertEqual(len(months), 12, lg)
            self.assertEqual(len(set(months)), 12, lg)
        self.assertEqual(T["tr"]["weekday_0"], "Pazartesi")
        self.assertEqual(T["ky"]["weekday_6"], "Жекшемби")
        self.assertEqual(T["tg"]["weekday_4"], "Ҷумъа")

    def test_programs_translated(self):
        for lg in EXTRA_LANGS:
            for prog in programs.PROGRAMS.values():
                self.assertNotEqual(programs.tr(prog["title"], lg), prog["title"], lg)
                self.assertTrue(programs.tr(prog["about"], lg))
            for key in programs.TR:
                got = programs.tr(key, lg)
                self.assertTrue(got, key)
        self.assertEqual(programs.tr("Uyqu kamida 7 soat.", "tr"), "En az 7 saat uyuyun.")
        self.assertEqual(programs.fmt_reps("30 s", "ky"), "30 сек")
        self.assertEqual(programs.fmt_rest(120, "tg"), "2 дақ")
        self.assertEqual(programs.rest_label("tr"), "Dinlenme")

    def test_food_names(self):
        for lg in EXTRA_LANGS:
            for f in food_db.FOODS_DB:
                self.assertTrue(f.label(lg), f.name)
        osh = food_db.BY_NAME["Osh (palov)"]
        self.assertEqual(osh.label("tr"), "Özbek pilavı (plov)")
        self.assertEqual(osh.label("ky"), "Палоо (плов)")
        self.assertEqual(len(food_db.FOODS_DB), len(NAMES))


class PickerAndSwitchTests(TestCase):
    def setUp(self):
        fresh_settings()

    def test_picker_lists_six_languages(self):
        html = Client().get("/").content.decode()
        for code in LANGS:
            self.assertIn(f"/lang/{code}/", html)
        for label in ("O&#x27;zbekcha", "Русский", "English", "Türkçe", "Кыргызча", "Тоҷикӣ"):
            self.assertIn(label, html)
        picker = html[html.index('class="lp-menu"'):]
        picker = picker[:picker.index("</details>")]
        self.assertEqual(picker.count("<svg"), 6)
        for label in ("TR", "KY", "TG"):
            self.assertNotIn(f'lp-code">{label}', html)  # the current language is Uzbek

    def test_switching_sets_cookie_lang_attribute_and_texts(self):
        for code, nav in (("tr", "Ana sayfa"), ("ky", "Башкы бет"), ("tg", "Саҳифаи асосӣ"), ("ru", "Главная"), ("en", "Home"), ("uz", "Bosh sahifa")):
            c = Client()
            r = c.get(f"/lang/{code}/")
            self.assertEqual(r.cookies["fz_lang"].value, code)
            page = c.get("/").content.decode()
            self.assertIn(f'<html lang="{code}"', page)
            self.assertIn(nav, page)
            self.assertIn(f'lp-code">{code.upper()}', page)

    def test_unknown_language_ignored(self):
        c = Client()
        c.get("/lang/zz/")
        self.assertNotIn("fz_lang", c.cookies)
        c.cookies["fz_lang"] = "zz"
        self.assertIn('<html lang="uz"', c.get("/").content.decode())

    def test_accept_language_detection(self):
        self.assertEqual(browser_lang("tr-TR,tr;q=0.9,en;q=0.8"), "tr")
        self.assertEqual(browser_lang("ky-KG,ru;q=0.8"), "ky")
        self.assertEqual(browser_lang("tg"), "tg")
        self.assertEqual(browser_lang("ru-RU,tr;q=0.5"), "uz")  # a known language first: nothing changes
        self.assertEqual(browser_lang("de-DE"), "uz")
        self.assertEqual(browser_lang(""), "uz")
        c = Client(HTTP_ACCEPT_LANGUAGE="tr-TR,tr;q=0.9")
        self.assertIn('<html lang="tr"', c.get("/").content.decode())
        c.get("/lang/ru/")  # the cookie wins over the browser
        self.assertIn('<html lang="ru"', c.get("/").content.decode())
        self.assertIn('<html lang="uz"', Client(HTTP_ACCEPT_LANGUAGE="en-US").get("/").content.decode())

    def test_member_language_saved(self):
        u = User.objects.create_user(phone="+998901112299", password="secret12", first_name="A", last_name="B")
        c = Client()
        c.post("/login/", {"login": "+998901112299", "password": "secret12"})
        c.get("/lang/ky/")
        c.get("/dashboard/")
        u.refresh_from_db()
        self.assertEqual(u.lang, "ky")

    def test_voice_config_languages(self):
        from . import support, voice
        self.assertEqual(voice.SPEECH_LANG["tr"], "tr-TR")
        self.assertEqual(voice.SPEECH_LANG["ky"], "ky-KG")
        self.assertEqual(voice.SPEECH_LANG["tg"], "tg-TJ")
        self.assertEqual(support.LANG_SPEECH["tg"], "tg-TJ")
        c = Client()
        c.get("/lang/tg/")
        html = c.get("/").content.decode()
        self.assertIn("tg-TJ", html)
        js = Path(__file__).parent.joinpath("static/js/voice.js").read_text(encoding="utf-8")
        self.assertIn("C.lang !== 'ru' && C.lang !== 'en'", js)  # no matching speech voice: text only

    def test_offline_page_and_script(self):
        html = Client().get("/offline/").content.decode()
        for lg in LANGS:
            self.assertIn(f'data-l="{lg}"', html)
        self.assertIn("Интернет жок", html)
        self.assertIn("İnternet yok", html)
        self.assertIn("Интернет нест", html)
        js = Path(__file__).parent.joinpath("static/js/offline.js").read_text(encoding="utf-8")
        self.assertIn("'tr', 'ky', 'tg'", js)

    def test_manifest_stays_uzbek(self):
        r = Client().get("/manifest.webmanifest")
        if r.status_code == 200:
            self.assertEqual(r.json()["lang"], "uz")


class LegalNoticeTests(TestCase):
    def setUp(self):
        fresh_settings()

    def test_legal_pages_not_translated(self):
        for code, shown_ru in (("tr", False), ("ky", True), ("tg", True)):
            c = Client()
            c.get(f"/lang/{code}/")
            for url in ("/oferta/", "/privacy/", "/refund/"):
                html = c.get(url).content.decode()
                self.assertIn('class="legal-note"', html, f"{code} {url}")
                self.assertIn("legal-body", html)
                self.assertIn(T[code]["legal_notice_ru" if shown_ru else "legal_notice"].replace("'", "&#x27;"), html)
        for code in ("uz", "ru", "en"):
            c = Client()
            c.get(f"/lang/{code}/")
            self.assertNotIn('class="legal-note"', c.get("/oferta/").content.decode())

    def test_notice_texts(self):
        self.assertIn("Özbekçe", T["tr"]["legal_notice"])
        self.assertIn("өзбек", T["ky"]["legal_notice"])
        self.assertIn("ӯзбекӣ", T["tg"]["legal_notice"])
        self.assertIn("орусча", T["ky"]["legal_notice_ru"])
        self.assertIn("русӣ", T["tg"]["legal_notice_ru"])


class FaqAndEmailTests(TestCase):
    def setUp(self):
        fresh_settings()

    def test_faq_seed_translated_and_fallback(self):
        rows = list(FaqItem.objects.all())
        self.assertTrue(rows)
        for it in rows:
            self.assertTrue(it.question_tr and it.question_ky and it.question_tg, it.question_en)
            self.assertTrue(it.answer_tr and it.answer_ky and it.answer_tg)
            for lg in EXTRA_LANGS:  # placeholders such as {hours} survive
                self.assertEqual(sorted(PH.findall(it.a(lg))), sorted(PH.findall(it.answer_en)), lg)
        it = FaqItem.objects.create(question_uz="Q uz", answer_uz="A uz", question_ru="Q ru", answer_ru="A ru", question_en="Q en", answer_en="A en")
        self.assertEqual((it.q("tr"), it.a("tr")), ("Q en", "A en"))
        self.assertEqual((it.q("ky"), it.a("tg")), ("Q ru", "A ru"))
        it.question_tg = "Q tg"
        self.assertEqual((it.q("tg"), it.a("tg")), ("Q tg", "A ru"))

    def test_faq_page_in_each_language(self):
        for code in EXTRA_LANGS:
            c = Client()
            c.get(f"/lang/{code}/")
            r = c.get("/faq/")
            self.assertEqual(r.status_code, 200)
            self.assertContains(r, FaqItem.objects.first().q(code)[:20])

    def test_login_code_email_languages(self):
        from . import emailcode
        u = User.objects.create_user(email="x@example.com", first_name="A", last_name="B", password="secret12")
        for code, word in (("tr", T["tr"]["ec_mail_secret"]), ("ky", T["ky"]["ec_mail_secret"]), ("tg", T["tg"]["ec_mail_secret"])):
            mail.outbox.clear()
            emailcode.send_code_mail(u, "123456", "login", code, 10)
            self.assertEqual(len(mail.outbox), 1)
            m = mail.outbox[0]
            self.assertIn("123456", m.subject)
            self.assertIn(word, m.body)
            self.assertIn("123456", m.alternatives[0][0])
            self.assertIn(f'lang="{code}"', m.alternatives[0][0])

    def test_password_reset_email_languages(self):
        User.objects.create_user(email="reset@example.com", first_name="A", last_name="B", password="secret12")
        for code, word in (("tr", "şifre sıfırlama"), ("ky", "сырсөздү калыбына келтирүү"), ("tg", "барқарор кардани рамз"), ("uz", "parolni tiklash")):
            mail.outbox.clear()
            c = Client()
            c.get(f"/lang/{code}/")
            c.post("/password/email/", {"email": "reset@example.com"})
            self.assertEqual(len(mail.outbox), 1, code)
            self.assertIn(word, mail.outbox[0].subject.lower() + mail.outbox[0].body.lower(), code)
            self.assertIn("/password/email/", mail.outbox[0].body)


class AssistantLanguagesTests(TestCase):
    def ask(self, q, lang="uz"):
        return assistant.answer(q, lang)

    def test_turkish_questions(self):
        r = self.ask("Çalışma saatleriniz nedir?")
        self.assertEqual(r["id"], "hours")
        self.assertIn("Salon her gün", r["answer"])
        self.assertEqual(self.ask("Üyeliğimi nasıl dondururum?")["id"], "freeze")
        self.assertIn("Üyeliği bir kez", self.ask("Üyeliğimi nasıl dondururum?")["answer"])
        self.assertEqual(self.ask("şifremi unuttum")["id"], "password_reset")
        self.assertEqual(self.ask("SIFREMI UNUTTUM")["id"], "password_reset")  # no diacritics, capitals
        self.assertEqual(self.ask("Antrenmandan sonra ne yenir?")["id"], "post_workout_meal")
        self.assertEqual(self.ask("Squat nasıl yapılır?")["id"], "squat")

    def test_kyrgyz_questions(self):
        r = self.ask("Иш убактысы кандай?")
        self.assertEqual(r["id"], "hours")
        self.assertIn("Зал күн сайын", r["answer"])
        self.assertNotIn("Сейчас", r["answer"])
        self.assertEqual(self.ask("Абонементти кантип тоңдурам?", "ky")["id"], "freeze")
        self.assertEqual(self.ask("Сырсөздү унуттум", "ky")["id"], "password_reset")
        self.assertEqual(self.ask("Машыгуудан кийин эмне жейт?", "ky")["id"], "post_workout_meal")
        self.assertEqual(self.ask("Күнүнө канча суу ичишим керек?")["id"], "water")
        self.assertEqual(assistant.guess_lang("Абонемент баасы канча турат", "uz"), "ky")
        self.assertEqual(assistant.guess_lang("үй жумушу", "uz"), "ky")  # ү is a Kyrgyz-only letter

    def test_tajik_questions(self):
        r = self.ask("Соатҳои корӣ кадомҳоянд?")
        self.assertEqual(r["id"], "hours")
        self.assertIn("Толор ҳар рӯз", r["answer"])
        self.assertEqual(self.ask("Абонементро чӣ тавр яхбандӣ кунам?", "tg")["id"], "freeze")
        self.assertEqual(self.ask("Рамзро фаромӯш кардам", "tg")["id"], "password_reset")
        self.assertEqual(self.ask("Нархи абонемент чанд аст?")["id"], "prices")
        self.assertEqual(assistant.guess_lang("Ман чӣ бояд хӯрам", "uz"), "tg")  # ӣ is a Tajik-only letter

    def test_language_detection_of_old_languages_unchanged(self):
        self.assertEqual(assistant.guess_lang("What are your opening hours?", "uz"), "en")
        self.assertEqual(assistant.guess_lang("Ish vaqtingiz qanday?", "ru"), "uz")
        self.assertEqual(assistant.guess_lang("Режим работы", "uz"), "ru")
        self.assertEqual(assistant.guess_lang("Қанча туради", "uz"), "uz")
        self.assertEqual(assistant.guess_lang("Nasılsın", "uz"), "tr")

    def test_answers_for_every_translated_entry(self):
        from .assistant_kb_x import XT
        self.assertGreaterEqual(len(XT), 100)
        for eid, row in XT.items():
            e = assistant_kb.BY_ID[eid]
            for lg, kw, ans in zip(EXTRA_LANGS, row[:3], row[3:]):
                self.assertTrue(kw.strip(), f"{eid} {lg}: keywords")
                self.assertEqual(e["a"][lg], ans)
                self.assertEqual(sorted(PH.findall(ans)), sorted(PH.findall(e["a"]["en"])) if ans else [], f"{eid} {lg}: placeholders")
            self.assertEqual(sum(1 for a in row[3:] if a) in (0, 3), True, f"{eid}: answers for all three languages or none")

    def test_fallback_answers(self):
        e = assistant_kb.BY_ID["strength_train"]  # keywords in tr / ky / tg but no answer text
        self.assertEqual(assistant_kb.answer_text(e, "tr"), e["a"]["en"])
        self.assertEqual(assistant_kb.answer_text(e, "ky"), e["a"]["ru"])
        self.assertEqual(assistant_kb.answer_text(e, "tg"), e["a"]["ru"])
        self.assertEqual(assistant_kb.answer_text(e, "uz"), e["a"]["uz"])
        self.assertEqual(self.ask("güçlenmek")["answer"], e["a"]["en"])
        self.assertEqual(self.ask("күчтүү болуу")["answer"], e["a"]["ru"])
        self.assertEqual(self.ask("қавӣ шудан")["answer"], e["a"]["ru"])
        # an entry with no new-language text at all is still answered, in the fallback language of the site language
        other = next(x for x in assistant_kb.ENTRIES if x["id"] == "hl_" or not x["kw"]["tr"])
        self.assertEqual(assistant_kb.answer_text(other, "tr"), other["a"]["en"])
        self.assertEqual(assistant_kb.title_text(other, "ky"), other["kw"]["ru"][0])

    def test_titles_and_suggestions_use_chain(self):
        e = assistant_kb.BY_ID["hours"]
        self.assertEqual(assistant_kb.title_text(e, "tr"), e["kw"]["tr"][0])
        self.assertEqual(assistant_kb.title_text(e, "tg"), e["kw"]["tg"][0])

    def test_calculators_and_facts_in_fallback_language(self):
        r = assistant.calculator("2+2", "tr")
        self.assertIsNotNone(r)
        self.assertIn("4", r[0])
        r = assistant.calculator("2+2", "ky")
        self.assertIsNotNone(r)

    def test_unknown_and_offtopic_localised(self):
        r = self.ask("kjhsd qweoiu zxcmn", "tr")
        self.assertFalse(r["matched"])
        self.assertIn("uydurmayacağım", r["answer"])
        r = self.ask("мааниси жок суроо xyz qwerty", "ky")
        self.assertFalse(r["matched"])
        self.assertIn("ойлоп таппайм", r["answer"])
        r = self.ask("пурсиши бемаъно zzzz qqqq", "tg")
        self.assertFalse(r["matched"])

    def test_personal_answers_need_login_in_each_language(self):
        for q, lg in (("Üyeliğim ne zaman bitiyor?", "tr"), ("Менин абонементим качан бүтөт?", "ky"), ("Абонементам кай тамом мешавад?", "tg")):
            r = self.ask(q, lg)
            self.assertEqual(r["id"], "me_membership")
            self.assertEqual(r["answer"], T[lg]["asst_login"])

    def test_ask_endpoint_in_new_languages(self):
        c = Client()
        r = c.post("/assistant/ask/", {"q": "Çalışma saatleriniz nedir?", "lang": "tr"})
        self.assertEqual(r.status_code, 200)
        self.assertIn("Salon her gün", r.json()["answer"])
        r = c.post("/assistant/ask/", {"q": "Иш убактысы кандай?", "lang": "ky"})
        self.assertIn("Зал күн сайын", r.json()["answer"])

    def test_plan_builder_fallback(self):
        from . import assistant_plan
        for lg, expect in (("tr", "days"), ("ky", "дн."), ("tg", "дн.")):
            plan = assistant_plan.build_plan("muscle", "beginner", 3, "gym", lg)
            self.assertIn(expect, plan["title"])


class SmokeNewLanguagesTests(FullSmokeTests):
    """The crawler of tests_full_smoke for tr / ky / tg: no 500 and no raw i18n key on the key pages."""
    test_every_site_url_all_roles = test_new_endpoints_guard = None

    def test_key_pages_in_new_languages(self):
        clients = {"guest": Client(), "member": self.member, "trainer": self.trainer_client, "staff": self.staff}
        for lang in EXTRA_LANGS:
            for who, client in clients.items():
                client.get(f"/lang/{lang}/")
                for url in ("/", "/plans/", "/shop/", "/classes/", "/trainers/", "/tools/", "/ai/", "/reviews/", "/login/", "/register/", "/faq/",
                            "/workouts/", "/calories/", "/dashboard/", "/progress/", "/oferta/", "/privacy/", "/refund/", "/password/email/"):
                    self.check(client, url, f"{lang} {who}")

    def test_dates_and_weekdays_localised_on_pages(self):
        c = self.member
        for lang, day in (("tr", "Pazartesi"), ("ky", "Дүйшөмбү"), ("tg", "Душанбе")):
            c.get(f"/lang/{lang}/")
            html = c.get("/workouts/").content.decode()
            self.assertIn(day, html, lang)


class TrackerTextTests(TestCase):
    def test_tracker_text_has_new_languages(self):
        from . import tracker_text as tt
        self.assertEqual(set(tt.TX), set(tt.TX_X))
        self.assertEqual(set(tt.LIFT_NAMES), set(tt.LIFT_X))
        for lg in EXTRA_LANGS:
            got = tt.tx_for(lg)
            self.assertEqual(set(got), set(tt.TX))
            self.assertTrue(all(v.strip() for v in got.values()))
            self.assertNotEqual(got["history"], tt.tx_for("en")["history"])
            self.assertEqual(tt.lift_name("squat", lg)[1], "Squat")

    def test_record_new_has_no_emoji(self):
        for lg in LANGS:
            self.assertNotIn("\U0001F3C6", T[lg]["record_new"], lg)
