"""Support widget: guest and member conversations, unread counts, staff replies (notify + push mocked), permissions, rate limit,
honeypot, FAQ search + feedback, the widget on public pages and not in the admin, and the floating-button cleanup."""
import json
import shutil
import tempfile
from unittest import mock

from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import Client, TestCase, override_settings

from . import support
from .i18n import T
from .models import FaqFeedback, FaqItem, SupportMessage, SupportThread, User

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
FETCH = {"HTTP_X_REQUESTED_WITH": "fetch"}
GUEST = {"name": "Mehmon Bek", "phone": "90 123 45 67", "email": "bek@test.uz"}


class Base(TestCase):
    def setUp(self):
        cache.clear()
        call_command("setup_gym", demo=True, verbosity=0)
        self.media = tempfile.mkdtemp()
        o = override_settings(MEDIA_ROOT=self.media)
        o.enable()
        self.addCleanup(lambda: (o.disable(), shutil.rmtree(self.media, ignore_errors=True)))
        self.admin = User.objects.get(is_superuser=True)
        self.admin.set_password("AdminPass1")
        self.admin.first_name = "Admin"
        self.admin.save()
        self.member = User.objects.create_user(phone="+998901112233", password="Kuchli-Parol-77", first_name="Aziz", last_name="Karimov")
        self.mc = Client()
        self.mc.force_login(self.member)
        self.staff = Client()
        self.staff.post("/login/", {"login": "admin1", "password": "AdminPass1.admin"})

    def send(self, client, text="Salom", **extra):
        return client.post("/support/send/", {"text": text, **extra}, **FETCH)

    def guest_send(self, client=None, text="Salom", **extra):
        return self.send(client or Client(), text, **{**GUEST, **extra})


class GuestTests(Base):
    def test_guest_starts_and_continues_with_token(self):
        c = Client()
        r = self.guest_send(c, "Narxlar qanday?")
        self.assertTrue(r.json()["ok"])
        self.assertIn("fz_support", r.cookies)
        self.assertTrue(r.cookies["fz_support"]["httponly"])
        t = SupportThread.objects.get()
        self.assertIsNone(t.user)
        self.assertEqual((t.guest_name, t.guest_phone, t.guest_email), ("Mehmon Bek", "+998901234567", "bek@test.uz"))
        self.assertEqual(t.unread_by_staff, 1)
        # the second message needs no contact data: the cookie identifies the conversation
        r2 = self.send(c, "Yana savol")
        self.assertTrue(r2.json()["ok"])
        self.assertEqual(SupportThread.objects.count(), 1)
        self.assertEqual(t.messages.count(), 2)
        d = c.get("/support/thread/", **FETCH).json()
        self.assertEqual([m["text"] for m in d["messages"]], ["Narxlar qanday?", "Yana savol"])

    def test_guest_needs_valid_contact(self):
        for extra in ({"name": "", "phone": "90 123 45 67"}, {"name": "Bek", "phone": "123"}, {"name": "Bek", "phone": "90 123 45 67", "email": "x"}):
            r = self.send(Client(), "Salom", **extra)
            self.assertFalse(r.json()["ok"])
            self.assertEqual(r.status_code, 400)
        self.assertEqual(SupportThread.objects.count(), 0)

    def test_guest_sees_only_own_thread(self):
        a, b = Client(), Client()
        self.guest_send(a, "A xabari")
        self.guest_send(b, "B xabari", name="Boshqa", phone="91 111 22 33")
        self.assertEqual([m["text"] for m in a.get("/support/thread/").json()["messages"]], ["A xabari"])
        self.assertEqual([m["text"] for m in b.get("/support/thread/").json()["messages"]], ["B xabari"])
        self.assertEqual(Client().get("/support/thread/").json()["messages"], [])

    def test_forged_token_gets_nothing(self):
        self.guest_send(Client(), "Maxfiy")
        c = Client()
        c.cookies["fz_support"] = "x" * 30
        self.assertEqual(c.get("/support/thread/").json()["thread"], None)

    def test_honeypot_stores_nothing(self):
        r = self.guest_send(Client(), "Spam", website="http://spam.example")
        self.assertTrue(r.json()["ok"])
        self.assertEqual(SupportThread.objects.count(), 0)
        self.assertEqual(SupportMessage.objects.count(), 0)

    def test_csrf_required(self):
        c = Client(enforce_csrf_checks=True)
        r = c.post("/support/send/", {"text": "x", **GUEST}, **FETCH)
        self.assertEqual(r.status_code, 403)
        self.assertEqual(SupportThread.objects.count(), 0)

    def test_rate_limits(self):
        c = Client()
        self.guest_send(c, "1")
        codes = [self.send(c, str(i)).status_code for i in range(support.RATE_PER_MIN + 2)]
        self.assertIn(429, codes)
        cache.clear()
        for i in range(support.NEW_GUEST_PER_HOUR):
            self.assertEqual(self.guest_send(text=f"g{i}").status_code, 200)
        r = self.guest_send(text="too many")
        self.assertEqual(r.status_code, 429)
        self.assertFalse(r.json()["ok"])


class MemberTests(Base):
    def test_member_thread_send_poll_read_and_unread(self):
        r = self.send(self.mc, "Abonementim haqida")
        self.assertTrue(r.json()["ok"])
        t = SupportThread.objects.get(user=self.member)
        self.assertEqual((t.unread_by_staff, t.unread_by_user, t.status), (1, 0, "open"))
        first = r.json()["message"]["id"]
        # staff reply: the member's unread counter and the poll
        with mock.patch("gym.services.notify") as notify:
            support.staff_reply(t, self.admin, "Ha, yordam beramiz")
        t.refresh_from_db()
        self.assertEqual((t.unread_by_staff, t.unread_by_user, t.status), (0, 1, "pending"))
        self.assertEqual(t.assigned_to, self.admin)
        d = self.mc.get(f"/support/thread/?after={first}", **FETCH).json()
        self.assertEqual(d["unread"], 1)
        self.assertEqual([m["text"] for m in d["messages"]], ["Ha, yordam beramiz"])
        self.assertTrue(d["messages"][0]["staff"])
        home = self.mc.get("/support/home/").json()
        self.assertEqual(home["unread"], 1)
        self.assertTrue(home["last"]["unread"])
        self.assertEqual(home["last"]["name"], "Admin")
        # the widget button shows the badge number on the next page load
        cfg = json.loads(self.mc.get("/").content.decode().split('id="sw-config" type="application/json">')[1].split("</script>")[0])
        self.assertEqual(cfg["unread"], 1)
        # mark read
        self.assertTrue(self.mc.post("/support/read/", **FETCH).json()["ok"])
        t.refresh_from_db()
        self.assertEqual(t.unread_by_user, 0)
        self.assertTrue(SupportMessage.objects.get(is_staff=True).read_at)
        self.assertEqual(self.mc.get("/support/thread/").json()["unread"], 0)
        # a new member message reopens the thread
        self.send(self.mc, "Rahmat")
        t.refresh_from_db()
        self.assertEqual((t.status, t.unread_by_staff), ("open", 1))
        self.assertEqual(notify.call_count, 1)

    def test_staff_reply_notifies_member_with_push(self):
        self.send(self.mc, "Salom")
        t = SupportThread.objects.get(user=self.member)
        with mock.patch("gym.pwa.push_user", return_value=1) as push, mock.patch("gym.telegram.send") as tg:
            support.staff_reply(t, self.admin, "Javob matni")
        from .models import Notification
        n = Notification.objects.get(user=self.member)
        self.assertEqual(n.body, "Javob matni")
        self.assertEqual(n.sender, self.admin)
        push.assert_called_once()
        self.assertEqual(push.call_args[0][0], self.member)
        self.assertIn("support", push.call_args[0][3])
        tg.assert_not_called()

    def test_guest_reply_sends_no_notification(self):
        self.guest_send(Client(), "Salom")
        t = SupportThread.objects.get()
        with mock.patch("gym.services.notify") as notify:
            support.staff_reply(t, self.admin, "Javob")
        notify.assert_not_called()

    def test_staff_alert_goes_to_telegram_when_configured(self):
        with mock.patch("gym.telegram.alert_admin") as alert:
            self.send(self.mc, "Birinchi")
            self.send(self.mc, "Ikkinchi")
        self.assertEqual(alert.call_count, 1)  # one alert per unread run, not one per message

    def test_one_thread_per_member_and_validation(self):
        self.send(self.mc, "bir")
        self.send(self.mc, "ikki")
        self.assertEqual(SupportThread.objects.filter(user=self.member).count(), 1)
        self.assertEqual(self.send(self.mc, "").status_code, 400)
        self.assertEqual(self.send(self.mc, "x" * (support.MAX_TEXT + 1)).status_code, 400)
        self.assertFalse(self.send(self.mc, "   ").json()["ok"])

    def test_image_upload_validation_and_permissions(self):
        r = self.mc.post("/support/send/", {"text": "", "image": SimpleUploadedFile("a.png", PNG)}, **FETCH)
        self.assertTrue(r.json()["ok"], r.content)
        url = r.json()["message"]["image"]
        self.assertEqual(self.mc.get(url).status_code, 200)
        self.assertEqual(self.mc.get(url)["X-Content-Type-Options"], "nosniff")
        self.assertEqual(self.staff.get(url).status_code, 200)  # staff in admin mode
        other = User.objects.create_user(phone="+998935556677", password="Kuchli-Parol-77", first_name="Bek")
        oc = Client()
        oc.force_login(other)
        self.assertEqual(oc.get(url).status_code, 404)
        self.assertEqual(Client().get(url).status_code, 404)
        bad = self.mc.post("/support/send/", {"text": "x", "image": SimpleUploadedFile("a.png", b"not an image at all")}, **FETCH)
        self.assertEqual(bad.status_code, 400)
        bad2 = self.mc.post("/support/send/", {"text": "x", "image": SimpleUploadedFile("a.exe", PNG)}, **FETCH)
        self.assertEqual(bad2.status_code, 400)

    def test_cannot_read_others_threads(self):
        self.send(self.mc, "Mening maxfiy xabarim")
        other = User.objects.create_user(phone="+998935556677", password="Kuchli-Parol-77", first_name="Bek")
        oc = Client()
        oc.force_login(other)
        d = oc.get("/support/thread/").json()
        self.assertEqual(d["messages"], [])
        self.assertIsNone(d["thread"])
        self.assertNotIn("maxfiy", oc.get("/support/home/").content.decode())
        # a thread id in the URL or query is ignored: there is no way to ask for another thread
        t = SupportThread.objects.get(user=self.member)
        self.assertEqual(oc.get(f"/support/thread/?id={t.pk}&thread={t.pk}").json()["messages"], [])
        self.assertTrue(oc.post("/support/read/", **FETCH).json()["ok"])
        t.refresh_from_db()
        self.assertEqual(t.unread_by_staff, 1)

    def test_endpoints_are_json_with_ok_false_errors(self):
        self.assertEqual(self.client.get("/support/send/").status_code, 405)
        self.assertEqual(self.client.get("/support/faq/999999/").json(), {"ok": False, "error": T["uz"]["sw_err_notfound"]})


class AdminTests(Base):
    def test_inbox_thread_and_actions(self):
        self.send(self.mc, "Yordam kerak")
        self.guest_send(Client(), "Mehmon savoli")
        t = SupportThread.objects.get(user=self.member)
        r = self.staff.get("/django-admin/support/")
        self.assertContains(r, "Aziz Karimov")
        self.assertContains(r, "Murojaatlar")
        self.assertContains(self.staff.get("/django-admin/support/?f=open&w=free"), "Mehmon Bek")
        self.assertNotContains(self.staff.get("/django-admin/support/?f=closed"), "Aziz Karimov")
        page = self.staff.get(f"/django-admin/support/{t.pk}/")
        self.assertContains(page, "Yordam kerak")
        self.assertContains(page, f"/django-admin/member/{self.member.pk}/")
        t.refresh_from_db()
        self.assertEqual(t.unread_by_staff, 0)  # opening marks it seen
        with mock.patch("gym.services.notify") as notify:
            r = self.staff.post(f"/django-admin/support/{t.pk}/reply/", {"text": "Javob"}, follow=True)
        self.assertContains(r, "Javob yuborildi")
        notify.assert_called_once()
        t.refresh_from_db()
        self.assertEqual(t.status, "pending")
        self.staff.post(f"/django-admin/support/{t.pk}/close/")
        t.refresh_from_db()
        self.assertEqual(t.status, "closed")
        self.staff.post(f"/django-admin/support/{t.pk}/reopen/")
        t.refresh_from_db()
        self.assertEqual(t.status, "open")
        self.staff.post(f"/django-admin/support/{t.pk}/assign/")
        t.refresh_from_db()
        self.assertEqual(t.assigned_to, self.admin)
        self.assertContains(self.staff.get("/django-admin/support/?w=mine&f=all"), "Aziz Karimov")

    def test_staff_only(self):
        self.send(self.mc, "x")
        t = SupportThread.objects.get()
        self.assertNotEqual(self.mc.get("/django-admin/support/").status_code, 200)
        self.assertNotEqual(self.mc.post(f"/django-admin/support/{t.pk}/reply/", {"text": "hack"}).status_code, 200)
        self.assertNotEqual(Client().get(f"/django-admin/support/{t.pk}/").status_code, 200)
        self.assertEqual(t.messages.count(), 1)

    def test_nav_badge_and_entry(self):
        self.send(self.mc, "Yangi")
        r = self.staff.get("/django-admin/")
        self.assertContains(r, 'href="/django-admin/support/"')
        from .admin_site import nav_badges
        cache.clear()
        self.assertEqual(nav_badges()["support"], 1)

    def test_faq_admin_shows_votes(self):
        item = FaqItem.objects.create(question_uz="Test savol", answer_uz="Test javob")
        FaqFeedback.objects.create(faq=item, helpful=True, session_key="a")
        FaqFeedback.objects.create(faq=item, helpful=False, session_key="b")
        r = self.staff.get("/django-admin/gym/faqitem/")
        self.assertContains(r, "Foydali (ha)")
        self.assertContains(r, "Test savol")


class FaqTests(Base):
    def setUp(self):
        super().setUp()
        FaqItem.objects.all().delete()
        self.f1 = FaqItem.objects.create(question_uz="Abonementni muzlatsa bo'ladimi?", answer_uz="Ha, {freeze_min} kundan.", order=1)
        self.f2 = FaqItem.objects.create(question_uz="Qanday to'lov usullari bor?", answer_uz="Naqd va karta.", order=2)
        self.f3 = FaqItem.objects.create(question_uz="Yashirin", answer_uz="x", active=False)

    def test_list_and_categories(self):
        d = self.client.get("/support/faq/").json()
        self.assertTrue(d["ok"])
        keys = {c["key"] for c in d["categories"]}
        self.assertEqual(keys, {"membership", "payment"})
        ids = [i["id"] for c in d["categories"] for i in c["items"]]
        self.assertNotIn(self.f3.pk, ids)
        self.assertEqual(len(d["top"]), 2)

    def test_article_fills_placeholders(self):
        d = self.client.get(f"/support/faq/{self.f1.pk}/").json()
        self.assertEqual(d["a"], "Ha, 7 kundan.")
        self.assertEqual(self.client.get(f"/support/faq/{self.f3.pk}/").status_code, 404)

    def test_search_finds_faq_and_assistant(self):
        d = self.client.get("/support/search/", {"q": "muzlatish"}).json()
        self.assertEqual([i["id"] for i in d["faq"]], [self.f1.pk])
        d = self.client.get("/support/search/", {"q": "Ish vaqti qanday?"}).json()
        self.assertTrue(d["assistant"])
        self.assertTrue(d["assistant"]["answer"])
        for link in d["assistant"]["links"]:
            self.assertTrue(link["url"].startswith("/"))
        self.assertEqual(self.client.get("/support/search/", {"q": ""}).json()["faq"], [])

    def test_feedback_is_stored_once_per_person(self):
        c = Client()
        r = c.post(f"/support/faq/{self.f1.pk}/feedback/", json.dumps({"helpful": True}), content_type="application/json", **FETCH)
        self.assertTrue(r.json()["ok"])
        c.post(f"/support/faq/{self.f1.pk}/feedback/", json.dumps({"helpful": False}), content_type="application/json", **FETCH)
        self.assertEqual(FaqFeedback.objects.filter(faq=self.f1).count(), 1)
        self.assertFalse(FaqFeedback.objects.get(faq=self.f1).helpful)
        self.assertIs(c.get(f"/support/faq/{self.f1.pk}/").json()["voted"], False)
        # a member's vote is tied to the account
        self.mc.post(f"/support/faq/{self.f1.pk}/feedback/", json.dumps({"helpful": True}), content_type="application/json", **FETCH)
        self.assertTrue(FaqFeedback.objects.filter(faq=self.f1, user=self.member, helpful=True).exists())

    def test_feedback_validation(self):
        for body in ('{"helpful": "yes"}', "not json", "[]"):
            r = self.client.post(f"/support/faq/{self.f1.pk}/feedback/", body, content_type="application/json", **FETCH)
            self.assertEqual(r.status_code, 400)
        r = self.client.post("/support/faq/99999/feedback/", '{"helpful": true}', content_type="application/json", **FETCH)
        self.assertEqual(r.status_code, 404)
        self.assertEqual(FaqFeedback.objects.count(), 0)


class WidgetMarkupTests(Base):
    def test_widget_on_public_pages(self):
        for url in ("/", "/plans/", "/faq/", "/login/", "/shop/"):
            html = self.client.get(url).content.decode()
            self.assertIn('id="sw-fab"', html, url)
            self.assertIn('id="sw-panel"', html, url)
            self.assertIn("js/support.js", html, url)
            self.assertIn('data-sw-tab="home"', html)
            self.assertIn('data-sw-tab="msgs"', html)
            self.assertIn('data-sw-tab="help"', html)

    def test_widget_not_in_admin(self):
        for url in ("/django-admin/", "/django-admin/support/"):
            html = self.staff.get(url).content.decode()
            self.assertNotIn("sw-fab", html)
            self.assertNotIn("support.js", html)

    def test_fab_cleanup(self):
        html = self.client.get("/").content.decode()
        self.assertEqual(html.count('class="sw-fab"'), 1)
        self.assertNotIn('class="vmic"', html)  # no separate floating mic button
        self.assertNotIn('class="fab"', html)  # no separate Telegram FAB on the home page
        self.assertIn('class="totop"', html)  # back-to-top stays
        # the mic lives inside the Help tab and still drives the voice panel
        help_part = html.split('id="sw-v-help"')[1].split('class="sw-tabs"')[0]
        self.assertIn('id="vmic"', help_part)
        self.assertIn('id="vpanel"', html)
        # Telegram is a row in Home
        home_part = html.split('id="sw-v-home"')[1].split('id="sw-v-msgs"')[0]
        self.assertIn("t.me/", home_part)

    def test_greeting_and_guest_name(self):
        self.assertIn("Salom, mehmon", self.client.get("/").content.decode())
        self.assertIn("Salom, Aziz", self.mc.get("/").content.decode())

    def test_no_raw_keys_and_all_keys_translated(self):
        for lang in ("uz", "ru", "en"):
            for k in support.UI_KEYS:
                self.assertIn(k, T[lang], (lang, k))
        self.client.cookies["fz_lang"] = "ru"
        self.assertIn("Чем мы можем вам помочь?", self.client.get("/").content.decode())

    def test_progress_template_removed(self):
        import os
        from django.conf import settings
        self.assertFalse(os.path.exists(os.path.join(settings.BASE_DIR, "gym", "templates", "gym", "progress.html")))

    def test_js_contract(self):
        js = open("gym/static/js/support.js", encoding="utf-8").read()
        for needle in ("fz_sw_tab", "Escape", "prefers-reduced-motion", "visibilitychange", "d.messages", "C.urls.send"):
            self.assertIn(needle, js)
        self.assertNotIn("innerHTML = m", js)
