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
