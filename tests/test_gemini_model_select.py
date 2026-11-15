import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("gemini_model_select", ROOT / "gemini-model-select.py")
selector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(selector)

ROWS = [
    {"id": "gemini-3.8-flash-high", "released_on": "2026-09-02", "included_no_credits": True},
    {"id": "gemini-3.7-flash-high", "released_on": "2026-08-13", "included_no_credits": False},
    {"id": "gemini-3.6-flash-high", "released_on": "2026-07-21", "included_no_credits": False},
]


class GeminiModelSelectTests(unittest.TestCase):
    def select(self, requested, **extra):
        policy = {
            "hard_model": "gemini-3.8-flash-high",
            "routine_two_releases_down_scope": "all_models",
            "models_newest_first": ROWS,
            **extra,
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "policy.json"
            path.write_text(json.dumps(policy))
            return selector.select(path, requested)

    def test_checked_in_policy_selects_available_models(self):
        policy = ROOT / "gemini-model-policy.json"
        self.assertEqual(selector.select(policy, "hard"), "gemini-3.8-flash-high")
        self.assertEqual(selector.select(policy, "routine"), "gemini-3.8-flash-medium")

    def test_routine_without_fallback_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "fewer than two older"):
            self.select("routine")

    def test_fallback_used_only_when_older_releases_are_missing(self):
        self.assertEqual(self.select("routine", routine_fallback_model="gemini-3.8-flash-low"), "gemini-3.8-flash-low")
        rows = [dict(row, included_no_credits=True) for row in ROWS]
        self.assertEqual(
            self.select("routine", routine_fallback_model="gemini-3.8-flash-low", models_newest_first=rows),
            "gemini-3.6-flash-high",
        )

    def test_fallback_must_be_hard_release_at_another_effort(self):
        for bad in ("gemini-3.7-flash-medium", "gemini-3.8-pro-medium", "gemini-3.8-flash-high", "gemini-3.8-flash-ultra", 7):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    self.select("hard", routine_fallback_model=bad)

    def test_fallback_can_be_named_and_unlisted_models_cannot(self):
        self.assertEqual(self.select("gemini-3.8-flash-medium", routine_fallback_model="gemini-3.8-flash-medium"), "gemini-3.8-flash-medium")
        with self.assertRaises(ValueError):
            self.select("gemini-3.8-flash-medium")
        with self.assertRaises(ValueError):
            self.select("gemini-3.6-flash-high", routine_fallback_model="gemini-3.8-flash-medium")


if __name__ == "__main__":
    unittest.main()
