import copy
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("copilot_model_select", ROOT / "copilot-model-select.py")
selector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(selector)
agents = selector.agents
POLICY = json.loads((ROOT / "copilot-model-policy.json").read_text())


class CopilotModelSelectTests(unittest.TestCase):
    def setUp(self):
        self.reg = agents.load()

    def select(self, tier, policy=POLICY, **kw):
        return selector.select(policy, tier, self.reg, **kw)

    def test_shipped_policy_maps_every_model_to_its_own_vendor(self):
        for tier, spec_ in POLICY["tiers"].items():
            self.assertEqual(sorted(spec_["vendor_order"]), sorted(spec_["models"]), tier)
            for vendor, model in spec_["models"].items():
                with self.subTest(tier=tier, model=model):
                    self.assertEqual(agents.model_vendor(self.reg, model), vendor)

    def test_first_allowed_vendor_in_order(self):
        self.assertEqual(self.select("hard", owner="codex")[:2], ("claude-sonnet-5.5", "anthropic"))
        self.assertEqual(self.select("hard", owner="claude")[:2], ("gpt-6.1-terra", "openai"))
        self.assertEqual(self.select("routine", owner="claude")[:2], ("gpt-6-luna", "openai"))

    def test_copilot_owned_work_skips_every_author_model_vendor(self):
        model, vendor, _ = self.select("hard", owner="copilot",
                                       author_models=["claude-sonnet-5.5", "gpt-6.1-terra"])
        self.assertEqual((model, vendor), ("gemini-4-hydrogen", "google"))

    def test_forced_vendor_is_checked(self):
        self.assertEqual(self.select("routine", vendor="xai", owner="claude")[0], "grok-4.6")
        with self.assertRaises(agents.IdentityError):
            self.select("hard", vendor="anthropic", owner="claude")
        with self.assertRaises(agents.IdentityError):
            self.select("hard", vendor="nobody", owner="claude")

    def test_copilot_owned_work_without_author_models_is_refused(self):
        with self.assertRaises(agents.IdentityError):
            self.select("hard", owner="copilot")

    def test_policy_errors(self):
        bad = copy.deepcopy(POLICY)
        bad["tiers"]["hard"]["models"]["anthropic"] = "gpt-6.1-terra"
        with self.assertRaises(ValueError):
            self.select("hard", policy=bad, owner="codex")
        bad = copy.deepcopy(POLICY)
        for credits in (0, 29, 30.0, True):
            bad["tiers"]["hard"]["max_ai_credits"] = credits
            with self.subTest(credits=credits), self.assertRaises(ValueError):
                self.select("hard", policy=bad, owner="codex")
        with self.assertRaises(ValueError):
            self.select("medium", owner="codex")

    def run_main(self, *argv, policy=POLICY):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "policy.json"
            path.write_text(json.dumps(policy))
            out, err = io.StringIO(), io.StringIO()
            with mock.patch("sys.stdout", out), mock.patch("sys.stderr", err):
                code = selector.main(["copilot-model-select.py", str(path), *argv])
            return code, out.getvalue().strip()

    def test_cli(self):
        hard = POLICY["tiers"]["hard"]["max_ai_credits"]
        self.assertEqual(self.run_main("hard", "--owner", "claude"), (0, f"gpt-6.1-terra openai {hard}"))
        self.assertEqual(self.run_main("hard", "--owner", "copilot")[0], 64)
        self.assertEqual(self.run_main("hard", "--bogus", "x")[0], 64)
        self.assertEqual(self.run_main("hard", "--owner")[0], 64)
        bad = copy.deepcopy(POLICY)
        bad["tiers"]["hard"]["models"]["openai"] = "claude-haiku-5.5"
        self.assertEqual(self.run_main("hard", "--owner", "claude", policy=bad)[0], 78)


if __name__ == "__main__":
    unittest.main()
