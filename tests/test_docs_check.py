#!/usr/bin/env python3
"""Provider-free tests for docs-check.py (workspace framework v6)."""

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOL = ROOT / "docs-check.py"
A = "ATTESTATION: all actionable findings and conditions are labeled."
REVIEW1 = f"""# Codex review

Owner: claude
Wrapper revision: {{rev}}

F1 [blocker]: the handoff loses work.
F2 [major]: budgets drift.
C1: fix the handoff.
{A}

VERDICT: REJECT
"""
REVIEW2 = f"""# Codex review

Owner: claude
Wrapper revision: {{rev}}

F1 [minor]: R01-F1 is resolved: the handoff now commits pending work.
{A}

VERDICT: ACCEPT
"""
LEGACY = """# Codex review

## Blockers

1. **First.** text

## Major

2. **Second.** text

VERDICT: REJECT
"""


def run(*args, cwd=None):
    r = subprocess.run([sys.executable, str(TOOL), *map(str, args)], capture_output=True, text=True, cwd=cwd)
    return r.returncode, r.stdout + r.stderr


def git(repo, *args):
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


class Fixture:
    def __init__(self, base):
        self.repo = Path(base) / "repo"
        (self.repo / ".collab").mkdir(parents=True)
        (self.repo / "workstreams").mkdir()
        self.rev = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"],
                                  capture_output=True, text=True).stdout.strip()

    def artifact(self, name, text):
        p = self.repo / ".collab" / name
        p.write_text(text.replace("{rev}", self.rev))
        (self.repo / ".collab" / (name + ".sha256")).write_text(
            hashlib.sha256(p.read_bytes()).hexdigest() + "  " + name + "\n")
        return p

    def workstream(self, rows, reviews=None, decisions="", log="", extra=""):
        reviews = reviews or [("r01", "codex-x-r01.md", "REJECT"), ("r02", "codex-x-r02.md", "ACCEPT")]
        idx = "".join(f"| {r} | Codex | hard | `.collab/{p}` | {v} |\n" for r, p, v in reviews)
        table = "".join(f"| {i} | {s} | {d} | {st} |\n" for i, s, d, st in rows)
        text = f"""# X

Workstream: x
Owner: Claude (2026-10-03)
Status: active

## Decisions

{decisions}

## Reviews

| Round | Reviewer | Tier | Artifact | Verdict |
| :--- | :--- | :--- | :--- | :--- |
{idx}
## Findings and conditions

| ID | Severity | Disposition | Status |
| :--- | :--- | :--- | :--- |
{table}
## Log

{log}
{extra}"""
        (self.repo / "workstreams" / "x.md").write_text(text)


GOOD_ROWS = [
    ("R01-F1", "blocker", 'verified r02 "R01-F1 is resolved: the handoff now commits pending work."', "closed"),
    ("R01-F2", "major", "rejected: outside the agreed pilot scope per the scope decision", "closed"),
    ("R01-C1", "condition", "carried R01-F1", "closed"),
    ("R02-F1", "minor", "rejected: informational confirmation, nothing left to act on", "closed"),
]
CLOSURE_LOG = ("- r01: raw review compared with its rows; no unlabeled actionable item\n"
               "- r02: raw review compared with its rows; no unlabeled actionable item\n")


class DocsCheckTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.f = Fixture(self.tmp.name)
        self.f.artifact("codex-x-r01.md", REVIEW1)
        self.f.artifact("codex-x-r02.md", REVIEW2)

    def tearDown(self):
        self.tmp.cleanup()

    def test_record_and_done_pass(self):
        self.f.workstream(GOOD_ROWS, log=CLOSURE_LOG)
        self.assertEqual(run("record", self.f.repo)[0], 0, run("record", self.f.repo)[1])
        code, out = run("done", self.f.repo, "workstreams/x.md")
        self.assertEqual(code, 0, out)

    def test_missing_extra_and_wrong_severity_rows(self):
        rows = [r for r in GOOD_ROWS if r[0] != "R01-C1"] + [("R01-F9", "minor", "x", "open")]
        rows = [("R01-F2", "minor", r[2], r[3]) if r[0] == "R01-F2" else r for r in rows]
        self.f.workstream(rows)
        code, out = run("record", self.f.repo)
        self.assertEqual(code, 1)
        self.assertIn("no disposition row for R01-C1", out)
        self.assertIn("row R01-F9 matches no item", out)
        self.assertIn("R01-F2 severity", out)

    def test_checksum_mismatch(self):
        self.f.workstream(GOOD_ROWS)
        (self.f.repo / ".collab" / "codex-x-r01.md").write_text(REVIEW1.replace("{rev}", self.f.rev) + "tampered\n")
        self.assertIn("checksum missing or mismatched", run("record", self.f.repo)[1])

    def test_unindexed_and_ambiguous_collab_files(self):
        self.f.workstream(GOOD_ROWS)
        self.f.artifact("codex-x-r03.md", REVIEW2)
        (self.f.repo / ".collab" / "notes.md").write_text("# notes\n")
        out = run("record", self.f.repo)[1]
        self.assertIn("codex-x-r03.md is not in any workstream review index", out)
        self.assertIn("notes.md is not a recognizable review artifact", out)
        (self.f.repo / "docs-baseline.json").write_text(json.dumps(
            {"legacy_collab": [".collab/codex-x-r03.md", ".collab/notes.md"]}))
        self.assertEqual(run("record", self.f.repo)[0], 0)

    def test_legacy_numbered_review(self):
        self.f.artifact("codex-x-r01.md", LEGACY)
        self.f.workstream([("R01-F1", "blocker", "x", "open"), ("R01-F2", "major", "x", "open"),
                           ("R02-F1", "minor", "x", "open")])
        code, out = run("record", self.f.repo)
        self.assertEqual(code, 0, out)

    def test_dirty_wrapper_revision_fails_record(self):
        self.f.artifact("codex-x-r02.md", REVIEW2.replace("{rev}", "{rev} (dirty)"))
        self.f.workstream(GOOD_ROWS)
        self.assertIn("unversioned or dirty wrapper", run("record", self.f.repo)[1])

    def test_done_rules(self):
        bad = [
            ("R01-F1", "blocker", 'verified r02 "this sentence is not in the review"', "closed"),
            ("R01-F2", "major", "rejected: too costly", "closed"),
            ("R01-C1", "condition", "fixed abc1234", "closed"),
            ("R02-F1", "minor", "rejected: informational confirmation, nothing left to act on", "open"),
        ]
        self.f.workstream(bad)
        out = run("done", self.f.repo, "workstreams/x.md")[1]
        self.assertIn("R01-F1: verified quote does not occur in r02", out)
        self.assertIn("R01-F2: no valid final disposition", out)
        self.assertIn("R01-C1: a condition closes only by", out)
        self.assertIn("R02-F1: status is 'open'", out)
        self.assertIn("closure: log lacks 'r01:", out)

    def test_carried_to_open_target_fails_and_user_decided_quote(self):
        rows = [r for r in GOOD_ROWS]
        rows[0] = ("R01-F1", "blocker", 'user-decided 2026-10-03 "accept the handoff risk for the pilot"', "closed")
        rows[2] = ("R01-C1", "condition", "carried R02-F1", "closed")
        rows[3] = ("R02-F1", "minor", "open", "open")
        self.f.workstream(rows, decisions='- 2026-10-03, user: "accept the handoff risk for the pilot"', log=CLOSURE_LOG)
        out = run("done", self.f.repo, "workstreams/x.md")[1]
        self.assertNotIn("R01-F1:", out)
        self.assertIn("R01-C1: carried target is not closed", out)

    def test_budgets_and_ratchet(self):
        self.f.workstream(GOOD_ROWS)
        (self.f.repo / "STATUS.md").write_text("x" * 4001)
        self.assertIn("STATUS.md has 4001 characters", run("record", self.f.repo)[1])
        (self.f.repo / "STATUS.md").write_text("x" * 100)
        (self.f.repo / "AGENTS.md").write_text("y" * 13000)
        self.assertIn("AGENTS.md has 13000", run("record", self.f.repo)[1])
        self.assertEqual(run("report", self.f.repo, "--write-baseline")[0], 0)
        self.assertEqual(run("record", self.f.repo)[0], 0)
        self.assertNotEqual(run("report", self.f.repo, "--write-baseline")[0], 0)
        (self.f.repo / "AGENTS.md").write_text("y" * 13001)
        self.assertIn("limit 13000", run("record", self.f.repo)[1])
        (self.f.repo / "AGENTS.md").write_text("y" * 12500)
        run("report", self.f.repo, "--lower")
        self.assertEqual(json.loads((self.f.repo / "docs-baseline.json").read_text())["files"]["AGENTS.md"], 12500)
        (self.f.repo / "AGENTS.md").write_text("y" * 12600)
        run("report", self.f.repo, "--lower")
        self.assertEqual(json.loads((self.f.repo / "docs-baseline.json").read_text())["files"]["AGENTS.md"], 12500)
        (self.f.repo / "docs").mkdir()
        (self.f.repo / "docs" / "a.md").write_text("z" * 60001)
        self.assertIn("T2 knowledge totals 60001", run("record", self.f.repo)[1])

    def test_broken_link(self):
        self.f.workstream(GOOD_ROWS, extra="See [missing](../nope.md).\n")
        self.assertIn("does not resolve", run("record", self.f.repo)[1])

    def test_transfer(self):
        self.f.workstream(GOOD_ROWS)
        remote = Path(self.tmp.name) / "remote.git"
        subprocess.run(["git", "init", "-q", "--bare", str(remote)], check=True)
        git(self.f.repo, "init", "-q", "-b", "main")
        git(self.f.repo, "-c", "user.email=t@t", "-c", "user.name=t", "add", "-A")
        git(self.f.repo, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", "x")
        out = run("transfer", self.f.repo, "workstreams/x.md")[1]
        self.assertIn("not equal to its pushed upstream", out)
        self.assertIn("no '### Handoff' block", out)
        git(self.f.repo, "remote", "add", "origin", str(remote))
        git(self.f.repo, "push", "-q", "-u", "origin", "main")
        ws = self.f.repo / "workstreams" / "x.md"
        ws.write_text(ws.read_text() + "\n### Handoff 2026-10-03\n\nInventory: none\n")
        out = run("transfer", self.f.repo, "workstreams/x.md")[1]
        self.assertIn("uncommitted tracked changes", out)
        self.assertIn("lacks 'Runtime observation:'", out)
        ws.write_text(ws.read_text() + "Runtime observation: n/a (not operational)\nRestart sequence: read this file\n")
        git(self.f.repo, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-am", "handoff")
        git(self.f.repo, "push", "-q")
        code, out = run("transfer", self.f.repo, "workstreams/x.md")
        self.assertEqual(code, 0, out)

    def test_dispositions_output(self):
        code, out = run("dispositions", self.f.repo / ".collab" / "codex-x-r01.md", "r01")
        self.assertEqual(code, 0)
        self.assertEqual(out.splitlines(), ["| R01-F1 | blocker | | open |", "| R01-F2 | major | | open |",
                                            "| R01-C1 | condition | | open |"])


if __name__ == "__main__":
    unittest.main()
