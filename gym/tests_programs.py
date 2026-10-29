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
