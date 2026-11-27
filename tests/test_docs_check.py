#!/usr/bin/env python3
"""Provider-free tests for docs-check.py (workspace framework v6, as tightened
by implementation reviews r06 and r07)."""

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
R01-F1 is resolved.
R01-C1 is resolved.
R01-F2 remains open: budgets still drift.
R01-F3 was discussed at length.
> R02-F9 is resolved.

F1 [minor]: the handoff wording could be tighter.
F2 [major]: budgets still drift.
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
GOOD_ROWS = [
    ("R01-F1", "blocker", "verified r02", "closed"),
    ("R01-F2", "major", "rejected: budgets are out of scope per the scope decision of 2026-10-03", "closed"),
    ("R01-F3", "minor", "rejected: superseded by the scope decision recorded on 2026-10-03", "closed"),
    ("R01-C1", "condition", "verified r02", "closed"),
    ("R02-F1", "minor", "rejected: wording preference outside the agreed pilot scope", "closed"),
    ("R02-F2", "major", "rejected: budgets are out of scope per the scope decision of 2026-10-03", "closed"),
]
CLOSURE_LOG = ("- r01: raw review compared with its rows; no unlabeled actionable item\n"
               "- r02: raw review compared with its rows; no unlabeled actionable item\n")


GATEWAY_BASELINE_ENV = {}


def run(*args):
    import os
    env = dict(os.environ, **GATEWAY_BASELINE_ENV)
    r = subprocess.run([sys.executable, str(TOOL), *map(str, args)], capture_output=True, text=True, env=env)
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

    def baseline(self, legacy=()):
        (self.repo / "docs-baseline.json").write_text(json.dumps({"created": "2026-10-03", "legacy_collab": list(legacy)}))
        (self.repo / "AGENTS.md").write_text(f"# Agents\n\nStandards: reviewer-agent-gateway@{self.rev}\n")

    def workstream(self, rows, reviews=None, decisions="", log="", extra="", header=""):
        reviews = reviews or [("r01", "codex-x-r01.md", "REJECT"), ("r02", "codex-x-r02.md", "REJECT")]
        idx = "".join(f"| {r} | Codex | hard | `.collab/{p}` | {v} |\n" for r, p, v in reviews)
        table = "".join(f"| {i} | {s} | {d} | {st} |\n" for i, s, d, st in rows)
        (self.repo / "workstreams" / "x.md").write_text(f"""# X

Workstream: x
Owner: Claude (2026-10-03)
Status: active
{header}
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
        git(self.repo, "init", "-q", "-b", "main")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", "x")


class DocsCheckTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.f = Fixture(self.tmp.name)
        self.f.artifact("codex-x-r01.md", REVIEW1)
        self.f.artifact("codex-x-r02.md", REVIEW2)
        self.f.baseline()
        # Fixture agent cache, so tests never depend on live memory.
        self.mem = Path(self.tmp.name) / "memory"
        self.mem.mkdir()
        (self.mem / "MEMORY.md").write_text("- [a](a.md)\n")
        (self.mem / "a.md").write_text("a" * 100)
        gb = Path(self.tmp.name) / "gateway-baseline.json"
        gb.write_text(json.dumps({"agent_cache": {"dir": str(self.mem), "files": {}, "total": 0}}))
        GATEWAY_BASELINE_ENV["DOCS_CHECK_GATEWAY_BASELINE"] = str(gb)

    def tearDown(self):
        self.tmp.cleanup()

    def record(self):
        return run("record", self.f.repo)

    def done(self):
        return run("done", self.f.repo, "workstreams/x.md")

    # ------------------------------------------------------------- record

    def test_record_and_done_pass(self):
        self.f.workstream(GOOD_ROWS, log=CLOSURE_LOG)
        code, out = self.record()
        self.assertEqual(code, 0, out)
        code, out = self.done()
        self.assertEqual(code, 0, out)

    def test_clean_accept_without_items_passes_record(self):
        self.f.artifact("codex-x-r03.md", CLEAN_ACCEPT)
        self.f.workstream(GOOD_ROWS, reviews=[("r01", "codex-x-r01.md", "REJECT"), ("r02", "codex-x-r02.md", "REJECT"),
                                              ("r03", "codex-x-r03.md", "ACCEPT")])
        code, out = self.record()
        self.assertEqual(code, 0, out)

    def test_rows_missing_extra_duplicate_malformed_wrong_severity(self):
        rows = [r for r in GOOD_ROWS if r[0] != "R01-C1"] + [("R01-F9", "minor", "x", "open"), ("R02-F1", "minor", "x", "open")]
        rows = [("R01-F2", "minor", r[2], r[3]) if r[0] == "R01-F2" else r for r in rows]
        self.f.workstream(rows)
        ws = self.f.repo / "workstreams" / "x.md"
        ws.write_text(ws.read_text().replace("| R01-F9 |", "| RX-9 | minor | x | open |\n| R01-F9 |"))
        code, out = self.record()
        self.assertEqual(code, 1)
        for expected in ("no disposition row for R01-C1", "row R01-F9 matches no item", "R01-F2 severity",
                         "duplicate findings row R02-F1", "malformed findings row"):
            self.assertIn(expected, out)

    def test_checksum_mismatch_and_malformed_sidecar(self):
        self.f.workstream(GOOD_ROWS)
        (self.f.repo / ".collab" / "codex-x-r01.md").write_text(REVIEW1.replace("{rev}", self.f.rev) + "tampered\n")
        (self.f.repo / ".collab" / "codex-x-r02.md.sha256").write_text("")
        out = self.record()[1]
        self.assertIn("r01 artifact .collab/codex-x-r01.md checksum missing, malformed, or mismatched", out)
        self.assertIn("r02 artifact .collab/codex-x-r02.md checksum missing, malformed, or mismatched", out)

    def test_unindexed_and_ambiguous_collab_files_and_pin(self):
        self.f.workstream(GOOD_ROWS)
        self.f.artifact("codex-x-r03.md", REVIEW2)
        (self.f.repo / ".collab" / "notes.md").write_text("# notes\n")
        out = self.record()[1]
        self.assertIn("codex-x-r03.md is not in any workstream review index", out)
        self.assertIn("notes.md is not a recognizable review artifact", out)
        (self.f.repo / "AGENTS.md").write_text("# no pin\n")
        self.assertIn("has no 'Standards: reviewer-agent-gateway@<commit>' pin", self.record()[1])
        self.f.baseline(legacy=[".collab/codex-x-r03.md", ".collab/notes.md"])
        code, out = self.record()
        self.assertEqual(code, 0, out)

    def test_failed_invocation_extraction(self):
        collab = self.f.repo / ".collab"
        rel = ".collab/gemini-x-r09.extracted.md"
        named = f"- Owner extraction of a failed invocation: `{rel}`\n"
        text = "F1 [major]: extracted text\nVERDICT: REJECT\n"
        ext = collab / "gemini-x-r09.extracted.md"
        ext.write_text(text)
        side = collab / "gemini-x-r09.extracted.md.sha256"
        diag = collab / "gemini-x-r09.diagnostic.json"
        good = hashlib.sha256(text.encode()).hexdigest() + "  " + rel + "\n"
        side.write_text(good)
        diag.write_text('{"exit_code": 70}\n')

        def fails(reason):
            code, out = self.record()
            self.assertEqual(code, 1, out)
            self.assertIn(f"{rel} is an extraction that does not qualify: {reason}", out)

        # Qualifies only with the exact classification line; other mentions do not count.
        missing = f"no workstream line 'Owner extraction of a failed invocation: `{rel}`'"
        self.f.workstream(GOOD_ROWS)
        fails(missing)
        for other in (f"`{rel}` is a review, not an extraction.\n",
                      f"- Owner extraction of a failed invocation: `{rel}.backup`\n",
                      f"- Owner extraction of a failed invocation: `{rel}` (draft)\n"):
            self.f.workstream(GOOD_ROWS, extra=other)
            fails(missing)
        # Only an active statement in the Reviews section counts: not the Log,
        # a fenced example, or an HTML comment.
        ws = self.f.repo / "workstreams" / "x.md"
        self.f.workstream(GOOD_ROWS, log=named)
        fails(missing)
        for wrap in (f"```\n{named}```\n", f"<!--\n{named}-->\n", f"<!-- {named.strip()} -->\n"):
            self.f.workstream(GOOD_ROWS)
            ws.write_text(ws.read_text().replace("## Findings and conditions", wrap + "\n## Findings and conditions"))
            fails(missing)
        self.f.workstream(GOOD_ROWS)
        ws.write_text(ws.read_text().replace("## Findings and conditions", named + "\n## Findings and conditions"))
        self.assertEqual(self.record()[0], 0, self.record()[1])
        code, out = self.record()
        self.assertEqual(code, 0, out)
        # Diagnostic: missing, malformed, not a failure.
        diag.unlink()
        fails("no gemini-x-r09.diagnostic.json beside it")
        diag.write_bytes(b"\xff\xfe not json")
        fails("gemini-x-r09.diagnostic.json is unreadable or malformed")
        for body in ('{"exit_code": 0}', '{"exit_code": true}', '{"exit_code": "70"}', '{}'):
            diag.write_text(body)
            fails("gemini-x-r09.diagnostic.json records no failed exit code")
        for body in ("[70]", "[" * 100000 + "]" * 100000):
            diag.write_text(body)
            fails("gemini-x-r09.diagnostic.json is unreadable or malformed")
        diag.write_text('{"exit_code": 70}\n')
        # Sidecar: missing, undecodable, empty, wrong; stale after the extraction changes.
        side.unlink()
        fails("no checksum sidecar")
        side.write_bytes(b"\xff\xfe\x00")
        fails("checksum sidecar or extraction is unreadable")
        side.write_text("")
        fails("checksum sidecar is malformed or does not match")
        side.write_text("0" * 64 + "\n")
        fails("checksum sidecar is malformed or does not match")
        side.write_text(good)
        ext.write_text(text + "edited\n")
        fails("checksum sidecar is malformed or does not match")
        ext.write_text(text)
        self.assertEqual(self.record()[0], 0)
        # Any other unrecognized file is still flagged.
        (collab / "gemini-x-r09.notes.md").write_text("# notes\n")
        code, out = self.record()
        self.assertEqual(code, 1)
        self.assertIn("gemini-x-r09.notes.md is not a recognizable review artifact", out)

    def test_newly_staged_artifact_passes_before_commit(self):
        self.f.workstream(GOOD_ROWS)
        self.f.adopt()
        self.f.artifact("codex-x-r03.md", CLEAN_ACCEPT)
        ws = self.f.repo / "workstreams" / "x.md"
        ws.write_text(ws.read_text().replace("| r02 | Codex | hard | `.collab/codex-x-r02.md` | REJECT |\n",
                      "| r02 | Codex | hard | `.collab/codex-x-r02.md` | REJECT |\n| r03 | Codex | hard | `.collab/codex-x-r03.md` | ACCEPT |\n"))
        self.assertIn("codex-x-r03.md is not tracked", self.record()[1])
        git(self.f.repo, "add", "-A")
        code, out = self.record()
        self.assertEqual(code, 0, out)

    def test_wrapper_revision_must_not_be_newer_than_pin(self):
        parent = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD~1"], capture_output=True, text=True).stdout.strip()
        self.f.workstream(GOOD_ROWS)
        self.f.artifact("codex-x-r01.md", REVIEW1.replace("{rev}", parent))
        code, out = self.record()
        self.assertEqual(code, 0, out)  # older standards than the pin are fine
        (self.f.repo / "AGENTS.md").write_text(f"Standards: reviewer-agent-gateway@{parent}\n")
        self.assertIn("r02 wrapper revision", self.record()[1])  # r02 ran newer standards than the pin
        self.assertIn("newer than, or unrelated to, the standards pin", self.record()[1])

    def test_budget_override_needs_user_decision(self):
        self.f.artifact("codex-x-r03.md", CLEAN_ACCEPT.replace("{rev}\n", "{rev}\nBudget override: user approved\n"))
        reviews = [("r01", "codex-x-r01.md", "REJECT"), ("r02", "codex-x-r02.md", "REJECT"), ("r03", "codex-x-r03.md", "ACCEPT")]
        self.f.workstream(GOOD_ROWS, reviews=reviews)
        self.assertIn("r03 ran with a review budget override", self.record()[1])
        self.f.workstream(GOOD_ROWS, reviews=reviews, decisions=(
            '- 2026-10-03, user, scope: review rounds for x.\n  Quote: "budget override approved for r02". Supersedes: none.'))
        self.assertIn("r03 ran with a review budget override", self.record()[1])
        self.f.workstream(GOOD_ROWS, reviews=reviews, decisions=(
            '- 2026-10-03, user, scope: review rounds for x.\n  Quote: "budget override approved for r03". Supersedes: none.'))
        code, out = self.record()
        self.assertEqual(code, 0, out)

    def test_adopted_repo_needs_baseline(self):
        self.f.workstream(GOOD_ROWS)
        (self.f.repo / "docs-baseline.json").unlink()
        self.assertIn("docs-baseline.json is missing", self.record()[1])

    def test_legacy_numbered_review(self):
        self.f.artifact("codex-x-r01.md", LEGACY)
        self.f.baseline(legacy=[".collab/codex-x-r01.md"])
        self.f.workstream([("R01-F1", "blocker", "x", "open"), ("R01-F2", "major", "x", "open"),
                           ("R02-F1", "minor", "x", "open"), ("R02-F2", "major", "x", "open")])
        code, out = self.record()
        self.assertEqual(code, 0, out)

    def test_provenance_and_contract_for_post_adoption_reviews(self):
        self.f.artifact("codex-x-r02.md", REVIEW2.replace("{rev}", "{rev} (dirty)"))
        self.f.workstream(GOOD_ROWS)
        self.assertIn("unversioned or dirty wrapper", self.record()[1])
        self.f.artifact("codex-x-r02.md", REVIEW2.replace("Wrapper revision: {rev}\n", "").replace(A, ""))
        out = self.record()[1]
        self.assertIn("r02 has no wrapper revision", out)
        self.assertIn("r02 fails the output contract", out)

    def test_committed_artifact_edit_is_detected(self):
        self.f.workstream(GOOD_ROWS)
        self.f.adopt()
        # Edit the artifact and its sidecar together, so the checksum still matches.
        self.f.artifact("codex-x-r01.md", REVIEW1.replace("wording is loose", "wording is LOOSE"))
        self.assertIn("codex-x-r01.md has uncommitted changes", self.record()[1])
        git(self.f.repo, "commit", "-q", "-am", "edit")
        self.assertIn("codex-x-r01.md was modified, deleted, or renamed after its first commit", self.record()[1])

    def test_untracked_and_replaced_artifacts(self):
        self.f.workstream(GOOD_ROWS)
        self.f.adopt()
        git(self.f.repo, "rm", "-q", "--cached", ".collab/codex-x-r02.md", ".collab/codex-x-r02.md.sha256")
        git(self.f.repo, "commit", "-q", "-m", "untrack")
        self.assertIn("codex-x-r02.md is not tracked; review evidence must be committed", self.record()[1])
        git(self.f.repo, "add", "-A")
        git(self.f.repo, "commit", "-q", "-m", "re-add")
        self.assertIn("codex-x-r02.md was modified, deleted, or renamed", self.record()[1])

    def test_baseline_refuses_untracked_collab_and_legacy_cannot_grow(self):
        self.f.workstream(GOOD_ROWS)
        (self.f.repo / "docs-baseline.json").unlink()
        self.f.adopt()
        self.f.artifact("codex-x-r09.md", REVIEW2)
        self.assertNotEqual(run("report", self.f.repo, "--write-baseline")[0], 0)
        (self.f.repo / ".collab" / "codex-x-r09.md").unlink()
        (self.f.repo / ".collab" / "codex-x-r09.md.sha256").unlink()
        self.assertEqual(run("report", self.f.repo, "--write-baseline")[0], 0)
        git(self.f.repo, "add", "-A")
        git(self.f.repo, "commit", "-q", "-m", "baseline")
        b = json.loads((self.f.repo / "docs-baseline.json").read_text())
        (self.f.repo / "docs-baseline.json").write_text(json.dumps(dict(b, legacy_collab=b["legacy_collab"] + [".collab/new.md"])))
        self.assertIn("legacy list grew after its first commit", self.record()[1])

    def test_owner_line_forms(self):
        ws = self.f.repo / "workstreams" / "x.md"
        cases = {
            "Owner: Copilot (2026-11-20, assigned by the user)": True,
            "Owner: Claude (from Codex, 2026-10-03, Codex limit reached)": True,
            "Owner: sponsor's GitHub Copilot agent (user-assigned 2026-11-20)": True,
            "Owner: the sponsor": False,
            "Owner: Kimi (2026-11-20)": False,
            "Owner: sponsor's Copilot agent, reviewed by Kimi": True,  # notes after "," never name the owner
            "Owner: sponsor's Copilot or Codex agent": False,
            "Owner: Copilotish helper": False,
            "Owner: Copilot (reviewer wrapper owner codex)": True,
            "Owner: Claude (2026-11-18, assigned by the user at 1bc6649); build handed to the sponsor's GitHub Copilot agents": True,
            "Owner: not Copilot": False,
            "Owner: human, assisted by Copilot": False,
            "Owner: Copilot or Codex": False,
            "Owner: Copilot2": False,
            "Owner: !Copilot": False,
            "Owner: Copilot.": False,
            "Owner: sponsor's Copilot2 agent": False,
            "Owner: sponsor's GitHub Codex agent": True,
            "Owner: sponsor's GitHub Kimi agent": False,
        }
        for line, ok in cases.items():
            with self.subTest(line=line):
                self.f.workstream(GOOD_ROWS)
                ws.write_text(ws.read_text().replace("Owner: Claude (2026-10-03)", line))
                code, out = self.record()
                self.assertEqual("Owner must name" not in out, ok, out)

    def test_legacy_owner_line_passes_but_vendor_check_still_applies(self):
        ws = self.f.repo / "workstreams" / "x.md"
        self.f.workstream(GOOD_ROWS)
        ws.write_text(ws.read_text().replace("Owner: Claude (2026-10-03)",
                                             "Owner: sponsor's GitHub Copilot agent (user-assigned 2026-11-20)\n"
                                             "Owner: Claude (from Copilot, 2026-11-21)"))
        code, out = self.record()
        self.assertEqual(code, 0, out)
        # An artifact whose recorded reviewer shares a vendor with its owner
        # fails regardless of the workstream's Owner line.
        art = self.f.repo / ".collab" / "codex-x-r01.md"
        art.chmod(0o644)
        self.f.artifact("codex-x-r01.md", REVIEW1.replace("Owner: claude", "Owner: codex"))
        code, out = self.record()
        self.assertNotEqual(code, 0, out)
        self.assertIn("r01 breaks reviewer independence", out)
        self.assertNotIn("Owner must name", out)

    def test_copilot_artifact_is_checked_by_its_selected_model(self):
        def copilot(text, model):
            return (text.replace("# Codex review", "# Copilot review")
                        .replace("Owner: claude\n", f"Owner: claude\nSelected model: {model}\nReviewer vendor: x\n"))
        base = [("r01", "codex-x-r01.md", "REJECT"), ("r02", "codex-x-r02.md", "REJECT")]
        r03 = base + [("r03", "copilot-x-r03.md", "ACCEPT")]
        self.f.artifact("copilot-x-r03.md", copilot(CLEAN_ACCEPT, "gpt-6-luna"))
        self.f.workstream(GOOD_ROWS, reviews=r03)
        code, out = self.record()
        self.assertEqual(code, 0, out)
        # Labeled items in a Copilot artifact are read like any other review.
        (self.f.repo / ".collab" / "copilot-x-r03.md").chmod(0o644)
        self.f.artifact("copilot-x-r03.md", copilot(CLEAN_ACCEPT.replace(A, "F1 [minor]: wording.\n" + A), "gpt-6-luna"))
        code, out = self.record()
        self.assertNotEqual(code, 0, out)
        self.assertIn("R03-F1", out)
        # A Claude model reviewing Claude-owned work fails, as does a missing model.
        for name, model in (("copilot-x-r04.md", "claude-haiku-5.5"), ("copilot-x-r05.md", None)):
            with self.subTest(model=model):
                text = copilot(CLEAN_ACCEPT, model or "")
                if model is None:
                    text = text.replace("Selected model: \n", "")
                self.f.artifact(name, text)
                self.f.workstream(GOOD_ROWS, reviews=base + [(name[-6:-3], name, "ACCEPT")])
                code, out = self.record()
                self.assertNotEqual(code, 0, out)
                self.assertIn(f"{name[-6:-3]} breaks reviewer independence", out)
                (self.f.repo / ".collab" / name).unlink()
                (self.f.repo / ".collab" / (name + ".sha256")).unlink()

    # ------------------------------------------------------- Copilot tasks (D7, D10)

    def copilot_ws(self, tasks, reviews, decisions="", owner="Owner: Copilot (coordinator, 2026-11-21)"):
        rows = "".join(f"| {' | '.join(r)} |\n" for r in tasks)
        extra = ("## Tasks\n\n| Task | Author | Author-models | Branch | PR | State | Covers |\n"
                 "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n" + rows)
        self.f.workstream([], reviews=reviews, decisions=decisions, extra=extra)
        ws = self.f.repo / "workstreams" / "x.md"
        ws.write_text(ws.read_text().replace("Owner: Claude (2026-10-03)", owner))

    def task_review(self, name, task, models, owner="copilot", verdict="ACCEPT"):
        text = CLEAN_ACCEPT.replace("# Codex review", "# Claude review").replace("ACCEPT", verdict)
        head = f"Owner: {owner}\n" + (f"Author models: {', '.join(models)}\n" if models else "") + (f"Task: {task}\n" if task else "")
        self.f.artifact(name, text.replace("Owner: claude\n", head))
        return (name[-6:-3], name, verdict)

    def drop_default_reviews(self):
        for n in ("codex-x-r01.md", "codex-x-r02.md"):
            for f in (n, n + ".sha256"):
                (self.f.repo / ".collab" / f).unlink()

    def test_copilot_artifact_must_match_its_task_row(self):
        self.drop_default_reviews()
        t7 = ("T7", "copilot", "gpt-6.1-terra", "b-t7", "pr7", "draft", "")
        cases = [
            ([t7], ("T7", ["gpt-6.1-terra"]), None),
            ([t7], ("T7", ["gpt-6.1-terra", "gpt-6-luna"]), "!= task T7 Author-models"),
            ([t7], ("T8", ["gpt-6.1-terra"]), "task 'T8' has no row"),
            ([t7], (None, ["gpt-6.1-terra"]), "records no --task"),
            ([("T7", "copilot", "auto", "b", "pr", "draft", "")], ("T7", ["gpt-6.1-terra"]), "task T7: model 'auto'"),
            ([("T7", "copilot", "", "b", "pr", "draft", "")], ("T7", ["gpt-6.1-terra"]), "needs an Author and Author-models"),
            ([("T7", "copilot", "gpt-6.1-terra", "b", "pr", "shipped", "")], ("T7", ["gpt-6.1-terra"]), "state must be one of"),
            ([("T7", "kimi2", "gpt-6.1-terra", "b", "pr", "draft", "")], ("T7", ["gpt-6.1-terra"]), "unknown author"),
            ([("T7", "copilot", "gpt-6.1-terra", "", "pr", "draft", "")], ("T7", ["gpt-6.1-terra"]), "needs its Branch"),
            ([("T7", "copilot", "gpt-6.1-terra", "b", "", "merged", "")], ("T7", ["gpt-6.1-terra"]), "needs its PR"),
            ([t7, ("T8", "copilot", "gpt-6.1-terra", "b", "pr", "merged", "T7")], ("T7", ["gpt-6.1-terra"]),
             "only batch rows and integration rows"),
            ([t7, t7], ("T7", ["gpt-6.1-terra"]), "duplicate task row T7"),
            ([t7[:6]], ("T7", ["gpt-6.1-terra"]), "malformed task row"),
        ]
        for tasks, (task, models), err in cases:
            with self.subTest(err=err):
                r = self.task_review("claude-x-r01.md", task, models)
                self.copilot_ws(tasks, [r])
                code, out = self.record()
                if err is None:
                    self.assertEqual(code, 0, out)
                else:
                    self.assertNotEqual(code, 0, out)
                    self.assertIn(err, out)
                for f in ("claude-x-r01.md", "claude-x-r01.md.sha256"):
                    (self.f.repo / ".collab" / f).unlink()
        # Owner mismatch: a Codex-owned artifact in a workstream only Copilot owns.
        r = self.task_review("claude-x-r01.md", None, [], owner="codex")
        self.copilot_ws([t7], [r])
        self.assertIn("r01 owner 'codex' is not an owner named", self.record()[1])
        # A non-Copilot owner naming a Copilot task must still match its row.
        for f in ("claude-x-r01.md", "claude-x-r01.md.sha256"):
            (self.f.repo / ".collab" / f).unlink()
        r = self.task_review("kimi-x-r01.md", "T7", [], owner="claude")
        self.copilot_ws([t7], [r], owner="Owner: Copilot (2026-11-21)\nOwner: Claude (from Copilot, 2026-11-21)")
        self.assertIn("r01 author models [] != task T7", self.record()[1])

    def test_batch_rows_carry_member_identity(self):
        self.drop_default_reviews()
        t3 = ("T3", "copilot", "gpt-6-luna", "b3", "pr3", "draft", "")
        t4 = ("T4", "copilot", "gpt-6.1-terra", "b4", "pr4", "planned", "")
        b1 = ("B1", "copilot", "gpt-6-luna, gpt-6.1-terra", "-", "", "batch", "T3, T4")
        r = self.task_review("claude-x-r01.md", "B1", ["gpt-6-luna", "gpt-6.1-terra"])
        self.copilot_ws([t3, t4, b1], [r])
        code, out = self.record()
        self.assertEqual(code, 0, out)
        short = ("B1", "copilot", "gpt-6-luna", "-", "", "batch", "T3, T4")
        r = self.task_review("claude-x-r01.md", "B1", ["gpt-6-luna"])
        self.copilot_ws([t3, t4, short], [r])
        self.assertIn("task B1 omits gpt-6.1-terra", self.record()[1])

    def test_integration_gate(self):
        self.drop_default_reviews()
        gate = lambda: run("integration", self.f.repo, "workstreams/x.md")
        t6 = ("T6", "copilot", "gpt-6-luna", "b-t6", "pr6", "merged", "")
        t7 = ("T7", "copilot", "gpt-6.1-terra", "b-t7", "pr7", "merged", "")
        reviews = [self.task_review("claude-x-r01.md", "T6", ["gpt-6-luna"]),
                   self.task_review("claude-x-r02.md", "T7", ["gpt-6.1-terra"])]
        self.copilot_ws([t6, t7], reviews)
        self.f.adopt()
        self.assertEqual(self.record()[0], 0, self.record()[1])
        code, out = gate()
        self.assertNotEqual(code, 0, out)
        self.assertIn("task T6 is merged but no accepted integration review covers it", out)
        self.assertIn("task T7 is merged", out)
        i1 = ("I1", "copilot", "gpt-6-luna, gpt-6.1-terra", "main@abcdef1", "", "ready", "T6, T7")
        # A rejected integration review does not open the gate.
        rej = self.task_review("claude-x-r03.md", "I1", ["gpt-6-luna", "gpt-6.1-terra"], verdict="REJECT")
        self.f.artifact("claude-x-r03.md", (self.f.repo / ".collab" / "claude-x-r03.md").read_text()
                        .replace(A, "F1 [minor]: x.\n" + A))
        self.copilot_ws([t6, t7, i1], reviews + [rej])
        code, out = gate()
        self.assertIn("task T6 is merged but no accepted", out)
        ok = self.task_review("claude-x-r04.md", "I1", ["gpt-6-luna", "gpt-6.1-terra"])
        self.copilot_ws([t6, t7, i1], reviews + [rej, ok])
        # Uncommitted, the accepted review does not count; committed with its row, it does.
        self.assertIn("integration review is not committed", gate()[1])
        git(self.f.repo, "add", "-A")
        git(self.f.repo, "commit", "-q", "-m", "i1")
        code, out = gate()
        self.assertIn("R03-F1", out)  # the record is part of the gate
        self.assertNotIn("is merged but", out)
        # Widening Covers after the review does not cover the new task.
        t8 = ("T8", "copilot", "gpt-6.1-terra", "b-t8", "pr8", "merged", "")
        wide = ("I1", "copilot", "gpt-6-luna, gpt-6.1-terra", "main@abcdef1", "", "ready", "T6, T7, T8")
        self.copilot_ws([t6, t7, t8, wide], reviews + [rej, ok])
        out = gate()[1]
        self.assertIn("I1 Covers or Branch changed after its review", out)
        self.assertIn("task T8 is merged but", out)
        # A batch row is not an integration review, nor is a task that names Covers.
        b1 = ("B1", "copilot", "gpt-6-luna, gpt-6.1-terra", "-", "", "batch", "T6, T7")
        bat = self.task_review("claude-x-r05.md", "B1", ["gpt-6-luna", "gpt-6.1-terra"])
        self.copilot_ws([t6, t7, b1], reviews + [rej, ok, bat])
        git(self.f.repo, "add", "-A")
        git(self.f.repo, "commit", "-q", "-m", "b1")
        self.assertIn("task T6 is merged but", gate()[1])
        bad = [
            (("I1", "copilot", "gpt-6-luna", "main@abcdef1", "", "ready", "T6, T7"), "omits gpt-6.1-terra"),
            (("I1", "copilot", "gpt-6-luna, gpt-6.1-terra", "main@abcdef1", "", "ready", "T6, T9"), "covers 'T9', which is not a task row"),
            (("I1", "copilot", "gpt-6-luna, gpt-6.1-terra", "main", "", "ready", "T6, T7"), "Branch must be main@"),
            (("I1", "copilot", "gpt-6-luna, gpt-6.1-terra", "main@abcdef1", "", "batch", "T6, T7"), "may not be a batch"),
        ]
        for row, err in bad:
            with self.subTest(err=err):
                self.copilot_ws([t6, t7, row], reviews)
                self.assertIn(err, self.record()[1])
        draft = ("T7", "copilot", "gpt-6.1-terra", "b-t7", "pr7", "draft", "")
        self.copilot_ws([t6, draft, i1], reviews)
        self.assertIn("covers T7, which is not merged", self.record()[1])

    def test_legacy_owner_map(self):
        self.drop_default_reviews()
        r = self.task_review("claude-x-r01.md", None, [], owner="codex")
        today = datetime.now().strftime("%Y-%m-%d")
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        entry = lambda d: (f'- {d}, user, scope: legacy owners.\n  Quote: "map them". '
                           "Legacy owner map: codex -> copilot. Supersedes: none.\n")
        self.copilot_ws([], [r])
        self.f.adopt()
        self.assertIn("r01 owner 'codex' is not an owner named", self.record()[1])
        self.copilot_ws([], [r], decisions=entry(today))
        code, out = self.record()
        self.assertEqual(code, 0, out)
        self.copilot_ws([], [r], decisions=entry(yesterday))
        self.assertIn("r01 owner 'codex' is not an owner named", self.record()[1])
        # One entry per repository.
        self.copilot_ws([], [r], decisions=entry(today))
        (self.f.repo / "workstreams" / "y.md").write_text(
            "# Y\n\nWorkstream: y\nOwner: Claude (2026-11-21)\nStatus: active\n\n## Decisions\n\n" + entry(today))
        self.assertIn("more than one 'Legacy owner map'", self.record()[1])

    def test_broken_link(self):
        self.f.workstream(GOOD_ROWS, extra="See [missing](../nope.md).\n")
        self.assertIn("does not resolve", self.record()[1])

    # ------------------------------------------------------------- budgets

    def test_budgets_and_ratchets(self):
        self.f.workstream(GOOD_ROWS)
        (self.f.repo / "STATUS.md").write_text("x" * 4001)
        self.assertIn("STATUS.md has 4001 characters", self.record()[1])
        (self.f.repo / "STATUS.md").write_text("x" * 100)
        (self.f.repo / "docs-baseline.json").unlink()
        (self.f.repo / "CLAUDE.md").write_text("z" * 61000)
        (self.f.repo / "AGENTS.md").write_text(f"Standards: reviewer-agent-gateway@{self.f.rev}\n" + "y" * 13000)
        self.f.adopt()
        self.assertEqual(run("report", self.f.repo, "--write-baseline")[0], 0)
        git(self.f.repo, "add", "-A")
        git(self.f.repo, "commit", "-q", "-m", "baseline")
        code, out = self.record()
        self.assertEqual(code, 0, out)
        self.assertNotEqual(run("report", self.f.repo, "--write-baseline")[0], 0)
        agents = self.f.repo / "AGENTS.md"
        size = len(agents.read_text())
        agents.write_text(agents.read_text() + "y")
        self.assertIn(f"limit {size}", self.record()[1])
        agents.write_text(agents.read_text()[:12500])
        run("report", self.f.repo, "--lower")
        self.assertEqual(json.loads((self.f.repo / "docs-baseline.json").read_text())["files"]["AGENTS.md"], 12500)
        agents.write_text(agents.read_text() + "y" * 50)
        run("report", self.f.repo, "--lower")
        self.assertEqual(json.loads((self.f.repo / "docs-baseline.json").read_text())["files"]["AGENTS.md"], 12500)
        agents.write_text(agents.read_text()[:12500])
        (self.f.repo / "docs").mkdir()
        (self.f.repo / "docs" / "a.md").write_text("q" * 10)
        (self.f.repo / "CLAUDE.md").write_text("z" * 60000)
        self.assertIn("T2 file docs/a.md grew to 10 characters while T2 is over budget", self.record()[1])

    # ---------------------------------------------------------------- done

    def test_done_rejects_weak_closures(self):
        bad = [
            ("R01-F1", "blocker", "verified r01", "closed"),
            ("R01-F2", "major", "verified r02", "closed"),
            ("R01-F3", "minor", "verified r02", "closed"),
            ("R01-C1", "condition", "fixed abc1234", "closed"),
            ("R02-F1", "minor", "rejected: too costly", "open"),
            ("R02-F2", "major", 'user-decided 2026-10-03 "accept drift for the pilot"', "closed"),
        ]
        self.f.workstream(bad, decisions='- 2026-10-03, user, scope: pilot. Quote: "accept drift for the pilot"')
        out = self.done()[1]
        self.assertIn("R01-F1: verified cites r01, which is not a later indexed round", out)
        self.assertIn("R01-F2: r02 has no line 'R01-F2 is resolved.'", out)
        self.assertIn("R01-F3: r02 has no line 'R01-F3 is resolved.'", out)
        self.assertIn("R01-C1: a condition closes only by", out)
        self.assertIn("R02-F1: status is 'open'", out)
        self.assertIn("R02-F1: no valid final disposition", out)
        self.assertIn("R02-F2: user-decided quote must say 'R02-F2 accepted'", out)
        self.assertIn("closure: log lacks 'r01:", out)

    def test_user_decided_needs_dated_scoped_entry(self):
        rows = list(GOOD_ROWS)
        rows[0] = ("R01-F1", "blocker", 'user-decided 2026-10-03 "R01-F1 accepted: handoff risk for the pilot"', "closed")
        quote = '"R01-F1 accepted: handoff risk for the pilot"'
        self.f.workstream(rows, decisions=f"- 2026-10-02, user, scope: pilot. Quote: {quote}", log=CLOSURE_LOG)
        self.assertIn("no Decisions entry dated 2026-10-03 with a scope", self.done()[1])
        self.f.workstream(rows, decisions=f"Free text: {quote}", log=CLOSURE_LOG)
        self.assertIn("no Decisions entry dated 2026-10-03 with a scope", self.done()[1])
        self.f.workstream(rows, decisions=f"- 2026-10-03, user, scope: pilot handoff.\n  Quote: {quote}", log=CLOSURE_LOG)
        code, out = self.done()
        self.assertEqual(code, 0, out)

    def test_verified_line_must_be_exact_and_uncontradicted(self):
        quoted = REVIEW2.replace("R01-F1 is resolved.", "> R01-F1 is resolved.")
        self.f.artifact("codex-x-r02.md", quoted)
        self.f.workstream(GOOD_ROWS, log=CLOSURE_LOG)
        self.assertIn("R01-F1: r02 has no line 'R01-F1 is resolved.'", self.done()[1])
        contradicted = REVIEW2.replace("R01-C1 is resolved.\n", "R01-C1 is resolved.\nR01-C1 remains open: actually not.\n")
        self.f.artifact("codex-x-r02.md", contradicted)
        self.assertIn("R01-C1: r02 also says R01-C1 remains open", self.done()[1])

    def test_verified_line_ignores_trailing_spaces_only(self):
        self.f.workstream(GOOD_ROWS, log=CLOSURE_LOG)
        padded = REVIEW2.replace("R01-F1 is resolved.\n", "R01-F1 is resolved.  \n").replace(
            "R01-C1 is resolved.\n", "R01-C1 is resolved.\t\n")
        self.f.artifact("codex-x-r02.md", padded)
        code, out = self.done()
        self.assertEqual(code, 0, out)
        for tail in (" but see below", ".", "  x", "\u00a0"):
            with self.subTest(tail=tail):
                self.f.artifact("codex-x-r02.md", REVIEW2.replace("R01-F1 is resolved.\n", f"R01-F1 is resolved.{tail}\n"))
                self.assertIn("R01-F1: r02 has no line 'R01-F1 is resolved.'", self.done()[1])

    def test_verified_line_accepts_crlf_in_md_artifacts(self):
        self.f.workstream(GOOD_ROWS, log=CLOSURE_LOG)
        self.f.artifact("codex-x-r02.md", REVIEW2.replace("\n", "\r\n"))
        code, out = self.done()
        self.assertEqual(code, 0, out)

    def test_verified_line_accepts_crlf_in_json_artifacts(self):
        for name in ("codex-x-r02.md", "codex-x-r02.md.sha256"):
            (self.f.repo / ".collab" / name).unlink(missing_ok=True)
        body = REVIEW2.split("\n\n", 1)[1].replace("\n", "\r\n")
        review = json.dumps({"reviewer_metadata": {"owner": "claude", "wrapper_revision": "{rev}"}, "response": body})
        self.f.artifact("gemini-x-r02.json", review)
        self.f.workstream(GOOD_ROWS, reviews=[("r01", "codex-x-r01.md", "REJECT"), ("r02", "gemini-x-r02.json", "REJECT")],
                          log=CLOSURE_LOG)
        code, out = self.done()
        self.assertEqual(code, 0, out)

    def test_pilot_record_enforces_gateway_memory_budget(self):
        self.f.workstream(GOOD_ROWS)
        code, out = self.record()
        self.assertEqual(code, 0, out)
        (self.mem / "a.md").write_text("a" * 1600)
        self.assertIn("agent cache a.md has 1600 characters (limit 1500)", self.record()[1])
        (self.mem / "a.md").write_text("a" * 100)
        for i in range(12):
            (self.mem / f"m{i}.md").write_text("m" * 1400)
        self.assertIn("agent cache totals", self.record()[1])
        Path(GATEWAY_BASELINE_ENV["DOCS_CHECK_GATEWAY_BASELINE"]).write_text("{}")
        self.assertIn("gateway baseline records no agent cache", self.record()[1])

    def test_carried_is_no_longer_accepted(self):
        rows = list(GOOD_ROWS)
        rows[1] = ("R01-F2", "major", "carried R02-F2", "closed")
        self.f.workstream(rows, log=CLOSURE_LOG)
        self.assertIn("R01-F2: no valid final disposition (got 'carried R02-F2')", self.done()[1])

    # ------------------------------------------------------------ transfer

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
        base_text = ws.read_text()

        def handoff(inventory, observation, operational_no=False):
            text = base_text.replace("Status: active\n", "Status: active\nOperational: no\n") if operational_no else base_text
            ws.write_text(text + f"\n### Handoff 2026-10-03\n\nInventory: {inventory}\n"
                          f"Runtime observation: {observation}\nRestart sequence: read this file\n")
            git(self.f.repo, "commit", "-q", "-am", "handoff")
            git(self.f.repo, "push", "-q")
            return run("transfer", self.f.repo, "workstreams/x.md")[1]

        now = datetime.now()
        inv = "`git status --short --ignored`; 0 untracked, 0 ignored; needed by next owner: none"
        stale = (now - timedelta(hours=3)).strftime("%Y-%m-%d %H:%M")
        future = (now + timedelta(hours=2)).strftime("%Y-%m-%d %H:%M")
        fresh = now.strftime("%Y-%m-%d %H:%M")
        self.assertIn("older than two hours", handoff(inv, f"{stale} `curl /health` -> 200"))
        self.assertIn("in the future", handoff(inv, f"{future} `curl /health` -> 200"))
        self.assertIn("must read 'YYYY-MM-DD HH:MM `<command>` -> <result>'", handoff(inv, f"{fresh} deploy ok"))
        self.assertIn("needs 'Operational: no'", handoff(inv, "n/a (not operational)"))
        (self.f.repo / "new").mkdir()
        (self.f.repo / "new" / "a.txt").write_text("x")
        (self.f.repo / "new" / "b.txt").write_text("y")
        self.assertIn("git status shows 2 and 0", handoff(inv, f"{fresh} `curl /health` -> 200"))
        (self.f.repo / "new" / "a.txt").unlink()
        (self.f.repo / "new" / "b.txt").unlink()
        (self.f.repo / "new").rmdir()
        self.assertIn("is not a valid date", handoff(inv, "2026-13-45 99:99 `curl /health` -> 200"))
        self.assertIn("needed file notes/missing.md is not committed",
                      handoff(inv.replace("next owner: none", "next owner: notes/missing.md"), f"{fresh} `curl /health` -> 200"))
        self.assertIn("docs-check transfer: PASS", handoff(inv, "n/a (not operational)", operational_no=True))
        self.assertIn("docs-check transfer: PASS", handoff(inv, f"{fresh} `curl /health` -> 200"))

    # --------------------------------------------------------- dispositions

    def test_dispositions_output(self):
        code, out = run("dispositions", self.f.repo / ".collab" / "codex-x-r01.md", "r01")
        self.assertEqual(code, 0)
        self.assertEqual(out.splitlines(), ["| R01-F1 | blocker | | open |", "| R01-F2 | major | | open |",
                                            "| R01-F3 | minor | | open |", "| R01-C1 | condition | | open |"])


if __name__ == "__main__":
    unittest.main()
