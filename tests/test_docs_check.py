#!/usr/bin/env python3
"""Provider-free tests for docs-check.py (workspace framework v6)."""

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOL = ROOT / "docs-check.py"
A = "ATTESTATION: all actionable findings and conditions are labeled."
PAD = "The packet was read in full and each claim was checked against the stated invariants. " * 6
REVIEW1 = f"""# Codex review

Owner: claude
Wrapper revision: {{rev}}

{PAD}
F1 [blocker]: the handoff loses work.
F2 [major]: budgets drift.
F3 [minor]: wording is loose.
C1: fix the handoff under F1.
{A}

VERDICT: REJECT
"""
REVIEW2 = f"""# Codex review

Owner: claude
Wrapper revision: {{rev}}

{PAD}
F1 [minor]: R01-F1 is resolved: the handoff now commits pending work.
F2 [major]: R01-F2 remains open: budgets still drift.
{A}

VERDICT: REJECT
"""
CLEAN_ACCEPT = f"""# Codex review

Owner: claude
Wrapper revision: {{rev}}

{PAD}
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


def run(*args):
    r = subprocess.run([sys.executable, str(TOOL), *map(str, args)], capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


def git(repo, *args):
    subprocess.run(["git", "-C", str(repo), "-c", "user.email=t@t", "-c", "user.name=t", *args],
                   check=True, capture_output=True)


class Fixture:
    def __init__(self, base):
        self.base = Path(base)
        self.repo = self.base / "repo"
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
        reviews = reviews or [("r01", "codex-x-r01.md", "REJECT"), ("r02", "codex-x-r02.md", "REJECT")]
        idx = "".join(f"| {r} | Codex | hard | `.collab/{p}` | {v} |\n" for r, p, v in reviews)
        table = "".join(f"| {i} | {s} | {d} | {st} |\n" for i, s, d, st in rows)
        (self.repo / "workstreams" / "x.md").write_text(f"""# X

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
{extra}""")

    def adopt(self):
        (self.repo / "AGENTS.md").write_text(f"# Agents\n\nStandards: reviewer-agent-gateway@{self.rev}\n")
        git(self.repo, "init", "-q", "-b", "main")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", "x")


GOOD_ROWS = [
    ("R01-F1", "blocker", 'verified r02 "R01-F1 is resolved: the handoff now commits pending work."', "closed"),
    ("R01-F2", "major", "carried R02-F2", "closed"),
    ("R01-F3", "minor", "rejected: superseded by the scope decision recorded on 2026-10-03", "closed"),
    ("R01-C1", "condition", "carried R01-F1", "closed"),
    ("R02-F1", "minor", "rejected: informational confirmation that R01-F1 closed; nothing to act on", "closed"),
    ("R02-F2", "major", "rejected: budgets are out of scope per the scope decision of 2026-10-03", "closed"),
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

    def done_out(self):
        return run("done", self.f.repo, "workstreams/x.md")

    def test_record_and_done_pass(self):
        self.f.workstream(GOOD_ROWS, log=CLOSURE_LOG)
        code, out = run("record", self.f.repo)
        self.assertEqual(code, 0, out)
        code, out = self.done_out()
        self.assertEqual(code, 0, out)

    def test_clean_accept_without_items_passes_record(self):
        self.f.artifact("codex-x-r03.md", CLEAN_ACCEPT)
        self.f.workstream(GOOD_ROWS, reviews=[("r01", "codex-x-r01.md", "REJECT"), ("r02", "codex-x-r02.md", "REJECT"),
                                              ("r03", "codex-x-r03.md", "ACCEPT")])
        code, out = run("record", self.f.repo)
        self.assertEqual(code, 0, out)

    def test_missing_extra_duplicate_malformed_and_wrong_severity_rows(self):
        rows = [r for r in GOOD_ROWS if r[0] != "R01-C1"] + [("R01-F9", "minor", "x", "open"), ("R02-F1", "minor", "x", "open")]
        rows = [("R01-F2", "minor", r[2], r[3]) if r[0] == "R01-F2" else r for r in rows]
        self.f.workstream(rows, extra="")
        ws = self.f.repo / "workstreams" / "x.md"
        ws.write_text(ws.read_text().replace("| R01-F9 |", "| RX-9 | minor | x | open |\n| R01-F9 |"))
        code, out = run("record", self.f.repo)
        self.assertEqual(code, 1)
        for expected in ("no disposition row for R01-C1", "row R01-F9 matches no item", "R01-F2 severity",
                         "duplicate findings row R02-F1", "malformed findings row"):
            self.assertIn(expected, out)

    def test_checksum_mismatch_and_malformed_sidecar(self):
        self.f.workstream(GOOD_ROWS)
        (self.f.repo / ".collab" / "codex-x-r01.md").write_text(REVIEW1.replace("{rev}", self.f.rev) + "tampered\n")
        (self.f.repo / ".collab" / "codex-x-r02.md.sha256").write_text("")
        out = run("record", self.f.repo)[1]
        self.assertIn("r01 artifact .collab/codex-x-r01.md checksum missing, malformed, or mismatched", out)
        self.assertIn("r02 artifact .collab/codex-x-r02.md checksum missing, malformed, or mismatched", out)

    def test_committed_artifact_edit_is_detected(self):
        self.f.workstream(GOOD_ROWS)
        self.f.adopt()
        self.f.artifact("codex-x-r01.md", REVIEW1 + "\nedited later\n")
        out = run("record", self.f.repo)[1]
        self.assertIn("codex-x-r01.md has uncommitted changes", out)
        git(self.f.repo, "commit", "-q", "-am", "edit")
        self.assertIn("codex-x-r01.md was modified after its first commit", run("record", self.f.repo)[1])

    def test_unindexed_and_ambiguous_collab_files_and_pin(self):
        self.f.workstream(GOOD_ROWS)
        self.f.artifact("codex-x-r03.md", REVIEW2)
        (self.f.repo / ".collab" / "notes.md").write_text("# notes\n")
        out = run("record", self.f.repo)[1]
        self.assertIn("codex-x-r03.md is not in any workstream review index", out)
        self.assertIn("notes.md is not a recognizable review artifact", out)
        (self.f.repo / "docs-baseline.json").write_text(json.dumps(
            {"legacy_collab": [".collab/codex-x-r03.md", ".collab/notes.md"]}))
        self.assertIn("has no 'Standards: reviewer-agent-gateway@<commit>' pin", run("record", self.f.repo)[1])
        (self.f.repo / "AGENTS.md").write_text(f"Standards: reviewer-agent-gateway@{self.f.rev}\n")
        code, out = run("record", self.f.repo)
        self.assertEqual(code, 0, out)

    def test_baseline_refuses_untracked_collab(self):
        self.f.workstream(GOOD_ROWS)
        self.f.adopt()
        self.f.artifact("codex-x-r09.md", REVIEW2)
        self.assertNotEqual(run("report", self.f.repo, "--write-baseline")[0], 0)

    def test_legacy_numbered_review(self):
        self.f.artifact("codex-x-r01.md", LEGACY)
        (self.f.repo / "docs-baseline.json").write_text(json.dumps({"legacy_collab": [".collab/codex-x-r01.md"]}))
        (self.f.repo / "AGENTS.md").write_text(f"Standards: reviewer-agent-gateway@{self.f.rev}\n")
        self.f.workstream([("R01-F1", "blocker", "x", "open"), ("R01-F2", "major", "x", "open"),
                           ("R02-F1", "minor", "x", "open"), ("R02-F2", "major", "x", "open")])
        code, out = run("record", self.f.repo)
        self.assertEqual(code, 0, out)

    def test_provenance_and_contract_for_post_adoption_reviews(self):
        self.f.artifact("codex-x-r02.md", REVIEW2.replace("{rev}", "{rev} (dirty)"))
        self.f.workstream(GOOD_ROWS)
        self.assertIn("unversioned or dirty wrapper", run("record", self.f.repo)[1])
        self.f.artifact("codex-x-r02.md", REVIEW2.replace("Wrapper revision: {rev}\n", "").replace(A, ""))
        out = run("record", self.f.repo)[1]
        self.assertIn("r02 has no wrapper revision", out)
        self.assertIn("r02 fails the output contract", out)

    def test_done_rejects_weak_closures(self):
        bad = [
            ("R01-F1", "blocker", 'verified r02 "this sentence is not in the review"', "closed"),
            ("R01-F2", "major", 'verified r02 "R01-F2 remains open: budgets still drift."', "closed"),
            ("R01-F3", "minor", "rejected: too costly", "closed"),
            ("R01-C1", "condition", "fixed abc1234", "closed"),
            ("R02-F1", "minor", "rejected: informational confirmation that R01-F1 closed; nothing to act on", "open"),
            ("R02-F2", "major", 'user-decided 2026-10-03 "accept drift for the pilot"', "closed"),
        ]
        self.f.workstream(bad, decisions='- 2026-10-03, user: "accept drift for the pilot"')
        out = self.done_out()[1]
        self.assertIn("R01-F1: verified quote does not occur in r02", out)
        self.assertIn("R01-F2: verified quote must name R01-F2 and affirm resolution", out)
        self.assertIn("R01-F3: no valid final disposition", out)
        self.assertIn("R01-C1: a condition closes only by", out)
        self.assertIn("R02-F1: status is 'open'", out)
        self.assertIn("R02-F2: user-decided quote must name R02-F2", out)
        self.assertIn("closure: log lacks 'r01:", out)

    def test_carried_rules(self):
        rows = list(GOOD_ROWS)
        # Blocker carried into an unrelated finding that does not cite it.
        rows[0] = ("R01-F1", "blocker", "carried R02-F2", "closed")
        # Condition carried to a same-round finding it does not cite.
        rows[3] = ("R01-C1", "condition", "carried R01-F2", "closed")
        self.f.workstream(rows, log=CLOSURE_LOG)
        out = self.done_out()[1]
        self.assertIn("R01-F1: carried requires R02-F2's review text to cite R01-F1", out)
        self.assertIn("R01-C1: carried requires R01-C1's review text to cite F2", out)
        # A blocker carried into a cited minor must still close by strict evidence.
        rows = list(GOOD_ROWS)
        rows[0] = ("R01-F1", "blocker", "carried R02-F1", "closed")
        self.f.workstream(rows, log=CLOSURE_LOG)
        self.assertIn("R01-F1: carried target is not closed (R02-F1: a minor (carried from R01-F1) closes only by",
                      self.done_out()[1])

    def test_user_decided_names_finding(self):
        rows = list(GOOD_ROWS)
        rows[0] = ("R01-F1", "blocker", 'user-decided 2026-10-03 "R01-F1: accept the handoff risk for the pilot"', "closed")
        self.f.workstream(rows, decisions='- 2026-10-03, user: "R01-F1: accept the handoff risk for the pilot"', log=CLOSURE_LOG)
        code, out = self.done_out()
        self.assertEqual(code, 0, out)

    def test_budgets_and_ratchets(self):
        self.f.workstream(GOOD_ROWS)
        (self.f.repo / "STATUS.md").write_text("x" * 4001)
        self.assertIn("STATUS.md has 4001 characters", run("record", self.f.repo)[1])
        (self.f.repo / "STATUS.md").write_text("x" * 100)
        (self.f.repo / "CLAUDE.md").write_text("z" * 61000)
        self.f.adopt()
        (self.f.repo / "AGENTS.md").write_text(f"Standards: reviewer-agent-gateway@{self.f.rev}\n" + "y" * 13000)
        git(self.f.repo, "commit", "-q", "-am", "big")
        self.assertIn("AGENTS.md has", run("record", self.f.repo)[1])
        self.assertEqual(run("report", self.f.repo, "--write-baseline")[0], 0)
        code, out = run("record", self.f.repo)
        self.assertEqual(code, 0, out)
        self.assertNotEqual(run("report", self.f.repo, "--write-baseline")[0], 0)
        size = len((self.f.repo / "AGENTS.md").read_text())
        (self.f.repo / "AGENTS.md").write_text((self.f.repo / "AGENTS.md").read_text() + "y")
        self.assertIn(f"limit {size}", run("record", self.f.repo)[1])
        (self.f.repo / "AGENTS.md").write_text((self.f.repo / "AGENTS.md").read_text()[:12500])
        run("report", self.f.repo, "--lower")
        self.assertEqual(json.loads((self.f.repo / "docs-baseline.json").read_text())["files"]["AGENTS.md"], 12500)
        (self.f.repo / "AGENTS.md").write_text((self.f.repo / "AGENTS.md").read_text() + "y" * 50)
        run("report", self.f.repo, "--lower")
        self.assertEqual(json.loads((self.f.repo / "docs-baseline.json").read_text())["files"]["AGENTS.md"], 12500)
        (self.f.repo / "AGENTS.md").write_text((self.f.repo / "AGENTS.md").read_text()[:12500])
        # T2 over budget: shrinking one file does not let another grow.
        (self.f.repo / "docs").mkdir()
        (self.f.repo / "docs" / "a.md").write_text("q" * 10)
        (self.f.repo / "CLAUDE.md").write_text("z" * 60000)
        out = run("record", self.f.repo)[1]
        self.assertIn("T2 file docs/a.md grew to 10 characters while T2 is over budget", out)

    def test_broken_link(self):
        self.f.workstream(GOOD_ROWS, extra="See [missing](../nope.md).\n")
        self.assertIn("does not resolve", run("record", self.f.repo)[1])

    def test_transfer(self):
        self.f.workstream(GOOD_ROWS)
        self.f.adopt()
        remote = self.f.base / "remote.git"
        subprocess.run(["git", "init", "-q", "--bare", str(remote)], check=True)
        out = run("transfer", self.f.repo, "workstreams/x.md")[1]
        self.assertIn("not equal to its pushed upstream", out)
        self.assertIn("no '### Handoff' block", out)
        git(self.f.repo, "remote", "add", "origin", str(remote))
        git(self.f.repo, "push", "-q", "-u", "origin", "main")
        ws = self.f.repo / "workstreams" / "x.md"
        stale = (datetime.now() - timedelta(hours=3)).strftime("%Y-%m-%d %H:%M")
        ws.write_text(ws.read_text() + f"\n### Handoff 2026-10-03\n\nInventory: none\nRuntime observation: {stale} deploy ok\n")
        out = run("transfer", self.f.repo, "workstreams/x.md")[1]
        self.assertIn("uncommitted tracked changes", out)
        self.assertIn("Inventory must read", out)
        self.assertIn("older than two hours", out)
        self.assertIn("lacks 'Restart sequence:'", out)
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        base_text = ws.read_text().split("### Handoff")[0]
        ws.write_text(base_text + "### Handoff 2026-10-03\n\n"
                      "Inventory: `git status --short --ignored`; 1 untracked, 3 ignored; needed by next owner: notes/missing.md\n"
                      f"Runtime observation: {now} health endpoint 200\nRestart sequence: read this file\n")
        git(self.f.repo, "commit", "-q", "-am", "handoff")
        git(self.f.repo, "push", "-q")
        self.assertIn("needed file notes/missing.md is not committed", run("transfer", self.f.repo, "workstreams/x.md")[1])
        ws.write_text(ws.read_text().replace("needed by next owner: notes/missing.md", "needed by next owner: none"))
        git(self.f.repo, "commit", "-q", "-am", "handoff2")
        git(self.f.repo, "push", "-q")
        code, out = run("transfer", self.f.repo, "workstreams/x.md")
        self.assertEqual(code, 0, out)

    def test_dispositions_output(self):
        code, out = run("dispositions", self.f.repo / ".collab" / "codex-x-r01.md", "r01")
        self.assertEqual(code, 0)
        self.assertEqual(out.splitlines(), ["| R01-F1 | blocker | | open |", "| R01-F2 | major | | open |",
                                            "| R01-F3 | minor | | open |", "| R01-C1 | condition | | open |"])


if __name__ == "__main__":
    unittest.main()
