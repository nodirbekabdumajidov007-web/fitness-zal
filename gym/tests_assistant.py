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


class MatchingTests(TestCase):
    def setUp(self):
        cache.clear()
        GymSettings.load()
        GymSettings.objects.get(pk=1).save()

    def test_kb_size_and_shape(self):
        self.assertGreaterEqual(len(assistant_kb.ENTRIES), 150)
        for e in assistant_kb.ENTRIES:
            for lang in assistant_kb.LANGS:
                self.assertTrue(e["kw"][lang] and e["a"][lang].strip(), (e["id"], lang))

    def test_representative_questions(self):
        for q, lang, want in CASES:
            scored = assistant.score_all(q)
            got = scored[0][1]["id"] if scored and scored[0][0] >= assistant.THRESHOLD else None
            self.assertEqual(got, want, (q, lang))

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
        for q in ("bugun ob-havo qanday", "what is the capital of france", ""):
            res = assistant.answer(q, "en")
            self.assertFalse(res["matched"])
            self.assertTrue(3 <= len(res["suggest"]) <= 4)
        close = assistant.answer("qaysi mashqlar yaxshi", "uz")
        self.assertFalse(close["matched"])

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
