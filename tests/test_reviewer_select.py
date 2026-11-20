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

    def select(self, owner="codex", name="auto-2026-10-16-new.md", authors=()):
        return selector.order(self.roster, owner, self.output(name), today=TODAY, authors=authors)

    def artifact(self, name):
        (self.collab / name).write_text("")

    def diagnostic(self, name, reason="Kimi invocation timed out"):
        (self.collab / name).write_text(json.dumps({"exit_code": 70, "reason": reason}))

    def test_owner_is_excluded_and_kimi_cannot_own(self):
        self.assertEqual(self.select("codex"), ["kimi", "claude"])
        self.assertEqual(self.select("claude"), ["kimi", "codex"])
        for owner in ("kimi", "gemini", ""):
            with self.subTest(owner=owner), self.assertRaisesRegex(ValueError, "owner must be one of claude, codex, copilot"):
                self.select(owner)

    def test_gemini_is_never_in_the_subscription_rotation(self):
        self.write_roster(active=("kimi", "claude", "codex", "gemini"))
        with self.assertRaisesRegex(ValueError, "Gemini is fallback-only"):
            self.select()
        self.write_roster(order=("kimi", "claude", "gemini"))
        with self.assertRaisesRegex(ValueError, "must contain claude, codex, and kimi"):
            self.select()

    def test_additional_authors_are_excluded(self):
        self.assertEqual(self.select(authors=("kimi",)), ["claude"])
        with self.assertRaisesRegex(ValueError, "no eligible"):
            self.select(authors=("kimi", "claude"))
        with self.assertRaisesRegex(ValueError, "unknown agent"):
            self.select(authors=("nobody",))

    def test_copilot_owner_needs_author_models(self):
        with self.assertRaisesRegex(ValueError, "needs --author-model"):
            self.select("copilot")
        with self.assertRaisesRegex(ValueError, "needs --author-model"):
            self.select("claude", authors=("copilot",))

    def test_vendor_rule_ignores_model_version(self):
        # Copilot on an Anthropic model: no Claude review, whatever the version.
        self.assertEqual(selector.order(self.roster, "copilot", self.output(), today=TODAY,
                                        author_models=("claude-sonnet-5",)), ["kimi", "codex"])
        # Copilot on OpenAI models: Codex excluded, Claude eligible.
        self.assertEqual(selector.order(self.roster, "copilot", self.output(), today=TODAY,
                                        author_models=("gpt-6.1-terra", "gpt-5.3-codex")), ["kimi", "claude"])
        # Mixed Anthropic + Moonshot + OpenAI authorship leaves no subscription reviewer.
        with self.assertRaisesRegex(ValueError, "no eligible"):
            selector.order(self.roster, "copilot", self.output(), today=TODAY,
                           author_models=("claude-haiku-4.5", "kimi-k3", "gpt-6-luna"))

    def test_unknown_and_router_models_fail_closed(self):
        for model in ("copilot-fusion", "auto", "mystery-1"):
            with self.subTest(model=model), self.assertRaises(ValueError):
                selector.order(self.roster, "copilot", self.output(), today=TODAY, author_models=(model,))

    def test_template_date_must_be_today(self):
        with self.assertRaisesRegex(ValueError, "date must be today"):
            self.select(name="auto-2026-10-15-new.md")

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
    --owner|--packet-root|--author|--author-model|--task) shift 2 ;;
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
        for name in ("auto-review.sh", "reviewer-select.py", "review-budget.py", "review-budget.json", "reviewer-roster.json", "agents.py", "agents.json"):
            shutil.copy2(ROOT / name, self.gateway / name)
        # Fixed roster: tests must not depend on which subscriptions are live today.
        (self.gateway / "reviewer-roster.json").write_text(json.dumps(
            {"active_reviewers": ["kimi", "claude", "codex"], "tie_break_order": ["kimi", "claude", "codex"]}))
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
        self.day = date.today().isoformat()
        self.log.write_text("")
        self.git("init", "-q")
        self.git("add", "-A")
        self.git("-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", "snapshot")

    def tearDown(self):
        self.tmp.cleanup()

    def git(self, *args):
        subprocess.run(["git", "-C", str(self.gateway), *args], check=True, capture_output=True)

    def run_auto(self, *extra_env, tier="routine", owner="codex", name=None, roster=None, authors=(), author_models=()):
        env = os.environ.copy()
        env["AUTO_MOCK_LOG"] = str(self.log)
        for key in ("AUTO_MOCK_KIMI_CODE", "AUTO_MOCK_CLAUDE_CODE", "AUTO_MOCK_CODEX_CODE"):
            env.pop(key, None)
        for assignment in extra_env:
            key, value = assignment.split("=", 1)
            env[key] = value
        if roster is not None:
            (self.gateway / "reviewer-roster.json").write_text(json.dumps(roster))
            self.git("add", "reviewer-roster.json")
            self.git("-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", "test roster")
        name = name or f"auto-{self.day}-topic.md"
        output = self.collab / name
        result = subprocess.run(
            [str(self.gateway / "auto-review.sh"), "--owner", owner,
             *(arg for author in authors for arg in ("--author", author)),
             *(arg for model in author_models for arg in ("--author-model", model)), tier,
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
        self.assertEqual(self.calls(), [f"kimi|routine|kimi-{self.day}-topic.md"])
        self.assertTrue((self.collab / f"kimi-{self.day}-topic.md").is_file())
        self.assertFalse((self.collab / f"auto-{self.day}-topic.md").exists())

    def test_auto_excludes_kimi_coauthor(self):
        result = self.run_auto(authors=("kimi",))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.calls(), [f"claude|sonnet|claude-{self.day}-topic.md"])

    def test_auto_copilot_owner_follows_author_model_vendor(self):
        result = self.run_auto(owner="copilot", author_models=("claude-sonnet-5.5",))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.calls(), [f"kimi|routine|kimi-{self.day}-topic.md"])
        refused = self.run_auto(owner="copilot", name=f"auto-{self.day}-other.md")
        self.assertEqual(refused.returncode, 64, refused.stderr)
        self.assertIn("needs --author-model", refused.stderr)

    def test_preflight_failure_fails_over_and_maps_claude_hard_tier(self):
        result = self.run_auto("AUTO_MOCK_KIMI_CODE=69", tier="hard")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.calls(), [
            f"kimi|hard|kimi-{self.day}-topic.md",
            f"claude|opus|claude-{self.day}-topic.md",
        ])
        self.assertIn("trying the next eligible reviewer", result.stderr)

    def test_claude_routine_tier_maps_to_sonnet(self):
        roster = {"active_reviewers": ["claude"], "tie_break_order": ["kimi", "claude", "codex"]}
        result = self.run_auto(roster=roster)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.calls(), [f"claude|sonnet|claude-{self.day}-topic.md"])

    def test_model_failure_and_budget_refusal_are_not_retried(self):
        for code in (70, 79):
            with self.subTest(code=code):
                self.log.write_text("")
                result = self.run_auto(f"AUTO_MOCK_KIMI_CODE={code}", name=f"auto-{self.day}-topic-{code}.md")
                self.assertEqual(result.returncode, code)
                self.assertEqual(self.calls(), [f"kimi|routine|kimi-{self.day}-topic-{code}.md"])
                self.assertNotIn("trying the next eligible reviewer", result.stderr)
                (self.collab / f"kimi-{self.day}-topic-{code}.diagnostic.json").unlink()

    def test_existing_candidate_diagnostic_is_not_retried(self):
        name = f"auto-{self.day}-attempt-once.md"
        result = self.run_auto("AUTO_MOCK_KIMI_CODE=70", name=name)
        self.assertEqual(result.returncode, 70)
        self.assertEqual(self.calls(), [f"kimi|routine|kimi-{self.day}-attempt-once.md"])
        result = self.run_auto(name=name)
        self.assertEqual(result.returncode, 65)
        self.assertEqual(self.calls(), [f"kimi|routine|kimi-{self.day}-attempt-once.md"])
        self.assertIn("reserved by", result.stderr)

    def test_all_preflight_failures_end_with_gemini_fallback_instruction(self):
        result = self.run_auto("AUTO_MOCK_KIMI_CODE=69", "AUTO_MOCK_CLAUDE_CODE=78")
        self.assertEqual(result.returncode, 78)
        self.assertEqual(self.calls(), [
            f"kimi|routine|kimi-{self.day}-topic.md",
            f"claude|sonnet|claude-{self.day}-topic.md",
        ])
        self.assertIn("use gemini-review.sh as the fallback reviewer", result.stderr)


if __name__ == "__main__":
    unittest.main()
