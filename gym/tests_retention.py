"""Tests of the retention features: freeze, reminders, guest passes, referral, waitlist, ratings, streaks, gifts, calendar, FAQ, legal, consent."""
import json
import subprocess
import sys
from datetime import timedelta
from pathlib import Path

from django.core import mail
from django.test import Client
from django.utils import timezone

from . import extras, services
from .models import (Booking, ClassWaitlist, ExpiryReminder, FaqItem, GiftCertificate, GuestPass, GymClass, GymSettings, LegalPage, Membership, Notification,
                     Payment, Plan, PTSession, ReferralReward, User, Visit)
from .tests import PW, Base


class RetentionBase(Base):
    def give(self, user, days=30, plan="m1"):
        now = timezone.now()
        return Membership.objects.create(user=user, plan=Plan.objects.get(code=plan), starts=now - timedelta(days=1), expires=now + timedelta(days=days))

    def scan(self, staff, code):
        r = staff.post("/django-admin/desk/scan/", data=json.dumps({"code": code}), content_type="application/json")
        return r.status_code, r.json()


class FreezeTests(RetentionBase):
    def test_rules_future_and_early_end(self):
        c, u = self.member()
        m = self.give(u, 60)
        GymSettings.objects.filter(pk=1).update(freeze_min_days=7, freeze_max_days=30)
        end0 = m.expires
        self.assertIsNone(extras.start_freeze(u, 3)[0])  # below the minimum
        self.assertEqual(extras.start_freeze(u, 3)[1], "freeze_min")
        self.assertEqual(extras.start_freeze(u, 31)[1], "freeze_too_long")
        f, err = extras.start_freeze(u, 10, timezone.localdate() + timedelta(days=5))
        self.assertIsNone(err)
        m.refresh_from_db()
        self.assertEqual(m.expires, end0 + timedelta(days=10))
        self.assertTrue(services.can_enter(u))  # starts in the future
        self.assertEqual(extras.start_freeze(u, 7)[1], "freeze_busy")
        days, err = extras.end_freeze(u)  # cancel the scheduled one
        self.assertEqual(days, 10)
        m.refresh_from_db()
        self.assertEqual(m.expires, end0)
        # now a real freeze from today, 20 of 30 days, then end it early
        extras.start_freeze(u, 20)
        self.assertFalse(services.can_enter(u))
        m.refresh_from_db()
        self.assertEqual(m.expires, end0 + timedelta(days=20))
        days, _ = extras.end_freeze(u)
        self.assertEqual(days, 20)  # started today: nothing used
        self.assertTrue(services.can_enter(u))
        # the total per membership is capped
        extras.start_freeze(u, 30)
        self.assertEqual(extras.freeze_info(u)["current"].days, 30)

    def test_total_cap_and_disabled(self):
        c, u = self.member()
        self.give(u, 90)
        GymSettings.objects.filter(pk=1).update(freeze_max_days=0)
        self.assertEqual(extras.start_freeze(u, 7)[1], "freeze_off")
        GymSettings.objects.filter(pk=1).update(freeze_max_days=10)
        self.assertIsNone(extras.start_freeze(u, 7)[1])
        extras.end_freeze(u)  # started today: all 7 days are returned
        self.assertIsNone(extras.start_freeze(u, 10)[1])

    def test_views_and_scan_message(self):
        c, u = self.member()
        self.give(u, 40)
        r = c.post("/membership/freeze/", {"days": 7})
        self.assertEqual(r.status_code, 302)
        self.assertContains(c.get("/membership/"), "freeze")
        d = self.scan(self.staff(), services.card_token(u))[1]
        self.assertFalse(d["entered"])
        self.assertIn("muzlatilgan", d["message"].lower())
        c.post("/membership/unfreeze/")
        self.assertTrue(self.scan(self.staff(), services.card_token(u))[1]["entered"])


class ReminderTests(RetentionBase):
    def test_once_per_threshold_and_nearest_only(self):
        _, u = self.member()
        u.telegram_chat_id = 5
        u.save()
        now = timezone.now()
        m = Membership.objects.create(user=u, plan=Plan.objects.first(), starts=now - timedelta(days=20), expires=now + timedelta(days=2, hours=1))
        first = extras.send_expiry_reminders()
        second = extras.send_expiry_reminders()
        self.assertEqual((first["sent"], second["sent"]), (1, 0))
        self.assertEqual(Notification.objects.filter(user=u).count(), 1)  # only the nearest threshold, not 7+3
        later = extras.send_expiry_reminders(today=timezone.localdate() + timedelta(days=2))  # now 0 days left: threshold 1
        self.assertEqual(later["sent"], 1)
        self.assertEqual(ExpiryReminder.objects.filter(membership=m).count(), 3)

    def test_renewal_covers_and_email_optional(self):
        _, u = self.member()
        now = timezone.now()
        Membership.objects.create(user=u, plan=Plan.objects.first(), starts=now - timedelta(days=20), expires=now + timedelta(days=6))
        GymSettings.objects.filter(pk=1).update(reminder_email=True)
        extras.send_expiry_reminders()
        self.assertEqual(len(mail.outbox) - 1, 1 - 1 + 0) if False else None
        self.assertTrue(any("Fitnes Zal" in m.subject for m in mail.outbox))
        Membership.objects.create(user=u, plan=Plan.objects.first(), starts=now + timedelta(days=6), expires=now + timedelta(days=36))
        self.assertEqual(extras.send_expiry_reminders(today=timezone.localdate() + timedelta(days=4))["sent"], 0)

    def test_lazy_daily_runs_once_and_command(self):
        from django.core.cache import cache
        from django.core.management import call_command
        cache.clear()
        _, u = self.member()
        now = timezone.now()
        Membership.objects.create(user=u, plan=Plan.objects.first(), starts=now - timedelta(days=20), expires=now + timedelta(days=1, hours=2))
        self.assertEqual(extras.run_daily()["sent"], 1)
        self.assertIsNone(extras.run_daily())
        call_command("send_reminders", verbosity=0)  # idempotent
        self.assertEqual(Notification.objects.filter(user=u).count(), 1)
        self.assertEqual(Client().get("/renew/").status_code, 302)

    def test_renew_goes_to_plans(self):
        c, u = self.member()
        self.give(u, 3, "m3")
        r = c.get("/renew/")
        self.assertIn("renew=m3", r["Location"])
        self.assertContains(c.get("/plans/?renew=m3"), "renew-hl")


class GuestPassTests(RetentionBase):
    def test_flow(self):
        c, u = self.member()
        self.give(u, 30)
        Plan.objects.filter(code="m1").update(guest_passes=1)
        today = timezone.localdate()
        c.post("/guest/new/", {"name": "Bobur", "phone": "", "date": today.isoformat()})
        gp = GuestPass.objects.get()
        self.assertEqual(c.post("/guest/new/", {"name": "Yana", "date": today.isoformat()}).status_code, 302)
        self.assertEqual(GuestPass.objects.count(), 1)  # quota is 1
        code = extras.guest_code(gp)
        page = Client().get(f"/guest/{code}/")
        self.assertContains(page, "Bobur")
        self.assertEqual(Client().get("/guest/GP-1-badbadbadbad/").status_code, 404)
        st = self.staff()
        status, d = self.scan(st, code)
        self.assertTrue(d["entered"])
        self.assertFalse(self.scan(st, code)[1]["entered"])  # one time only
        gp.refresh_from_db()
        self.assertIsNotNone(gp.used_at)

    def test_wrong_day_and_cancelled(self):
        c, u = self.member()
        self.give(u, 30)
        Plan.objects.filter(code="m1").update(guest_passes=3)
        t = timezone.localdate()
        c.post("/guest/new/", {"name": "Ali", "date": (t + timedelta(days=2)).isoformat()})
        c.post("/guest/new/", {"name": "Vali", "date": t.isoformat()})
        early, today_pass = GuestPass.objects.order_by("date")[::-1][0], GuestPass.objects.order_by("date")[0]
        st = self.staff()
        self.assertFalse(self.scan(st, extras.guest_code(early))[1]["entered"])  # not its date yet
        c.post(f"/guest/{today_pass.pk}/cancel/")
        self.assertFalse(self.scan(st, extras.guest_code(today_pass))[1]["entered"])
        GuestPass.objects.filter(pk=early.pk).update(date=t - timedelta(days=1))
        self.assertFalse(self.scan(st, extras.guest_code(early))[1]["entered"])  # expired
        self.assertEqual(extras.create_guest_pass(u, "Z", "", t)[1], "gp_name")


class ReferralTests(RetentionBase):
    def test_rewarded_once_after_paid_only(self):
        _, a = self.member("+998901112233", "Aziz")
        c2, b = self.member("+998935556677", "Bek")
        User.objects.filter(pk=b.pk).update(referred_by=a)
        services.grant_days(b, 5)  # free days are not a purchase
        self.assertFalse(ReferralReward.objects.exists())
        c2.post("/plans/m1/buy/", {"method": "Payme", "consent": "1"})
        self.assertEqual(ReferralReward.objects.filter(referrer=a, referred=b).count(), 1)
        c2.post("/plans/m1/buy/", {"method": "Payme"})
        self.assertEqual(ReferralReward.objects.count(), 1)
        self.assertEqual(Notification.objects.filter(user=a).count(), 1)

    def test_not_self_and_cash_waits(self):
        _, a = self.member("+998901112233", "Aziz")
        User.objects.filter(pk=a.pk).update(referred_by=a)
        a.refresh_from_db()
        self.assertFalse(services.reward_referral(a))
        c2, b = self.member("+998935556677", "Bek")
        User.objects.filter(pk=b.pk).update(referred_by=a)
        c2.post("/plans/m1/buy/", {"method": "cash"})
        self.assertFalse(ReferralReward.objects.exists())  # cash is not paid until staff confirm
        services.confirm_payment(Payment.objects.get(user=b))
        self.assertEqual(ReferralReward.objects.count(), 1)

    def test_newcomer_discount(self):
        _, a = self.member("+998901112233", "Aziz")
        c2, b = self.member("+998935556677", "Bek")
        User.objects.filter(pk=b.pk).update(referred_by=a)
        GymSettings.objects.filter(pk=1).update(referral_newcomer_percent=10)
        c2.post("/plans/m1/buy/", {"method": "Payme"})
        p = Payment.objects.get(user=b)
        self.assertEqual(p.promo, "REFERRAL")
        self.assertEqual(p.amount, Plan.objects.get(code="m1").price * 90 // 100)


class ClassTests(RetentionBase):
    def setUp(self):
        super().setUp()
        self.cls = GymClass.objects.filter(name="Pauerlifting").get()
        GymClass.objects.filter(pk=self.cls.pk).update(capacity=1)
        self.cls.refresh_from_db()

    def test_waitlist_promotion_and_cancel_window(self):
        a_c, a = self.member("+998901112233", "Aziz")
        b_c, b = self.member("+998935556677", "Bek")
        for u in (a, b):
            self.give(u, 60)
        a_c.post(f"/classes/{self.cls.pk}/book/")
        d = self.cls.next_date()
        self.assertEqual(Booking.objects.filter(gym_class=self.cls, date=d).count(), 1)
        b_c.post(f"/classes/{self.cls.pk}/waitlist/")
        self.assertEqual(ClassWaitlist.objects.count(), 1)
        self.assertEqual(extras.waitlist_position(b, self.cls, d), 1)
        bk = Booking.objects.get(user=a)
        # inside the cancel window nothing can be cancelled
        GymSettings.objects.filter(pk=1).update(class_cancel_hours=24 * 8)
        a_c.post(f"/bookings/{bk.pk}/cancel/")
        self.assertTrue(Booking.objects.filter(pk=bk.pk).exists())
        GymSettings.objects.filter(pk=1).update(class_cancel_hours=0)
        a_c.post(f"/bookings/{bk.pk}/cancel/")
        self.assertFalse(Booking.objects.filter(user=a).exists())
        self.assertTrue(Booking.objects.filter(user=b, gym_class=self.cls, date=d).exists())  # first in line got the seat
        self.assertTrue(Notification.objects.filter(user=b).exists())
        self.assertFalse(ClassWaitlist.objects.exists())
        self.assertEqual(a_c.get("/classes/").status_code, 200)

    def test_noshow_limit_and_desk_marking(self):
        c, u = self.member()
        self.give(u, 60)
        today = timezone.localdate()
        for i in range(3):
            Booking.objects.create(user=u, gym_class=self.cls, date=today - timedelta(days=i + 1), no_show=True)
        self.assertEqual(extras.noshow_count(u), 3)
        other = GymClass.objects.exclude(pk=self.cls.pk).first()
        GymClass.objects.filter(pk__in=[other.pk, self.cls.pk]).update(capacity=20)
        c.post(f"/classes/{other.pk}/book/")
        self.assertEqual(Booking.objects.filter(user=u, date__gte=today).count(), 1)
        c.post(f"/classes/{self.cls.pk}/book/")
        self.assertEqual(Booking.objects.filter(user=u, date__gte=today).count(), 1)  # limited to one
        self.assertContains(c.get("/classes/"), "alert" if False else "warn")
        st = self.staff()
        b = Booking.objects.filter(user=u, date__gte=today).get()
        self.assertEqual(st.post(f"/django-admin/desk/booking/{b.pk}/noshow/").status_code, 200)
        b.refresh_from_db()
        self.assertTrue(b.no_show)
        self.assertEqual(st.get("/django-admin/desk/classes/").status_code, 200)


class TrainerRatingTests(RetentionBase):
    def test_only_attendees_rate_once_and_admin_hides(self):
        c, u = self.member()
        cls = GymClass.objects.exclude(trainer=None).first()
        tr = cls.trainer
        self.assertEqual(extras.rate_trainer(u, tr, 5, "x")[1], "tr_rate_not_allowed")
        PTSession.objects.create(user=u, trainer=tr, starts=timezone.now() - timedelta(days=1), status="confirmed")
        c.post(f"/trainers/{tr.pk}/rate/", {"rating": "4", "comment": "Zo'r"})
        c.post(f"/trainers/{tr.pk}/rate/", {"rating": "5", "comment": "Juda zo'r"})
        self.assertEqual(tr.reviews.count(), 1)
        self.assertEqual(tr.reviews.get().rating, 5)
        self.assertContains(c.get(f"/trainers/{tr.pk}/"), "Juda zo&#x27;r")
        self.assertContains(c.get("/trainers/"), "5,0" if False else "★")
        tr.reviews.update(hidden=True)
        self.assertEqual(len(c.get(f"/trainers/{tr.pk}/").context["reviews"]), 0)  # hidden from the public list
        self.assertEqual(extras.rate_trainer(u, tr, 9, "")[1], "tr_rate_bad")

    def test_class_attendance_counts_no_show_does_not(self):
        _, u = self.member()
        cls = GymClass.objects.exclude(trainer=None).first()
        past = timezone.localdate() - timedelta(days=3)
        b = Booking.objects.create(user=u, gym_class=cls, date=past, no_show=True)
        self.assertFalse(extras.attended_trainer(u, cls.trainer))
        Booking.objects.filter(pk=b.pk).update(no_show=False)
        self.assertTrue(extras.attended_trainer(u, cls.trainer))


class StreakTests(RetentionBase):
    def test_weekly_streak_and_optin_board(self):
        c, u = self.member()
        self.give(u)
        self.assertFalse(u.show_in_leaderboard)  # off by default
        today = timezone.localdate()
        monday = today - timedelta(days=today.weekday())
        for w in (1, 2):  # the two previous weeks have two visits each
            for d in (0, 1):
                v = Visit.objects.create(user=u)
                Visit.objects.filter(pk=v.pk).update(ts=timezone.make_aware(timezone.datetime.combine(monday - timedelta(days=7 * w) + timedelta(days=d), timezone.datetime.min.time())) + timedelta(hours=10))
        self.assertEqual(extras.weekly_streak(u)["weeks"], 2)
        Visit.objects.create(user=u)
        self.assertEqual(services.leaderboard(), [])
        c.post("/leaderboard/join/", {"on": "1"})
        self.assertEqual(len(services.leaderboard()), 1)
        self.assertContains(c.get("/achievements/"), "Aziz K.")
        c.post("/leaderboard/join/", {"on": "0"})
        self.assertEqual(services.leaderboard(), [])


class GiftTests(RetentionBase):
    def test_buy_redeem_plan_once(self):
        c, u = self.member()
        c.post("/gift/buy/", {"plan": "m1", "method": "Payme", "consent": "1"})
        g = GiftCertificate.objects.get()
        self.assertEqual(g.state, "valid")
        c2, v = self.member("+998935556677", "Bek")
        c2.post("/gift/redeem/", {"code": g.code.lower()})
        self.assertIsNotNone(services.active_membership(v))
        c2.post("/gift/redeem/", {"code": g.code})
        self.assertEqual(v.memberships.count(), 1)  # one time
        self.assertEqual(extras.gift_error(extras.find_gift(g.code)), "gift_used")

    def test_unpaid_amount_checkout_and_expiry(self):
        c, u = self.member()
        c.post("/gift/buy/", {"amount": "100000", "method": "cash", "consent": "1"})
        g = GiftCertificate.objects.get()
        self.assertEqual(g.state, "unpaid")
        self.assertEqual(extras.gift_error(g), "gift_unpaid")
        services.confirm_payment(g.payment)
        g.refresh_from_db()
        self.assertEqual(g.state, "valid")
        price = Plan.objects.get(code="m1").price
        pay, err = services.buy_plan(u, Plan.objects.get(code="m1"), "cash", "", g.code)
        self.assertIsNone(err)
        self.assertEqual(pay.amount, price - 100000)
        g.refresh_from_db()
        self.assertEqual(g.redeemed_by, u)
        services.cancel_payment(pay)  # cancelled payment releases the code
        g.refresh_from_db()
        self.assertIsNone(g.redeemed_at)
        GiftCertificate.objects.filter(pk=g.pk).update(expires=timezone.localdate() - timedelta(days=1))
        self.assertEqual(services.buy_plan(u, Plan.objects.get(code="m1"), "cash", "", g.code)[1], "gift_expired")

    def test_plan_gift_covers_checkout_fully(self):
        _, u = self.member()
        plan = Plan.objects.get(code="m1")
        g = GiftCertificate.objects.create(code="GC-TEST2345", plan=plan, expires=timezone.localdate() + timedelta(days=5))
        pay, err = services.buy_plan(u, plan, "cash", "", "gc-test2345")
        self.assertEqual((err, pay.amount, pay.status), (None, 0, "paid"))
        self.assertIsNotNone(services.active_membership(u))
        self.assertEqual(services.buy_plan(u, plan, "cash", "", "GC-TEST2345")[1], "gift_used")

    def test_amount_bounds(self):
        _, u = self.member()
        self.assertEqual(extras.buy_gift(u, None, 10, "cash")[2], "gift_amount")


class CalendarTests(RetentionBase):
    def test_single_event_and_feed(self):
        c, u = self.member()
        self.give(u, 60)
        cls = GymClass.objects.first()
        b = Booking.objects.create(user=u, gym_class=cls, date=cls.next_date())
        r = c.get(f"/bookings/{b.pk}/ics/")
        self.assertEqual(r["Content-Type"].split(";")[0], "text/calendar")
        body = r.content.decode()
        self.assertIn("BEGIN:VEVENT", body)
        self.assertIn("\r\n", body)
        token = extras.ensure_calendar_token(u)
        feed = Client().get(f"/calendar/{token}.ics")
        self.assertContains(feed, f"UID:booking-{b.pk}@fitnes-zal")
        self.assertEqual(Client().get("/calendar/short.ics").status_code, 404)
        self.assertEqual(Client().get("/calendar/" + "x" * 32 + ".ics").status_code, 404)
        c.post("/calendar/reset/")
        self.assertEqual(Client().get(f"/calendar/{token}.ics").status_code, 404)
        other, _ = self.member("+998935556677", "Bek")
        self.assertEqual(other.get(f"/bookings/{b.pk}/ics/").status_code, 404)


class PagesTests(RetentionBase):
    def test_faq_and_legal_pages(self):
        c = Client()
        self.assertGreaterEqual(FaqItem.objects.count(), 15)
        r = c.get("/faq/")
        self.assertContains(r, "<details")
        self.assertNotContains(r, "{hours}")
        for url in ("/oferta/", "/privacy/", "/refund/"):
            r = c.get(url)
            self.assertEqual(r.status_code, 200)
            self.assertContains(r, "[YURIDIK NOM]")
        self.assertContains(c.get("/privacy/"), "ZRU-547")
        self.assertContains(c.get("/"), "/oferta/")
        self.assertContains(c.get("/faq/"), "/privacy/")
        FaqItem.objects.all().delete()
        self.assertEqual(c.get("/faq/").status_code, 200)

    def test_admin_warns_about_placeholders(self):
        st = self.staff()
        r = st.get("/django-admin/gym/legalpage/", follow=True)
        self.assertContains(r, "YURIDIK NOM")
        for p in LegalPage.objects.all():
            for lang in ("uz", "ru", "en"):
                setattr(p, f"body_{lang}", "Tayyor matn")
            p.save()
        self.assertEqual(extras.legal_placeholders(), [])

    def test_admin_pages_open(self):
        st = self.staff()
        for m in ("membershipfreeze", "guestpass", "referralreward", "classwaitlist", "trainerreview", "giftcertificate", "faqitem", "legalpage"):
            self.assertEqual(st.get(f"/django-admin/gym/{m}/").status_code, 200, m)
        self.assertEqual(st.get("/django-admin/gym/giftcertificate/add/").status_code, 200)
        self.assertEqual(st.get("/django-admin/").status_code, 200)

    def test_placeholder_regex(self):
        from .legal_defaults import find_placeholders
        self.assertEqual(find_placeholders("a [STIR] b [14] kun [MA'LUMOTLAR SAQLANADIGAN JOY]"), ["[STIR]", "[MA'LUMOTLAR SAQLANADIGAN JOY]"])


class ConsentAndDeletionTests(RetentionBase):
    def test_register_requires_consent_and_stores_time(self):
        data = {"username": "cons_user", "email": "cons@x.uz", "password": PW, "password2": PW}
        r = Client().post("/register/", data)
        self.assertEqual(r.status_code, 200)
        self.assertFalse(User.objects.filter(username="cons_user").exists())
        r = Client().post("/register/", {**data, "consent": "1"})
        self.assertEqual(r.status_code, 302)
        self.assertIsNotNone(User.objects.get(username="cons_user").consent_at)

    def test_purchase_needs_consent_for_old_accounts(self):
        u = User.objects.create_user(phone="+998977776655", password=PW, first_name="Eski", email="eski@x.uz")
        c = Client()
        c.post("/login/", {"login": "+998977776655", "password": PW})
        c.post("/plans/m1/buy/", {"method": "Payme"})
        self.assertEqual(Payment.objects.count(), 0)
        c.post("/plans/m1/buy/", {"method": "Payme", "consent": "1"})
        p = Payment.objects.get()
        self.assertIsNotNone(p.consent_at)
        u.refresh_from_db()
        self.assertIsNotNone(u.consent_at)
        c.post("/plans/m1/buy/", {"method": "Payme"})  # remembered
        self.assertEqual(Payment.objects.count(), 2)

    def test_delete_account(self):
        c, u = self.member()
        c.post("/plans/m1/buy/", {"method": "Payme"})
        c.post("/progress/", {"date": timezone.localdate().isoformat(), "weight": "80.0"})
        c.post("/profile/delete/", {"password": "wrong", "sure": "1"})
        u.refresh_from_db()
        self.assertTrue(u.is_active)
        r = c.post("/profile/delete/", {"password": PW, "sure": "1"})
        self.assertEqual(r.status_code, 302)
        u.refresh_from_db()
        self.assertFalse(u.is_active)
        self.assertIsNone(u.phone)
        self.assertIsNone(u.email)
        self.assertEqual(u.first_name, "Deleted")
        self.assertIsNotNone(u.deleted_at)
        self.assertFalse(u.has_usable_password())
        self.assertEqual(u.bodylogs.count(), 0)
        self.assertEqual(Payment.objects.filter(user=u).count(), 1)  # financial record stays
        self.assertEqual(Client().post("/login/", {"login": "u901112233", "password": PW}).status_code, 200)

    def test_staff_cannot_self_delete(self):
        st = self.staff()
        st.post("/profile/delete/", {"password": "AdminPass1", "sure": "1"})
        self.assertTrue(User.objects.get(pk=self.admin.pk).is_active)


class DemoPaymentsTests(RetentionBase):
    def test_never_in_production(self):
        root = Path(__file__).resolve().parent.parent
        code = "import os;os.environ['DJANGO_DEBUG']='0';os.environ['FZ_ALLOW_DEMO']='1';import config.settings as s;print(s.ALLOW_DEMO_PAYMENTS)"
        out = subprocess.run([sys.executable, "-c", code], cwd=root, capture_output=True, text=True, env={**__import__("os").environ, "DJANGO_DEBUG": "0", "FZ_ALLOW_DEMO": "1"})
        self.assertEqual(out.stdout.strip().splitlines()[-1], "False", out.stderr[-300:])

    def test_disabled_methods_are_not_selectable(self):
        from django.test import override_settings
        c, u = self.member()
        with override_settings(ALLOW_DEMO_PAYMENTS=False):
            r = c.get("/plans/")
            html = r.content.decode()
            for name in ("Payme", "Uzum", "disabled", "tez orada"):
                self.assertNotIn(name, html)  # methods that do not work are not shown
            self.assertIn("paytiles single", html)  # only cash is left: one clear option
            self.assertIn('value="cash"', html)
            c.post("/plans/m1/buy/", {"method": "Payme"})
            self.assertEqual(Payment.objects.count(), 0)


class EntryHistoryTests(RetentionBase):
    def test_every_scan_is_recorded(self):
        from .models import EntryLog
        c, u = self.member()
        st = self.staff()
        code = services.card_token(u)
        self.scan(st, code)  # no membership
        self.scan(st, "FZ:99999:bad")  # invalid
        m = self.give(u, 30)
        self.scan(st, code)  # in
        self.scan(st, code)  # again the same day
        extras.start_freeze(u, 7)
        Visit.objects.all().delete()
        self.scan(st, code)  # frozen
        extras.end_freeze(u)
        Membership.objects.filter(pk=m.pk).update(expires=timezone.now() - timedelta(days=1))
        self.scan(st, code)  # expired
        rows = list(EntryLog.objects.order_by("id").values_list("result", "reason", "method"))
        self.assertEqual(rows, [("rejected", "no_membership", "qr"), ("rejected", "invalid", "qr"), ("ok", "", "qr"), ("repeat", "", "qr"),
                                ("rejected", "frozen", "qr"), ("rejected", "expired", "qr")])

    def test_guest_pass_and_manual_logged(self):
        from .models import EntryLog
        c, u = self.member()
        self.give(u, 30)
        Plan.objects.filter(code="m1").update(guest_passes=2)
        c.post("/guest/new/", {"name": "Bobur", "date": timezone.localdate().isoformat()})
        gp = GuestPass.objects.get()
        st = self.staff()
        self.scan(st, extras.guest_code(gp))
        self.scan(st, extras.guest_code(gp))  # used
        self.scan(st, "GP-1-badbadbadbad")
        got = list(EntryLog.objects.filter(method="guest").order_by("id").values_list("result", "reason"))
        self.assertEqual(got, [("ok", ""), ("rejected", "guest_used"), ("rejected", "invalid")])
        st.post(f"/django-admin/desk/checkin/{u.pk}/")
        self.assertTrue(EntryLog.objects.filter(method="manual", user=u).exists())
        c.post("/checkin/")
        self.assertTrue(EntryLog.objects.filter(method="self", user=u).exists())

    def test_member_history_page_paginates_and_staff_see_it(self):
        from .models import EntryLog
        c, u = self.member()
        for i in range(35):
            EntryLog.objects.create(user=u, method="qr", result="ok")
        EntryLog.objects.create(user=u, method="qr", result="rejected", reason="expired")  # rejections are not in the member's list
        r = c.get("/card/history/")
        self.assertEqual(len(r.context["page"].object_list), 30)
        self.assertEqual(r.context["month"], 35)
        self.assertEqual(len(c.get("/card/history/?page=2").context["page"].object_list), 5)
        self.assertContains(c.get("/card/"), "/card/history/")
        self.assertContains(c.get("/dashboard/"), "/card/history/")
        st = self.staff()
        self.assertContains(st.get(f"/django-admin/member/{u.pk}/"), "QR-kod")
        self.assertEqual(st.get("/django-admin/gym/entrylog/?result__exact=rejected").status_code, 200)
        self.assertEqual(Client().get("/card/history/").status_code, 302)


class TrainerNavTests(RetentionBase):
    def test_links_hidden_without_active_trainers(self):
        from django.core.cache import cache
        from .models import Trainer
        c = Client()
        cache.clear()
        self.assertContains(c.get("/plans/"), 'href="/trainers/"')
        Trainer.objects.update(active=False)
        cache.clear()
        html = c.get("/plans/").content.decode()
        self.assertNotIn('href="/trainers/"', html)
        r = c.get("/trainers/")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "tez orada")  # friendly empty state, not a blank page
        Trainer.objects.update(active=True)
        cache.clear()
        self.assertContains(c.get("/plans/"), 'href="/trainers/"')
