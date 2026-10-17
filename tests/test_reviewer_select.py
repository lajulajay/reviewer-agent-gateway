#!/usr/bin/env python3
import importlib.util
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TODAY = date(2026, 10, 16)
_spec = importlib.util.spec_from_file_location("reviewer_select", ROOT / "reviewer-select.py")
selector = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(selector)


class ReviewerSelectTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.collab = self.base / "repo" / ".collab"
        self.collab.mkdir(parents=True)
        self.roster = self.base / "roster.json"
        self.write_roster()

    def tearDown(self):
        self.tmp.cleanup()

    def write_roster(self, active=("kimi", "claude", "codex"), order=("kimi", "claude", "codex")):
        self.roster.write_text(json.dumps({"active_reviewers": list(active), "tie_break_order": list(order)}))

    def output(self, name="auto-2026-10-16-new.md"):
        return self.collab / name

    def select(self, owner="codex", name="auto-2026-10-16-new.md"):
        return selector.order(self.roster, owner, self.output(name), today=TODAY)

    def artifact(self, name):
        (self.collab / name).write_text("")

    def diagnostic(self, name, reason="Kimi invocation timed out"):
        (self.collab / name).write_text(json.dumps({"exit_code": 70, "reason": reason}))

    def test_owner_is_excluded_and_kimi_cannot_own(self):
        self.assertEqual(self.select("codex"), ["kimi", "claude"])
        self.assertEqual(self.select("claude"), ["kimi", "codex"])
        for owner in ("kimi", "gemini", ""):
            with self.subTest(owner=owner), self.assertRaisesRegex(ValueError, "owner must be codex or claude"):
                self.select(owner)

    def test_gemini_is_never_in_the_subscription_rotation(self):
        self.write_roster(active=("kimi", "claude", "codex", "gemini"))
        with self.assertRaisesRegex(ValueError, "Gemini is fallback-only"):
            self.select()
        self.write_roster(order=("kimi", "claude", "gemini"))
        with self.assertRaisesRegex(ValueError, "must contain claude, codex, and kimi"):
            self.select()

    def test_inactive_subscriptions_and_empty_eligible_set(self):
        self.write_roster(active=("claude", "codex"))
        self.assertEqual(self.select("codex"), ["claude"])
        self.write_roster(active=("kimi",))
        self.assertEqual(self.select("codex"), ["kimi"])
        self.write_roster(active=("claude",))
        with self.assertRaisesRegex(ValueError, "use gemini-review.sh"):
            self.select("claude")

    def test_spent_rounds_balance_load_and_roster_breaks_ties(self):
        self.assertEqual(self.select(), ["kimi", "claude"])
        self.diagnostic("kimi-2026-10-16-spent-r01.diagnostic.json")
        self.assertEqual(self.select(), ["claude", "kimi"])
        self.artifact("claude-2026-10-16-spent-r01.md")
        self.artifact("kimi-2026-10-15-older-r01.md")
        self.assertEqual(self.select(), ["kimi", "claude"])

    def test_followup_stays_with_latest_eligible_reviewer(self):
        self.artifact("claude-2026-10-16-topic-r01.md")
        self.artifact("kimi-2026-10-16-topic-r02.md")
        self.artifact("kimi-2026-10-16-other-r01.md")
        self.assertEqual(self.select(name="auto-2026-10-16-topic-r03.md"), ["kimi", "claude"])
        self.artifact("claude-2026-10-16-topic-r03.md")
        self.assertEqual(self.select(name="auto-2026-10-16-topic-r04.md"), ["claude", "kimi"])

    def test_followup_ignores_latest_reviewer_when_no_longer_eligible(self):
        self.artifact("claude-2026-10-16-topic-r01.md")
        self.artifact("kimi-2026-10-16-topic-r02.md")
        self.write_roster(active=("claude", "codex"))
        self.assertEqual(self.select("codex", "auto-2026-10-16-topic-r03.md"), ["claude"])

    def test_ineligible_latest_reviewer_does_not_restore_older_reviewer(self):
        self.artifact("claude-2026-10-16-topic-r01.md")
        self.artifact("codex-2026-10-16-topic-r02.md")
        self.assertEqual(self.select("codex", "auto-2026-10-16-topic-r03.md"), ["kimi", "claude"])

    def test_capped_latest_reviewer_uses_daily_balancing(self):
        self.artifact("claude-2026-10-16-topic-r01.md")
        self.artifact("kimi-2026-10-16-topic-r02.md")
        for i in range(7):
            self.artifact(f"kimi-2026-10-16-capped-{i:02d}.md")
        self.assertEqual(self.select("codex", "auto-2026-10-16-topic-r03.md"), ["claude"])

    def test_daily_cap_excludes_provider_from_new_and_followup_selection(self):
        for i in range(1, 9):
            self.artifact(f"kimi-2026-10-16-capped-{i:02d}.md")
        self.assertEqual(self.select(name="auto-2026-10-16-after-cap.md"), ["claude"])
        for i in range(1, 9):
            self.artifact(f"kimi-2026-10-16-follow-r{i:02d}.md")
        self.assertEqual(self.select(name="auto-2026-10-16-follow-r09.md"), ["claude"])

    def test_owner_change_excludes_latest_reviewer_and_rebalances(self):
        self.artifact("codex-2026-10-16-topic-r01.md")
        self.artifact("claude-2026-10-16-topic-r02.md")
        self.artifact("codex-2026-10-16-other-r01.md")
        self.assertEqual(self.select("claude", "auto-2026-10-16-topic-r03.md"), ["kimi", "codex"])

    def test_ambiguous_latest_round_falls_back_to_balancing(self):
        self.artifact("kimi-2026-10-16-topic-r02.md")
        self.artifact("claude-2026-10-16-topic-r02.md")
        self.artifact("kimi-2026-10-16-other-r01.md")
        self.assertEqual(self.select(name="auto-2026-10-16-topic-r03.md"), ["claude", "kimi"])

    def test_mixed_numbered_and_unnumbered_history_is_ambiguous(self):
        self.artifact("claude-2026-10-16-topic-r01.md")
        self.artifact("kimi-2026-10-16-topic.md")
        self.artifact("claude-2026-10-16-other-r01.md")
        # Claude has more spent rounds, so balancing (not topic continuity) must win.
        self.assertEqual(self.select(name="auto-2026-10-16-topic-r02.md"), ["kimi", "claude"])

    def test_failed_spent_diagnostic_can_continue_topic(self):
        self.artifact("claude-2026-10-16-failed-r01.md")
        self.diagnostic("kimi-2026-10-16-failed-r02.diagnostic.json")
        self.assertEqual(self.select(name="auto-2026-10-16-failed-r03.md"), ["kimi", "claude"])

    def test_malformed_rosters_fail_closed(self):
        cases = (
            ("{", json.JSONDecodeError),
            (json.dumps({"active_reviewers": "kimi", "tie_break_order": ["kimi", "claude", "codex"]}), ValueError),
            (json.dumps({"active_reviewers": ["kimi", "kimi"], "tie_break_order": ["kimi", "claude", "codex"]}), ValueError),
            (json.dumps({"active_reviewers": ["kimi"], "tie_break_order": ["kimi", "claude"]}), ValueError),
        )
        for text, error in cases:
            with self.subTest(text=text):
                self.roster.write_text(text)
                with self.assertRaises(error):
                    self.select()

    def test_cli_reports_malformed_roster_as_preflight_failure(self):
        self.roster.write_text("{}")
        result = subprocess.run(
            ["python3", str(ROOT / "reviewer-select.py"), str(self.roster), "codex", str(self.output())],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 78)
        self.assertIn("reviewer selection error", result.stderr)


MOCK_PROVIDER = r"""#!/bin/zsh
set -euo pipefail
provider="${0:t}"; provider="${provider%-review.sh}"
while [[ "${1:-}" == --* ]]; do
  case "$1" in
    --owner|--packet-root) shift 2 ;;
    *) exit 64 ;;
  esac
done
tier="$1"; output="$3"
print -r -- "$provider|$tier|${output:t}" >> "$AUTO_MOCK_LOG"
case "$provider" in
  kimi) code="${AUTO_MOCK_KIMI_CODE:-0}" ;;
  claude) code="${AUTO_MOCK_CLAUDE_CODE:-0}" ;;
  codex) code="${AUTO_MOCK_CODEX_CODE:-0}" ;;
esac
if [[ "$code" -ne 0 ]]; then
  jq -n --arg provider "$provider" --argjson code "$code" --arg reason "simulated provider returned nonzero after model invocation began" \
    '{provider:$provider,exit_code:$code,reason:$reason}' > "${output%.md}.diagnostic.json"
  exit "$code"
fi
print 'mock review' > "$output"
"""


class AutoReviewTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.gateway = self.base / "gateway"
        self.gateway.mkdir()
        for name in ("auto-review.sh", "reviewer-select.py", "review-budget.py", "review-budget.json", "reviewer-roster.json"):
            shutil.copy2(ROOT / name, self.gateway / name)
        provider = self.gateway / "provider-mock.sh"
        provider.write_text(MOCK_PROVIDER)
        provider.chmod(0o755)
        for name in ("kimi", "claude", "codex"):
            os.link(provider, self.gateway / f"{name}-review.sh")
        self.repo = self.base / "repo"
        self.collab = self.repo / ".collab"
        self.collab.mkdir(parents=True)
        (self.repo / "prompt.md").write_text("Review prompt.\n")
        (self.repo / "packet.md").write_text("Safe packet.\n")
        self.log = self.base / "calls.log"
        self.log.write_text("")
        self.git("init", "-q")
        self.git("add", "-A")
        self.git("-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", "snapshot")

    def tearDown(self):
        self.tmp.cleanup()

    def git(self, *args):
        subprocess.run(["git", "-C", str(self.gateway), *args], check=True, capture_output=True)

    def run_auto(self, *extra_env, tier="routine", owner="codex", name="auto-2026-10-16-topic.md", roster=None):
        env = os.environ.copy()
        env["AUTO_MOCK_LOG"] = str(self.log)
        for key in ("AUTO_MOCK_KIMI_CODE", "AUTO_MOCK_CLAUDE_CODE", "AUTO_MOCK_CODEX_CODE", "REVIEWER_ROSTER"):
            env.pop(key, None)
        for assignment in extra_env:
            key, value = assignment.split("=", 1)
            env[key] = value
        if roster is not None:
            path = self.base / "custom-roster.json"
            path.write_text(json.dumps(roster))
            env["REVIEWER_ROSTER"] = str(path)
        output = self.collab / name
        result = subprocess.run(
            [str(self.gateway / "auto-review.sh"), "--owner", owner, tier,
             str(self.repo / "prompt.md"), str(output), str(self.repo / "packet.md")],
            capture_output=True,
            text=True,
            env=env,
        )
        return result

    def calls(self):
        return self.log.read_text().splitlines()

    def test_auto_uses_first_eligible_reviewer_and_provider_artifact(self):
        result = self.run_auto()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.calls(), ["kimi|routine|kimi-2026-10-16-topic.md"])
        self.assertTrue((self.collab / "kimi-2026-10-16-topic.md").is_file())
        self.assertFalse((self.collab / "auto-2026-10-16-topic.md").exists())

    def test_preflight_failure_fails_over_and_maps_claude_hard_tier(self):
        result = self.run_auto("AUTO_MOCK_KIMI_CODE=69", tier="hard")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.calls(), [
            "kimi|hard|kimi-2026-10-16-topic.md",
            "claude|opus|claude-2026-10-16-topic.md",
        ])
        self.assertIn("trying the next eligible reviewer", result.stderr)

    def test_claude_routine_tier_maps_to_sonnet(self):
        roster = {"active_reviewers": ["claude"], "tie_break_order": ["kimi", "claude", "codex"]}
        result = self.run_auto(roster=roster)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.calls(), ["claude|sonnet|claude-2026-10-16-topic.md"])

    def test_model_failure_and_budget_refusal_are_not_retried(self):
        for code in (70, 79):
            with self.subTest(code=code):
                self.log.write_text("")
                result = self.run_auto(f"AUTO_MOCK_KIMI_CODE={code}", name=f"auto-2026-10-16-topic-{code}.md")
                self.assertEqual(result.returncode, code)
                self.assertEqual(self.calls(), [f"kimi|routine|kimi-2026-10-16-topic-{code}.md"])
                self.assertNotIn("trying the next eligible reviewer", result.stderr)

    def test_existing_candidate_diagnostic_is_not_retried(self):
        name = "auto-2026-10-16-attempt-once.md"
        result = self.run_auto("AUTO_MOCK_KIMI_CODE=70", name=name)
        self.assertEqual(result.returncode, 70)
        self.assertEqual(self.calls(), ["kimi|routine|kimi-2026-10-16-attempt-once.md"])
        result = self.run_auto(name=name)
        self.assertEqual(result.returncode, 65)
        self.assertEqual(self.calls(), ["kimi|routine|kimi-2026-10-16-attempt-once.md"])
        self.assertIn("reserved by", result.stderr)

    def test_all_preflight_failures_end_with_gemini_fallback_instruction(self):
        result = self.run_auto("AUTO_MOCK_KIMI_CODE=69", "AUTO_MOCK_CLAUDE_CODE=78")
        self.assertEqual(result.returncode, 78)
        self.assertEqual(self.calls(), [
            "kimi|routine|kimi-2026-10-16-topic.md",
            "claude|sonnet|claude-2026-10-16-topic.md",
        ])
        self.assertIn("use gemini-review.sh as the fallback reviewer", result.stderr)


if __name__ == "__main__":
    unittest.main()
