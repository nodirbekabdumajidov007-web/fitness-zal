from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from . import calories
from .models import Announcement, FoodEntry, GymSettings, Plan, Product, Category, Trainer, User


class CaloriesTests(TestCase):
    def setUp(self):
        GymSettings.load()
        GymSettings.objects.get(pk=1).save()  # a fresh row holds string times until it is read back
        self.u = User.objects.create_user(username="kal", email="kal@x.uz", password="pw12345678", first_name="Kal")
        self.client.force_login(self.u)

    def test_requires_login(self):
        self.client.logout()
        r = self.client.get(reverse("calories"))
        self.assertEqual(r.status_code, 302)

    def test_page_and_default_target(self):
        r = self.client.get(reverse("calories"))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.context["target"], calories.DEFAULT_TARGET)
        self.assertContains(r, "calFoods")

    def test_add_from_table_and_totals(self):
        idx = next(i for i, f in enumerate(calories.FOODS) if f[0].startswith("Osh"))
        r = self.client.post(reverse("calories_add"), {"food": idx, "grams": 300, "meal": "lunch"})
        self.assertEqual(r.status_code, 302)
        e = FoodEntry.objects.get()
        self.assertEqual(e.kcal, Decimal("600.0"))
        self.assertEqual(e.meal, "lunch")
        r = self.client.get(reverse("calories"))
        self.assertEqual(r.context["eaten"], 600)
        self.assertEqual(r.context["left"], calories.DEFAULT_TARGET - 600)
        # lunch is filled, so the advice covers the other three meals
        self.assertEqual({m for m, _ in r.context["advice"]}, {"breakfast", "dinner", "snack"})

    def test_add_custom_and_validation(self):
        self.client.post(reverse("calories_add"), {"name": "Uy burgeri", "grams": 150, "kcal": "420,5", "protein": 20, "fat": 15, "carbs": 40, "meal": "dinner"})
        self.assertEqual(FoodEntry.objects.get().kcal, Decimal("420.5"))
        self.client.post(reverse("calories_add"), {"name": "", "grams": 100, "kcal": 10})  # no name
        self.client.post(reverse("calories_add"), {"name": "x", "grams": 0, "kcal": 10})  # bad grams
        self.client.post(reverse("calories_add"), {"name": "x", "grams": 10, "kcal": "abc"})
        self.assertEqual(FoodEntry.objects.count(), 1)

    def test_delete_only_own_and_past_days(self):
        other = User.objects.create_user(username="oth", email="o@x.uz", password="pw12345678")
        theirs = FoodEntry.objects.create(user=other, name="a", grams=10, kcal=5)
        mine = FoodEntry.objects.create(user=self.u, name="b", grams=10, kcal=5, date=timezone.localdate() - timedelta(days=2))
        self.assertEqual(self.client.post(reverse("calories_delete", args=[theirs.pk])).status_code, 404)
        r = self.client.get(reverse("calories"), {"d": mine.date.isoformat()})
        self.assertEqual(r.context["eaten"], 5)
        self.client.post(reverse("calories_delete", args=[mine.pk]))
        self.assertFalse(FoodEntry.objects.filter(pk=mine.pk).exists())

    def test_future_or_bad_day_falls_back_to_today(self):
        r = self.client.get(reverse("calories"), {"d": "2999-01-01"})
        self.assertTrue(r.context["is_today"])
        self.assertTrue(self.client.get(reverse("calories"), {"d": "junk"}).context["is_today"])

    def test_target_from_profile(self):
        from .models import BodyLog
        self.u.birth_date = timezone.localdate().replace(year=timezone.localdate().year - 30)
        self.u.goal = "lose"
        self.u.save()
        BodyLog.objects.create(user=self.u, weight=80, height_cm=180)
        t, how = calories.daily_target(self.u)
        self.assertEqual(how, "profile")
        self.assertTrue(1200 <= t < 3000)

    def test_ai_button_hidden_without_key(self):
        import os
        os.environ.pop("ANTHROPIC_API_KEY", None)
        r = self.client.get(reverse("calories"))
        self.assertNotContains(r, 'id="calAi"')
        r = self.client.post(reverse("calories_ai"), {"text": "2 ta somsa"}, headers={"X-Requested-With": "fetch"})
        self.assertEqual(r.status_code, 400)

    def test_ai_estimate_saved(self):
        from unittest import mock
        fake = '{"items":[{"name":"Somsa","grams":240,"kcal":700,"protein":22,"fat":40,"carbs":60}]}'
        with mock.patch("gym.ai.enabled", return_value=True), mock.patch("gym.ai._call", return_value=fake):
            r = self.client.post(reverse("calories_ai"), {"text": "2 ta somsa", "meal": "lunch"}, headers={"X-Requested-With": "fetch"})
        self.assertEqual(r.json(), {"ok": True, "n": 1})
        self.assertEqual(FoodEntry.objects.get().name, "Somsa")


class MiscUiTests(TestCase):
    def setUp(self):
        GymSettings.load()
        GymSettings.objects.get(pk=1).save()

    def test_trainer_names_clean_after_migration_logic(self):
        from importlib import import_module
        from django.apps import apps
        t = Trainer.objects.create(name="Sardor Rahimov (namuna)", specialty="x", experience_years=1)
        import_module("gym.migrations.0022_strip_namuna").strip_suffix(apps, None)
        t.refresh_from_db()
        self.assertEqual(t.name, "Sardor Rahimov")

    def test_shop_pagination_keeps_filters(self):
        c = Category.objects.create(name="Ichimlik")
        for i in range(45):
            Product.objects.create(category=c, name=f"Suv {i:02d}", price=1000, stock=5)
        r = self.client.get(reverse("shop"), {"cat": c.pk, "q": "Suv"})
        self.assertEqual(len(r.context["products"]), 20)
        self.assertContains(r, f"?cat={c.pk}&amp;q=Suv&amp;page=2")
        r3 = self.client.get(reverse("shop"), {"page": 3})
        self.assertEqual(len(r3.context["products"]), 5)
        self.assertEqual(self.client.get(reverse("shop"), {"page": "zzz"}).status_code, 200)

    def test_route_has_taxi_link(self):
        gs = GymSettings.load()
        gs.map_lat, gs.map_lng = Decimal("41.311081"), Decimal("69.240562")
        gs.save()
        self.assertIn("end-lat=41.311081&end-lon=69.240562", gs.routes()["taxi"])
        self.assertContains(self.client.get("/"), "Yandex Go")

    def test_plans_tiles_cash_only_marks_rest_soon(self):
        Plan.objects.create(code="m1", name="1 oy", months=1, price=100000)
        r = self.client.get(reverse("plans"))
        self.assertContains(r, 'class="paytiles"')
        self.assertContains(r, "tez orada")

    def test_announcement_card(self):
        Announcement.objects.create(title="Yangilik", body="Birinchi qator\nIkkinchi qator", pinned=True)
        r = self.client.get("/")
        self.assertContains(r, "ann-body")
        self.assertContains(r, "Birinchi qator<br>Ikkinchi qator")
