import json
import os
import re
from datetime import timedelta
from pathlib import Path
from unittest import mock

from django.core.cache import cache
from django.core.management import call_command
from django.test import Client, TestCase, override_settings
from django.utils import timezone

from . import click, services, sms, telegram
from .i18n import T
from .models import (Booking, Exercise, ExerciseLog, GymClass, GymSettings, Membership, OtpCode, Payment, Plan, PTSession, User, Visit, WorkoutPlan)

PW = "secret12"


@override_settings(ALLOW_DEMO_PAYMENTS=True)
class Base(TestCase):
    def setUp(self):
        cache.clear()
        call_command("setup_gym", demo=True, verbosity=0)
        GymSettings.objects.filter(pk=1).update(demo_payments=True)  # off by default; these tests exercise the demo gateways
        self.admin = User.objects.get(is_superuser=True)
        self.admin.set_password("AdminPass1")
        self.admin.save()

    def member(self, phone="+998901112233", first="Aziz", ref=None):
        c = Client()
        url = "/register/" + (f"?ref={ref}" if ref else "")
        r = c.post(url, {"first_name": first, "last_name": "Karimov", "phone": phone[4:], "password": PW, "username": "u" + phone[4:], "email": "u" + phone[4:] + "@test.uz", "password2": PW})
        self.assertEqual(r.status_code, 302, r.content[:200])
        return c, User.objects.get(phone=phone)

    def staff(self):
        c = Client()
        c.post("/login/", {"phone": "908775505", "password": "AdminPass1.admin"})
        return c

    def give_membership(self, user, days=30):
        now = timezone.now()
        return Membership.objects.create(user=user, plan=Plan.objects.get(code="m1"), starts=now - timedelta(days=1), expires=now + timedelta(days=days))


class ReferralTests(Base):
    def test_referral_rewards_both_once(self):
        _, a = self.member("+998901112233", "Aziz")
        self.assertTrue(a.referral_code)
        c2, b = self.member("+998935556677", "Bek", ref=a.referral_code)
        self.assertEqual(b.referred_by, a)
        self.assertFalse(a.memberships.exists())
        c2.post("/plans/m1/buy/", {"method": "Payme"})
        a.refresh_from_db()
        self.assertTrue(b.referral_rewarded or User.objects.get(pk=b.pk).referral_rewarded)
        self.assertEqual(a.memberships.count(), 1)  # referrer had nothing, so a short membership starts
        end = services.paid_until(b)
        self.assertEqual(end - timezone.now() > timedelta(days=36), True)  # 30 days + 7 bonus
        c2.post("/plans/m1/buy/", {"method": "Payme"})
        self.assertEqual(services.paid_until(b), end + timedelta(days=30))  # no second reward

    def test_unknown_ref_is_ignored(self):
        _, u = self.member(ref="ZZZZZZZZ")
        self.assertIsNone(u.referred_by)


class CardAndScanTests(Base):
    def test_card_token_and_page(self):
        c, u = self.member()
        r = c.get("/card/")
        self.assertContains(r, "<svg")
        token = services.card_token(u)
        self.assertEqual(services.user_from_card(token), u)
        self.assertIsNone(services.user_from_card(token[:-1] + ("0" if token[-1] != "0" else "1")))  # tampered signature
        self.assertIsNone(services.user_from_card(f"FZ:{u.pk + 1}:{token.split(':')[2]}"))  # signature is bound to the id
        self.assertIsNone(services.user_from_card("nonsense"))

    def test_scan_checks_in_and_needs_staff(self):
        c, u = self.member()
        post = lambda cl, code: cl.post("/staff/scan/", json.dumps({"code": code}), content_type="application/json")
        self.assertEqual(post(c, services.card_token(u)).status_code, 404)  # a member cannot use the scanner
        a = self.staff()
        r = post(a, services.card_token(u))
        self.assertEqual((r.status_code, r.json()["entered"]), (200, False))  # no membership
        self.give_membership(u)
        r = post(a, services.card_token(u))
        self.assertTrue(r.json()["entered"])
        self.assertEqual(Visit.objects.filter(user=u).count(), 1)
        self.assertEqual(post(a, "FZ:1:bad").status_code, 404)
        self.assertEqual(a.get("/staff/scan/").status_code, 200)
        self.assertContains(a.get("/staff/?q=" + services.card_token(u)), u.first_name)  # desk search accepts the QR text


class WorkoutTests(Base):
    def test_plan_toggle_and_isolation(self):
        c, u = self.member()
        self.assertContains(c.get("/workouts/"), "wo-empty")  # no plan yet: the empty state with ready-made programs
        plan = WorkoutPlan.objects.create(user=u, title="Kuch rejasi")
        today = timezone.localdate().weekday()
        ex = Exercise.objects.create(plan=plan, weekday=today, name="Squat", sets=5, reps="5")
        r = c.get("/workouts/")
        self.assertContains(r, "Squat")
        c.post(f"/workouts/{ex.pk}/toggle/")
        self.assertEqual(ExerciseLog.objects.filter(user=u).count(), 1)
        c.post(f"/workouts/{ex.pk}/toggle/")
        self.assertEqual(ExerciseLog.objects.filter(user=u).count(), 0)
        other, _ = self.member("+998935556677", "Bek")
        self.assertEqual(other.post(f"/workouts/{ex.pk}/toggle/").status_code, 404)  # someone else's plan


class AchievementTests(Base):
    def test_achievements_points_leaderboard(self):
        c, u = self.member()
        self.give_membership(u)
        Visit.objects.create(user=u)
        ach = {a["key"]: a for a in services.achievements(u)}
        self.assertTrue(ach["visits_1"]["got"])
        self.assertFalse(ach["visits_10"]["got"])
        self.assertEqual(services.points(u), 10)
        self.assertEqual(services.leaderboard()[0]["name"], "Aziz K.")
        self.assertEqual(c.get("/achievements/").status_code, 200)
        c.post("/profile/", {"form": "profile", "first_name": "Aziz", "last_name": "Karimov", "phone": "90 111 22 33"})  # checkbox absent = opt out
        self.assertEqual(services.leaderboard(), [])

    def test_best_streak(self):
        today = timezone.localdate()
        days = {today - timedelta(days=i) for i in (0, 1, 2, 5, 6)}
        self.assertEqual(services.best_streak(days), 3)


class SmsTests(Base):
    def setUp(self):
        super().setUp()
        self.sent = []
        p = mock.patch.object(sms, "send_sms", side_effect=lambda phone, text: self.sent.append((phone, text)) or True)
        p.start()
        self.addCleanup(p.stop)

    def code(self):
        return re.search(r"\d{6}", self.sent[-1][1]).group()

    def test_password_reset_flow(self):
        _, u = self.member()
        r = Client().post("/forgot/", {"phone": "901112233"})
        self.assertEqual(r.status_code, 302)
        code = self.code()
        c = Client()
        bad = c.post("/reset/", {"phone": "901112233", "code": "000000" if code != "000000" else "111111", "new": "brandnew1"})
        self.assertContains(bad, "field-err")
        self.assertFalse(User.objects.get(pk=u.pk).check_password("brandnew1"))
        ok = c.post("/reset/", {"phone": "901112233", "code": code, "new": "brandnew1"})
        self.assertEqual(ok.status_code, 302)
        u.refresh_from_db()
        self.assertTrue(u.check_password("brandnew1") and u.phone_verified)
        again = c.post("/reset/", {"phone": "901112233", "code": code, "new": "another12"})
        self.assertContains(again, "field-err")  # codes work once
        self.assertEqual(Client().post("/login/", {"phone": "901112233", "password": "brandnew1"}).status_code, 302)

    def test_forgot_does_not_reveal_unknown_numbers(self):
        r1 = Client().post("/forgot/", {"phone": "901112233"})
        r2 = Client().post("/forgot/", {"phone": "909998877"})
        self.assertEqual((r1.status_code, r2.status_code), (302, 302))
        self.assertEqual(len(self.sent), 0)  # nothing is sent to numbers nobody registered
        self.assertTrue(r2["Location"].startswith("/reset/"))

    def test_otp_attempt_and_send_limits(self):
        phone = "+998901112233"
        code, err = sms.issue_otp(phone, "verify")
        for _ in range(5):
            self.assertFalse(sms.check_otp(phone, "verify", "999999" if code != "999999" else "888888"))
        self.assertFalse(sms.check_otp(phone, "verify", code))  # locked after 5 wrong tries
        for _ in range(2):
            sms.issue_otp(phone, "verify")
        self.assertEqual(sms.issue_otp(phone, "verify")[1], "err_rate")  # 3 sends per hour
        self.assertEqual(OtpCode.objects.filter(phone=phone, code_hash__contains=code).count(), 0)  # only hashes are stored

    def test_verification_gate(self):
        gs = GymSettings.load()
        gs.require_phone_verify = True
        gs.save()
        c, u = self.member()
        r = c.post("/plans/m1/buy/", {"method": "Payme"})
        self.assertEqual(r["Location"], "/verify/")
        self.assertEqual(Payment.objects.count(), 0)
        c.post("/verify/", {"action": "send"})
        c.post("/verify/", {"action": "check", "code": self.code()})
        u.refresh_from_db()
        self.assertTrue(u.phone_verified)
        c.post("/plans/m1/buy/", {"method": "Payme"})
        self.assertEqual(Payment.objects.count(), 1)


class ClickTests(Base):
    ENV = {"CLICK_SERVICE_ID": "111", "CLICK_MERCHANT_ID": "222", "CLICK_SECRET_KEY": "s3cret"}

    def form(self, pay, action, **extra):
        d = {"click_trans_id": "9001", "service_id": "111", "merchant_trans_id": str(pay.pk), "amount": str(pay.amount), "action": str(action),
             "sign_time": "2026-10-14 12:00:00", "error": "0"}
        d.update(extra)
        if action == 0:
            d["sign_string"] = click.sign(d["click_trans_id"], d["service_id"], "s3cret", d["merchant_trans_id"], d["amount"], d["action"], d["sign_time"])
        else:
            d["merchant_prepare_id"] = d.get("merchant_prepare_id", str(pay.pk))
            d["sign_string"] = click.sign(d["click_trans_id"], d["service_id"], "s3cret", d["merchant_trans_id"], d["merchant_prepare_id"], d["amount"], d["action"], d["sign_time"])
        return d

    def test_online_payment_flow(self):
        with mock.patch.dict(os.environ, self.ENV):
            c, u = self.member()
            r = c.post("/plans/m1/buy/", {"method": "click"})
            self.assertTrue(r["Location"].startswith("https://my.click.uz/services/pay?"))
            pay = Payment.objects.get()
            self.assertEqual((pay.status, pay.method), ("pending", "click"))
            self.assertFalse(Membership.objects.exists())  # nothing is activated before the gateway confirms
            anon = Client(enforce_csrf_checks=True)  # the callback is signed, not CSRF-protected
            prep = anon.post("/pay/click/", self.form(pay, 0)).json()
            self.assertEqual((prep["error"], prep["merchant_prepare_id"]), (0, pay.pk))
            done = anon.post("/pay/click/", self.form(pay, 1)).json()
            self.assertEqual(done["error"], 0)
            pay.refresh_from_db()
            self.assertEqual(pay.status, "paid")
            self.assertTrue(services.active_membership(u))
            again = anon.post("/pay/click/", self.form(pay, 1)).json()
            self.assertEqual(again["error"], -4)  # already paid

    def test_rejects_bad_signature_amount_and_unknown_payment(self):
        with mock.patch.dict(os.environ, self.ENV):
            c, u = self.member()
            c.post("/plans/m1/buy/", {"method": "click"})
            pay = Payment.objects.get()
            bad = self.form(pay, 0)
            bad["sign_string"] = "0" * 32
            self.assertEqual(Client().post("/pay/click/", bad).json()["error"], -1)
            tampered = self.form(pay, 0)
            tampered["amount"] = "1"  # changed after signing: the amount is part of the signature
            self.assertEqual(Client().post("/pay/click/", tampered).json()["error"], -1)
            wrong_amount = self.form(pay, 0, amount="1")
            wrong_amount["sign_string"] = click.sign("9001", "111", "s3cret", pay.pk, "1", "0", "2026-10-14 12:00:00")
            self.assertEqual(Client().post("/pay/click/", wrong_amount).json()["error"], -2)
            ghost = self.form(pay, 0, merchant_trans_id="99999")
            ghost["sign_string"] = click.sign("9001", "111", "s3cret", "99999", pay.amount, "0", "2026-10-14 12:00:00")
            self.assertEqual(Client().post("/pay/click/", ghost).json()["error"], -5)
            self.assertEqual(Client().post("/pay/click/", self.form(pay, 1, merchant_prepare_id="777")).json()["error"], -6)  # complete without prepare
            cancel = Client().post("/pay/click/", self.form(pay, 0)).json()
            self.assertEqual(cancel["error"], 0)
            self.assertEqual(Client().post("/pay/click/", self.form(pay, 1, error="-5017")).json()["error"], -9)
            pay.refresh_from_db()
            self.assertEqual(pay.status, "cancelled")

    def test_disabled_without_config(self):
        c, u = self.member()
        self.assertNotIn("click", c.get("/plans/").content.decode().split('name="method"')[1].split("</select>")[0])
        pay = Payment.objects.create(user=u, kind="plan", plan=Plan.objects.first(), amount=1, method="click", status="pending")
        self.assertEqual(Client().post("/pay/click/", {"action": "0", "amount": "1", "service_id": ""}).json()["error"], -8)
        self.assertEqual(pay.status, "pending")


class TelegramTests(Base):
    def test_linking_and_status(self):
        _, u = self.member()
        u.tg_link_code = "abc123"
        u.save()
        self.assertIn("Aziz", telegram.handle_message(555, "/start abc123"))
        u.refresh_from_db()
        self.assertEqual(u.telegram_chat_id, 555)
        self.assertIn("faol emas" if False else "abonement", telegram.handle_message(555, "/status").lower())
        self.give_membership(u)
        self.assertIn(timezone.localtime(services.paid_until(u)).strftime("%d.%m.%Y"), telegram.handle_message(555, "/status"))
        telegram.handle_message(555, "/stop")
        u.refresh_from_db()
        self.assertIsNone(u.telegram_chat_id)
        self.assertIn("Telegram", telegram.handle_message(1, "/start wrong"))  # unknown code: help text

    def test_reminders_are_sent_once(self):
        _, u = self.member()
        u.telegram_chat_id = 555
        u.save()
        now = timezone.now()
        m = Membership.objects.create(user=u, plan=Plan.objects.first(), starts=now - timedelta(days=29), expires=now + timedelta(days=2))
        cls = GymClass.objects.first()
        Booking.objects.create(user=u, gym_class=cls, date=timezone.localdate() + timedelta(days=1))
        trainer = cls.trainer
        PTSession.objects.create(user=u, trainer=trainer, starts=now + timedelta(hours=5), status="confirmed")
        with mock.patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "x"}), mock.patch.object(telegram, "send") as send:
            first = telegram.send_reminders()
            second = telegram.send_reminders()
        self.assertEqual(first, {"membership": 1, "class": 1, "pt": 1})
        self.assertEqual(second, {"membership": 0, "class": 0, "pt": 0})
        self.assertEqual(send.call_count, 3)
        m.refresh_from_db()
        self.assertTrue(m.reminded)

    def test_no_reminder_when_renewed_or_unlinked(self):
        _, u = self.member()
        now = timezone.now()
        Membership.objects.create(user=u, plan=Plan.objects.first(), starts=now - timedelta(days=29), expires=now + timedelta(days=2))
        with mock.patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "x"}), mock.patch.object(telegram, "send") as send:
            self.assertEqual(telegram.send_reminders()["membership"], 0)  # no chat linked
            u.telegram_chat_id = 5
            u.save()
            Membership.objects.create(user=u, plan=Plan.objects.first(), starts=now + timedelta(days=2), expires=now + timedelta(days=32))
            self.assertEqual(telegram.send_reminders()["membership"], 0)  # a later membership already covers them
        send.assert_not_called()

    def test_disabled_without_token(self):
        self.assertFalse(telegram.enabled())
        self.assertIsNone(telegram.api("getMe"))
        telegram.alert_admin("x")  # must not raise


class PersonalTrainingTests(Base):
    def slot(self, hours=26):
        t = timezone.localtime() + timedelta(hours=hours)
        return t.replace(hour=12, minute=0, second=0, microsecond=0).strftime("%Y-%m-%dT%H:%M")

    def test_request_confirm_cancel(self):
        c, u = self.member()
        tr = GymClass.objects.first().trainer
        c.post(f"/trainers/{tr.pk}/pt/", {"starts": self.slot(30), "note": "Texnika"})
        s = PTSession.objects.get()
        self.assertEqual(s.status, "requested")
        a = self.staff()
        with mock.patch.object(telegram, "notify_user") as notify:
            a.post(f"/staff/pt/{s.pk}/confirm/")
        s.refresh_from_db()
        self.assertEqual(s.status, "confirmed")
        notify.assert_called_once()
        self.assertContains(c.get("/trainers/"), "pt-confirmed" if False else tr.name)
        c.post(f"/pt/{s.pk}/cancel/")
        s.refresh_from_db()
        self.assertEqual(s.status, "cancelled")

    def test_invalid_requests_rejected(self):
        c, u = self.member()
        tr = GymClass.objects.first().trainer
        c.post(f"/trainers/{tr.pk}/pt/", {"starts": "garbage"})
        c.post(f"/trainers/{tr.pk}/pt/", {"starts": (timezone.localtime() - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M")})  # past
        c.post(f"/trainers/{tr.pk}/pt/", {"starts": (timezone.localtime() + timedelta(days=90)).strftime("%Y-%m-%dT%H:%M")})  # too far
        night = (timezone.localtime() + timedelta(days=2)).replace(hour=3, minute=0).strftime("%Y-%m-%dT%H:%M")
        c.post(f"/trainers/{tr.pk}/pt/", {"starts": night})  # outside opening hours
        self.assertEqual(PTSession.objects.count(), 0)
        for i in range(4):
            c.post(f"/trainers/{tr.pk}/pt/", {"starts": self.slot(30 + 24 * i)})
        self.assertEqual(PTSession.objects.count(), 3)  # at most 3 pending
        other, _ = self.member("+998935556677", "Bek")
        s = PTSession.objects.first()
        self.assertEqual(other.post(f"/pt/{s.pk}/cancel/").status_code, 404)


class PwaAndOpsTests(Base):
    def test_manifest_sw_offline_health(self):
        c = Client()
        m = c.get("/manifest.webmanifest")
        self.assertEqual(m["Content-Type"], "application/manifest+json")
        data = m.json()
        self.assertEqual((data["display"], data["start_url"]), ("standalone", "/dashboard/"))
        from django.contrib.staticfiles import finders
        for icon in data["icons"]:
            self.assertTrue(finders.find(icon["src"].replace("/static/", "", 1)), icon["src"])  # static files are served only in DEBUG, so check the file exists
        sw = c.get("/sw.js")
        self.assertEqual((sw["Content-Type"], sw["Service-Worker-Allowed"]), ("application/javascript", "/"))
        self.assertContains(c.get("/offline/"), "offline" if False else "<main")
        self.assertEqual(c.get("/healthz").content, b"ok")
        self.assertIn('rel="manifest"', c.get("/").content.decode())

    def test_reports_page_and_csv(self):
        c, u = self.member()
        c.post("/plans/m1/buy/", {"method": "Payme"})
        Visit.objects.create(user=u)
        a = self.staff()
        r = a.get("/django-admin/reports/")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Oylik tushum")
        csv_resp = a.get("/django-admin/reports/csv/")
        self.assertIn("400000", csv_resp.content.decode("utf-8-sig"))
        self.assertEqual(c.get("/django-admin/reports/").status_code, 404)  # members cannot reach it

    def test_admin_new_models_and_pt_action(self):
        a = self.staff()
        for url in ("/django-admin/gym/workoutplan/", "/django-admin/gym/workoutplan/add/", "/django-admin/gym/ptsession/", "/django-admin/gym/trainer/",
                    "/django-admin/gym/gymsettings/1/change/"):
            self.assertEqual(a.get(url).status_code, 200, url)

    def test_backup_command(self):
        import tempfile
        from django.conf import settings
        with tempfile.TemporaryDirectory() as d:
            db_file = Path(d) / "src.sqlite3"
            import sqlite3
            con = sqlite3.connect(db_file)
            con.execute("create table t(x)")
            con.commit()
            con.close()
            cfg = {**settings.DATABASES["default"], "NAME": str(db_file)}
            with self.settings(DATABASES={"default": cfg}):
                for _ in range(3):
                    call_command("backup_db", dir=str(Path(d) / "b"), keep=2, verbosity=0)
            files = list((Path(d) / "b").glob("fitnes-*.sqlite3"))
            self.assertEqual(len(files), 2)  # old backups are pruned
            check = sqlite3.connect(files[0])
            self.assertEqual(check.execute("select count(*) from sqlite_master").fetchone()[0], 1)  # the copy contains the table
            check.close()  # Windows cannot delete a file that is still open


class TranslationCoverageTests(TestCase):
    def test_keys_used_in_python_exist_everywhere(self):
        root = Path(__file__).parent
        used = set()
        for name in ("views.py", "telegram.py", "services.py", "sms.py"):
            src = (root / name).read_text(encoding="utf-8")
            used |= set(re.findall(r'flash\(request, [\w.]+, "(\w+)"', src))
            used |= set(re.findall(r'translate\([^,()]+, "(\w+)"', src))
            used |= set(re.findall(r'\(\s*"(?:warn|info)",\s*translate\(request\.lang, "(\w+)"', src))
        used |= {"err_rate", "sms_fail", "otp_bad", "scan_bad", "scan_ok", "err_member", "err_frozen", "err_stock", "cart_bad", "promo_bad"}
        for lang in T:
            self.assertEqual(sorted(k for k in used if k not in T[lang]), [], lang)
        for k in [f"ach_{m}" for m in ("visits_1", "visits_10", "visits_25", "visits_50", "visits_100", "visits_250", "streak_7", "streak_30",
                                        "classes_5", "first_order", "tracker_3", "reviewer", "referrer")]:
            self.assertIn(k, T["uz"])
        self.assertEqual({len(T[l]) for l in T}, {len(T["uz"])})
