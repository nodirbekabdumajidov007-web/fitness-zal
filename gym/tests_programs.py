"""Ready-made programs on the workouts page: cards, no emoji, start, active marker, recommendation, data sanity."""
import re

from django.core.cache import cache
from django.core.management import call_command
from django.test import Client, TestCase

from . import programs, services
from .models import User, WorkoutPlan

EMOJI = re.compile("[\U0001F000-\U0001FFFF☀-➿⬀-⯿️]")


class ProgramsTests(TestCase):
    def setUp(self):
        cache.clear()
        call_command("setup_gym", demo=True, verbosity=0)
        self.m = User.objects.create_user(phone="+998901112233", password="Kuchli-Parol-77", first_name="Aziz", last_name="Karimov")
        self.c = Client()
        self.c.force_login(self.m)

    def section(self):
        html = self.c.get("/workouts/").content.decode()
        return html[html.index("data-pfilters"):html.index("data-pf-none")]

    def test_data_is_valid(self):
        self.assertGreaterEqual(len(programs.PROGRAMS), 8)
        for k, p in programs.PROGRAMS.items():
            self.assertIn(p["goal"], programs.GOALS)
            self.assertIn(p["level"], programs.LEVELS)
            self.assertIn(p["place"], programs.PLACES)
            self.assertFalse(EMOJI.search(repr(p)), k)
            for wd, name, sets, reps, _rest in programs.rows(p):
                self.assertTrue(0 <= wd <= 6 and len(name) <= 80 and len(reps) <= 20 and sets >= 1, (k, name))

    def test_page_renders_all_presets_without_emoji(self):
        r = self.c.get("/workouts/")
        self.assertEqual(r.status_code, 200)
        for p in programs.PROGRAMS.values():
            self.assertContains(r, p["title"].replace("'", "&#x27;"))
        self.assertContains(r, "data-pfilters")
        self.assertIsNone(EMOJI.search(self.section()))

    def test_start_new_preset_creates_plan(self):
        for key in ("upper_lower", "home", "glute"):
            r = self.c.post(f"/workouts/program/{key}/")
            self.assertEqual(r.status_code, 302)
            plan = self.m.workout_plans.get(active=True)
            self.assertEqual(plan.title, programs.PROGRAMS[key]["title"])
            self.assertEqual(plan.exercises.count(), len(programs.rows(programs.PROGRAMS[key])))
            self.assertTrue(plan.exercises.filter(note__startswith="Dam: ").exists() or key == "cardio")
        self.assertEqual(WorkoutPlan.objects.filter(user=self.m, active=True).count(), 1)
        self.assertEqual(services.PROGRAMS["ppl"]["ex"][0][0], 0)  # the trainer plan builder still gets its rows

    def test_anonymous_redirects_to_login(self):
        anon = Client()
        r = anon.get("/workouts/")
        self.assertEqual(r.status_code, 302)
        self.assertIn("next=", r["Location"])
        self.assertEqual(anon.post("/workouts/program/home/").status_code, 302)
        self.assertFalse(WorkoutPlan.objects.exists())

    def test_active_marker(self):
        self.assertNotContains(self.c.get("/workouts/"), "is-active")
        self.c.post("/workouts/program/strength5x5/")
        html = self.section_html = self.c.get("/workouts/").content.decode()
        self.assertEqual(html.count('class="card prog lvl-intermediate is-active'), 1)

    def test_recommended_follows_profile_goal(self):
        self.assertNotContains(self.c.get("/workouts/"), "is-rec")
        self.m.goal = "lose"
        self.m.save()
        html = self.c.get("/workouts/").content.decode()
        self.assertEqual(html.count(" is-rec"), 1)
        self.assertEqual(programs.recommended("lose", 0), "home")
        self.assertEqual(programs.recommended("lose", 50), "fatloss")
        self.assertIsNone(programs.recommended("", 0))

    def test_trainer_plan_is_not_replaced(self):
        from .models import Trainer
        t = Trainer.objects.create(name="Coach", speciality="x") if hasattr(Trainer, "speciality") else Trainer.objects.create(name="Coach")
        WorkoutPlan.objects.create(user=self.m, trainer=t, title="T", active=True)
        self.c.post("/workouts/program/home/")
        self.assertEqual(self.m.workout_plans.get(active=True).title, "T")


CYRILLIC = re.compile("[А-Яа-яЁё]")


def program_strings():
    """Every Uzbek string of the program data that a member reads."""
    out = set(programs.COMMON_TIPS)
    for p in programs.PROGRAMS.values():
        out |= {p["title"], p["about"], *p["tips"]}
        for label, _days, exs in p["sessions"]:
            out.add(label)
            for name, _sets, reps, _rest in exs:
                out.add(name)
                if not (reps.isdigit() or re.fullmatch(r"\d+ (s|daq)", reps)):
                    out.add(reps)  # "30 s" / "20 daq" are converted by fmt_reps; "12" needs no translation
    return out


class ProgramsLanguageTests(TestCase):
    """Names, descriptions and tips are shown in the site language, and a started plan is stored in the language of that moment."""

    def setUp(self):
        cache.clear()
        call_command("setup_gym", demo=True, verbosity=0)
        self.m = User.objects.create_user(phone="+998901112233", password="Kuchli-Parol-77", first_name="Aziz", last_name="Karimov")
        self.c = Client()
        self.c.force_login(self.m)

    def lang(self, code):
        self.c.cookies["fz_lang"] = code

    def test_every_string_has_ru_and_en(self):
        missing = sorted(s for s in program_strings() if s not in programs.TR)
        self.assertEqual(missing, [], "add these to programs.TR")
        self.assertEqual(sorted(k for k in programs.TR if k not in program_strings()), [], "programs.TR has a string no program uses")
        for uz, (ru, en) in programs.TR.items():
            self.assertTrue(CYRILLIC.search(ru), uz)
            self.assertFalse(CYRILLIC.search(en), uz)
            self.assertTrue(en.strip(), uz)
            self.assertEqual((ru.count("("), en.count("(")), (ru.count(")"), en.count(")")), uz)
            self.assertFalse(EMOJI.search(ru + en), uz)

    def test_tr_fallbacks(self):
        self.assertEqual(programs.tr("Planka (Plank)", "uz"), "Planka (Plank)")
        self.assertEqual(programs.tr("Planka (Plank)", "ru"), "Планка (Plank)")
        self.assertEqual(programs.tr("Planka (Plank)", "en"), "Plank")
        self.assertEqual(programs.tr("Planka (Plank)", "de"), "Planka (Plank)")
        self.assertEqual(programs.tr("not in the table", "ru"), "not in the table")

    def test_rest_and_repetition_units(self):
        self.assertEqual([programs.fmt_rest(s, "uz") for s in (0, 45, 60, 120, 150)], ["", "45 s", "60 s", "2 daq", "2,5 daq"])
        self.assertEqual([programs.fmt_rest(s, "ru") for s in (0, 45, 120, 150)], ["", "45 с", "2 мин", "2,5 мин"])
        self.assertEqual([programs.fmt_rest(s, "en") for s in (0, 45, 120, 150)], ["", "45 s", "2 min", "2.5 min"])
        self.assertEqual([programs.fmt_reps(r, "ru") for r in ("12", "30 s", "20 daq", "1 daq tez")], ["12", "30 с", "20 мин", "1 мин быстро"])
        self.assertEqual([programs.fmt_reps(r, "en") for r in ("12", "30 s", "20 daq", "1 daq tez")], ["12", "30 s", "20 min", "1 min fast"])
        self.assertEqual(programs.fmt_reps("20 daq", "uz"), "20 daq")

    def test_rows_fit_the_database_in_every_language(self):
        from .models import Exercise, WorkoutPlan
        name_max, reps_max = Exercise._meta.get_field("name").max_length, Exercise._meta.get_field("reps").max_length
        note_max, title_max = Exercise._meta.get_field("note").max_length, WorkoutPlan._meta.get_field("title").max_length
        for lang in programs.LANGS:
            for k, p in programs.PROGRAMS.items():
                self.assertLessEqual(len(programs.tr(p["title"], lang)), title_max, (lang, k))
                for wd, name, sets, reps, rest in programs.rows(p, lang):
                    self.assertLessEqual(len(name), name_max, (lang, name))
                    self.assertLessEqual(len(reps), reps_max, (lang, reps))
                    self.assertLessEqual(len(f"{programs.rest_label(lang)}: {rest}"), note_max, (lang, rest))
            # the uz rows are exactly what they were before the translation
        self.assertEqual(programs.rows(programs.PROGRAMS["home"]), programs.rows(programs.PROGRAMS["home"], "uz"))

    def test_page_is_shown_in_the_chosen_language(self):
        for lang, shown in (("ru", "Дома: без оборудования"), ("en", "At home: no equipment")):
            self.lang(lang)
            html = self.c.get("/workouts/").content.decode()
            section = html[html.index("data-pfilters"):html.index("data-pf-none")]
            self.assertIn(shown, section)
            self.assertNotIn("Uyda: jihozsiz", section)
            self.assertNotIn("Haftasiga", section)  # no Uzbek description left
            self.assertNotIn("Planka (Plank)" if lang == "en" else "Planka", section)
            self.assertIsNone(EMOJI.search(section))
        self.lang("ru")
        section = self.c.get("/workouts/").content.decode()
        self.assertIn("Приседания (Squat)", section)
        self.assertIn("30 с", section)
        self.assertIn("Между тяжёлыми подходами отдыхайте 2–3 минуты.", section)
        self.assertIn("Перед тренировкой разминайтесь", section)  # the tips every program shows
        self.lang("uz")
        self.assertIn("O&#x27;tirib turish (Squat)", self.c.get("/workouts/").content.decode())

    def test_plan_is_created_in_the_language_of_the_start(self):
        expect = {"uz": ("Uyda: jihozsiz", "Dam: ", "30 s"), "ru": ("Дома: без оборудования", "Отдых: ", "30 с"), "en": ("At home: no equipment", "Rest: ", "30 s")}
        for lang, (title, rest_prefix, timed) in expect.items():
            self.lang(lang)
            self.assertEqual(self.c.post("/workouts/program/home/").status_code, 302)
            plan = self.m.workout_plans.get(active=True)
            self.assertEqual(plan.title, title)
            self.assertEqual(plan.notes, programs.tr(programs.PROGRAMS["home"]["about"], lang))
            exercises = list(plan.exercises.all())
            self.assertEqual(len(exercises), len(programs.rows(programs.PROGRAMS["home"])))
            self.assertEqual(exercises[0].name, programs.rows(programs.PROGRAMS["home"], lang)[0][1])
            self.assertTrue(all(e.note.startswith(rest_prefix) for e in exercises))
            self.assertIn(timed, [e.reps for e in exercises])
        self.assertEqual(self.m.workout_plans.filter(active=True).count(), 1)
        ru = programs.rows(programs.PROGRAMS["home"], "ru")[0][1]
        self.assertTrue(CYRILLIC.search(ru))

    def test_started_plan_keeps_the_active_marker_in_any_language(self):
        self.lang("ru")
        self.c.post("/workouts/program/strength5x5/")
        for lang in programs.LANGS:
            self.lang(lang)
            html = self.c.get("/workouts/").content.decode()
            self.assertEqual(html.count('class="card prog lvl-intermediate is-active'), 1, lang)
