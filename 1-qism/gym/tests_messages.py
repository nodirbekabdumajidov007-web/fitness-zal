"""Low-stock SMS to the owner, the member inbox, personal messages from the admin, the profile tabs, the map and the trainer photo reveal."""
import json
from datetime import date, timedelta
from unittest import mock

from django.core.cache import cache
from django.core.management import call_command
from django.test import Client, TestCase, override_settings
from django.utils import timezone

from . import services
from .forms import normalize_phone
from .models import GymSettings, Membership, Notification, Plan, Product, User

PW = "Kuchli-Parol-77"


@override_settings(GOOGLE_CLIENT_ID="")
class Base(TestCase):
    def setUp(self):
        cache.clear()
        call_command("setup_gym", demo=True, verbosity=0)
        self.admin = User.objects.get(is_superuser=True)
        self.admin.set_password("AdminPass1")
        self.admin.save()
        self.m = User.objects.create_user(phone="+998901112233", password=PW, first_name="Aziz", last_name="Karimov")
        self.m2 = User.objects.create_user(phone="+998935550011", password=PW, first_name="Malika", last_name="S")
        self.staff = Client()
        self.staff.post("/login/", {"phone": "908775505", "password": "AdminPass1.admin"})
        self.member = Client()
        self.member.post("/login/", {"phone": "901112233", "password": PW})
        gs = GymSettings.load()
        gs.alert_phone, gs.low_stock_threshold = "", 5
        gs.save()


class LowStockTests(Base):
    def buy(self, product, qty):
        self.member.post(f"/cart/add/{product.pk}/")
        self.member.post(f"/cart/update/{product.pk}/", {"qty": qty})
        return self.member.post("/checkout/", {"method": "cash"})

    @mock.patch("gym.telegram.alert_admin")
    @mock.patch("gym.sms.send_sms", return_value=True)
    def test_sms_says_what_ran_out_and_how_many_once_a_day(self, send, tg):
        p = Product.objects.filter(active=True).first()
        p.stock = 7
        p.save()
        self.buy(p, 1)  # 6 left: still above the threshold
        send.assert_not_called()
        self.buy(p, 2)  # 4 left
        self.assertEqual(send.call_count, 1)
        phone, text = send.call_args[0]
        self.assertEqual(phone, normalize_phone(GymSettings.load().phone))  # no alert phone set: the gym's own number
        self.assertIn(p.name, text)
        self.assertIn("4 ta qoldi", text)
        self.assertIn("olib keling", text)
        need, _ = services.restock_need(Product.objects.get(pk=p.pk))
        self.assertIn(f"Kamida {need} ta", text)
        self.assertTrue(Notification.objects.filter(user=self.admin, title__contains=p.name).exists())  # the admin's bell too
        self.buy(p, 1)  # same day: no second SMS for the same product
        self.assertEqual(send.call_count, 1)

    @mock.patch("gym.telegram.alert_admin")
    @mock.patch("gym.sms.send_sms", return_value=True)
    def test_alert_phone_overrides_and_sold_out_wording(self, send, tg):
        gs = GymSettings.load()
        gs.alert_phone = "93 111 22 33"
        gs.save()
        p = Product.objects.filter(active=True).first()
        p.stock = 1
        p.save()
        self.buy(p, 1)
        phone, text = send.call_args[0]
        self.assertTrue(phone.endswith("931112233"))
        self.assertIn("tugadi", text)

    def test_restock_need_never_below_four_thresholds(self):
        p = Product.objects.filter(active=True).first()
        p.stock = 2
        p.save()
        need, sold = services.restock_need(p)
        self.assertEqual((need, sold), (5 * 4 - 2, 0))

    @mock.patch("gym.telegram.alert_admin")
    @mock.patch("gym.sms.send_sms", return_value=True)
    def test_admin_restock_action_fills_and_rearms(self, send, tg):
        p = Product.objects.filter(active=True).first()
        Product.objects.filter(pk=p.pk).update(stock=0, low_alert_on=timezone.localdate())
        r = self.staff.post("/django-admin/gym/product/", {"action": "restock_to_need", "_selected_action": [p.pk]})
        self.assertEqual(r.status_code, 302)
        p.refresh_from_db()
        self.assertEqual((p.stock, p.low_alert_on), (20, None))
        page = self.staff.get("/django-admin/gym/product/?zaxira=low")
        self.assertEqual(page.status_code, 200)
        self.assertContains(self.staff.get("/django-admin/gym/product/"), "Olib kelish kerak")


class InboxTests(Base):
    def test_bell_counts_and_inbox_marks_read(self):
        services.notify(self.m, "Salom", "Matn", sender=self.admin, telegram_too=False)
        home = self.member.get("/dashboard/")
        self.assertContains(home, 'class="bell ring"')
        r = self.member.get("/inbox/")
        self.assertContains(r, "Salom")
        self.assertContains(r, "nf new")
        self.assertFalse(Notification.objects.filter(user=self.m, read_at=None).exists())
        self.assertNotContains(self.member.get("/dashboard/"), 'class="bell ring"')

    def test_inbox_is_private(self):
        services.notify(self.m2, "Faqat Malikaga", telegram_too=False)
        self.assertNotContains(self.member.get("/inbox/"), "Faqat Malikaga")
        self.assertEqual(Client().get("/inbox/").status_code, 302)


class PersonalMessageTests(Base):
    def test_admin_writes_to_one_person_with_name(self):
        r = self.staff.get(f"/django-admin/message/?ids={self.m.pk}")
        self.assertContains(r, "Aziz Karimov")
        r = self.staff.post("/django-admin/message/", {"ids": [self.m.pk], "title": "Salom, {ism}!", "body": "{ism}, sizni kutamiz"})
        self.assertRedirects(r, f"/django-admin/member/{self.m.pk}/", fetch_redirect_response=False)
        n = Notification.objects.get(user=self.m)
        self.assertEqual((n.title, n.body, n.sender), ("Salom, Aziz!", "Aziz, sizni kutamiz", self.admin))
        self.assertFalse(Notification.objects.filter(user=self.m2).exists())

    @mock.patch("gym.sms.send_sms", return_value=True)
    def test_many_people_and_sms(self, send):
        r = self.staff.post("/django-admin/message/", {"ids": [self.m.pk, self.m2.pk], "title": "Ertaga zal yopiq", "sms": "on"})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(Notification.objects.filter(title="Ertaga zal yopiq").count(), 2)
        self.assertEqual(send.call_count, 2)

    def test_validation_and_search(self):
        r = self.staff.post("/django-admin/message/", {"title": "Hech kimga"})
        self.assertContains(r, "qabul qiluvchini tanlang")
        r = self.staff.post("/django-admin/message/", {"ids": [self.m.pk], "title": ""})
        self.assertContains(r, "Sarlavhani yozing")
        self.assertEqual(Notification.objects.count(), 0)
        r = self.staff.get("/django-admin/message/?q=Malika")
        self.assertContains(r, "+ qo'shish")

    def test_group_shortcut_and_user_action(self):
        now = timezone.now()
        Membership.objects.create(user=self.m2, plan=Plan.objects.get(code="m1"), starts=now - timedelta(days=20), expires=now + timedelta(days=3))
        r = self.staff.get("/django-admin/message/?aud=expiring")
        self.assertContains(r, "Malika")
        r = self.staff.post("/django-admin/gym/user/", {"action": "message", "_selected_action": [self.m.pk, self.m2.pk]})
        self.assertEqual(r.status_code, 302)
        self.assertIn("/django-admin/message/?ids=", r["Location"])

    def test_member_card_has_quick_form_and_members_cannot_send(self):
        self.assertContains(self.staff.get(f"/django-admin/member/{self.m.pk}/"), "Shaxsan yozish")
        r = self.member.post("/django-admin/message/", {"ids": [self.m2.pk], "title": "x"})
        self.assertNotEqual(r.status_code, 200)
        self.assertEqual(Notification.objects.count(), 0)

    def test_dashboard_birthday_panel(self):
        today = timezone.localdate()
        try:
            self.m.birth_date = today.replace(year=today.year - 30)
        except ValueError:  # 29 February: 28 years back is a leap year too
            self.m.birth_date = today.replace(year=today.year - 28)
        self.m.save()
        r = self.staff.get("/django-admin/")
        self.assertContains(r, "Bugun tug'ilgan kun")
        self.assertContains(r, "Aziz Karimov")
        self.assertContains(r, f"/django-admin/message/?ids={self.m.pk}")


class ProfileTests(Base):
    def test_profile_tabs_and_goals(self):
        r = self.member.get("/profile/")
        for anchor in ('id="me"', 'id="goals"', 'id="security"', 'id="connect"'):
            self.assertContains(r, anchor)
        r = self.member.post("/profile/", {"form": "goals", "goal": "lose", "target_weight": "72,5", "birth_date": "1998-05-04"})
        self.assertEqual(r.status_code, 302)
        self.m.refresh_from_db()
        self.assertEqual((self.m.goal, float(self.m.target_weight), self.m.birth_date), ("lose", 72.5, date(1998, 5, 4)))

    def test_goals_reject_nonsense(self):
        self.member.post("/profile/", {"form": "goals", "goal": "fly", "target_weight": "900", "birth_date": "2030-01-01"})
        self.m.refresh_from_db()
        self.assertEqual((self.m.goal, self.m.target_weight, self.m.birth_date), ("", None, None))

    def test_logout_others_and_export(self):
        other = Client()
        other.post("/login/", {"phone": "901112233", "password": PW})
        self.assertEqual(other.get("/profile/").status_code, 200)
        self.member.post("/profile/sessions/")
        self.assertEqual(self.member.get("/profile/").status_code, 200)  # this device stays signed in
        self.assertEqual(other.get("/profile/").status_code, 302)
        r = self.member.get("/profile/export/")
        self.assertIn("attachment", r["Content-Disposition"])
        data = json.loads(r.content)
        self.assertEqual((data["member"]["first_name"], data["member"]["code"]), ("Aziz", self.m.member_code))
        self.assertNotIn("password", r.content.decode())


class ScanTicketTests(Base):
    def scan(self, code):
        return self.staff.post("/staff/scan/", json.dumps({"code": code}), content_type="application/json")

    def test_entry_prints_a_receipt(self):
        now = timezone.now()
        Membership.objects.create(user=self.m, plan=Plan.objects.get(code="m1"), starts=now - timedelta(days=1), expires=now + timedelta(days=10))
        d = self.scan(services.card_token(self.m)).json()
        self.assertTrue(d["entered"])
        visit = self.m.visits.get()
        self.assertIn(f"V-{visit.pk:06d}", d["ticket"])
        self.assertIn("Aziz Karimov", d["ticket"])
        self.assertIn('class="tk ok"', d["ticket"])
        self.assertIn("tk-bar", d["ticket"])
        self.assertEqual(d["today"], 1)
        again = self.scan(services.card_token(self.m)).json()  # second scan the same day: same receipt number, no new visit
        self.assertIn(f"V-{visit.pk:06d}", again["ticket"])
        self.assertEqual(self.m.visits.count(), 1)

    def test_denied_receipt_and_escaping(self):
        self.m.first_name = "<b>Aziz</b>"
        self.m.save()
        d = self.scan(services.card_token(self.m)).json()
        self.assertFalse(d["entered"])
        self.assertIn('class="tk no"', d["ticket"])
        self.assertNotIn("<b>Aziz</b>", d["ticket"])  # names are escaped before they reach innerHTML
        self.assertNotIn("tk-bar", d["ticket"])  # no number for a refused entry

    def test_scanner_page(self):
        r = self.staff.get("/staff/scan/")
        self.assertContains(r, "sc-printer")
        self.assertContains(r, 'id="sc-print"')


class MapAndRevealTests(Base):
    def test_map_from_yandex_link(self):
        gs = GymSettings.load()
        gs.yandex_map_url = "https://yandex.uz/maps/org/gladiator_gym/192510572062/?ll=71.6,40.9"
        gs.save()
        self.assertEqual(gs.map_embed(), "https://yandex.uz/map-widget/v1/org/gladiator_gym/192510572062/?z=17")
        r = Client().get("/")
        self.assertContains(r, 'id="map"')
        self.assertContains(r, "map-widget/v1/org/gladiator_gym/192510572062/")
        self.assertIn("https://yandex.uz", r["Content-Security-Policy"])

    def test_map_from_coordinates_and_none(self):
        gs = GymSettings.load()
        gs.yandex_map_url, gs.map_lat, gs.map_lng = "", 41.3, 69.24
        self.assertIn("pt=69.24,41.3", gs.map_embed())
        gs.map_lat = gs.map_lng = None
        self.assertEqual(gs.map_embed(), "")

    def test_trainer_photos_use_calm_reveal(self):
        r = Client().get("/trainers/")
        self.assertContains(r, "data-px")
        with open(services.__file__.replace("services.py", "static/js/app.js"), encoding="utf-8") as f:
            js = f.read()
        self.assertNotIn("px-layer", js)  # no more scattering tiles
        self.assertIn("px-done", js)
