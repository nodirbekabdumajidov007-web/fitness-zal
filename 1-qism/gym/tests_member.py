"""Member dashboard extras (water, activity map, weight trend), ready-made programs, the rest timer page, admin sections,
the timetable and the cash report."""
from datetime import timedelta

from django.core.cache import cache
from django.core.management import call_command
from django.test import Client, TestCase
from django.utils import timezone

from .models import BodyLog, Booking, GymClass, Payment, Trainer, User, Visit, WaterLog, WorkoutPlan

PW = "Kuchli-Parol-77"


class Base(TestCase):
    def setUp(self):
        cache.clear()
        call_command("setup_gym", demo=True, verbosity=0)
        self.admin = User.objects.get(is_superuser=True)
        self.admin.set_password("AdminPass1")
        self.admin.save()
        self.m = User.objects.create_user(phone="+998901112233", password=PW, first_name="Aziz", last_name="Karimov")
        self.c = Client()
        self.c.post("/login/", {"phone": "901112233", "password": PW})


class DashboardTests(Base):
    def test_water_tracker(self):
        r = self.c.post("/water/", {"delta": "1"}, HTTP_X_REQUESTED_WITH="fetch")
        self.assertEqual(r.json()["glasses"], 1)
        self.c.post("/water/", {"delta": "5"}, HTTP_X_REQUESTED_WITH="fetch")  # clamped to +1
        self.assertEqual(WaterLog.objects.get(user=self.m).glasses, 2)
        for _ in range(4):
            self.c.post("/water/", {"delta": "-1"}, HTTP_X_REQUESTED_WITH="fetch")
        self.assertEqual(WaterLog.objects.get(user=self.m).glasses, 0)  # never below zero
        self.assertEqual(Client().post("/water/").status_code, 302)  # visitors are sent to log in

    def test_dashboard_parts(self):
        Visit.objects.create(user=self.m)
        BodyLog.objects.create(user=self.m, weight=82, date=timezone.localdate() - timedelta(days=7))
        BodyLog.objects.create(user=self.m, weight=80.5)
        cls = GymClass.objects.filter(active=True).first()
        days_ahead = (cls.weekday - timezone.localdate().weekday()) % 7 or 7
        Booking.objects.create(user=self.m, gym_class=cls, date=timezone.localdate() + timedelta(days=days_ahead))
        r = self.c.get("/dashboard/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.context["heat"]), 12)
        self.assertTrue(any(c["on"] for w in r.context["heat"] for c in w))
        self.assertEqual(r.context["w_change"], -1.5)
        self.assertTrue(r.context["next_at"])
        for part in ("db-heat", "data-water", "data-countdown", "spark"):
            self.assertContains(r, part)


class ProgramTests(Base):
    def test_start_and_stop_program(self):
        self.assertContains(self.c.get("/workouts/"), "wo-empty")
        self.c.post("/workouts/program/ppl/")
        plan = WorkoutPlan.objects.get(user=self.m, active=True)
        self.assertEqual(plan.exercises.count(), 30)
        page = self.c.get("/workouts/")
        self.assertContains(page, "wo-strip")
        self.assertContains(page, "data-timer")
        self.c.post("/workouts/program/beginner/")  # switching replaces the own plan
        self.assertEqual(WorkoutPlan.objects.filter(user=self.m, active=True).count(), 1)
        self.c.post("/workouts/stop/")
        self.assertFalse(WorkoutPlan.objects.filter(user=self.m, active=True).exists())
        self.assertEqual(self.c.post("/workouts/program/nope/").status_code, 302)

    def test_trainer_plan_is_never_replaced(self):
        WorkoutPlan.objects.create(user=self.m, trainer=Trainer.objects.first(), title="Murabbiy rejasi")
        self.c.post("/workouts/program/fatloss/")
        self.assertEqual(list(WorkoutPlan.objects.filter(user=self.m, active=True).values_list("title", flat=True)), ["Murabbiy rejasi"])
        self.c.post("/workouts/stop/")
        self.assertTrue(WorkoutPlan.objects.filter(user=self.m, active=True).exists())
        self.assertNotContains(self.c.get("/workouts/"), "prog-grid")

    def test_all_done_celebrates(self):
        self.c.post("/workouts/program/ppl/")
        plan = WorkoutPlan.objects.get(user=self.m, active=True)
        todays = list(plan.exercises.filter(weekday=timezone.localdate().weekday()))
        r = None
        for e in todays:
            r = self.c.post(f"/workouts/{e.pk}/toggle/", follow=True)
        if todays:  # Sunday is a rest day in this program
            self.assertContains(r, "msg success")


class AdminExtraTests(Base):
    def setUp(self):
        super().setUp()
        self.staff = Client()
        self.staff.post("/login/", {"phone": "908775505", "password": "AdminPass1.admin"})

    def test_sidebar_sections(self):
        r = self.staff.get("/django-admin/")
        names = [a["name"] for a in r.context["available_apps"]]
        self.assertEqual(names[:6], ["A'zolar", "Moliya", "Do'kon", "Mashg'ulotlar", "Muloqot", "Sozlamalar"])
        self.assertEqual(self.staff.get("/django-admin/gym/").status_code, 200)  # the per-app page still works

    def test_schedule_and_cash(self):
        cls = GymClass.objects.filter(active=True).first()
        today = timezone.localdate()
        Booking.objects.create(user=self.m, gym_class=cls, date=today - timedelta(days=today.weekday()) + timedelta(days=cls.weekday))
        r = self.staff.get("/django-admin/schedule/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.context["total"], 1)
        self.assertEqual(self.staff.get("/django-admin/schedule/?w=1").context["total"], 0)
        Payment.objects.create(user=self.m, kind="plan", amount=400000, method="cash", status="paid")
        Payment.objects.create(user=self.m, kind="shop", amount=20000, method="card", status="paid")
        r = self.staff.get("/django-admin/cash/")
        self.assertEqual(r.context["total"], 420000)
        self.assertEqual(r.context["count"], 2)
        self.assertEqual(self.staff.get("/django-admin/cash/?d=2001-01-01").context["total"], 0)
        self.assertIn(Client().get("/django-admin/cash/").status_code, (302, 404))
