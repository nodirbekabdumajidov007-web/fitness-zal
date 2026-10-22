"""Trainer sign-in and panel (clients, PT requests, plan builder, privacy), calculators and personal records."""
from datetime import timedelta

from django.core.cache import cache
from django.core.management import call_command
from django.test import Client, TestCase
from django.utils import timezone
from django.utils.html import escape

from .i18n import T
from .models import Booking, GymClass, PersonalRecord, PTSession, Trainer, User, WorkoutPlan

PW = "Kuchli-Parol-77"


class Base(TestCase):
    def setUp(self):
        cache.clear()
        call_command("setup_gym", demo=True, verbosity=0)
        self.admin = User.objects.get(is_superuser=True)
        self.admin.set_password("AdminPass1")
        self.admin.save()
        self.coach_user = User.objects.create_user(phone="+998935554433", password=PW, first_name="Sardor", last_name="R")
        self.t = Trainer.objects.filter(active=True).first()
        self.t.user = self.coach_user
        self.t.save()
        self.other_t = Trainer.objects.filter(active=True).exclude(pk=self.t.pk).first()
        self.m = User.objects.create_user(phone="+998901112233", password=PW, first_name="Aziz", last_name="Karimov")
        self.stranger = User.objects.create_user(phone="+998977776655", password=PW, first_name="Begona", last_name="X")

    def coach(self):
        c = Client()
        c.post("/login/", {"phone": "935554433", "password": PW, "role": "trainer"})
        return c


class TrainerLoginTests(Base):
    def test_trainer_door(self):
        c = Client()
        r = c.post("/login/", {"phone": "935554433", "password": PW, "role": "trainer"})
        self.assertRedirects(r, "/coach/", fetch_redirect_response=False)
        page = c.get("/coach/")
        self.assertEqual(page.status_code, 200)
        self.assertContains(page, self.t.name)
        self.assertContains(c.get("/dashboard/"), "nav-coach")  # header link for trainers

    def test_member_cannot_use_trainer_door(self):
        r = Client().post("/login/", {"phone": "901112233", "password": PW, "role": "trainer"})
        self.assertContains(r, escape(T["uz"]["not_trainer"]))
        c = Client()
        c.post("/login/", {"phone": "901112233", "password": PW})
        self.assertRedirects(c.get("/coach/"), "/dashboard/", fetch_redirect_response=False)
        self.assertNotContains(c.get("/dashboard/"), "nav-coach")

    def test_login_page_has_role_switch(self):
        self.assertContains(Client().get("/login/"), 'name="role" value="trainer"')
        self.assertContains(Client().get("/login/?as=trainer"), 'value="trainer" checked')


class CoachPanelTests(Base):
    def test_clients_and_attention(self):
        PTSession.objects.create(user=self.m, trainer=self.t, starts=timezone.now() + timedelta(days=1), status="requested")
        r = self.coach().get("/coach/")
        names = [c["u"].pk for c in r.context["clients"]]
        self.assertEqual(names, [self.m.pk])  # only connected members
        self.assertTrue(r.context["clients"][0]["attention"])  # never came and no plan
        self.assertEqual(r.context["stats"]["pending"], 1)

    def test_pt_only_own_sessions(self):
        mine = PTSession.objects.create(user=self.m, trainer=self.t, starts=timezone.now() + timedelta(days=1), status="requested")
        theirs = PTSession.objects.create(user=self.m, trainer=self.other_t, starts=timezone.now() + timedelta(days=1), status="requested")
        c = self.coach()
        c.post(f"/coach/pt/{mine.pk}/confirm/")
        mine.refresh_from_db()
        self.assertEqual(mine.status, "confirmed")
        self.assertEqual(c.post(f"/coach/pt/{theirs.pk}/confirm/").status_code, 404)
        theirs.refresh_from_db()
        self.assertEqual(theirs.status, "requested")

    def test_client_card_privacy(self):
        c = self.coach()
        self.assertEqual(c.get(f"/coach/client/{self.stranger.pk}/").status_code, 404)
        self.assertEqual(c.get(f"/coach/plan/{self.stranger.pk}/").status_code, 404)
        cls = GymClass.objects.filter(trainer=self.t).first() or GymClass.objects.first()
        cls.trainer = self.t
        cls.save()
        Booking.objects.create(user=self.m, gym_class=cls, date=timezone.localdate())
        self.assertEqual(c.get(f"/coach/client/{self.m.pk}/").status_code, 200)

    def test_add_client_and_build_plan(self):
        c = self.coach()
        r = c.post("/coach/client/add/", {"q": f"FZ-{self.stranger.pk:04d}"})
        self.assertRedirects(r, f"/coach/plan/{self.stranger.pk}/", fetch_redirect_response=False)
        self.assertEqual(c.get(f"/coach/plan/{self.stranger.pk}/").status_code, 200)
        r = c.post(f"/coach/plan/{self.stranger.pk}/", {
            "title": "Kuch rejasi", "notes": "Dam 90 s",
            "wd": ["0", "0", "2"], "name": ["Squat", "", "Bench"], "sets": ["5", "3", "4"], "reps": ["5", "10", "8"], "note": ["", "", "pauza"]})
        self.assertRedirects(r, f"/coach/client/{self.stranger.pk}/", fetch_redirect_response=False)
        p = WorkoutPlan.objects.get(user=self.stranger, active=True)
        self.assertEqual((p.trainer_id, p.title, p.exercises.count()), (self.t.pk, "Kuch rejasi", 2))  # the empty row is skipped
        self.assertEqual(c.get(f"/coach/client/{self.stranger.pk}/").status_code, 200)  # now a real client
        self.assertContains(self.client_for(self.stranger).get("/workouts/"), "Kuch rejasi")

    def test_add_client_needs_exact_match(self):
        r = self.coach().post("/coach/client/add/", {"q": "Aziz"}, follow=True)
        self.assertContains(r, escape(T["uz"]["client_not_found"]))

    def client_for(self, u):
        c = Client()
        c.force_login(u)
        return c


class ToolsAndRecordsTests(Base):
    def test_tools_page(self):
        r = Client().get("/tools/")
        self.assertContains(r, "data-tools")
        self.assertContains(r, "js/tools.js")

    def test_records(self):
        c = Client()
        c.post("/login/", {"phone": "901112233", "password": PW})
        r = c.post("/records/", {"lift": "bench", "weight": "80", "reps": "5"}, follow=True)
        self.assertContains(r, escape(T["uz"]["record_new"]))
        rec = PersonalRecord.objects.get(user=self.m)
        self.assertEqual(rec.one_rm, 93.3)  # Epley: 80 × (1 + 5/30)
        r = c.post("/records/", {"lift": "bench", "weight": "60", "reps": "3"}, follow=True)
        self.assertContains(r, escape(T["uz"]["record_saved"]))  # not a new best
        self.assertContains(c.post("/records/", {"lift": "nope", "weight": "1", "reps": "1"}, follow=True), escape(T["uz"]["record_bad"]))
        self.assertEqual(c.get("/records/").context["lifts"][0]["best"].pk, rec.pk)
        other = Client()
        other.force_login(self.stranger)
        self.assertEqual(other.post(f"/records/{rec.pk}/delete/").status_code, 404)  # not theirs
        c.post(f"/records/{rec.pk}/delete/")
        self.assertFalse(PersonalRecord.objects.filter(pk=rec.pk).exists())

    def test_admin_dashboard_coaches(self):
        staff = Client()
        staff.post("/login/", {"phone": "908775505", "password": "AdminPass1.admin"})
        r = staff.get("/django-admin/")
        self.assertContains(r, "Murabbiylar reytingi")
        self.assertTrue(any(c["linked"] for c in r.context["coaches"]))
