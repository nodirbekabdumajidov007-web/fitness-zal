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

    def test_text_parse_preview_and_fallback_save(self):
        r = self.client.post(reverse("calories_parse"), {"text": "2 ta somsa va choy"}, headers={"X-Requested-With": "fetch"})
        d = r.json()
        self.assertTrue(d["ok"])
        self.assertEqual([i["grams"] for i in d["items"]], [240, 200])
        self.assertEqual(FoodEntry.objects.count(), 0)  # the preview saves nothing
        self.client.post(reverse("calories_parse"), {"text": "200 g osh", "meal": "lunch"})
        e = FoodEntry.objects.get()
        self.assertEqual((e.grams, e.meal, e.kcal), (200, "lunch", Decimal("400.0")))
        r = self.client.post(reverse("calories_parse"), {"text": "xyz"}, headers={"X-Requested-With": "fetch"})
        self.assertFalse(r.json()["ok"])

    def test_parse_text_variants(self):
        g = lambda t: [(i["name"].split()[0], i["grams"]) for i in calories.parse_text(t)]
        self.assertEqual(g("3 tuxum"), [("Tuxum", 165)])
        self.assertEqual(g("osh 300 gramm"), [("Osh", 300)])
        self.assertEqual(g("1.5 kg tarvuz"), [("Tarvuz", 1500)])
        self.assertEqual(g("2 самсы"), [("Somsa", 240)])
        self.assertEqual(g("nothing here"), [])

    def test_no_ai_leftovers_on_page(self):
        r = self.client.get(reverse("calories"))
        self.assertContains(r, 'id="calAi"')
        self.assertNotContains(r, "calories/ai")


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

    def test_home_has_no_announcements_or_trainer_cards(self):
        Announcement.objects.create(title="Yangilik", body="Birinchi qator", pinned=True)
        r = self.client.get("/")
        self.assertEqual(r.status_code, 200)
        self.assertNotContains(r, "ann-body")
        self.assertNotContains(r, "cine-thumbs")


class FoodDatabaseTests(TestCase):
    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        GymSettings.load()
        GymSettings.objects.get(pk=1).save()
        self.u = User.objects.create_user(username="fd", email="fd@x.uz", password="pw12345678")
        self.client.force_login(self.u)

    def names(self, q, client=None):
        r = (client or self.client).get(reverse("calories_search"), {"q": q})
        self.assertEqual(r.status_code, 200)
        return [i["name"] for i in r.json()["items"]], r.json()["items"]

    def test_database_size_and_old_table_order(self):
        from . import food_db
        self.assertGreaterEqual(len(food_db.FOODS_DB), 500)
        self.assertEqual(len(calories.FOODS), len(food_db.FOODS_DB))
        self.assertEqual([calories.FOODS[i][0] for i in (0, 3, 6, 54, 67)],
                         ["Osh (palov)", "Somsa (go'shtli)", "Non (tandir)", "Chuchvara", "Protein batonchik"])
        self.assertEqual(calories.FOODS[0][1:], (200, 6, 9, 24))  # old numbers are unchanged
        for f in food_db.FOODS_DB:  # sane numbers for every row
            self.assertTrue(0 <= f.kcal <= 900 and f.p + f.f + f.c <= 105 and f.name and len(f.name) <= 60, f.name)
            self.assertLessEqual(f.piece, 1000)

    def test_search_in_three_languages(self):
        for q, want in [("osh", "Osh (palov)"), ("плов", "Osh (palov)"), ("pilaf", "Osh (palov)"), ("борщ", "Borsch"), ("lag‘mon", "Lag'mon"),
                        ("lag'mon", "Lag'mon"), ("shawarma", "Shawarma (tovuq)"), ("шаурма", "Shawarma (tovuq)"), ("гречка", "Grechka (pishirilgan)"),
                        ("coffee", "Qahva (qora, shakarsiz)"), ("pizza", "Pitsa"), ("пельмени", "Chuchvara"), ("qurt", "Qurt"), ("chak-chak", "Chak-chak")]:
            names, _ = self.names(q)
            self.assertIn(want, names[:5], (q, names))

    def test_search_forgives_typos_and_case(self):
        for q, want in [("LAGMON", "Lag'mon"), ("lagman", "Lag'mon"), ("kapuchino", "Kapuchino"), ("bananna", "Banan"), ("hamburgr", "Burger"),
                        ("karbonara", "Pasta karbonara"), ("xalva", "Halva (kunjutli)"), ("tuhum", "Tuxum (qaynatilgan)"), ("sezar", "Sezar salat")]:
            names, _ = self.names(q)
            self.assertIn(want, names[:5], (q, names))
        self.assertEqual(self.names("zzzzqq")[0], [])
        self.assertEqual(self.names("x" * 500)[0], [])  # long junk is cut, not an error

    def test_search_ranks_exact_first_and_limits_to_ten(self):
        names, items = self.names("osh")
        self.assertEqual(names[0], "Osh (palov)")
        self.assertLessEqual(len(items), 10)
        self.assertEqual(self.names("somsa")[0][0], "Somsa (go'shtli)")

    def test_portion_defaults(self):
        _, items = self.names("somsa")
        somsa = next(i for i in items if i["name"] == "Somsa (go'shtli)")
        self.assertEqual((somsa["portion"], somsa["piece"], somsa["kcal"]), (120, 120, 290))
        self.assertEqual(self.names("tuxum")[1][0]["portion"], 55)
        self.assertEqual(next(i for i in self.names("butun non")[1] if i["name"].startswith("Non (butun"))["portion"], 250)
        self.assertTrue(all(i["portion"] >= 1 for i in self.names("choy")[1]))

    def test_search_needs_login_and_is_rate_limited(self):
        self.client.logout()
        self.assertEqual(self.client.get(reverse("calories_search"), {"q": "osh"}).status_code, 302)
        self.client.force_login(self.u)
        from . import views
        codes = {self.client.get(reverse("calories_search"), {"q": "osh"}).status_code for _ in range(views.SEARCH_LIMIT + 2)}
        self.assertEqual(codes, {200, 429})

    def test_add_any_database_food(self):
        _, items = self.names("borsch")
        r = self.client.post(reverse("calories_add"), {"food": items[0]["id"], "grams": 300, "meal": "lunch"})
        self.assertEqual(r.status_code, 302)
        e = FoodEntry.objects.get()
        self.assertEqual((e.name, e.kcal), ("Borsch", Decimal("150.0")))
        self.client.post(reverse("calories_add"), {"food": "99999", "grams": 100})  # unknown row: needs a name and numbers
        self.assertEqual(FoodEntry.objects.count(), 1)

    def test_parse_uses_big_database(self):
        g = lambda t: [(i["name"], i["grams"]) for i in calories.parse_text(t)]
        self.assertEqual(g("2 ta shawarma"), [("Shawarma (tovuq)", 600)])
        self.assertEqual(g("borsch va 2 ta pirojki"), [("Borsch", 300), ("Pirojki (go'shtli)", 120)])
        self.assertEqual(g("300 g гречка и 2 яйца"), [("Grechka (pishirilgan)", 300), ("Tuxum (qaynatilgan)", 110)])
        self.assertEqual(g("kapuchino"), [("Kapuchino", 200)])
        self.assertEqual(g("tovuq ko'kragi 200 g"), [("Tovuq ko'kragi (pishirilgan)", 200)])
        self.assertEqual(g("qatlama somsa"), [("Somsa (qatlama)", 100)])

    def test_parse_keeps_old_choices(self):
        g = lambda t: [i["name"] for i in calories.parse_text(t)]
        self.assertEqual(g("somsa"), ["Somsa (go'shtli)"])
        self.assertEqual(g("choy"), ["Choy (shakarsiz)"])
        self.assertEqual(g("nonushta qildim"), [])  # "nonushta" (breakfast) is not "non"


class UserFoodTests(TestCase):
    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        GymSettings.load()
        GymSettings.objects.get(pk=1).save()
        self.u = User.objects.create_user(username="uf", email="uf@x.uz", password="pw12345678")
        self.o = User.objects.create_user(username="ot", email="ot@x.uz", password="pw12345678")
        self.client.force_login(self.u)
        self.fetch = {"headers": {"X-Requested-With": "fetch"}}

    def save(self, **kw):
        data = {"name": "Uy kotleti", "kcal": "210,5", "protein": "15", "fat": "12", "carbs": "9", "portion_g": "90"}
        data.update(kw)
        return self.client.post(reverse("calories_food_save"), data, **self.fetch)

    def test_create_search_first_use_and_delete(self):
        from .models import UserFood
        r = self.save()
        self.assertEqual(r.status_code, 200)
        food = r.json()["food"]
        self.assertEqual((food["name"], food["kcal"], food["portion"], food["mine"]), ("Uy kotleti", 210.5, 90, True))
        # immediately searchable, before the built-in foods, marked as own
        items = self.client.get(reverse("calories_search"), {"q": "kotlet"}).json()["items"]
        self.assertEqual((items[0]["id"], items[0]["mine"]), (food["id"], True))
        self.assertTrue(any(not i["mine"] for i in items[1:]))
        self.assertEqual(self.client.get(reverse("calories_search")).json()["items"][0]["name"], "Uy kotleti")  # empty q lists own foods
        # usable: grams x per-100 g numbers
        self.client.post(reverse("calories_add"), {"food": food["id"], "grams": 200, "meal": "dinner"})
        e = FoodEntry.objects.get()
        self.assertEqual((e.name, e.kcal, e.protein), ("Uy kotleti", Decimal("421.0"), Decimal("30.0")))
        # the page lists it
        self.assertContains(self.client.get(reverse("calories")), "Uy kotleti")
        # delete keeps the diary entry
        self.client.post(reverse("calories_food_delete", args=[food["pk"]]))
        self.assertFalse(UserFood.objects.exists())
        self.assertEqual(FoodEntry.objects.count(), 1)

    def test_edit_and_unique_name(self):
        pk = self.save().json()["food"]["pk"]
        r = self.save(pk=pk, kcal="300", name="Uy kotleti")
        self.assertEqual(r.json()["food"]["kcal"], 300.0)
        self.assertEqual(self.save(name="UY KOTLETI").status_code, 400)  # same name, any case
        self.assertEqual(self.save(name="Boshqa").status_code, 200)
        self.assertEqual(self.save(pk=pk, name="boshqa").status_code, 400)
        # another member may use the same name
        self.client.force_login(self.o)
        self.assertEqual(self.save().status_code, 200)

    def test_permissions_between_members(self):
        food = self.save().json()["food"]
        self.client.force_login(self.o)
        self.assertEqual(self.client.post(reverse("calories_food_delete", args=[food["pk"]])).status_code, 404)
        self.assertEqual(self.save(pk=food["pk"], kcal="1").status_code, 404)
        self.assertNotIn("Uy kotleti", [i["name"] for i in self.client.get(reverse("calories_search"), {"q": "kotlet"}).json()["items"]])
        # a posted reference to somebody else's food is not accepted as a food
        self.client.post(reverse("calories_add"), {"food": food["id"], "grams": 100})
        self.assertEqual(FoodEntry.objects.count(), 0)
        self.client.logout()
        self.assertEqual(self.client.post(reverse("calories_food_save"), {"name": "x", "kcal": 1}).status_code, 302)

    def test_validation(self):
        bad = [dict(name=""), dict(name="x" * 61), dict(kcal=""), dict(kcal="901"), dict(kcal="-1"), dict(kcal="abc"), dict(kcal="nan"),
               dict(protein="101"), dict(fat="-2"), dict(protein="60", fat="40", carbs="20"), dict(portion_g="0"), dict(portion_g="5001"), dict(portion_g="x")]
        for kw in bad:
            self.assertEqual(self.save(**kw).status_code, 400, kw)
        ok = self.save(name="x" * 60, kcal="900", protein="", fat="", carbs="", portion_g="")
        self.assertEqual(ok.status_code, 200)
        self.assertEqual(ok.json()["food"]["portion"], 100)
        self.assertEqual(self.client.get(reverse("calories_food_save")).status_code, 405)

    def test_limit_per_member(self):
        from .models import UserFood
        from . import views
        UserFood.objects.bulk_create([UserFood(user=self.u, name=f"f{i}", kcal=1) for i in range(views.MY_FOODS_MAX)])
        self.assertEqual(self.save(name="one more").status_code, 400)

    def test_csrf_is_enforced(self):
        from django.test import Client
        c = Client(enforce_csrf_checks=True)
        c.force_login(self.u)
        self.assertEqual(c.post(reverse("calories_food_save"), {"name": "a", "kcal": 1}).status_code, 403)
        self.assertEqual(c.get(reverse("calories")).status_code, 200)

    def test_quick_add_is_not_saved_as_food(self):
        from .models import UserFood
        self.client.post(reverse("calories_add"), {"name": "Qo'shnining pirogi", "grams": 120, "kcal": "350", "meal": "snack"})
        e = FoodEntry.objects.get()
        self.assertEqual((e.name, e.grams, e.kcal), ("Qo'shnining pirogi", 120, Decimal("350.0")))
        self.assertFalse(UserFood.objects.exists())

    def test_parse_uses_own_foods(self):
        self.save(name="Dadam oshi", kcal="180", portion_g="300")
        r = self.client.post(reverse("calories_parse"), {"text": "dadam oshi 400 g va 2 ta somsa"}, **self.fetch).json()
        self.assertTrue(r["ok"])
        first = r["items"][0]
        self.assertEqual((first["name"], first["grams"], first["kcal"], first["mine"]), ("Dadam oshi", 400, 720.0, True))
        self.assertTrue(first["idx"].startswith("u"))
        self.assertEqual(r["items"][1]["name"], "Somsa (go'shtli)")
        # the returned reference is accepted by calories_add
        self.assertEqual(self.client.post(reverse("calories_add"), {"food": first["idx"], "grams": 400, "meal": "lunch"}).status_code, 302)
        self.assertEqual(FoodEntry.objects.get().kcal, Decimal("720.0"))
        # own food with the same words beats the built-in one
        self.save(name="Osh")
        self.assertEqual(calories.parse_text("osh", self.u)[0]["mine"], True)
        self.assertEqual(calories.parse_text("osh", self.o)[0]["mine"], False)

    def test_page_has_search_and_own_foods_ui(self):
        self.save()
        r = self.client.get(reverse("calories"))
        for needle in ('id="calSearch"', 'id="calFoodForm"', 'id="calMine"', reverse("calories_search"), reverse("calories_food_save")):
            self.assertContains(r, needle)

    def test_admin_registered(self):
        from django.contrib import admin
        from .models import UserFood
        self.assertIn(UserFood, admin.site._registry)
