"""Chat upgrade: replies, reactions, edits, typing, read markers, search, pins, @mentions, mute, privacy masking, history paging,
and the shape of the websocket / polling payloads."""
import json
from datetime import date, timedelta
from unittest import mock

from asgiref.sync import async_to_sync, sync_to_async
from django.test import Client
from django.utils import timezone

from . import chat
from .chat_views import day_label
from .models import ChatBlock, ChatMessage, ChatRoom, Mention, MessageReaction, RoomMute, User
from .tests_chat import FETCH, ChatBase
from .tests_ws import Sock


class FeatureBase(ChatBase):
    def setUp(self):
        super().setUp()
        chat.ensure_rooms()
        self.general = ChatRoom.objects.get(slug="general")

    def jpost(self, client, url, data=None):
        return client.post(url, json.dumps(data or {}), content_type="application/json", **FETCH)

    def say(self, client, room, body, **extra):
        r = client.post(f"/chat/{room.pk}/send/", dict({"body": body}, **extra), **FETCH)
        return r.json()

    def admin_client(self):
        c = self.staff()
        s = c.session
        s["admin_mode"] = True
        s.save()
        return c


class ReplyTests(FeatureBase):
    def test_reply_is_serialized_with_a_quote(self):
        room = self.dm()
        first = self.say(self.ca, room, "Ertaga zalga borasanmi?")["message"]
        r = self.say(self.cb, room, "Ha, soat 7 da", reply_to=first["id"])
        self.assertTrue(r["ok"])
        q = r["message"]["reply"]
        self.assertEqual((q["id"], q["name"], q["text"], q["deleted"]), (first["id"], "Aziz K.", "Ertaga zalga borasanmi?", False))
        self.assertIsNone(first["reply"])
        poll = self.ca.get(f"/chat/{room.pk}/poll/?after={first['id']}").json()
        self.assertEqual(poll["messages"][0]["reply"]["id"], first["id"])
        self.assertContains(self.ca.get(f"/chat/{room.pk}/"), 'data-jump="%d"' % first["id"])

    def test_reply_must_be_in_the_same_room(self):
        other = self.say(self.ca, self.general, "umumiy")["message"]
        r = self.say(self.cb, self.dm(), "javob", reply_to=other["id"])
        self.assertFalse(r["ok"])
        self.assertEqual(ChatMessage.objects.filter(room=self.dm()).count(), 0)

    def test_quote_of_a_deleted_message_shows_no_text(self):
        first = self.say(self.ca, self.dm(), "maxfiy matn")["message"]
        reply = self.say(self.cb, self.dm(), "ok", reply_to=first["id"])["message"]
        self.ca.post(f"/chat/message/{first['id']}/delete/", **FETCH)
        got = self.cb.get(f"/chat/{self.dm().pk}/poll/?after={reply['id'] - 1}").json()["messages"][0]["reply"]
        self.assertEqual((got["deleted"], got["text"]), (True, ""))

    def test_blocked_member_cannot_reply_to_the_blocker_in_a_room(self):
        m = self.say(self.ca, self.general, "salom")["message"]
        ChatBlock.objects.create(blocker=self.a, blocked=self.b)
        r = self.say(self.cb, self.general, "javob", reply_to=m["id"])
        self.assertFalse(r["ok"])


class ReactionTests(FeatureBase):
    def react(self, client, mid, emoji):
        return self.jpost(client, f"/chat/message/{mid}/react/", {"emoji": emoji})

    def test_toggle_change_and_counts(self):
        m = self.say(self.ca, self.general, "bugun mashq qildim")["message"]
        r = self.react(self.cb, m["id"], "🔥").json()
        self.assertEqual(r["reactions"], [{"e": "🔥", "n": 1, "mine": True}])
        self.react(self.ca, m["id"], "🔥")
        self.assertEqual(MessageReaction.objects.filter(message_id=m["id"]).count(), 2)
        r = self.react(self.cb, m["id"], "💪").json()  # one reaction per member: this replaces 🔥
        self.assertEqual({(x["e"], x["n"]) for x in r["reactions"]}, {("🔥", 1), ("💪", 1)})
        self.assertEqual(MessageReaction.objects.filter(message_id=m["id"], user=self.b).count(), 1)
        r = self.react(self.cb, m["id"], "💪").json()  # same emoji again removes it
        self.assertEqual(r["reactions"], [{"e": "🔥", "n": 1, "mine": False}])
        # the reader sees "mine" for himself only
        self.assertTrue(self.ca.get(f"/chat/{self.general.pk}/poll/?after=0").json()["messages"][0]["reactions"][0]["mine"])

    def test_only_the_six_emoji_and_only_visible_messages(self):
        m = self.say(self.ca, self.dm(), "salom")["message"]
        self.assertEqual(self.react(self.cb, m["id"], "🤡").status_code, 400)
        cc, _ = self.member("+998977778899", "Cami", "Rustamov")
        self.assertEqual(self.react(cc, m["id"], "👍").status_code, 404)  # not in the conversation
        self.assertEqual(Client().post(f"/chat/message/{m['id']}/react/").status_code, 302)
        self.ca.post(f"/chat/message/{m['id']}/delete/", **FETCH)
        self.assertEqual(self.react(self.cb, m["id"], "👍").status_code, 403)  # deleted

    def test_who_reacted(self):
        m = self.say(self.ca, self.general, "salom")["message"]
        self.react(self.cb, m["id"], "👏")
        self.react(self.ca, m["id"], "👏")
        groups = self.ca.get(f"/chat/message/{m['id']}/reactions/").json()["groups"]
        self.assertEqual(groups, [{"e": "👏", "names": ["Bek Z.", "Aziz K."]}])

    def test_blocked_members_cannot_react_to_each_other(self):
        m = self.say(self.ca, self.general, "salom")["message"]
        ChatBlock.objects.create(blocker=self.a, blocked=self.b)
        self.assertEqual(self.react(self.cb, m["id"], "👍").status_code, 403)
        self.assertEqual(MessageReaction.objects.count(), 0)
        self.assertEqual(self.react(self.ca, m["id"], "👍").status_code, 200)  # own message is fine

    def test_banned_cannot_react_and_rate_limit(self):
        m = self.say(self.ca, self.general, "salom")["message"]
        for _ in range(40):
            self.react(self.cb, m["id"], "👍")
        self.assertEqual(self.react(self.cb, m["id"], "👍").status_code, 429)
        User.objects.filter(pk=self.a.pk).update(chat_banned=True)
        self.assertEqual(self.react(self.ca, m["id"], "🔥").status_code, 403)

    def test_poll_carries_reactions_and_skips_them_when_unchanged(self):
        m = self.say(self.ca, self.general, "salom")["message"]
        self.react(self.cb, m["id"], "❤️")
        p = self.ca.get(f"/chat/{self.general.pk}/poll/?after={m['id']}").json()
        self.assertEqual(p["rx"][str(m["id"])][0]["e"], "❤️")
        again = self.ca.get(f"/chat/{self.general.pk}/poll/?after={m['id']}&rxh={p['rxh']}").json()
        self.assertNotIn("rx", again)
        self.react(self.cb, m["id"], "❤️")  # removed: the next poll must tell the page
        gone = self.ca.get(f"/chat/{self.general.pk}/poll/?after={m['id']}&rxh={p['rxh']}").json()
        self.assertEqual(gone["rx"][str(m["id"])], [])


class EditTests(FeatureBase):
    def edit(self, client, mid, body):
        return self.jpost(client, f"/chat/message/{mid}/edit/", {"body": body})

    def test_edit_within_window_marks_it(self):
        m = self.say(self.ca, self.dm(), "Salom")["message"]
        self.assertTrue(m["can_edit"] and not m["edited"])
        r = self.edit(self.ca, m["id"], "Salom, Bek!").json()
        self.assertEqual((r["message"]["body"], r["message"]["edited"]), ("Salom, Bek!", True))
        self.assertIsNotNone(ChatMessage.objects.get(pk=m["id"]).edited_at)
        self.assertContains(self.cb.get(f"/chat/{self.dm().pk}/"), "tahrirlandi")
        since = timezone.now().timestamp() - 5  # polling clients get edited messages
        got = self.cb.get(f"/chat/{self.dm().pk}/poll/?after={m['id']}&since={since}").json()
        self.assertEqual([x["id"] for x in got["edited"]], [m["id"]])

    def test_same_text_is_not_an_edit(self):
        m = self.say(self.ca, self.dm(), "Salom")["message"]
        self.edit(self.ca, m["id"], "Salom")
        self.assertIsNone(ChatMessage.objects.get(pk=m["id"]).edited_at)

    def test_only_the_author_and_only_for_15_minutes(self):
        m = self.say(self.ca, self.dm(), "Salom")["message"]
        self.assertEqual(self.edit(self.cb, m["id"], "hack").status_code, 404)
        self.assertEqual(ChatMessage.objects.get(pk=m["id"]).body, "Salom")
        ChatMessage.objects.filter(pk=m["id"]).update(created=timezone.now() - timedelta(minutes=16))
        r = self.edit(self.ca, m["id"], "kech")
        self.assertEqual(r.status_code, 403)
        self.assertEqual(ChatMessage.objects.get(pk=m["id"]).body, "Salom")
        ChatMessage.objects.filter(pk=m["id"]).update(created=timezone.now() - timedelta(minutes=14))
        self.assertEqual(self.edit(self.ca, m["id"], "o'z vaqtida").status_code, 200)
        poll = self.ca.get(f"/chat/{self.dm().pk}/poll/?after=0").json()["messages"][0]
        self.assertTrue(poll["can_edit"])
        ChatMessage.objects.filter(pk=m["id"]).update(created=timezone.now() - timedelta(minutes=20))
        self.assertFalse(self.ca.get(f"/chat/{self.dm().pk}/poll/?after=0").json()["messages"][0]["can_edit"])

    def test_cannot_empty_or_edit_deleted_or_when_blocked(self):
        m = self.say(self.ca, self.dm(), "Salom")["message"]
        self.assertEqual(self.edit(self.ca, m["id"], "  ").status_code, 400)
        self.assertEqual(self.edit(self.ca, m["id"], "x" * 1001).status_code, 400)
        ChatBlock.objects.create(blocker=self.b, blocked=self.a)
        self.assertEqual(self.edit(self.ca, m["id"], "yana").status_code, 400)
        ChatBlock.objects.all().delete()
        self.ca.post(f"/chat/message/{m['id']}/delete/", **FETCH)
        self.assertEqual(self.edit(self.ca, m["id"], "yana").status_code, 403)

    def test_edit_masks_private_data_in_the_public_room(self):
        m = self.say(self.ca, self.general, "salom")["message"]
        r = self.edit(self.ca, m["id"], "menga 901234567 ga yoz").json()
        self.assertEqual(r["message"]["body"], "menga ** *** ** 67 ga yoz")
        self.assertIn("notice", r)


class TypingTests(FeatureBase):
    def test_http_typing_reaches_polling_clients_and_the_group(self):
        room = self.dm()
        with mock.patch("gym.chat_views.announce") as ann:
            self.assertEqual(self.ca.post(f"/chat/{room.pk}/typing/", **FETCH).status_code, 200)
        ann.assert_called_once_with(room.pk, {"type": "chat.typing", "user": self.a.pk, "name": "Aziz K."})
        self.assertEqual(self.cb.get(f"/chat/{room.pk}/poll/?after=0").json()["typing"], ["Aziz K."])
        self.assertEqual(self.ca.get(f"/chat/{room.pk}/poll/?after=0").json()["typing"], [])  # not about myself

    def test_typing_in_the_public_room_and_blocked_dm(self):
        self.ca.post(f"/chat/{self.general.pk}/typing/", **FETCH)
        self.assertEqual(self.cb.get(f"/chat/{self.general.pk}/poll/?after=0").json()["typing"], ["Aziz K."])
        ChatBlock.objects.create(blocker=self.b, blocked=self.a)
        self.assertEqual(self.ca.post(f"/chat/{self.dm().pk}/typing/", **FETCH).status_code, 403)
        cc, _ = self.member("+998977778899", "Cami", "Rustamov")
        self.assertEqual(cc.post(f"/chat/{self.dm().pk}/typing/", **FETCH).status_code, 404)


class ReadMarkerTests(FeatureBase):
    def test_ticks_and_the_new_messages_divider(self):
        room = self.dm()
        m1 = self.say(self.ca, room, "bir")["message"]
        self.assertFalse(m1["read"])
        first_visit = self.cb.get(f"/chat/{room.pk}/").content.decode()
        self.assertNotIn('id="chat-new"', first_visit)  # nothing to divide on the very first visit
        self.assertTrue(self.ca.get(f"/chat/{room.pk}/poll/?after={m1['id']}").json()["read_upto"] >= m1["id"])
        m2 = self.say(self.ca, room, "ikki")["message"]
        html = self.cb.get(f"/chat/{room.pk}/").content.decode()
        self.assertIn('id="chat-new"', html)
        self.assertLess(html.index('id="chat-new"'), html.index(f'data-id="{m2["id"]}"'))
        self.assertGreater(html.index('id="chat-new"'), html.index(f'data-id="{m1["id"]}"'))
        self.assertIn("✓✓", self.ca.get(f"/chat/{room.pk}/").content.decode())  # B has now read both
        self.assertNotIn('id="chat-new"', self.cb.get(f"/chat/{room.pk}/").content.decode())

    def test_group_edges_and_compact_day_chip(self):
        room = self.dm()
        for t in ("bir", "ikki", "uch"):
            self.say(self.ca, room, t)
        html = self.ca.get(f"/chat/{room.pk}/").content.decode()
        self.assertEqual(html.count('class="m-day"'), 1)
        self.assertEqual(html.count(" first\""), 1)  # one run of three bubbles
        self.assertEqual(html.count('m-row mine last"'), 1)  # only the last bubble of the run carries the time


class DayLabelTests(FeatureBase):
    def test_compact_localized_chips(self):
        today = timezone.localdate()
        self.assertEqual(day_label("uz", today), "Bugun")
        self.assertEqual(day_label("uz", today - timedelta(days=1)), "Kecha")
        d = today - timedelta(days=100)
        year = f" {d.year}" if d.year != today.year else ""
        uz = ["yanvar", "fevral", "mart", "aprel", "may", "iyun", "iyul", "avgust", "sentabr", "oktyabr", "noyabr", "dekabr"][d.month - 1]
        self.assertEqual(day_label("uz", d), f"{d.day}-{uz}{year}")
        self.assertTrue(day_label("en", d).endswith(f"{d.day}{year}"))
        self.assertIn(str(d.day), day_label("ru", d))
        self.assertEqual(day_label("uz", date(2020, 10, 28)), "28-oktyabr 2020")


class SearchTests(FeatureBase):
    def test_search_in_a_room(self):
        a = self.say(self.ca, self.general, "Bugun oyoq mashqi qildim")["message"]
        self.say(self.cb, self.general, "Men esa yelka mashqini yaxshi ko'raman")
        gone = self.say(self.cb, self.general, "mashq o'chirilgan")["message"]
        self.cb.post(f"/chat/message/{gone['id']}/delete/", **FETCH)
        res = self.ca.get(f"/chat/{self.general.pk}/search/?q=oyoq").json()["results"]
        self.assertEqual([r["id"] for r in res], [a["id"]])
        self.assertEqual(set(res[0]), {"id", "name", "text", "time", "date", "day"})
        self.assertEqual(len(self.ca.get(f"/chat/{self.general.pk}/search/?q=mashq").json()["results"]), 2)  # deleted ones are not searchable
        self.assertEqual(self.ca.get(f"/chat/{self.general.pk}/search/?q=o").json()["results"], [])  # too short

    def test_search_is_limited_to_conversations_you_are_in(self):
        self.say(self.ca, self.dm(), "maxfiy kod")
        cc, _ = self.member("+998977778899", "Cami", "Rustamov")
        self.assertEqual(cc.get(f"/chat/{self.dm().pk}/search/?q=maxfiy").status_code, 404)
        self.assertEqual(len(self.cb.get(f"/chat/{self.dm().pk}/search/?q=maxfiy").json()["results"]), 1)
        self.assertEqual(self.ca.get(f"/chat/{self.general.pk}/search/?q=maxfiy").json()["results"], [])


class HistoryTests(FeatureBase):
    def test_older_pages_and_jump_target(self):
        ids = [ChatMessage.objects.create(room=self.general, sender=self.a, body=f"m{i}").id for i in range(130)]
        page = self.ca.get(f"/chat/{self.general.pk}/").content.decode()
        self.assertIn(f'data-id="{ids[-1]}"', page)
        self.assertNotIn(f'data-id="{ids[0]}"', page)
        self.assertIn('data-more="1"', page)
        before = ids[-50]
        j = self.ca.get(f"/chat/{self.general.pk}/history/?before={before}").json()
        self.assertEqual([m["id"] for m in j["messages"]], ids[-100:-50])
        self.assertTrue(j["has_more"])
        j = self.ca.get(f"/chat/{self.general.pk}/history/?before={before}&target={ids[3]}").json()  # jump: everything down to the target
        self.assertEqual(j["messages"][0]["id"], ids[3])
        self.assertEqual(j["messages"][-1]["id"], ids[-51])
        j = self.ca.get(f"/chat/{self.general.pk}/history/?before={ids[10]}").json()
        self.assertFalse(j["has_more"])
        cc, _ = self.member("+998977778899", "Cami", "Rustamov")
        self.assertEqual(cc.get(f"/chat/{self.dm().pk}/history/?before=999").status_code, 404)


class PinTests(FeatureBase):
    def pin(self, client, room, mid):
        return self.jpost(client, f"/chat/{room.pk}/pin/", {"id": mid})

    def test_only_staff_in_admin_mode_can_pin(self):
        m = self.say(self.ca, self.general, "Qoidalar: hurmat bilan")["message"]
        self.assertEqual(self.pin(self.ca, self.general, m["id"]).status_code, 404)
        plain = self.admin_client()
        sess = plain.session
        sess["admin_mode"] = False
        sess.save()
        self.assertEqual(self.pin(plain, self.general, m["id"]).status_code, 404)  # staff, but not in admin mode
        staff = self.admin_client()
        r = self.pin(staff, self.general, m["id"]).json()
        self.assertEqual((r["pin"]["id"], r["pin"]["name"]), (m["id"], "Aziz K."))
        page = self.cb.get(f"/chat/{self.general.pk}/").content.decode()
        self.assertIn(f'id="chat-pin" data-id="{m["id"]}"', page)
        self.assertNotIn('id="chat-pin-x"', page)  # members cannot unpin
        self.assertIn('id="chat-pin-x"', staff.get(f"/chat/{self.general.pk}/").content.decode())
        self.assertEqual(self.cb.get(f"/chat/{self.general.pk}/poll/?after=0").json()["pin"]["id"], m["id"])

    def test_one_pin_per_room_unpin_and_delete(self):
        a = self.say(self.ca, self.general, "bir")["message"]
        b = self.say(self.cb, self.general, "ikki")["message"]
        staff = self.admin_client()
        self.pin(staff, self.general, a["id"])
        self.pin(staff, self.general, b["id"])
        self.general.refresh_from_db()
        self.assertEqual(self.general.pinned_message_id, b["id"])
        self.pin(staff, self.general, 0)
        self.general.refresh_from_db()
        self.assertIsNone(self.general.pinned_message_id)
        self.pin(staff, self.general, a["id"])
        self.ca.post(f"/chat/message/{a['id']}/delete/", **FETCH)  # deleting the pinned message unpins it
        self.general.refresh_from_db()
        self.assertIsNone(self.general.pinned_message_id)

    def test_cannot_pin_in_private_chats_or_foreign_messages(self):
        staff = self.admin_client()
        m = self.say(self.ca, self.dm(), "salom")["message"]
        self.assertEqual(self.pin(staff, self.dm(), m["id"]).status_code, 404)
        self.assertEqual(self.pin(staff, self.general, m["id"]).status_code, 404)  # the message is in another room

    def test_broadcast_on_pin(self):
        m = self.say(self.ca, self.general, "salom")["message"]
        with mock.patch("gym.chat_views.announce") as ann:
            self.pin(self.admin_client(), self.general, m["id"])
        ann.assert_called_once_with(self.general.pk, {"type": "chat.pin"})


class MentionTests(FeatureBase):
    def setUp(self):
        super().setUp()
        self.say(self.cb, self.general, "men shu yerdaman")  # people who wrote in the room can be mentioned

    def test_autocomplete_lists_recent_writers_only(self):
        res = self.ca.get(f"/chat/{self.general.pk}/members/?q=be").json()["members"]
        self.assertEqual([m["name"] for m in res], ["Bek Z."])
        self.assertEqual(self.ca.get(f"/chat/{self.general.pk}/members/?q=zzz").json()["members"], [])
        self.assertEqual([m["name"] for m in self.cb.get(f"/chat/{self.general.pk}/members/").json()["members"]], [])  # not myself
        self.assertEqual(self.ca.get(f"/chat/{self.dm().pk}/members/?q=be").json()["members"], [])  # rooms only
        ChatBlock.objects.create(blocker=self.b, blocked=self.a)
        self.assertEqual(self.ca.get(f"/chat/{self.general.pk}/members/?q=be").json()["members"], [])

    def test_mention_notifies_even_when_the_room_is_muted(self):
        RoomMute.objects.create(user=self.b, room=self.general)
        with mock.patch("gym.services.notify") as n:
            m = self.say(self.ca, self.general, "@Bek Z. qalaysan?")["message"]
        self.assertEqual(n.call_count, 1)
        self.assertEqual(n.call_args[0][0], self.b)
        self.assertEqual(m["mentions"], ["Bek Z."])
        self.assertEqual(list(Mention.objects.values_list("user_id", flat=True)), [self.b.pk])
        mine = self.cb.get(f"/chat/{self.general.pk}/poll/?after=0").json()["messages"][-1]
        self.assertTrue(mine["mentioned_me"])
        self.assertContains(self.cb.get(f"/chat/{self.general.pk}/"), '<mark class="m-mention">@Bek Z.</mark>')
        self.assertFalse(self.ca.get(f"/chat/{self.general.pk}/poll/?after=0").json()["messages"][-1]["mentioned_me"])

    def test_no_mention_for_blocked_unknown_or_self_and_none_in_dm(self):
        with mock.patch("gym.services.notify") as n:
            self.say(self.ca, self.general, "@Aziz K. o'zimga, @Nomalum X. va @Bek Zorlov")
            ChatBlock.objects.create(blocker=self.b, blocked=self.a)
            self.say(self.ca, self.general, "@Bek Z. blok")
            ChatBlock.objects.all().delete()
            self.say(self.ca, self.dm(), "@Bek Z. shaxsiy")
        n.assert_not_called()
        self.assertEqual(Mention.objects.count(), 0)

    def test_editing_notifies_only_new_mentions(self):
        with mock.patch("gym.services.notify") as n:
            m = self.say(self.ca, self.general, "@Bek Z. salom")["message"]
            self.jpost(self.ca, f"/chat/message/{m['id']}/edit/", {"body": "@Bek Z. salom, qalaysan"})
        self.assertEqual(n.call_count, 1)
        self.assertEqual(Mention.objects.count(), 1)

    def test_mute_toggle(self):
        r = self.cb.post(f"/chat/{self.general.pk}/mute/", **FETCH).json()
        self.assertEqual(r["muted"], True)
        self.assertContains(self.cb.get(f"/chat/{self.general.pk}/"), 'aria-pressed="true"')
        self.assertEqual(self.cb.post(f"/chat/{self.general.pk}/mute/", **FETCH).json()["muted"], False)
        self.assertFalse(RoomMute.objects.exists())
        cc, _ = self.member("+998977778899", "Cami", "Rustamov")
        self.assertEqual(cc.post(f"/chat/{self.dm().pk}/mute/", **FETCH).status_code, 404)

    def test_private_message_push_respects_mute_presence_and_floods(self):
        User.objects.filter(pk=self.b.pk).update(last_seen=None)
        room = self.dm()
        with mock.patch("gym.pwa.push_user") as push:
            self.say(self.ca, room, "birinchi")
            self.say(self.ca, room, "ikkinchi")  # B still has the first one unread: no second push
        self.assertEqual(push.call_count, 1)
        self.assertEqual(push.call_args[0][0], self.b)
        RoomMute.objects.create(user=self.b, room=room)
        self.cb.get(f"/chat/{room.pk}/poll/?after=0")  # reads everything
        User.objects.filter(pk=self.b.pk).update(last_seen=None)
        with mock.patch("gym.pwa.push_user") as push:
            self.say(self.ca, room, "uchinchi")
        push.assert_not_called()  # muted
        RoomMute.objects.all().delete()
        self.cb.get(f"/chat/{room.pk}/poll/?after=0")
        User.objects.filter(pk=self.b.pk).update(last_seen=timezone.now())
        with mock.patch("gym.pwa.push_user") as push:
            self.say(self.ca, room, "to'rtinchi")
        push.assert_not_called()  # online


class PrivacyMaskTests(FeatureBase):
    def test_masking_rules(self):
        cases = {
            "menga +998 90 123 45 67 ga yoz": "menga +998 ** *** ** 67 ga yoz",
            "raqamim 901234567": "raqamim ** *** ** 67",
            "998901234567": "+998 ** *** ** 67",
            "karta 4111 1111 1111 1111 shu": "karta **** **** **** 1111 shu",
            "4111111111111111": "**** **** **** 1111",
            "pochta test@mail.uz": "pochta t***@***.uz",
            "Bugun 3 marta 12 kg ko'tardim, 10:30 da": "Bugun 3 marta 12 kg ko'tardim, 10:30 da",
            "2025-01-05 va 12.05.2025": "2025-01-05 va 12.05.2025",
        }
        for src, want in cases.items():
            self.assertEqual(chat.mask_private(src)[0], want, src)
        self.assertFalse(chat.mask_private("salom")[1])
        self.assertTrue(chat.luhn_ok("4111111111111111") and not chat.luhn_ok("4111111111111112"))

    def test_public_room_masks_and_tells_the_sender(self):
        r = self.say(self.ca, self.general, "Qo'ng'iroq qiling +998901234567 yoki a.b@mail.com")
        self.assertEqual(r["message"]["body"], "Qo'ng'iroq qiling +998 ** *** ** 67 yoki a***@***.com")
        self.assertIn("shaxsiy", r["notice"])
        self.assertNotIn("901234567", ChatMessage.objects.get(pk=r["message"]["id"]).body)  # never stored
        self.assertNotIn("notice", self.say(self.ca, self.general, "oddiy xabar"))

    def test_direct_messages_are_not_masked(self):
        r = self.say(self.ca, self.dm(), "raqamim +998901234567")
        self.assertEqual(r["message"]["body"], "raqamim +998901234567")
        self.assertNotIn("notice", r)

    def test_masking_without_javascript_flashes_a_notice(self):
        r = self.ca.post(f"/chat/{self.general.pk}/send/", {"body": "901234567"}, follow=True)
        self.assertContains(r, "** *** ** 67")


class PayloadShapeTests(FeatureBase):
    KEYS = {"id", "mine", "sender", "name", "initials", "hue", "body", "deleted", "image", "ts", "time", "date", "day", "read", "can_delete",
            "can_report", "can_edit", "edited", "reply", "reactions", "mentions", "mentioned_me"}

    def test_message_shape_is_stable(self):
        m = self.say(self.ca, self.dm(), "salom")["message"]
        self.assertEqual(set(m), self.KEYS)
        poll = self.cb.get(f"/chat/{self.dm().pk}/poll/?after=0&since=1").json()
        self.assertEqual(set(poll["messages"][0]), self.KEYS)
        self.assertTrue({"messages", "last_id", "read_upto", "now", "presence", "deleted", "pin", "typing", "stats", "edited", "rxh"} <= set(poll))
        room_poll = self.ca.get(f"/chat/{self.general.pk}/poll/?after=0").json()
        self.assertEqual(set(room_poll["stats"]), {"members", "online"})
        self.assertIsNone(poll["stats"])

    def test_room_header_counts_members_and_online(self):
        stats = chat.room_stats(self.general)
        self.assertGreaterEqual(stats["members"], 2)
        self.assertGreaterEqual(stats["online"], 0)
        page = self.ca.get(f"/chat/{self.general.pk}/").content.decode()
        self.assertIn(f"{stats['members']} a&#x27;zo", page)

    def test_n_plus_one_is_avoided(self):
        for i in range(20):
            m = ChatMessage.objects.create(room=self.general, sender=self.a, body=f"xabar {i}")
            MessageReaction.objects.create(message=m, user=self.b, emoji="👍")
        from django.db import connection
        from django.test.utils import CaptureQueriesContext
        with CaptureQueriesContext(connection) as q:
            self.cb.get(f"/chat/{self.general.pk}/poll/?after=0")
        self.assertLess(len(q), 40)

    def test_page_markup_is_accessible(self):
        html = self.ca.get(f"/chat/{self.general.pk}/").content.decode()
        for needle in ('role="log"', 'aria-live="polite"', 'id="chat-fab"', 'aria-haspopup', 'id="chat-search"', 'id="chat-suggest"', 'role="listbox"'):
            self.assertIn(needle, html)
        self.assertNotIn("⚑", html)
        self.assertNotIn("LIVE", html)
        js = (__import__("pathlib").Path(__file__).parent / "static/js/chat.js").read_text(encoding="utf-8")
        self.assertIn("role', 'menu'", js)
        self.assertIn("ArrowDown", js)


class SocketEventTests(FeatureBase):
    def test_reaction_edit_and_pin_events(self):
        async def run():
            sa, sb = Sock(self.a, self.general), Sock(self.b, self.general)
            self.assertTrue((await sa.connect())[0])
            self.assertTrue((await sb.connect())[0])
            post = lambda c, url, data: sync_to_async(c.post)(url, json.dumps(data), content_type="application/json", **FETCH)
            r = await sync_to_async(self.cb.post)(f"/chat/{self.general.pk}/send/", {"body": "salom"}, **FETCH)
            mid = r.json()["message"]["id"]
            self.assertEqual((await sa.receive_json_from())["t"], "msg")
            self.assertEqual((await sb.receive_json_from())["t"], "msg")
            await post(self.ca, f"/chat/message/{mid}/react/", {"emoji": "🔥"})
            self.assertEqual(await sa.receive_json_from(), {"t": "reaction", "id": mid, "reactions": [{"e": "🔥", "n": 1, "mine": True}]})
            self.assertEqual(await sb.receive_json_from(), {"t": "reaction", "id": mid, "reactions": [{"e": "🔥", "n": 1, "mine": False}]})  # "mine" per reader
            await post(self.cb, f"/chat/message/{mid}/edit/", {"body": "salom hammaga"})
            got = await sa.receive_json_from()
            self.assertEqual((got["t"], got["m"]["body"], got["m"]["edited"], got["m"]["mine"]), ("edit", "salom hammaga", True, False))
            await sb.receive_json_from()
            staff = await sync_to_async(self.admin_client)()
            await post(staff, f"/chat/{self.general.pk}/pin/", {"id": mid})
            got = await sa.receive_json_from()
            self.assertEqual((got["t"], got["pin"]["id"]), ("pin", mid))
            await sa.disconnect()
            await sb.disconnect()
        async_to_sync(run)()

    def test_typing_over_the_socket_is_visible_to_pollers(self):
        async def run():
            sb = Sock(self.b, self.general)
            self.assertTrue((await sb.connect())[0])
            await sb.send_json_to({"t": "typing"})
            await sb.disconnect()
        async_to_sync(run)()
        self.assertEqual(self.ca.get(f"/chat/{self.general.pk}/poll/?after=0").json()["typing"], ["Bek Z."])
