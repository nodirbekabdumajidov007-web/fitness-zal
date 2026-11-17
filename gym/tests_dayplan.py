"""2026-11-17: the one-day pass (Plan.days), the exercise "Video" links and the extra shop products."""
from datetime import timedelta

from django.core.management import call_command
from django.test import TestCase

from . import programs, services
from .models import Category, Plan, Product, User


class DayPassTests(TestCase):
    def test_day_pass_lasts_one_day_and_month_plan_thirty(self):
        u = User.objects.create_user(username="kun1", password="x-parol-12")
        day = Plan.objects.create(code="dx", name="1 kunlik", months=1, days=1, price=50000)
        m = services.add_membership(u, day)
        self.assertEqual(m.expires - m.starts, timedelta(days=1))
        month = Plan.objects.create(code="mx", name="1 oylik", months=1, price=400000)
        m2 = services.add_membership(u, month)
        self.assertEqual(m2.starts, m.expires)  # stacks after the day pass
        self.assertEqual(m2.expires - m2.starts, timedelta(days=30))

    def test_setup_seeds_the_day_pass_and_plans_page_shows_it(self):
        call_command("setup_gym")
        d1 = Plan.objects.get(code="d1")
        self.assertEqual((d1.days, d1.price), (1, 50000))
        html = self.client.get("/plans/").content.decode()
        self.assertIn("1 kun", html)
        self.assertIn("50 000", html)
        call_command("setup_gym")  # idempotent
        self.assertEqual(Plan.objects.filter(code="d1").count(), 1)

    def test_setup_seeds_accessories(self):
        call_command("setup_gym")
        self.assertTrue(Category.objects.filter(name="Aksessuarlar").exists())
        self.assertGreaterEqual(Product.objects.count(), 27)


class ExerciseVideoTests(TestCase):
    def test_library_names_map_to_english_in_every_language(self):
        prog = programs.PROGRAMS["beginner"]
        for lang in programs.LANGS:
            name = programs.rows(prog, lang)[0][1]
            url = programs.video_url(name)
            self.assertTrue(url.startswith("https://www.youtube.com/results?search_query="), url)
            self.assertIn(programs.rows(prog, "en")[0][1].split()[0], url)

    def test_custom_exercise_uses_brackets_or_the_name(self):
        self.assertIn("Zercher+squat", programs.video_url("Maxsus (Zercher squat)"))
        self.assertIn("Farmer+walk", programs.video_url("Farmer walk"))
