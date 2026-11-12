import csv
import io
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.messages import get_messages
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from . import tracker
from .i18n import T
from .models import BodyLog, Exercise, ExerciseLog, FoodEntry, GymSettings, PersonalRecord, Trainer, User, Visit, WorkoutPlan
from .models_tracker import TrackerGoal, WorkoutSession, WorkoutSet


def mk(username, **kw):
    return User.objects.create_user(username=username, email=f"{username}@x.uz", password="pw12345678", first_name=username.title(), **kw)


def sets_post(name, rows, **extra):
    """POST body of the workout forms: parallel lists for one exercise."""
    d = {"name": [name] * len(rows), "reps": [r[0] for r in rows], "weight": [r[1] for r in rows], "rpe": [r[2] if len(r) > 2 else "" for r in rows],
         "snote": [""] * len(rows)}
    d.update(extra)
    return d


def msgs(resp):
    return getattr(resp, "msgs", None) or [str(m) for m in get_messages(resp.wsgi_request)]


class TrackerBase(TestCase):
    def setUp(self):
        GymSettings.load()
        GymSettings.objects.get(pk=1).save()
        self.u = mk("ali")
        self.other = mk("vali")
        self.client.force_login(self.u)
        self.today = timezone.localdate()


class MathTests(TestCase):
    def test_epley(self):
        self.assertEqual(tracker.epley(100, 1), 100.0)
        self.assertEqual(tracker.epley(100, 5), 116.7)
        self.assertEqual(tracker.epley(Decimal("60.5"), 10), 80.7)

    def test_navy_body_fat(self):
        m = tracker.navy_body_fat("m", 180, 90, 38)
        f = tracker.navy_body_fat("f", 165, 75, 32, 100)
        self.assertTrue(12 < m < 25, m)
        self.assertTrue(15 < f < 35, f)
        self.assertIsNone(tracker.navy_body_fat("f", 165, 75, 32))  # women need the hips
        self.assertIsNone(tracker.navy_body_fat("", 180, 90, 38))
        self.assertIsNone(tracker.navy_body_fat("m", 180, 30, 38))  # neck wider than waist: nonsense

    def test_linreg_and_moving_average(self):
        d0 = date(2026, 1, 1)
        slope, _, _ = tracker.linreg([(d0 + timedelta(days=i), 80 - i * 0.1) for i in range(10)])
        self.assertAlmostEqual(slope, -0.1, places=6)
        self.assertIsNone(tracker.linreg([(d0, 80)]))
        self.assertIsNone(tracker.linreg([(d0, 80), (d0, 81)]))
        ma = tracker.moving_average([(d0, 80), (d0 + timedelta(days=1), 82), (d0 + timedelta(days=10), 90)])
        self.assertEqual([v for _, v in ma], [80.0, 81.0, 90.0])  # the third point is more than 7 days away from the others

    def test_lift_for(self):
        self.assertEqual(tracker.lift_for("Bench press"), "bench")
        self.assertEqual(tracker.lift_for("Barbell Squat"), "squat")
        self.assertEqual(tracker.lift_for("Romanian deadlift"), "deadlift")
        self.assertEqual(tracker.lift_for("Pull-ups"), "pullup")
        self.assertEqual(tracker.lift_for("Overhead press"), "ohp")
        self.assertEqual(tracker.lift_for("Barbell row"), "row")
        self.assertIsNone(tracker.lift_for("Bicep curl"))
        self.assertIsNone(tracker.lift_for("Bulgarian split squat"))

    def test_goal_projection_on_track(self):
        today = date(2026, 6, 30)
        pts = [(today - timedelta(days=28 - i), 80 - i * 0.1) for i in range(29)]  # 80.0 -> 77.2, losing 0.1 kg a day
        g = tracker.goal_progress(pts, 75, start=80, target_date=today + timedelta(days=60), today=today)
        self.assertEqual(g["state"], "on_track")
        self.assertAlmostEqual(g["current"], 77.2, places=1)
        self.assertEqual(g["remaining"], 2.2)
        self.assertEqual(g["pct"], 56)  # 2.8 of 5 kg
        self.assertEqual(g["projected"], today + timedelta(days=22))  # 2.2 kg at 0.1 kg a day
        self.assertAlmostEqual(g["per_week"], -0.7, places=2)

    def test_goal_projection_off_track_and_reached(self):
        today = date(2026, 6, 30)
        pts = [(today - timedelta(days=28 - i), 80 - i * 0.1) for i in range(29)]
        late = tracker.goal_progress(pts, 75, start=80, target_date=today + timedelta(days=10), today=today)
        self.assertEqual(late["state"], "off_track")  # the projected day is after the deadline
        wrong = tracker.goal_progress(pts, 85, start=80, target_date=None, today=today)
        self.assertEqual(wrong["state"], "off_track")  # wants to gain, loses
        self.assertIsNone(wrong["projected"])
        done = tracker.goal_progress(pts, 78, start=80, today=today)
        self.assertEqual((done["state"], done["pct"], done["remaining"]), ("reached", 100, 0))
        self.assertEqual(tracker.goal_progress([], 70)["state"], "nodata")
        one = tracker.goal_progress([(today, 80)], 70, today=today)
        self.assertEqual(one["state"], "no_trend")
        gain = tracker.goal_progress([(today - timedelta(days=14 - i), 60 + i * 0.1) for i in range(15)], 65, start=60, today=today)
        self.assertEqual(gain["state"], "on_track")


class BodyEntryTests(TrackerBase):
    def post(self, **kw):
        data = {"date": self.today.isoformat(), "weight": "80,5", "height_cm": "180"}
        data.update(kw)
        return self.client.post(reverse("progress"), data)

    def test_model_validators(self):
        for field, bad in [("waist", 10), ("waist", 400), ("neck", 5), ("body_fat", 1), ("body_fat", 90), ("resting_hr", 10), ("resting_hr", 300), ("arm", 200)]:
            log = BodyLog(user=self.u, weight=Decimal("70"), **{field: bad})
            with self.assertRaises(ValidationError, msg=f"{field}={bad}"):
                log.full_clean()
        BodyLog(user=self.u, weight=Decimal("70"), waist=Decimal("80"), chest=Decimal("100"), hips=Decimal("95"), neck=Decimal("38"), arm=Decimal("35"),
                thigh=Decimal("55"), calf=Decimal("38"), body_fat=Decimal("18.5"), resting_hr=60).full_clean()

    def test_quick_entry_and_same_day_update(self):
        r = self.post()
        self.assertEqual(r.status_code, 302)
        log = BodyLog.objects.get()
        self.assertEqual((log.weight, log.height_cm, log.date), (Decimal("80.5"), 180, self.today))
        self.post(weight="79.9", waist="85")  # same day: the row is updated, not duplicated
        self.assertEqual(BodyLog.objects.count(), 1)
        log.refresh_from_db()
        self.assertEqual((log.weight, log.waist), (Decimal("79.9"), Decimal("85.0")))

    def test_validation_errors_save_nothing(self):
        for bad in [{"weight": "5"}, {"weight": "abc"}, {"weight": "nan"}, {"waist": "999"}, {"resting_hr": "10"}, {"height_cm": "50"},
                    {"date": (self.today + timedelta(days=2)).isoformat()}, {"body_fat": "99"}]:
            r = self.post(**bad)
            self.assertEqual(r.status_code, 302, bad)
            self.assertEqual(BodyLog.objects.count(), 0, bad)
        self.assertIn(T["uz"]["ftr_err_date"], msgs(r))  # the last bad post was the future date... or the body fat; either way an error was flashed

    def test_auto_body_fat_needs_sex(self):
        self.post(waist="90", neck="38")
        self.assertIsNone(BodyLog.objects.get().body_fat)  # sex unknown
        self.post(waist="90", neck="38", sex="m")
        log = BodyLog.objects.get()
        self.u.refresh_from_db()
        self.assertEqual(self.u.sex, "m")
        self.assertEqual(log.body_fat, Decimal(str(tracker.navy_body_fat("m", 180, 90, 38))))
        self.post(waist="90", neck="38", body_fat="21.5")  # a typed value wins over the formula
        self.assertEqual(BodyLog.objects.get().body_fat, Decimal("21.5"))

    def test_women_need_hips(self):
        self.post(waist="75", neck="32", sex="f")
        self.assertIsNone(BodyLog.objects.get().body_fat)
        self.post(waist="75", neck="32", hips="100", sex="f")
        self.assertIsNotNone(BodyLog.objects.get().body_fat)

    def test_edit_and_delete_own_only(self):
        self.post()
        log = BodyLog.objects.get()
        r = self.client.get(reverse("progress"), {"edit": log.pk})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.context["edit"], log)
        self.client.post(reverse("progress"), {"pk": log.pk, "date": self.today.isoformat(), "weight": "78", "note": "x"})
        log.refresh_from_db()
        self.assertEqual((log.weight, log.note), (Decimal("78.0"), "x"))
        theirs = BodyLog.objects.create(user=self.other, weight=Decimal("60"))
        self.assertIsNone(self.client.get(reverse("progress"), {"edit": theirs.pk}).context["edit"])
        self.client.post(reverse("progress"), {"pk": theirs.pk, "weight": "99"})
        theirs.refresh_from_db()
        self.assertEqual(theirs.weight, Decimal("60.0"))
        self.assertEqual(self.client.post(reverse("progress_delete", args=[theirs.pk])).status_code, 404)
        self.assertTrue(BodyLog.objects.filter(pk=theirs.pk).exists())
        self.assertEqual(self.client.post(reverse("progress_delete", args=[log.pk])).status_code, 302)
        self.assertFalse(BodyLog.objects.filter(pk=log.pk).exists())

    def test_page_renders_with_units_and_charts(self):
        self.post(waist="85")
        r = self.client.get(reverse("progress"))
        self.assertEqual(r.status_code, 200)
        for needle in ("data-tk", "data-chart=\"weight\"", "data-chart=\"strength\"", "data-chart=\"calories\"", "data-compare", "tkLabels", "placeholder=\"cm\""):
            self.assertContains(r, needle)
        self.assertEqual(r.context["period"], "3m")
        self.assertEqual(self.client.get(reverse("progress"), {"period": "zzz"}).context["period"], "3m")

    def test_quick_weight_from_dashboard(self):
        r = self.client.post(reverse("progress_weight"), {"weight": "71,2", "next": reverse("dashboard")})
        self.assertRedirects(r, reverse("dashboard"), fetch_redirect_response=False)
        self.assertEqual(BodyLog.objects.get().weight, Decimal("71.2"))
        self.client.post(reverse("progress_weight"), {"weight": "70"})
        self.assertEqual(BodyLog.objects.get().weight, Decimal("70.0"))  # same day -> updated
        self.client.post(reverse("progress_weight"), {"weight": "9"})
        self.assertEqual(BodyLog.objects.count(), 1)
        r = self.client.post(reverse("progress_weight"), {"weight": "70", "next": "https://evil.example/"})
        self.assertRedirects(r, reverse("dashboard"), fetch_redirect_response=False)  # an outside "next" is ignored


class WorkoutLogTests(TrackerBase):
    def add(self, name="Bench press", rows=(("5", "80"), ("5", "80"), ("3", "90", "8")), day=None, **kw):
        data = sets_post(name, rows, date=(day or self.today).isoformat(), **kw)
        r = self.client.post(reverse("workout_add"), data)
        r.msgs = [str(m) for m in get_messages(r.wsgi_request)]
        self.client.get(reverse("workouts_log"))  # shows (and so clears) the flash messages, so the next call starts clean
        return r

    def test_log_sets_and_volume(self):
        r = self.add()
        self.assertRedirects(r, reverse("workouts_log"), fetch_redirect_response=False)
        s = WorkoutSession.objects.get()
        self.assertEqual(s.sets.count(), 3)
        self.assertEqual(s.volume, 5 * 80 + 5 * 80 + 3 * 90)
        st = s.sets.last()
        self.assertEqual((st.reps, st.weight, st.rpe), (3, Decimal("90.0"), Decimal("8.0")))
        self.assertEqual(st.one_rm, 99.0)
        page = self.client.get(reverse("workouts_log"))
        self.assertContains(page, "Bench press")
        self.assertEqual(page.context["items"][0]["volume"], 1070.0)

    def test_two_exercises_and_free_text_name(self):
        data = {"date": self.today.isoformat(), "plan_day": "2", "note": "yaxshi",
                "name": ["Squat", "Squat", "My weird cable move"], "reps": ["5", "5", "12"], "weight": ["100", "100", "20"], "rpe": ["", "", ""], "snote": ["", "", ""]}
        self.client.post(reverse("workout_add"), data)
        s = WorkoutSession.objects.get()
        self.assertEqual((s.plan_day, s.note), (2, "yaxshi"))
        self.assertEqual(set(s.sets.values_list("exercise", flat=True)), {"Squat", "My weird cable move"})

    def test_bad_input_saves_nothing(self):
        for rows in ([("0", "50")], [("101", "50")], [("5", "501")], [("5", "-1")], [("5", "50", "11")], [("x", "50")]):
            r = self.add(rows=rows)
            self.assertEqual(r.status_code, 400, rows)
        self.assertEqual(self.add(name="  ", rows=[("5", "50")]).status_code, 400)
        self.assertEqual(self.client.post(reverse("workout_add"), {"date": self.today.isoformat()}).status_code, 400)
        self.assertEqual(self.add(day=self.today + timedelta(days=3)).status_code, 400)
        self.assertEqual(WorkoutSession.objects.count(), 0)
        r = self.add(rows=[("x", "50")])
        self.assertEqual(r.context["posted_rows"][0]["reps"], "x")  # the typed rows come back so nothing has to be retyped

    def test_bodyweight_set_allowed(self):
        self.add(name="Push-ups", rows=[("20", "")])
        self.assertEqual(WorkoutSet.objects.get().weight, Decimal("0.0"))

    def test_pr_detection_updates_personal_records(self):
        r = self.add()  # first bench ever: PersonalRecord created (1RM 99), no celebration (nothing to beat)
        self.assertEqual(PersonalRecord.objects.filter(user=self.u, lift="bench").count(), 1)
        self.assertFalse(any("rekord" in m.lower() for m in msgs(r)))
        r = self.add(rows=[("3", "90")])  # 99.0 again, not higher: nothing
        self.assertEqual(PersonalRecord.objects.filter(lift="bench").count(), 1)
        r = self.add(rows=[("5", "100")])  # 116.7 > 99
        self.assertEqual(PersonalRecord.objects.filter(lift="bench").count(), 2)
        best = PersonalRecord.objects.filter(lift="bench").order_by("-id").first()
        self.assertEqual((best.weight, best.reps, best.one_rm), (Decimal("100.0"), 5, 116.7))
        self.assertTrue(any("116.7" in m and "Bench press" in m for m in msgs(r)), msgs(r))
        r = self.add(rows=[("5", "60")])  # lighter
        self.assertEqual(PersonalRecord.objects.filter(lift="bench").count(), 2)
        self.assertFalse(any("116.7" in m for m in msgs(r)))

    def test_pr_beats_existing_manual_record_and_non_lift_exercise(self):
        PersonalRecord.objects.create(user=self.u, lift="squat", weight=Decimal("150"), reps=1)
        r = self.add(name="Squat", rows=[("5", "120")])  # 140 < 150: not a record
        self.assertEqual(PersonalRecord.objects.filter(lift="squat").count(), 1)
        r = self.add(name="Squat", rows=[("3", "150")])  # 165 > 150
        self.assertEqual(PersonalRecord.objects.filter(lift="squat").count(), 2)
        self.assertTrue(any("165" in m for m in msgs(r)))
        self.add(name="Cable curl", rows=[("10", "20")])
        r = self.add(name="cable curl", rows=[("10", "25")])  # not one of the six lifts: toast, but no PersonalRecord
        self.assertTrue(any("Cable curl".lower() in m.lower() for m in msgs(r)))
        self.assertFalse(PersonalRecord.objects.filter(user=self.u).exclude(lift="squat").exists())

    def test_plan_log_marks_done_and_replaces(self):
        plan = WorkoutPlan.objects.create(user=self.u, title="P", active=True)
        ex = Exercise.objects.create(plan=plan, weekday=self.today.weekday(), name="Row", sets=3, reps="8")
        url = reverse("workout_plan_log", args=[ex.pk])
        post = sets_post("ignored", [("8", "50"), ("8", "50")])
        self.assertEqual(self.client.post(url, post).status_code, 302)
        self.assertTrue(ExerciseLog.objects.filter(user=self.u, exercise=ex, date=self.today).exists())
        s = WorkoutSession.objects.get()
        self.assertEqual((s.plan_day, s.sets.count()), (self.today.weekday(), 2))
        self.assertEqual(set(s.sets.values_list("exercise", flat=True)), {"Row"})  # the plan's name wins over the posted one
        self.client.post(url, sets_post("x", [("8", "55"), ("8", "55"), ("6", "55")]))
        self.assertEqual(WorkoutSession.objects.count(), 1)
        self.assertEqual(s.sets.count(), 3)  # replaced, not appended
        page = self.client.get(reverse("workouts"))
        self.assertContains(page, "data-tk-sets")
        self.assertContains(page, 'value="55"')  # the logged weight shows in the box
        self.client.post(url, sets_post("x", [("0", "1")]))
        self.assertEqual(s.sets.count(), 3)  # a bad post changes nothing

    def test_plan_log_other_members_exercise_404(self):
        plan = WorkoutPlan.objects.create(user=self.other, title="P", active=True)
        ex = Exercise.objects.create(plan=plan, weekday=0, name="Row")
        self.assertEqual(self.client.post(reverse("workout_plan_log", args=[ex.pk]), sets_post("Row", [("8", "50")])).status_code, 404)
        self.assertEqual(WorkoutSet.objects.count(), 0)

    def test_exercise_autocomplete(self):
        plan = WorkoutPlan.objects.create(user=self.u, title="P", active=True)
        Exercise.objects.create(plan=plan, weekday=0, name="Zottman curl")
        self.add(name="Zercher squat")
        items = self.client.get(reverse("exercise_suggest"), {"q": "z"}).json()["items"]
        self.assertIn("Zottman curl", items)
        self.assertIn("Zercher squat", items)
        prog = self.client.get(reverse("exercise_suggest"), {"q": "squat"}).json()["items"]
        self.assertTrue(len(prog) >= 2)  # also names from the ready-made programs
        self.assertEqual(self.client.get(reverse("exercise_suggest"), {"q": "qqqqqqq"}).json(), {"items": []})
        other = self.client.get(reverse("exercise_suggest"), {"q": "zzz-nope"}).json()["items"]
        self.assertEqual(other, [])

    def test_delete_session_own_only(self):
        self.add()
        s = WorkoutSession.objects.get()
        theirs = WorkoutSession.objects.create(user=self.other)
        self.assertEqual(self.client.post(reverse("workout_delete", args=[theirs.pk])).status_code, 404)
        self.client.post(reverse("workout_delete", args=[s.pk]))
        self.assertEqual(WorkoutSession.objects.filter(user=self.u).count(), 0)
        self.assertEqual(WorkoutSet.objects.count(), 0)
        self.assertEqual(self.client.get(reverse("workout_delete", args=[theirs.pk])).status_code, 405)

    def test_add_form_and_history_pages(self):
        self.assertContains(self.client.get(reverse("workout_add")), "data-wform")
        self.assertContains(self.client.get(reverse("workouts_log")), "tk-links")
        self.assertContains(self.client.get(reverse("records")), reverse("workout_add"))


class GoalTests(TrackerBase):
    def logs(self, n=29, start=80.0, step=-0.1):
        for i in range(n):
            BodyLog.objects.create(user=self.u, date=self.today - timedelta(days=n - 1 - i), weight=Decimal(str(round(start + i * step, 1))))

    def test_weight_goal_saved_and_synced_to_profile(self):
        self.logs()
        r = self.client.post(reverse("goal_save"), {"kind": "weight", "target": "75", "target_date": (self.today + timedelta(days=90)).isoformat()})
        self.assertEqual(r.status_code, 302)
        g = TrackerGoal.objects.get()
        self.assertEqual((g.kind, g.metric, g.target, g.start_value), ("weight", "weight", Decimal("75.0"), Decimal("77.2")))
        self.u.refresh_from_db()
        self.assertEqual(self.u.target_weight, Decimal("75.0"))
        ov = self.client.get(reverse("progress")).context["goals"][0]
        self.assertEqual(ov["state"], "on_track")
        self.assertEqual(ov["projected"], self.today + timedelta(days=22))
        self.client.post(reverse("goal_save"), {"kind": "weight", "target": "76"})  # one weight goal per member: updated
        self.assertEqual(TrackerGoal.objects.count(), 1)
        self.client.post(reverse("goal_delete", args=[g.pk]))
        self.u.refresh_from_db()
        self.assertEqual((TrackerGoal.objects.count(), self.u.target_weight), (0, None))

    def test_profile_target_weight_counts_as_goal(self):
        self.logs(5)
        self.u.target_weight = Decimal("70")
        self.u.save()
        ov = tracker.goals_overview(self.u)
        self.assertEqual((ov[0]["kind"], ov[0]["target"], ov[0]["saved"]), ("weight", 70.0, False))

    def test_measure_and_strength_goals(self):
        for i in range(3):
            BodyLog.objects.create(user=self.u, date=self.today - timedelta(days=10 - i * 5), weight=Decimal("80"), waist=Decimal(str(95 - i * 2)))
        self.client.post(reverse("goal_save"), {"kind": "measure", "metric": "waist", "target": "85"})
        WorkoutSet.objects.create(session=WorkoutSession.objects.create(user=self.u), exercise="Bench press", reps=5, weight=Decimal("80"))
        self.client.post(reverse("goal_save"), {"kind": "strength", "metric": "Bench press", "target": "120"})
        by = {g["kind"]: g for g in tracker.goals_overview(self.u)}
        self.assertEqual(by["measure"]["current"], 91.0)
        self.assertEqual((by["measure"]["pct"], by["measure"]["remaining"], by["measure"]["start"]), (0, 6.0, 91.0))  # the bar starts at the value on the day the goal is set
        self.assertEqual(by["strength"]["current"], 93.3)
        self.assertEqual(by["strength"]["remaining"], 26.7)

    def test_goal_validation(self):
        today = self.today
        bad = [{"kind": "weight", "target": "10"}, {"kind": "weight", "target": "abc"}, {"kind": "measure", "metric": "foo", "target": "80"},
               {"kind": "strength", "metric": "", "target": "100"}, {"kind": "nope", "target": "1"},
               {"kind": "weight", "target": "70", "target_date": (today - timedelta(days=1)).isoformat()}, {"kind": "weight", "target": "70", "target_date": "garbage"}]
        for b in bad:
            self.client.post(reverse("goal_save"), b)
        self.assertEqual(TrackerGoal.objects.count(), 0)

    def test_goal_delete_own_only(self):
        g = TrackerGoal.objects.create(user=self.other, kind="weight", metric="weight", target=Decimal("70"))
        self.assertEqual(self.client.post(reverse("goal_delete", args=[g.pk])).status_code, 404)
        self.assertEqual(TrackerGoal.objects.count(), 1)


class ChartDataTests(TrackerBase):
    def seed(self):
        for i in range(40):
            BodyLog.objects.create(user=self.u, date=self.today - timedelta(days=39 - i), weight=Decimal(str(round(82 - i * 0.1, 1))),
                                   waist=Decimal("90") - Decimal(i) / 10 if i % 5 == 0 else None, body_fat=Decimal("20") if i % 10 == 0 else None,
                                   resting_hr=62 if i % 10 == 0 else None)
        for i in range(3):
            d = self.today - timedelta(days=i * 7)
            s = WorkoutSession.objects.create(user=self.u, date=d)
            WorkoutSet.objects.create(session=s, exercise="Bench press", reps=5, weight=Decimal(60 + i * 5))
            WorkoutSet.objects.create(session=s, exercise="Cable curl", reps=10, weight=Decimal("20"))
        for i in range(4):
            Visit.objects.create(user=self.u)
        tgt = tracker.chart_data(self.u)["calories"]["target"]
        FoodEntry.objects.create(user=self.u, date=self.today, name="a", grams=100, kcal=Decimal(tgt))
        FoodEntry.objects.create(user=self.u, date=self.today - timedelta(days=1), name="a", grams=100, kcal=Decimal(tgt * 2))

    def test_shapes(self):
        self.seed()
        r = self.client.get(reverse("progress_data"))
        self.assertEqual(r.status_code, 200)
        d = r.json()
        for k in ("period", "from", "to", "weight", "measures", "body_fat", "resting_hr", "strength", "volume", "activity", "calories", "streak"):
            self.assertIn(k, d)
        self.assertEqual(d["period"], "3m")
        w = d["weight"]
        self.assertEqual(len(w["points"]), 40)
        self.assertEqual(len(w["ma"]), 40)
        self.assertEqual(set(w["points"][0]), {"d", "v"})
        self.assertIsNone(w["goal"])
        self.assertEqual(set(d["measures"]["series"]), {"waist"})
        self.assertEqual(len(d["body_fat"]["points"]), 4)
        self.assertEqual(set(d["strength"]["exercises"]), {"Bench press", "Cable curl"})
        self.assertEqual([p["v"] for p in d["strength"]["series"]["Bench press"]], [81.7, 75.8, 70.0])  # oldest session first
        self.assertTrue(all(set(x) == {"w", "v"} for x in d["volume"]))
        self.assertTrue(all(set(x) == {"w", "workouts", "visits"} for x in d["activity"]))
        self.assertEqual(sum(x["workouts"] for x in d["activity"]), 3)
        self.assertEqual(d["activity"][-1]["visits"], 1)  # visits are counted per day, four in one day is one
        c = d["calories"]
        self.assertEqual((c["logged_days"], c["within_days"], c["adherence"]), (2, 1, 50))
        self.assertEqual(set(d["streak"]), {"days", "weeks", "this_week", "need"})

    def test_periods_cut_the_data(self):
        self.seed()
        n = {p: len(self.client.get(reverse("progress_data"), {"period": p}).json()["weight"]["points"]) for p in tracker.PERIODS}
        self.assertEqual((n["1m"], n["3m"], n["all"]), (31, 40, 40))
        self.assertEqual(self.client.get(reverse("progress_data"), {"period": "bogus"}).json()["period"], "3m")
        d1 = self.client.get(reverse("progress_data"), {"period": "1m"}).json()
        self.assertEqual(d1["from"], (self.today - timedelta(days=30)).isoformat())

    def test_goal_line_and_projection(self):
        self.seed()
        self.client.post(reverse("goal_save"), {"kind": "weight", "target": "75"})
        w = self.client.get(reverse("progress_data")).json()["weight"]
        self.assertEqual(w["goal"]["target"], 75.0)
        self.assertEqual(set(w["projection"]), {"d0", "v0", "d1", "v1"})
        self.assertGreater(w["projection"]["d1"], w["projection"]["d0"])

    def test_empty_member(self):
        d = self.client.get(reverse("progress_data")).json()
        self.assertEqual(d["weight"]["points"], [])
        self.assertEqual(d["strength"]["exercises"], [])
        self.assertIsNone(d["calories"]["adherence"])
        self.assertTrue(len(d["volume"]) >= 1)

    def test_pr_history_feeds_strength_chart(self):
        PersonalRecord.objects.create(user=self.u, lift="deadlift", weight=Decimal("150"), reps=3)
        d = self.client.get(reverse("progress_data")).json()
        self.assertEqual(d["strength"]["series"]["Stanovoy"][0]["v"], 165.0)

    def test_data_is_private(self):
        BodyLog.objects.create(user=self.other, weight=Decimal("99"))
        s = WorkoutSession.objects.create(user=self.other)
        WorkoutSet.objects.create(session=s, exercise="Secret lift", reps=1, weight=Decimal("200"))
        d = self.client.get(reverse("progress_data")).json()
        self.assertEqual(d["weight"]["points"], [])
        self.assertNotIn("Secret lift", d["strength"]["exercises"])


class CompareTests(TrackerBase):
    def test_before_after(self):
        a, b = self.today - timedelta(days=60), self.today
        BodyLog.objects.create(user=self.u, date=a, weight=Decimal("90"), height_cm=180, waist=Decimal("100"), body_fat=Decimal("25"))
        BodyLog.objects.create(user=self.u, date=b, weight=Decimal("84"), waist=Decimal("94"), arm=Decimal("36"))
        r = self.client.get(reverse("progress_compare"), {"a": a.isoformat(), "b": b.isoformat()})
        self.assertEqual(r.status_code, 200)
        rows = {x["key"]: x for x in r.json()["rows"]}
        self.assertEqual((rows["weight"]["a"], rows["weight"]["b"], rows["weight"]["diff"]), (90.0, 84.0, -6.0))
        self.assertEqual(rows["waist"]["diff"], -6.0)
        self.assertEqual((rows["bmi"]["a"], rows["bmi"]["b"], rows["bmi"]["diff"]), (27.8, 25.9, -1.9))  # the height of the first entry carries over
        self.assertEqual(rows["body_fat"]["b"], 25.0)  # latest known value on or before the date
        self.assertEqual(rows["arm"]["a"], 36.0)  # nothing before the first date: the first later value is used
        self.assertIsNone(rows["chest"]["diff"])
        self.assertEqual(len(r.json()["rows"]), len(tracker.COMPARE_KEYS))

    def test_bad_dates(self):
        for q in ({}, {"a": "x", "b": "y"}, {"a": self.today.isoformat()}, {"a": self.today.isoformat(), "b": (self.today + timedelta(days=1)).isoformat()}):
            self.assertEqual(self.client.get(reverse("progress_compare"), q).status_code, 400, q)


class CsvTests(TrackerBase):
    def rows(self, resp):
        return list(csv.reader(io.StringIO(resp.content.decode("utf-8-sig"))))

    def test_body_csv_is_own_data_and_safe(self):
        BodyLog.objects.create(user=self.u, weight=Decimal("80"), height_cm=180, waist=Decimal("90"), note="=HYPERLINK(\"http://x\")")
        BodyLog.objects.create(user=self.other, weight=Decimal("55"), note="hers")
        r = self.client.get(reverse("progress_export"))
        self.assertEqual(r["Content-Type"], "text/csv; charset=utf-8")
        self.assertIn("attachment", r["Content-Disposition"])
        rows = self.rows(r)
        self.assertEqual(rows[0][:4], ["date", "weight_kg", "height_cm", "bmi"])
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[1][1], "80.0")
        self.assertTrue(rows[1][-1].startswith("'="))  # a formula in a note is neutralised
        self.assertNotIn("hers", r.content.decode())

    def test_workout_csv(self):
        s = WorkoutSession.objects.create(user=self.u, note="+cmd")
        WorkoutSet.objects.create(session=s, exercise="Bench press", reps=5, weight=Decimal("80"), rpe=Decimal("8"))
        WorkoutSet.objects.create(session=s, exercise="Bench press", reps=5, weight=Decimal("80"))
        other = WorkoutSession.objects.create(user=self.other)
        WorkoutSet.objects.create(session=other, exercise="Theirs", reps=1, weight=Decimal("1"))
        rows = self.rows(self.client.get(reverse("progress_export"), {"kind": "workouts"}))
        self.assertEqual(rows[0][:5], ["date", "plan_day", "exercise", "set", "reps"])
        self.assertEqual([r[3] for r in rows[1:]], ["1", "2"])
        self.assertEqual(rows[1][7], "93.3")
        self.assertTrue(rows[1][-1].startswith("'+"))
        self.assertEqual(len(rows), 3)


class PermissionTests(TrackerBase):
    def setUp(self):
        super().setUp()
        self.t_user = mk("coach1")
        self.trainer = Trainer.objects.create(name="Coach", specialty="x", user=self.t_user)
        self.plan = WorkoutPlan.objects.create(user=self.u, trainer=self.trainer, title="Plan", active=True)  # ali is this trainer's client
        BodyLog.objects.create(user=self.u, weight=Decimal("81"))
        s = WorkoutSession.objects.create(user=self.u)
        WorkoutSet.objects.create(session=s, exercise="Bench press", reps=5, weight=Decimal("80"))

    def test_anonymous_redirected_everywhere(self):
        self.client.logout()
        pk = BodyLog.objects.first().pk
        gets = [reverse(n) for n in ("progress", "progress_data", "progress_compare", "progress_export", "workouts_log", "workout_add", "exercise_suggest")]
        gets += [reverse("coach_tracker", args=[self.u.pk]), reverse("coach_tracker_data", args=[self.u.pk]), reverse("coach_tracker_compare", args=[self.u.pk])]
        for url in gets:
            r = self.client.get(url)
            self.assertEqual(r.status_code, 302, url)
            self.assertIn("login", r["Location"])
        for url in (reverse("progress_delete", args=[pk]), reverse("progress_weight"), reverse("goal_save")):
            self.assertEqual(self.client.post(url).status_code, 302, url)

    def test_trainer_reads_client_tracker(self):
        self.client.force_login(self.t_user)
        page = self.client.get(reverse("coach_tracker", args=[self.u.pk]))
        self.assertEqual(page.status_code, 200)
        self.assertContains(page, "data-tk")
        self.assertContains(page, "Bench press")
        self.assertNotContains(page, 'name="weight"')  # read-only: no entry form
        self.assertNotContains(page, reverse("goal_save"))
        self.assertNotContains(page, "/delete/")
        d = self.client.get(reverse("coach_tracker_data", args=[self.u.pk])).json()
        self.assertEqual(len(d["weight"]["points"]), 1)
        self.assertEqual(self.client.get(reverse("coach_tracker_compare", args=[self.u.pk]),
                                         {"a": self.today.isoformat(), "b": self.today.isoformat()}).status_code, 200)

    def test_trainer_cannot_write(self):
        self.client.force_login(self.t_user)
        bl = BodyLog.objects.get(user=self.u)
        self.assertEqual(self.client.post(reverse("progress_delete", args=[bl.pk])).status_code, 404)  # the member endpoints only touch the signed-in user's rows
        self.client.post(reverse("progress"), {"weight": "50"})
        self.assertEqual(BodyLog.objects.get(user=self.u).weight, Decimal("81.0"))
        self.assertEqual(BodyLog.objects.filter(user=self.t_user).count(), 1)  # went to the trainer's own record
        s = WorkoutSession.objects.get(user=self.u)
        self.assertEqual(self.client.post(reverse("workout_delete", args=[s.pk])).status_code, 404)

    def test_trainer_of_someone_else_gets_404(self):
        stranger = mk("stranger")
        self.client.force_login(self.t_user)
        for n in ("coach_tracker", "coach_tracker_data", "coach_tracker_compare"):
            self.assertEqual(self.client.get(reverse(n, args=[stranger.pk]), {"a": "2026-01-01", "b": "2026-01-02"}).status_code, 404, n)

    def test_member_and_other_trainer_denied(self):
        for who, expected in ((self.other, 302), (self.u, 302)):  # a plain member is sent away from the coach area
            self.client.force_login(who)
            self.assertEqual(self.client.get(reverse("coach_tracker", args=[self.u.pk])).status_code, expected)
            self.assertEqual(self.client.get(reverse("coach_tracker_data", args=[self.u.pk])).status_code, expected)
        t2 = mk("coach2")
        Trainer.objects.create(name="Other coach", specialty="x", user=t2)
        self.client.force_login(t2)
        self.assertEqual(self.client.get(reverse("coach_tracker", args=[self.u.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse("coach_tracker_data", args=[self.u.pk])).status_code, 404)

    def test_coach_client_page_links_to_tracker(self):
        self.client.force_login(self.t_user)
        self.assertContains(self.client.get(reverse("coach_client", args=[self.u.pk])), reverse("coach_tracker", args=[self.u.pk]))

    def test_member_pages_never_show_other_members_data(self):
        BodyLog.objects.create(user=self.other, weight=Decimal("123.4"), note="private-note")
        WorkoutSession.objects.create(user=self.other, note="private-session")
        for url in (reverse("progress"), reverse("workouts_log"), reverse("progress_export"), reverse("progress_export") + "?kind=workouts"):
            body = self.client.get(url).content.decode()
            self.assertNotIn("123.4", body, url)
            self.assertNotIn("private-", body, url)

    def test_admin_member_card_lists_tracker_data(self):
        admin = User.objects.create_superuser(username="boss", email="boss@x.uz", password="pw12345678")
        self.client.force_login(admin)
        sess = self.client.session
        sess["admin_mode"] = True
        sess.save()
        r = self.client.get(reverse("admin:gym_user_change", args=[self.u.pk]))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "workout_sessions-TOTAL_FORMS")
        self.assertContains(r, "tracker_goals-TOTAL_FORMS")
        self.assertEqual(self.client.get(reverse("admin:gym_workoutsession_changelist")).status_code, 200)
        self.assertEqual(self.client.get(reverse("admin:gym_trackergoal_changelist")).status_code, 200)


class DashboardWidgetTests(TrackerBase):
    def test_widget_shows_goal_and_week_workouts(self):
        for i in range(8):
            BodyLog.objects.create(user=self.u, date=self.today - timedelta(days=7 - i), weight=Decimal(str(round(80 - i * 0.2, 1))))
        self.client.post(reverse("goal_save"), {"kind": "weight", "target": "75"})
        WorkoutSession.objects.create(user=self.u, date=self.today)
        WorkoutSession.objects.create(user=self.u, date=self.today - timedelta(days=self.today.weekday() + 1))  # last week: not counted
        r = self.client.get(reverse("dashboard"))
        self.assertEqual(r.status_code, 200)
        tk = r.context["tk"]
        self.assertEqual(tk["week_workouts"], 1)
        self.assertEqual(tk["goal"]["target"], 75.0)
        self.assertContains(r, "tk-goalbar")
        self.assertContains(r, reverse("progress_weight"))
        self.assertContains(r, "tk-quick")

    def test_widget_without_data(self):
        r = self.client.get(reverse("dashboard"))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.context["tk"], {"week_workouts": 0, "goal": None})
        self.assertContains(r, reverse("progress_weight"))


class MiscTests(TrackerBase):
    def test_i18n_keys_complete(self):
        keys = [k for k in T["uz"] if k.startswith("ftr_")]
        self.assertGreater(len(keys), 80)
        for lang in ("ru", "en"):
            for k in keys:
                self.assertTrue(T[lang].get(k), (lang, k))
        for p in tracker.PERIODS:
            self.assertIn(f"ftr_p_{p}", T["uz"])
        for s in ("nodata", "reached", "on_track", "off_track", "no_trend"):
            self.assertIn(f"ftr_state_{s}", T["uz"])
        for m in tracker.MEASURES:
            self.assertIn(f"ftr_m_{m}", T["uz"])

    def test_pages_render_in_every_language(self):
        BodyLog.objects.create(user=self.u, weight=Decimal("70"))
        for lang in ("uz", "ru", "en"):
            self.client.cookies["fz_lang"] = lang
            for name in ("progress", "workouts_log", "workout_add", "records", "dashboard", "workouts"):
                self.assertEqual(self.client.get(reverse(name)).status_code, 200, (lang, name))

    def test_account_deletion_wipes_tracker_data(self):
        from . import extras
        BodyLog.objects.create(user=self.u, weight=Decimal("70"))
        WorkoutSet.objects.create(session=WorkoutSession.objects.create(user=self.u), exercise="x", reps=1, weight=Decimal("1"))
        TrackerGoal.objects.create(user=self.u, kind="weight", metric="weight", target=Decimal("65"))
        self.u.sex = "m"
        self.u.save()
        extras.anonymize_user(self.u)
        self.u.refresh_from_db()
        self.assertEqual(self.u.sex, "")
        self.assertEqual((BodyLog.objects.count(), WorkoutSession.objects.count(), WorkoutSet.objects.count(), TrackerGoal.objects.count()), (0, 0, 0, 0))

    def test_data_export_contains_tracker(self):
        BodyLog.objects.create(user=self.u, weight=Decimal("70"), waist=Decimal("80"))
        WorkoutSet.objects.create(session=WorkoutSession.objects.create(user=self.u), exercise="Bench press", reps=5, weight=Decimal("80"))
        TrackerGoal.objects.create(user=self.u, kind="weight", metric="weight", target=Decimal("65"))
        d = self.client.get(reverse("export_data")).json()
        self.assertEqual(d["body"][0]["waist"], 80.0)
        self.assertEqual(d["workouts"][0]["sets"][0]["exercise"], "Bench press")
        self.assertEqual(d["goals"][0]["target"], 65.0)


class ProgressPolishTests(TrackerBase):
    def test_bmi_uses_height_from_an_earlier_entry(self):
        BodyLog.objects.create(user=self.u, date=self.today - timedelta(days=10), weight=Decimal("85"), height_cm=180)
        BodyLog.objects.create(user=self.u, date=self.today, weight=Decimal("78"))  # no height of its own
        s = self.client.get(reverse("progress")).context["summary"]
        self.assertEqual(s["bmi"], round(78 / 1.8 ** 2, 1))
        self.assertEqual(s["bmi_label"], "bmi_ok")
        self.assertEqual(s["d7"], -7.0)
        self.assertIsNone(s["d30"])

    def test_height_and_sex_are_prefilled(self):
        self.u.sex = "f"
        self.u.save(update_fields=["sex"])
        BodyLog.objects.create(user=self.u, date=self.today - timedelta(days=3), weight=Decimal("60"), height_cm=168)
        r = self.client.get(reverse("progress"))
        self.assertContains(r, 'name="height_cm" inputmode="numeric" placeholder="175" value="168"')
        self.assertContains(r, '<option value="f" selected>')
        self.assertNotContains(r, "data-focus=\"id_height_cm\"")

    def test_unknown_height_and_body_fat_hints(self):
        BodyLog.objects.create(user=self.u, date=self.today, weight=Decimal("50"))
        r = self.client.get(reverse("progress"))
        self.assertIsNone(r.context["summary"]["bmi"])
        self.assertContains(r, 'data-focus="id_height_cm"')
        self.assertContains(r, "data-open-more")
        self.assertContains(r, 'id="tk-more"')

    def test_header_has_one_primary_button_and_export_menu(self):
        r = self.client.get(reverse("progress"))
        self.assertContains(r, "data-menu")
        self.assertContains(r, reverse("progress_export") + "?kind=workouts")
        self.assertContains(r, reverse("workouts_log"))
        self.assertContains(r, reverse("records"))
        self.assertContains(r, 'class="btn primary" href="' + reverse("workout_add"))

    def test_week_tile_and_goal_prompt_and_chart_empty_labels(self):
        r = self.client.get(reverse("progress"))
        s = r.context["summary"]
        self.assertEqual((s["week_workouts"], s["week_target"], s["week_visits"]), (0, 3, 0))
        self.assertContains(r, "tk-goalprompt")
        self.assertNotContains(r, "tk-goal-top")
        for k in ("emptyweight", "emptymeasures", "emptyfat", "emptystrength", "emptyvolume", "emptyactivity", "emptycalories", "vweight", "vheight", "vdate"):
            self.assertIn(k, r.context["labels"])
            self.assertTrue(r.context["labels"][k])

    def test_goal_row_replaces_prompt(self):
        BodyLog.objects.create(user=self.u, date=self.today, weight=Decimal("80"))
        TrackerGoal.objects.create(user=self.u, kind="weight", metric="weight", target=Decimal("75"))
        r = self.client.get(reverse("progress"))
        self.assertContains(r, "tk-goal-top")
        self.assertNotContains(r, "tk-goalprompt")

    def test_body_fat_label(self):
        self.assertEqual(tracker.body_fat_label("m", 8), "bf_lean")
        self.assertEqual(tracker.body_fat_label("f", 25), "bf_ok")
        self.assertEqual(tracker.body_fat_label("m", 30), "bf_high")
        self.assertIsNone(tracker.body_fat_label("", 20))


class RecordsPageTests(TrackerBase):
    def test_empty_state_has_cards_and_first_result_links(self):
        r = self.client.get(reverse("records"))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.content.decode().count('class="card rc-card empty"'), 6)
        for k in ("bench", "squat", "deadlift", "ohp", "pullup", "row"):
            self.assertContains(r, f'data-lift="{k}"')
            self.assertContains(r, f"?lift={k}#rc-form")
        self.assertNotContains(r, "🏆")

    def test_preselect_lift(self):
        self.assertContains(self.client.get(reverse("records"), {"lift": "squat"}), '<option value="squat" selected>')
        self.assertNotContains(self.client.get(reverse("records"), {"lift": "bogus"}), " selected>")

    def test_card_with_records(self):
        from .models import PersonalRecord
        PersonalRecord.objects.create(user=self.u, lift="bench", weight=Decimal("80"), reps=5, date=self.today - timedelta(days=9))
        PersonalRecord.objects.create(user=self.u, lift="bench", weight=Decimal("90"), reps=3, date=self.today)
        r = self.client.get(reverse("records"))
        bench = next(l for l in r.context["lifts"] if l["key"] == "bench")
        self.assertEqual(bench["best"].weight, Decimal("90.0"))
        self.assertEqual(bench["vs_prev"], round(99.0 - 93.3, 1))
        self.assertEqual(bench["n"], 2)
        self.assertContains(r, "<svg class=\"spark\"")
        self.assertEqual(r.content.decode().count('class="card rc-card empty"'), 5)
        self.assertNotContains(r, "🏆")
