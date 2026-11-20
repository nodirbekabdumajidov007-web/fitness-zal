from unittest import mock

from django.test import Client, TestCase, override_settings

from . import llm


class LlmProvidersTests(TestCase):
    def test_gemini_first_then_claude(self):
        with self.settings(GEMINI_API_KEY="g", ANTHROPIC_API_KEY="a"):
            with mock.patch("gym.llm._gemini", return_value="G javob"), mock.patch("gym.llm._claude", return_value="C javob") as c:
                self.assertEqual(llm.ask("salom"), "G javob")
                c.assert_not_called()
            with mock.patch("gym.llm._gemini", return_value=""), mock.patch("gym.llm._claude", return_value="C javob"):
                self.assertEqual(llm.ask("salom"), "C javob")
        with self.settings(GEMINI_API_KEY="", ANTHROPIC_API_KEY=""):
            self.assertFalse(llm.enabled())
            self.assertIsNone(llm.ask("salom"))

    def test_gemini_request_shape_with_photo(self):
        img = llm.image_part(b"\x89PNG\r\n\x1a\n" + b"0" * 20, "image/png")
        seen = {}

        def fake(url, body, headers, timeout):
            seen.update(url=url, body=body, headers=headers)
            return {"candidates": [{"content": {"parts": [{"text": "Bu osh"}]}}]}

        with self.settings(GEMINI_API_KEY="g", ANTHROPIC_API_KEY=""), mock.patch("gym.llm._post", side_effect=fake):
            out = llm.ask("bu nima", "uz", "Phone: 1", [("user", "a"), ("assistant", "b")], img)
        self.assertEqual(out, "Bu osh")
        self.assertEqual(seen["headers"], {"x-goog-api-key": "g"})
        self.assertIn("generateContent", seen["url"])
        parts = seen["body"]["contents"][-1]["parts"]
        self.assertEqual(parts[1]["inlineData"]["mimeType"], "image/png")
        self.assertEqual(seen["body"]["contents"][1]["role"], "model")

    def test_a_failing_provider_falls_through(self):
        with self.settings(GEMINI_API_KEY="g", ANTHROPIC_API_KEY="a"):
            with mock.patch("gym.llm._gemini", side_effect=OSError("down")), mock.patch("gym.llm._claude", return_value="C javob"):
                self.assertEqual(llm.ask("salom"), "C javob")

    def test_busy_provider_is_retried_once(self):
        import io
        import urllib.error
        calls = []

        def flaky(*a):
            calls.append(1)
            if len(calls) == 1:
                raise urllib.error.HTTPError("u", 503, "busy", {}, io.BytesIO(b"high demand"))
            return "Salom"

        with self.settings(GEMINI_API_KEY="g", ANTHROPIC_API_KEY=""), mock.patch("gym.llm._gemini", side_effect=flaky), mock.patch("gym.llm.time.sleep"):
            self.assertEqual(llm.ask("salom"), "Salom")
        self.assertEqual(len(calls), 2)

    def test_auth_errors_are_not_retried(self):
        import io
        import urllib.error
        calls = []

        def bad(*a):
            calls.append(1)
            raise urllib.error.HTTPError("u", 403, "no", {}, io.BytesIO(b"key"))

        with self.settings(GEMINI_API_KEY="g", ANTHROPIC_API_KEY=""), mock.patch("gym.llm._gemini", side_effect=bad):
            self.assertIsNone(llm.ask("salom"))
        self.assertEqual(len(calls), 1)

    def test_openai_compatible_provider_request_and_order(self):
        img = llm.image_part(b"\x89PNG\r\n\x1a\n" + b"0" * 20, "image/png")
        seen = {}

        def fake(url, body, headers, timeout):
            seen.update(url=url, body=body, headers=headers)
            return {"choices": [{"message": {"content": "Bu osh"}}]}

        cfg = dict(GEMINI_API_KEY="", ANTHROPIC_API_KEY="", LLM_BASE_URL="https://api.example.com/openai/v1/", LLM_API_KEY="k", LLM_MODEL="m1")
        with self.settings(**cfg), mock.patch("gym.llm._post", side_effect=fake):
            self.assertTrue(llm.enabled())
            self.assertEqual(llm.ask("bu nima", "uz", "", [("user", "a"), ("assistant", "b")], img), "Bu osh")
        self.assertEqual(seen["url"], "https://api.example.com/openai/v1/chat/completions")
        self.assertEqual(seen["headers"]["authorization"], "Bearer k")
        self.assertEqual(seen["body"]["model"], "m1")
        self.assertEqual(seen["body"]["messages"][0]["role"], "system")
        self.assertEqual(seen["body"]["messages"][-1]["content"][1]["type"], "image_url")
        # Gemini first, then this service, then Claude
        with self.settings(GEMINI_API_KEY="g", ANTHROPIC_API_KEY="a", LLM_BASE_URL="https://x/v1", LLM_API_KEY="k", LLM_MODEL="m"):
            with mock.patch("gym.llm._gemini", return_value=""), mock.patch("gym.llm._compat", return_value="C1") as c, mock.patch("gym.llm._claude", return_value="C2"):
                self.assertEqual(llm.ask("salom"), "C1")
                c.assert_called_once()

    def test_incomplete_openai_settings_are_ignored(self):
        with self.settings(GEMINI_API_KEY="", ANTHROPIC_API_KEY="", LLM_BASE_URL="", LLM_API_KEY="k", LLM_MODEL="m"):
            self.assertFalse(llm.enabled())
            self.assertIsNone(llm.ask("salom"))

    def test_mistral_gets_image_url_as_a_string(self):
        img = llm.image_part(b"\x89PNG\r\n\x1a\n" + b"0" * 20, "image/png")
        seen = {}

        def fake(url, body, headers, timeout):
            seen["body"] = body
            return {"choices": [{"message": {"content": "ok"}}]}

        with self.settings(GEMINI_API_KEY="", ANTHROPIC_API_KEY="", LLM_BASE_URL="https://api.mistral.ai/v1", LLM_API_KEY="k", LLM_MODEL="m"), \
                mock.patch("gym.llm._post", side_effect=fake):
            llm.ask("bu nima", "uz", "", (), img)
        self.assertIsInstance(seen["body"]["messages"][-1]["content"][1]["image_url"], str)

    def test_quota_exhausted_provider_is_not_retried_and_is_skipped_for_a_while(self):
        import io
        import urllib.error
        from django.core.cache import cache
        cache.clear()
        calls = []

        def quota(*a):
            calls.append(1)
            raise urllib.error.HTTPError("u", 429, "quota", {}, io.BytesIO(b"quota exceeded"))

        with self.settings(GEMINI_API_KEY="g", ANTHROPIC_API_KEY="a"), mock.patch("gym.llm._gemini", side_effect=quota), \
                mock.patch("gym.llm._claude", return_value="C javob"):
            self.assertEqual(llm.ask("salom"), "C javob")
            self.assertEqual(llm.ask("yana"), "C javob")
        self.assertEqual(len(calls), 1)  # one try, then Gemini is skipped
        cache.clear()


class MealMarkerTests(TestCase):
    def test_marker_is_parsed_and_removed(self):
        text = "Bu osh, taxminan 600 kkal.\n[[meal|Osh|620|22|24|75|300]]"
        clean, meal = llm.split_meal(text)
        self.assertEqual(clean, "Bu osh, taxminan 600 kkal.")
        self.assertEqual(meal, {"name": "Osh", "kcal": 620, "p": 22.0, "f": 24.0, "c": 75.0, "grams": 300})

    def test_absurd_or_broken_markers_give_no_meal_but_are_still_hidden(self):
        for bad in ("[[meal|Osh|999999|1|1|1|300]]", "[[meal|Osh|500|1|1|1|0]]", "[[meal|Osh|abc]]", "[[meal|Osh|500"):
            clean, meal = llm.split_meal("Javob " + bad)
            self.assertIsNone(meal, bad)
            self.assertNotIn("[[", clean)
        self.assertEqual(llm.split_meal("Oddiy javob"), ("Oddiy javob", None))

    def test_view_returns_the_meal_and_a_clean_answer(self):
        from django.core.cache import cache
        from django.urls import reverse
        from .models import User
        cache.clear()
        u = User.objects.create_user(username="mealu", password="x")
        c = Client()
        c.force_login(u)
        with self.settings(GEMINI_API_KEY="g"), mock.patch("gym.llm.ask", return_value="Lag'mon.\n[[meal|Lag'mon|480|20|16|60|350]]"):
            r = c.post(reverse("ai_ask"), {"q": "zzqx vbnmk ttyrq wwpl"}, HTTP_X_REQUESTED_WITH="fetch").json()
        self.assertEqual(r["answer"], "Lag'mon.")
        self.assertEqual(r["meal"]["kcal"], 480)

    def test_facts_include_classes_and_trainers(self):
        from django.core.cache import cache
        from .models import GymClass, Trainer
        from .views import llm_facts
        cache.clear()
        t = Trainer.objects.create(name="Jasur Test", specialty="Kuch", experience_years=5)
        GymClass.objects.create(name="Funksional", trainer=t, weekday=1, start_time="18:30")
        f = llm_facts()
        self.assertIn("Funksional", f)
        self.assertIn("Jasur Test", f)
        cache.clear()


class SecondServiceTests(TestCase):
    def test_second_openai_compatible_service_is_a_fallback(self):
        from django.core.cache import cache
        cache.clear()
        calls = []

        def post(url, body, headers, timeout):
            calls.append(url)
            if "first" in url:
                raise OSError("down")
            return {"choices": [{"message": {"content": "Ikkinchidan"}}]}

        cfg = dict(GEMINI_API_KEY="", ANTHROPIC_API_KEY="", LLM_BASE_URL="https://first.example/v1", LLM_API_KEY="k1", LLM_MODEL="m1",
                   LLM2_BASE_URL="https://second.example/v1", LLM2_API_KEY="k2", LLM2_MODEL="m2")
        with self.settings(**cfg), mock.patch("gym.llm._post", side_effect=post):
            self.assertTrue(llm.enabled())
            self.assertEqual(llm.ask("salom"), "Ikkinchidan")
        self.assertEqual(calls[0], "https://first.example/v1/chat/completions")
        self.assertEqual(calls[-1], "https://second.example/v1/chat/completions")

    def test_only_the_second_service_configured(self):
        with self.settings(GEMINI_API_KEY="", ANTHROPIC_API_KEY="", LLM_BASE_URL="", LLM_API_KEY="", LLM_MODEL="",
                           LLM2_BASE_URL="https://s.example/v1", LLM2_API_KEY="k", LLM2_MODEL="m"), \
                mock.patch("gym.llm._post", return_value={"choices": [{"message": {"content": "Bor"}}]}):
            self.assertEqual(llm.ask("salom"), "Bor")


class ExtraSlotsTests(TestCase):
    def test_third_and_fourth_services_are_used_in_order(self):
        from unittest import mock
        from django.core.cache import cache
        from . import llm
        cache.clear()
        cfg = dict(GEMINI_API_KEY="", ANTHROPIC_API_KEY="", LLM_API_KEY="", LLM2_API_KEY="",
                   LLM3_BASE_URL="https://a.test/v1", LLM3_API_KEY="k3", LLM3_MODEL="m3",
                   LLM4_BASE_URL="https://b.test/v1", LLM4_API_KEY="k4", LLM4_MODEL="m4")
        with override_settings(**cfg):
            self.assertTrue(llm.enabled())
            seen = []

            def fake(url, body, headers, timeout):
                seen.append(url)
                if "a.test" in url:
                    raise OSError("down")
                return {"choices": [{"message": {"content": "salom"}}]}
            with mock.patch.object(llm, "_post", fake):
                self.assertEqual(llm.ask("hi"), "salom")
        self.assertTrue(seen[0].startswith("https://a.test") and seen[-1].startswith("https://b.test"))
