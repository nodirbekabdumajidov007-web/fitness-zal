"""Visits every URL of the site (and every admin page) as a guest, a member and staff: nothing may crash, and templates must not
reference variables that do not exist."""
import copy
import os
import re
from datetime import timedelta

from django.conf import settings
from django.contrib import admin
from django.core.cache import cache
from django.core.management import call_command
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from . import chat, services
from .models import (BodyLog, Booking, ChatMessage, Exercise, GymClass, Lesson, Membership, Order, Payment, PaymentCard, Plan, Product,
                     PTSession, Review, User, WorkoutPlan)
from .urls import urlpatterns

INVALID = "@@INVALID[%s]@@"
TEMPLATES = copy.deepcopy(settings.TEMPLATES)
TEMPLATES[0]["OPTIONS"]["string_if_invalid"] = INVALID
# variables that are optional on purpose (e.g. "the member's own review, if any")
ALLOWED_INVALID = {"mine.comment", "mine.rating", "q", "next"}


@override_settings(TEMPLATES=TEMPLATES)
class SmokeTests(TestCase):
    def setUp(self):
        cache.clear()
        call_command("setup_gym", demo=True, verbosity=0)
        self.admin = User.objects.get(is_superuser=True)
        self.admin.set_password("AdminPass1")
        self.admin.save()
        PaymentCard.objects.create(bank="Uzcard", number="4111111111111111", holder="TEST", is_primary=True)
        self.member = Client()
        self.member.post("/register/", {"first_name": "Aziz", "last_name": "Karimov", "phone": "90 111 22 33", "password": "secret12", "username": "u" + "".join(ch for ch in str("90 111 22 33") if ch.isdigit()), "email": "u" + "".join(ch for ch in str("90 111 22 33") if ch.isdigit()) + "@test.uz", "password2": "secret12"})
        self.u = User.objects.get(phone="+998901112233")
        other = User.objects.create_user(phone="+998935556677", password="secret12", first_name="Bek", last_name="Z")
        now = timezone.now()
        Membership.objects.create(user=self.u, plan=Plan.objects.get(code="m1"), starts=now - timedelta(days=2), expires=now + timedelta(days=3))
        self.cls = GymClass.objects.first()
        self.booking = Booking.objects.create(user=self.u, gym_class=self.cls, date=self.cls.next_date())
        self.member.post("/plans/m1/buy/", {"method": "card"})
        self.card_pay = Payment.objects.filter(method="card").first()
        prod = Product.objects.first()
        self.member.post(f"/cart/add/{prod.pk}/")
        self.member.post("/checkout/", {"method": "cash"})
        self.order = Order.objects.first()
        self.trainer = self.cls.trainer
        self.pt = PTSession.objects.create(user=self.u, trainer=self.trainer, starts=now + timedelta(days=2))
        plan = WorkoutPlan.objects.create(user=self.u, title="Reja", trainer=self.trainer)
        self.ex = Exercise.objects.create(plan=plan, weekday=0, name="Squat")
        self.log = BodyLog.objects.create(user=self.u, weight=80, height_cm=180)
        BodyLog.objects.create(user=self.u, weight=79, height_cm=180, date=timezone.localdate() - timedelta(days=7))
        Review.objects.create(user=self.u, rating=5, comment="Zo'r", approved=True)
        chat.ensure_rooms()
        self.room = chat.direct_room(self.u, other)
        self.msg = ChatMessage.objects.create(room=self.room, sender=other, body="salom")
        self.lesson = Lesson.objects.first()
        self.staff = Client()
        self.staff.post("/login/", {"login": "admin1", "password": "AdminPass1.admin"})
        self.other = other

    def args_for(self, name, converters):
        objs = {
            "set_lang": {"code": "ru"}, "buy_plan": {"code": "m1"}, "receipt": {"pk": self.card_pay.pk}, "pay": {"pk": self.card_pay.pk},
            "pay_report": {"pk": self.card_pay.pk}, "pay_cancel": {"pk": self.card_pay.pk}, "book_class": {"pk": self.cls.pk},
            "cancel_booking": {"pk": self.booking.pk}, "pt_request": {"pk": self.trainer.pk}, "pt_cancel": {"pk": self.pt.pk},
            "progress_delete": {"pk": self.log.pk}, "workout_toggle": {"pk": self.ex.pk}, "lesson": {"pk": self.lesson.pk},
            "lesson_video": {"pk": self.lesson.pk}, "chat_room": {"pk": self.room.pk}, "chat_send": {"pk": self.room.pk},
            "chat_poll": {"pk": self.room.pk}, "chat_delete": {"pk": self.msg.pk}, "chat_report": {"pk": self.msg.pk},
            "desk_pt": {"pk": self.pt.pk, "action": "confirm"}, "desk_confirm": {"pid": self.card_pay.pk}, "desk_reject": {"pid": self.card_pay.pk},
            "desk_handover": {"oid": self.order.pk},
            "image": {"kind": "product", "pk": Product.objects.first().pk}, "product": {"pk": Product.objects.first().pk},
            "trainer": {"pk": self.trainer.pk},
            "start_program": {"key": "beginner"}, "coach_pt": {"pk": self.pt.pk, "action": "confirm"},
            "coach_client": {"uid": self.other.pk}, "coach_plan": {"uid": self.other.pk},
            "pw_confirm": {"uidb64": "MQ", "token": "set-password"},
        }
        if name in objs:
            return objs[name]
        guess = {"uid": self.other.pk, "pid": Product.objects.first().pk, "pk": 1, "oid": self.order.pk}
        return {k: guess[k] for k in converters}

    def check(self, client, url, who):
        r = client.get(url)
        self.assertLess(r.status_code, 500, f"{who} {url}")
        if r.status_code == 200 and "text/html" in r.get("Content-Type", ""):
            found = set(re.findall(r"@@INVALID\[(.*?)\]@@", r.content.decode()))
            self.assertEqual(found - ALLOWED_INVALID, set(), f"{who} {url}: template variables that do not exist")

    def test_every_site_url(self):
        clients = {"guest": Client(), "member": self.member, "staff": self.staff}
        seen = 0
        for p in urlpatterns:
            name = p.name
            url = reverse(name, kwargs=self.args_for(name, p.pattern.converters) or None) if name else "/" + str(p.pattern)
            for who, client in clients.items():
                self.check(client, url, who)
            seen += 1
        self.assertGreater(seen, 50)
        for extra in ("/training/?day=3&level=advanced", "/shop/?q=suv", "/chat/?q=bek", f"/staff/?q={self.u.member_code}",
                      "/staff/?q=FZ", "/plans/", "/dashboard/"):
            for who, client in clients.items():
                self.check(client, extra, who)

    def test_admin_shortcuts(self):
        for url in ("/admin", "/admin/", "/panel", "/adminka/"):
            self.assertEqual(Client().get(url)["Location"], "/django-admin/", url)
        self.assertEqual(Client().get("/django-admin/")["Location"], "/login/?next=/django-admin/")  # guests are sent to sign in
        self.assertEqual(self.staff.get("/admin", follow=True).status_code, 200)

    def test_every_admin_page(self):
        for model, model_admin in admin.site._registry.items():
            meta = model._meta
            base = f"/django-admin/{meta.app_label}/{meta.model_name}/"
            r = self.staff.get(base)
            self.assertEqual(r.status_code, 200, base)
            obj = model_admin.get_queryset(type("R", (), {"user": self.admin, "GET": {}, "META": {}})()).first() if False else model.objects.first()
            if obj is not None:
                r = self.staff.get(f"{base}{obj.pk}/change/")
                self.assertIn(r.status_code, (200, 302), f"{base}{obj.pk}/change/")
            if model_admin.has_add_permission(type("R", (), {"user": self.admin})()):
                self.assertEqual(self.staff.get(f"{base}add/").status_code, 200, f"{base}add/")
        for url in ("/django-admin/", "/django-admin/reports/", "/django-admin/reports/csv/"):
            self.assertEqual(self.staff.get(url).status_code, 200, url)
