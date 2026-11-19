from unittest import mock

from django.test import TestCase

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
