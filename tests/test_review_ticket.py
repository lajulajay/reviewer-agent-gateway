#!/usr/bin/env python3
import importlib.util
import io
import json
import os
import subprocess
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("review_ticket", ROOT / "review-ticket.py")
rt = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rt)

TODAY = date.today().isoformat()
WS = """# Work

Workstream: 2026-11-21-work
Owner: Copilot (coordinator, assigned by the user)

## Decisions

- 2026-11-21, user, scope: review pool. Quote: "pool ok". Review pool: copilot 2/day, claude 3/day. Supersedes: none.
- 2026-11-21, codex, scope: not the user. Review pool: copilot 50/day.

## Log
- Review pool: copilot 99/day (not a decision)
"""


class TicketTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name).resolve() / "repo"
        (self.repo / ".collab").mkdir(parents=True)
        (self.repo / "src").mkdir()
        (self.repo / "src" / "a.py").write_text("a = 1\n")
        (self.repo / "other.py").write_text("b = 2\n")
        (self.repo / "workstreams").mkdir()
        (self.repo / "workstreams" / "2026-11-21-work.md").write_text(WS)
        self.cwd = os.getcwd()
        os.chdir(self.repo)

    def tearDown(self):
        os.chdir(self.cwd)
        self.tmp.cleanup()

    def main(self, *argv):
        err = io.StringIO()
        with mock.patch("sys.stderr", err), mock.patch("sys.stdout", io.StringIO()) as out:
            code = rt.main(["review-ticket.py", *argv])
        self.err, self.out = err.getvalue(), out.getvalue()
        return code

    def issue(self, *extra, reviewer="claude", tier="routine", output=None, models=("gpt-6.1-terra",), task="T7"):
        output = output or f".collab/{reviewer}-{TODAY}-work-t7-r01.md"
        args = ["issue", "--workstream", "workstreams/2026-11-21-work.md", "--task", task, "--tier", tier,
                "--reviewer", reviewer, "--owner", "copilot", "--scope", "src", *extra]
        for m in models:
            args += ["--author-model", m]
        return self.main(*args, "--", output)

    def check(self, provider, requested, output, *extra, packets=("src/a.py",), owner="copilot", task="T7",
              models=("gpt-6.1-terra",)):
        args = ["check", provider, requested, output, "--owner", owner]
        if task:
            args += ["--task", task]
        for m in models:
            args += ["--author-model", m]
        return self.main(*args, *extra, "--", *packets)

    def test_issue_then_matching_call_passes_and_mismatches_fail(self):
        self.assertEqual(self.issue(), 0, self.err)
        body = json.loads((self.repo / "reviewers" / "tickets" / f"claude-{TODAY}-work-t7-r01.md.ticket.json").read_text())
        self.assertEqual((body["task"], body["tier"], body["scope"]), ("T7", "routine", ["src"]))
        out = f".collab/claude-{TODAY}-work-t7-r01.md"
        self.assertEqual(self.check("claude", "sonnet", out), 0, self.err)
        cases = [
            (dict(provider="claude", requested="opus"), "tier"),
            (dict(packets=("other.py",)), "outside the ticket scope"),
            (dict(task="T8"), "task"),
            (dict(models=("gpt-6-luna",)), "author models"),
            (dict(owner="claude", models=()), "owner"),
        ]
        for kw, msg in cases:
            with self.subTest(kw=kw):
                provider = kw.pop("provider", "claude")
                requested = kw.pop("requested", "sonnet")
                self.assertEqual(self.check(provider, requested, out, **kw), 64)
                self.assertIn(msg, self.err)

    def test_copilot_task_without_ticket_is_refused_and_others_are_not_affected(self):
        out = f".collab/claude-{TODAY}-work-t9.md"
        self.assertEqual(self.check("claude", "sonnet", out, task="T9"), 66)
        self.assertIn("no review ticket", self.err)
        self.assertEqual(self.check("claude", "sonnet", out, task=None), 0, self.err)
        self.assertEqual(self.check("codex", "hard", out.replace("claude-", "codex-"), owner="claude", models=()), 0)

    def test_auto_ticket_covers_candidates_only(self):
        self.assertEqual(self.issue(reviewer="auto", output=f".collab/auto-{TODAY}-work-t7.md"), 0, self.err)
        self.assertEqual(self.check("kimi", "routine", f".collab/kimi-{TODAY}-work-t7.md"), 0, self.err)
        self.assertEqual(self.check("copilot", "routine", f".collab/copilot-{TODAY}-work-t7.md", "--vendor", "google"), 0, self.err)
        self.assertEqual(self.check("kimi", "hard", f".collab/kimi-{TODAY}-work-t7.md"), 64)

    def test_copilot_ticket_fixes_the_vendor(self):
        self.assertEqual(self.issue("--vendor", "openai", reviewer="copilot", models=("claude-sonnet-5.5",)), 0, self.err)
        out = f".collab/copilot-{TODAY}-work-t7-r01.md"
        self.assertEqual(self.check("copilot", "routine", out, "--vendor", "openai", models=("claude-sonnet-5.5",)), 0, self.err)
        self.assertEqual(self.check("copilot", "routine", out, "--vendor", "google", models=("claude-sonnet-5.5",)), 64)
        self.assertIn("vendor", self.err)

    def test_issue_refusals(self):
        self.assertEqual(self.issue(reviewer="codex"), 64)  # OpenAI author, OpenAI reviewer
        self.assertIn("same vendor", self.err)
        self.assertEqual(self.issue("--vendor", "openai", reviewer="copilot"), 64)
        self.assertEqual(self.issue("--batch", "T3", "--batch", "T5", tier="hard"), 64)
        self.assertIn("batch is routine only", self.err)
        self.assertEqual(self.issue("--batch", "T3", "--batch", "T5", task="B1"), 0, self.err)
        self.assertEqual(self.issue(task="B1"), 73)
        (self.repo / ".collab" / f"claude-{TODAY}-work-t7-r02.md").write_text("done")
        self.assertEqual(self.issue(output=f".collab/claude-{TODAY}-work-t7-r02.md"), 73)
        self.assertEqual(self.issue(output=f".collab/kimi-{TODAY}-work-t7-r03.md"), 64)  # name vs reviewer

    def test_damaged_ticket_is_never_ignored(self):
        d = self.repo / "reviewers" / "tickets"
        d.mkdir(parents=True)
        (d / f"claude-{TODAY}-x.md.ticket.json").write_text("{not json")
        self.assertEqual(self.check("claude", "sonnet", f".collab/claude-{TODAY}-x.md", owner="claude", task=None, models=()), 64)

    def test_scope_replaced_by_a_symlink_is_refused(self):
        self.assertEqual(self.issue(), 0, self.err)
        outside = Path(self.tmp.name).resolve() / "outside"
        outside.mkdir()
        (outside / "a.py").write_text("secret = 1\n")
        (self.repo / "src" / "a.py").unlink()
        (self.repo / "src").rmdir()
        (self.repo / "src").symlink_to(outside)
        self.assertEqual(self.check("claude", "sonnet", f".collab/claude-{TODAY}-work-t7-r01.md"), 64)
        self.assertIn("leaves the repository", self.err)

    def test_pool_counts_only_user_decisions(self):
        self.assertEqual(self.issue(), 0, self.err)
        _, body = rt.find(self.repo, f"claude-{TODAY}-work-t7-r01.md")
        self.assertEqual(rt.pool(self.repo, body, "copilot"), 2)
        self.assertEqual(rt.pool(self.repo, body, "claude"), 3)
        self.assertIsNone(rt.pool(self.repo, body, "kimi"))

    def test_list_shows_unused_tickets(self):
        self.assertEqual(self.issue(), 0)
        self.assertEqual(self.main("list"), 0)
        self.assertIn("T7 routine claude", self.out)
        (self.repo / ".collab" / f"claude-{TODAY}-work-t7-r01.md").write_text("done")
        self.main("list")
        self.assertIn("no open review tickets", self.out)


class BudgetPoolTest(unittest.TestCase):
    """review-budget.py with tickets, pools and the Copilot escalation substitute."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name).resolve() / "repo"
        self.collab = self.repo / ".collab"
        self.collab.mkdir(parents=True)
        (self.repo / "workstreams").mkdir()
        (self.repo / "workstreams" / "w.md").write_text(WS)
        self.tickets = self.repo / "reviewers" / "tickets"
        self.tickets.mkdir(parents=True)

    def tearDown(self):
        self.tmp.cleanup()

    def ticket(self, output, reviewer="copilot"):
        body = {"version": 1, "issued": "2026-11-21T00:00:00+00:00", "workstream": "workstreams/w.md", "task": "T1",
                "batch": [], "tier": "routine", "reviewer": reviewer, "vendor": None, "owner": "claude", "authors": [],
                "author_models": [], "packet_root": None, "scope": ["workstreams"], "output": output}
        (self.tickets / (output + ".ticket.json")).write_text(json.dumps(body))

    def artifact(self, name, vendor=None, requested="routine"):
        text = f"# review\n\nRequested model: {requested}\n" + (f"Reviewer vendor: {vendor}\n" if vendor else "")
        (self.collab / name).write_text(text)

    def budget(self, provider, tier, name, *extra):
        return subprocess.run(["python3", str(ROOT / "review-budget.py"), provider, tier, str(self.collab / name), *extra],
                              capture_output=True, text=True)

    def test_pool_replaces_the_repository_cap_for_its_workstream(self):
        for i in range(2):
            self.ticket(f"copilot-{TODAY}-p{i}.md")
            self.artifact(f"copilot-{TODAY}-p{i}.md", "google")
        self.ticket(f"copilot-{TODAY}-p2.md")
        r = self.budget("copilot", "routine", f"copilot-{TODAY}-p2.md")
        self.assertEqual(r.returncode, 1)
        self.assertIn("2 copilot reviews already ran today under the copilot review pool of workstreams/w.md (cap 2)", r.stderr)
        # Unpooled work in the same repository does not count the pooled rounds.
        r = self.budget("copilot", "routine", f"copilot-{TODAY}-free.md")
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_escalation_substitute_needs_an_uninvolved_vendor(self):
        for i, (prov, vendor) in enumerate([("kimi", None), ("codex", None), ("kimi", None), ("codex", None), ("copilot", "xai")]):
            self.artifact(f"{prov}-{TODAY}-esc-r0{i + 1}.md", vendor)
        r = self.budget("copilot", "routine", f"copilot-{TODAY}-esc-r06.md")
        self.assertEqual(r.returncode, 1)
        self.assertIn("escalate to gemini", r.stderr)
        r = self.budget("copilot", "routine", f"copilot-{TODAY}-esc-r06.md", "--escalation-substitute", "openai")
        self.assertEqual(r.returncode, 1)
        self.assertIn("openai already reviewed it", r.stderr)
        r = self.budget("copilot", "routine", f"copilot-{TODAY}-esc-r06.md", "--escalation-substitute", "xai")
        self.assertEqual(r.returncode, 1)
        r = self.budget("copilot", "routine", f"copilot-{TODAY}-esc-r06.md", "--escalation-substitute", "microsoft")
        self.assertEqual(r.returncode, 0, r.stderr)
        r = self.budget("kimi", "routine", f"kimi-{TODAY}-esc-r06.md", "--escalation-substitute", "microsoft")
        self.assertEqual(r.returncode, 64)
        (self.collab / f"copilot-{TODAY}-esc-r05.md").write_text("Requested model: routine\n")  # vendor unknown
        r = self.budget("copilot", "routine", f"copilot-{TODAY}-esc-r07.md", "--escalation-substitute", "microsoft")
        self.assertEqual(r.returncode, 1)
        self.assertIn("does not name its reviewer vendor", r.stderr)


if __name__ == "__main__":
    unittest.main()
