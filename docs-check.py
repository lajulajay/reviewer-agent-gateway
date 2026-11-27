#!/usr/bin/env python3
"""Check workspace documentation against the framework (proposal v6).

  docs-check.py record REPO                 records complete, budgets hold
  docs-check.py transfer REPO WORKSTREAM    record + safe to hand off
  docs-check.py done REPO WORKSTREAM        record + every obligation closed
  docs-check.py integration REPO WORKSTREAM merged tasks lack no integration review (D7)
  docs-check.py dispositions ARTIFACT ROUND print empty disposition rows
  docs-check.py report REPO [--write-baseline | --lower | --add-memory] [--memory DIR]

WORKSTREAM is a path relative to REPO (e.g. workstreams/2026-10-03-x.md).
Exit status 0 means pass; 1 means at least one error was printed.
"""

import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path

GATEWAY = Path(__file__).resolve().parent
BASELINE = "docs-baseline.json"
BUDGET = {"STATUS.md": 4000, "AGENTS.md": 12000, "PROTOCOL.md": 12000,
          "CLAUDE.md:stub": 1500, "workstream": 30000, "T2": 60000,
          "memory:index": 2000, "memory:entry": 1500, "memory:total": 15000}
REVIEW_HEADERS = ("# Claude review", "# Codex review", "# Copilot review", "# Kimi review")
FINDING = re.compile(r"^\s*(?:[-*]\s*)?\**F(\d+)\**\s*\[(blocker|major|minor)\]")
CONDITION = re.compile(r"^\s*(?:[-*]\s*)?\**C(\d+)\**\s*:")
VALIDATOR = GATEWAY / "reviewer-validate.py"
_spec = __import__("importlib.util").util.spec_from_file_location("agents", GATEWAY / "agents.py")
agents = __import__("importlib.util").util.module_from_spec(_spec)
_spec.loader.exec_module(agents)
ROW_ID = re.compile(r"^R(\d+)-([FC]\d+)$")
TASK_ID = re.compile(r"^[A-Za-z0-9._-]+$")
INTEGRATION_ID = re.compile(r"^I\d+$")
TASK_STATES = ("planned", "draft", "ready", "merged", "dropped", "batch")
LEGACY_MAP = re.compile(r"legacy owner map: codex -> copilot\b", re.I)
CLOSURE = "raw review compared with its rows; no unlabeled actionable item"
MAX_OBSERVATION_AGE = 2 * 3600


def git(repo, *args):
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    return r.returncode, r.stdout.strip()


def norm(text):
    return re.sub(r"\s+", " ", re.sub(r"[*_`]", "", text)).strip().lower()


def cells(line):
    return [c.strip() for c in line.strip().strip("|").split("|")]


# ---------------------------------------------------------------- artifacts

def artifact_text(path):
    raw = path.read_text(errors="replace")
    if path.suffix == ".json":
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return raw
        return data.get("response") or data.get("result") or raw
    return raw


def artifact_identity(path):
    """Return (reviewer, owner, authors, author_models, reviewer_model) recorded by
    the wrapper. reviewer_model is the selected model, which sets the vendor of a
    multi-vendor reviewer channel (Copilot)."""
    reviewer = path.name.split("-", 1)[0]
    if path.suffix == ".json":
        try:
            meta = json.loads(path.read_text(errors="replace")).get("reviewer_metadata") or {}
        except json.JSONDecodeError:
            meta = {}
        return (reviewer, meta.get("owner") or None, list(meta.get("authors") or []),
                list(meta.get("author_models") or []), meta.get("selected_model") or None)
    head = path.read_text(errors="replace").split("\n\n", 2)[:2]
    fields = dict(m.groups() for m in re.finditer(r"(?m)^(Owner|Authors|Author models|Selected model): (.+)$", "\n".join(head)))
    split = lambda key: [v.strip() for v in fields.get(key, "").split(",") if v.strip()]
    return reviewer, fields.get("Owner"), split("Authors"), split("Author models"), fields.get("Selected model")


def artifact_task(path):
    if path.suffix == ".json":
        try:
            return (json.loads(path.read_text(errors="replace")).get("reviewer_metadata") or {}).get("task") or None
        except json.JSONDecodeError:
            return None
    head = path.read_text(errors="replace").split("\n\n", 2)[:2]
    m = re.search(r"(?m)^Task: (.+)$", "\n".join(head))
    return m.group(1).strip() if m else None


def is_review_artifact(path):
    if path.suffix == ".json":
        try:
            return "reviewer_metadata" in json.loads(path.read_text(errors="replace"))
        except json.JSONDecodeError:
            return False
    first = path.read_text(errors="replace").split("\n", 1)[0].strip()
    return first in REVIEW_HEADERS


def labeled_items(path):
    """Return ({ID: (severity, text)}, duplicate IDs) for a review.

    Conditions have severity 'condition'. Labeled output (F<n> [severity]: /
    C<n>:) is parsed directly; a legacy review without labels is parsed from
    numbered items under Blocker/Major/Minor headings, numbered as F<n>.
    """
    text = artifact_text(path)
    items, dupes = {}, []
    def put(key, sev, line):
        if key in items:
            dupes.append(key)
        items[key] = (sev, line.strip())
    lines = text.splitlines()
    for line in lines:
        m = FINDING.match(line)
        if m:
            put(f"F{m.group(1)}", m.group(2), line)
        m = CONDITION.match(line)
        if m:
            put(f"C{m.group(1)}", "condition", line)
    if items:
        return items, dupes
    severity = None
    for line in lines:
        heading = re.match(r"^#+\s*(.*)", line)
        if heading:
            h = heading.group(1).lower()
            severity = ("blocker" if "blocker" in h else "major" if "major" in h
                        else "minor" if "minor" in h else None)
            continue
        num = re.match(r"^(\d+)\.\s", line)
        if num and severity:
            put(f"F{num.group(1)}", severity, line)
    return items, dupes


def verdict(path):
    m = re.findall(r"(?im)^\W*verdict\W*:\s*(accept with conditions|accept|reject)\b", artifact_text(path))
    return m[-1].lower() if m else None


def budget_override(path):
    """The REVIEW_BUDGET_OVERRIDE reason a wrapper recorded, or None."""
    if path.suffix == ".json":
        try:
            return json.loads(path.read_text()).get("reviewer_metadata", {}).get("budget_override")
        except json.JSONDecodeError:
            return None
    # The wrapper header is the block after the title line, before the review.
    parts = path.read_text(errors="replace").split("\n\n", 2)
    m = re.search(r"(?m)^Budget override: (.+)$", parts[1]) if len(parts) > 1 else None
    return m.group(1).strip() if m else None


def wrapper_revision(path):
    if path.suffix == ".json":
        try:
            return json.loads(path.read_text()).get("reviewer_metadata", {}).get("wrapper_revision")
        except json.JSONDecodeError:
            return None
    m = re.search(r"(?m)^Wrapper revision: (.+)$", path.read_text(errors="replace"))
    return m.group(1).strip() if m else None


# --------------------------------------------------------------- workstreams

class Workstream:
    def __init__(self, repo, path):
        self.repo, self.path = repo, path
        self.text = path.read_text()
        self.header, self.sections, current = {}, {}, None
        for line in self.text.splitlines():
            if line.startswith("## "):
                current = line[3:].strip()
                self.sections[current] = []
            elif current is None:
                m = re.match(r"^(\w[\w ]*):\s*(.+)$", line)
                if m:
                    self.header.setdefault(m.group(1), []).append(m.group(2))
            else:
                self.sections[current].append(line)
        self.reviews, self.rows, self.problems = {}, {}, []
        for line in self.sections.get("Reviews", []):
            c = cells(line) if line.startswith("|") else []
            if not c or c[0] in ("Round", "") or set(c[0]) <= set(":- "):
                continue
            m = re.search(r"`([^`]*\.collab/[^`]+)`", line)
            r = re.match(r"^r(\d+)", c[0])
            if not (m and r):
                self.problems.append(f"malformed review index row: {line.strip()[:80]}")
                continue
            if int(r.group(1)) in self.reviews:
                self.problems.append(f"duplicate review round r{int(r.group(1)):02d}")
            self.reviews[int(r.group(1))] = m.group(1)
        for line in self.sections.get("Findings and conditions", []):
            c = cells(line) if line.startswith("|") else []
            if not c or c[0] in ("ID", "") or set(c[0]) <= set(":- "):
                continue
            if not ROW_ID.match(c[0]) or len(c) < 4:
                self.problems.append(f"malformed findings row: {line.strip()[:80]}")
                continue
            if c[0] in self.rows:
                self.problems.append(f"duplicate findings row {c[0]}")
            self.rows[c[0]] = {"severity": c[1], "disposition": c[-2], "status": c[-1]}
        self.tasks = self.parse_tasks(self.text, self.problems)

    @staticmethod
    def parse_tasks(text, problems=None):
        """Task table (Copilot delegation, proposal D2/D6/D7):
        | Task | Author | Author-models | Branch | PR | State | Covers |"""
        problems = [] if problems is None else problems
        tasks, inside = {}, False
        split = lambda v: [x.strip() for x in v.split(",") if x.strip() and x.strip() not in ("-", "—")]
        for line in text.splitlines():
            if line.startswith("## "):
                inside = line[3:].strip() == "Tasks"
                continue
            c = cells(line) if inside and line.startswith("|") else []
            if not c or c[0] in ("Task", "") or set(c[0]) <= set(":- "):
                continue
            if len(c) != 7 or not TASK_ID.match(c[0]):
                problems.append(f"malformed task row: {line.strip()[:80]}")
                continue
            if c[0] in tasks:
                problems.append(f"duplicate task row {c[0]}")
            tasks[c[0]] = {"authors": [a.lower() for a in split(c[1])], "models": split(c[2]),
                           "branch": c[3], "pr": c[4], "state": c[5], "covers": split(c[6])}
        return tasks

    def section(self, name):
        return "\n".join(self.sections.get(name, []))


def workstreams(repo):
    root = repo / "workstreams"
    return sorted(root.glob("*.md")) + sorted((root / "closed").glob("*.md")) if root.is_dir() else []


# ------------------------------------------------------------------ budgets

def tiers(repo):
    """Return {path: (tier, chars, cap-or-None)} for documentation files."""
    out = {}
    def add(p, tier, cap):
        out[str(p.relative_to(repo))] = (tier, len(p.read_text(errors="replace")), cap)
    for name, cap in (("STATUS.md", BUDGET["STATUS.md"]), ("AGENTS.md", BUDGET["AGENTS.md"]),
                      ("PROTOCOL.md", BUDGET["PROTOCOL.md"])):
        if (repo / name).is_file():
            add(repo / name, "T0" if name == "STATUS.md" else "T1", cap)
    claude = repo / "CLAUDE.md"
    if claude.is_file():
        stub = claude.read_text().lstrip().startswith("@AGENTS.md")
        add(claude, "T1" if stub else "T2", BUDGET["CLAUDE.md:stub"] if stub else None)
    for p in sorted((repo / "docs").rglob("*.md")) if (repo / "docs").is_dir() else []:
        add(p, "T2", None)
    for p in sorted((repo / "workstreams").glob("*.md")) if (repo / "workstreams").is_dir() else []:
        add(p, "T3", BUDGET["workstream"])
    for p in sorted((repo / "experiments").rglob("*.md")) if (repo / "experiments").is_dir() else []:
        add(p, "T3", None)
    for pattern in ("COLLAB.md", "workstreams/closed/*.md", ".collab/*", "reviewers/packets/*", "reviewers/prompts/*"):
        for p in sorted(repo.glob(pattern)):
            if p.is_file():
                add(p, "T4", None)
    return out


def memory_sizes(directory):
    d = Path(directory).expanduser()
    files = {p.name: len(p.read_text(errors="replace")) for p in sorted(d.glob("*.md"))}
    return files, sum(files.values())


def load_baseline(repo):
    p = repo / BASELINE
    return json.loads(p.read_text()) if p.is_file() else {}


def limit(cap, base):
    """An existing overage's recorded baseline is its effective limit (v6 §2)."""
    return base if base is not None and base > cap else cap


def check_budgets(repo, errors):
    base = load_baseline(repo)
    files, t2 = tiers(repo), 0
    for rel, (tier, chars, cap) in files.items():
        if tier == "T2":
            t2 += chars
        if cap is not None and chars > limit(cap, base.get("files", {}).get(rel)):
            errors.append(f"budget: {rel} has {chars} characters (limit {limit(cap, base.get('files', {}).get(rel))})")
    t2_base = base.get("tiers", {}).get("T2")
    if t2 > limit(BUDGET["T2"], t2_base):
        errors.append(f"budget: T2 knowledge totals {t2} characters (limit {limit(BUDGET['T2'], t2_base)})")
    if t2_base is not None and t2_base > BUDGET["T2"]:
        # Over-budget tier: no T2 file may grow or appear until compaction.
        t2_files = base.get("t2_files", {})
        for rel, (tier, chars, _) in files.items():
            if tier == "T2" and chars > t2_files.get(rel, 0):
                errors.append(f"budget: T2 file {rel} grew to {chars} characters while T2 is over budget (baseline {t2_files.get(rel, 0)})")
    proto = GATEWAY / "PROTOCOL.md"
    if repo != GATEWAY and proto.is_file() and len(proto.read_text()) > BUDGET["PROTOCOL.md"]:
        errors.append(f"budget: gateway PROTOCOL.md exceeds {BUDGET['PROTOCOL.md']} characters")
    if base.get("agent_cache"):
        check_memory(base["agent_cache"], errors)


def check_memory(mem, errors):
    if not Path(mem["dir"]).is_dir():
        errors.append(f"budget: agent cache directory {mem['dir']} is missing")
        return
    sizes, total = memory_sizes(mem["dir"])
    if total > limit(BUDGET["memory:total"], mem.get("total")):
        errors.append(f"budget: agent cache totals {total} characters (limit {limit(BUDGET['memory:total'], mem.get('total'))})")
    for name, chars in sizes.items():
        cap = BUDGET["memory:index"] if name == "MEMORY.md" else BUDGET["memory:entry"]
        if chars > limit(cap, mem.get("files", {}).get(name)):
            errors.append(f"budget: agent cache {name} has {chars} characters (limit {limit(cap, mem.get('files', {}).get(name))})")


# ------------------------------------------------------------------- checks

def check_links(repo, errors):
    targets = [repo / "AGENTS.md", repo / "STATUS.md"] + workstreams(repo)
    for f in targets:
        if not f.is_file():
            continue
        for link in re.findall(r"\]\(([^)\s]+)\)", f.read_text()):
            if re.match(r"^(https?:|mailto:|#)", link):
                continue
            if not (f.parent / link.split("#", 1)[0]).exists():
                errors.append(f"link: {f.relative_to(repo)} -> {link} does not resolve")


def review_statements(ws):
    """A workstream's Reviews-section text outside fenced code blocks and HTML
    comments: where an owner records active statements about review artifacts.
    A fence closes only on the same character, at least as long, with nothing
    after it; '<!--' inside an inline code span does not open a comment."""
    out, fence, comment = [], None, False
    for line in ws.sections.get("Reviews", []):
        stripped = line.strip()
        if comment:
            comment = "-->" not in line
            continue
        m = re.match(r"^(`{3,}|~{3,})", stripped)
        if fence:
            if m and m.group(1)[0] == fence[0] and len(m.group(1)) >= len(fence) and not stripped[len(m.group(1)):].strip():
                fence = None
            continue
        if m:
            fence = m.group(1)
            continue
        bare = re.sub(r"(`+)(?:(?!\1).)+?\1", "", line)
        if "<!--" in bare:
            comment = "-->" not in bare.split("<!--", 1)[1]
            continue
        out.append(line)
    return "\n".join(out)


def extraction_error(f, rel, ws_text):
    """Why a .collab '<stem>.extracted.md' is not an accepted owner extraction of a
    failed invocation's review text, or None. It qualifies only beside the wrapper's
    '<stem>.diagnostic.json' recording a non-zero exit, with a '.sha256' sidecar
    whose first field is its SHA-256, and when a line in a workstream's Reviews
    section (outside code fences and HTML comments) reads exactly
    "Owner extraction of a failed invocation: `<path>`" (the owner's classification)."""
    stem = f.name[: -len(".extracted.md")]
    diag = f.with_name(stem + ".diagnostic.json")
    side = f.with_name(f.name + ".sha256")
    if not diag.is_file():
        return f"no {stem}.diagnostic.json beside it"
    try:
        code = json.loads(diag.read_text()).get("exit_code")
    except (OSError, UnicodeDecodeError, ValueError, AttributeError, RecursionError):
        return f"{stem}.diagnostic.json is unreadable or malformed"
    if not isinstance(code, int) or isinstance(code, bool) or code == 0:
        return f"{stem}.diagnostic.json records no failed exit code"
    if not side.is_file():
        return "no checksum sidecar"
    try:
        digest = side.read_text().split()
        actual = hashlib.sha256(f.read_bytes()).hexdigest()
    except (OSError, UnicodeDecodeError):
        return "checksum sidecar or extraction is unreadable"
    if not digest or digest[0] != actual:
        return "checksum sidecar is malformed or does not match"
    if not re.search(rf"(?m)^\s*(?:- )?Owner extraction of a failed invocation: `{re.escape(rel)}`\.?[ \t]*$", ws_text):
        return f"no workstream line 'Owner extraction of a failed invocation: `{rel}`'"
    return None


def standards_pin(repo):
    agents = repo / "AGENTS.md"
    m = re.search(r"(?m)^Standards: reviewer-agent-gateway@([0-9a-f]{7,40})\s*$", agents.read_text()) if agents.is_file() else None
    return m.group(1) if m else None


def owner_named(value, registry):
    """True if an Owner line names exactly one owner. Only the head of the
    line counts: the text before the first "(", ";" or ",", which carries
    notes such as "(from Codex, ...)". Accepted heads: an owner agent alone
    ("Copilot"), or the pre-Phase-1 form "sponsor's GitHub Copilot agent".
    Earlier Owner lines are never rewritten, so that form stays valid."""
    owners, known = set(agents.owners(registry)), set(registry["channels"])
    head = re.split(r"[(;,]", value, maxsplit=1)[0].strip()
    words = [w.lower() for w in re.findall(r"\w+", head)]
    if re.fullmatch(r"\w+", head) and head.lower() in owners:
        return True
    m = re.fullmatch(r"(?:the )?(?:sponsor|user)'s (?:github )?(\w+) agent", head, re.I)
    return bool(m) and m.group(1).lower() in owners and len(set(words) & known) == 1


def record(repo):
    errors = []
    base = load_baseline(repo)
    legacy = set(base.get("legacy_collab", []))
    indexed = set()
    pin = standards_pin(repo)
    in_git = git(repo, "rev-parse", "--git-dir")[0] == 0
    # C/F: an adopted repository (one with workstreams/) must have a baseline,
    # whose legacy list may only shrink from its first committed version.
    if (repo / "workstreams").is_dir() and not base:
        errors.append(f"{BASELINE} is missing; run 'docs-check.py report <repo> --write-baseline' at adoption")
    if in_git and base and git(repo, "ls-files", "--error-unmatch", BASELINE)[0] == 0:
        code, first_rev = git(repo, "log", "--diff-filter=A", "--format=%H", "--", BASELINE)
        first_rev = first_rev.split()[-1] if first_rev else ""
        code, first = git(repo, "show", f"{first_rev}:{BASELINE}") if first_rev else (1, "")
        if code == 0:
            grown = legacy - set(json.loads(first).get("legacy_collab", []))
            if grown:
                errors.append(f"{BASELINE}: legacy list grew after its first commit: {sorted(grown)[:3]}")
    if repo == GATEWAY and base and "agent_cache" not in base:
        errors.append(f"{BASELINE}: the gateway baseline must record the agent cache (report --memory DIR --add-memory)")
    if repo != GATEWAY and base:
        # DOCS_CHECK_GATEWAY_BASELINE exists only so tests do not read live memory.
        override = os.environ.get("DOCS_CHECK_GATEWAY_BASELINE")
        gateway_base = json.loads(Path(override).read_text()) if override else load_baseline(GATEWAY)
        if "agent_cache" not in gateway_base:
            errors.append("the gateway baseline records no agent cache, so the memory budget is unenforced")
        else:
            check_memory(gateway_base["agent_cache"], errors)
    registry = agents.load()
    sets = [Workstream(repo, w) for w in workstreams(repo)]
    mapped_before = legacy_owner_map(repo, sets, errors)
    for ws in sets:
        wpath = ws.path
        name = wpath.relative_to(repo)
        errors.extend(f"{name}: {e}" for e in task_errors(ws, registry))
        if not ws.header.get("Owner"):
            errors.append(f"{name}: no Owner line")
        for value in ws.header.get("Owner", []):
            if not owner_named(value, registry):
                errors.append(f"{name}: Owner must name one of {', '.join(agents.owners(registry))}: {value[:60]}")
        errors.extend(f"{name}: {p}" for p in ws.problems)
        for rnd, rel in sorted(ws.reviews.items()):
            art = (repo / rel)
            indexed.add(str(art.resolve()))
            if not art.is_file():
                errors.append(f"{name}: r{rnd:02d} artifact {rel} does not exist")
                continue
            arel = str(art.relative_to(repo))
            side = art.with_name(art.name + ".sha256")
            digest = side.read_text().split() if side.is_file() else []
            if not digest or digest[0] != hashlib.sha256(art.read_bytes()).hexdigest():
                errors.append(f"{name}: r{rnd:02d} artifact {rel} checksum missing, malformed, or mismatched")
            for f in (art, side):
                frel = str(f.relative_to(repo))
                if in_git and git(repo, "ls-files", "--error-unmatch", frel)[0] != 0:
                    errors.append(f"{name}: {frel} is not tracked; review evidence must be committed")
                elif in_git:
                    # A newly staged artifact is not yet in HEAD; that is an addition
                    # about to be committed, not an edit (found in the pilot).
                    in_head = git(repo, "cat-file", "-e", f"HEAD:{frel}")[0] == 0
                    if in_head and git(repo, "diff", "--quiet", "HEAD", "--", frel)[0] != 0:
                        errors.append(f"{name}: {frel} has uncommitted changes (artifacts are never edited)")
                    if git(repo, "log", "--format=%H", "--diff-filter=MDR", "--", frel)[1]:
                        errors.append(f"{name}: {frel} was modified, deleted, or renamed after its first commit")
                    if len(git(repo, "log", "--format=%H", "--diff-filter=A", "--", frel)[1].split()) > 1:
                        errors.append(f"{name}: {frel} was added more than once (replaced)")
            reviewer, owner, authors, models, reviewer_model = artifact_identity(art)
            try:
                agents.check(registry, reviewer, owner, authors, models, reviewer_model)
            except agents.IdentityError as exc:
                errors.append(f"{name}: r{rnd:02d} breaks reviewer independence: {exc}")
            if arel not in legacy:
                errors.extend(f"{name}: {e}" for e in
                              copilot_artifact_errors(ws, rnd, art, owner, authors, models, mapped_before))
            items, dupes = labeled_items(art)
            errors.extend(f"{name}: r{rnd:02d} has duplicate label {d}" for d in dupes)
            post_adoption = arel not in legacy
            if post_adoption:
                v = subprocess.run([sys.executable, str(VALIDATOR)], input=artifact_text(art), capture_output=True, text=True)
                if v.returncode != 0:
                    errors.append(f"{name}: r{rnd:02d} fails the output contract: {v.stderr.strip()}")
            if not items and verdict(art) != "accept":
                errors.append(f"{name}: r{rnd:02d} artifact {rel} has no labeled items but its verdict requires them")
            expect = {f"R{rnd:02d}-{i}": s for i, (s, _) in items.items()}
            have = {k: v for k, v in ws.rows.items() if int(ROW_ID.match(k).group(1)) == rnd}
            for rid in sorted(set(expect) - set(have)):
                errors.append(f"{name}: no disposition row for {rid} ({expect[rid]})")
            for rid in sorted(set(have) - set(expect)):
                errors.append(f"{name}: row {rid} matches no item in r{rnd:02d}")
            for rid in sorted(set(have) & set(expect)):
                if have[rid]["severity"] != expect[rid]:
                    errors.append(f"{name}: row {rid} severity {have[rid]['severity']!r} != review {expect[rid]!r}")
            # Only the user may lift the review budget (review-budget.py).
            # decision_entries only returns '- <date>, user, scope:' entries.
            if budget_override(art) and not any("budget override" in e[1].lower() and re.search(rf"\br{rnd:02d}\b", e[1])
                                                for e in decision_entries(ws)):
                errors.append(f"{name}: r{rnd:02d} ran with a review budget override but no user Decisions entry approves a 'budget override' for r{rnd:02d}")
            rev = wrapper_revision(art)
            if post_adoption and rev is None:
                errors.append(f"{name}: r{rnd:02d} has no wrapper revision (post-adoption reviews need provenance)")
            if rev is not None and post_adoption:
                if rev == "unversioned" or rev.endswith("(dirty)"):
                    errors.append(f"{name}: r{rnd:02d} captured from an unversioned or dirty wrapper ({rev})")
                elif pin:
                    # A review may use the pinned standards or older ones in force when
                    # it was captured; never newer standards than the branch declares.
                    code, _ = git(GATEWAY, "merge-base", "--is-ancestor", rev.split()[0], pin)
                    if code != 0:
                        errors.append(f"{name}: r{rnd:02d} wrapper revision {rev[:12]} is newer than, or unrelated to, the standards pin {pin[:12]}")
        for rid in ws.rows:
            if int(ROW_ID.match(rid).group(1)) not in ws.reviews:
                errors.append(f"{name}: row {rid} refers to a round missing from the review index")
    ws_text = "\n".join(review_statements(ws) for ws in sets)
    collab = repo / ".collab"
    for f in sorted(collab.iterdir()) if collab.is_dir() else []:
        if not f.is_file() or f.name.endswith((".sha256", ".diagnostic.json")) or f.name.startswith("."):
            continue
        rel = str(f.relative_to(repo))
        if rel in legacy:
            continue
        if f.name.endswith(".extracted.md"):
            reason = extraction_error(f, rel, ws_text)
            if reason:
                errors.append(f".collab: {rel} is an extraction that does not qualify: {reason}")
            continue
        if not is_review_artifact(f):
            errors.append(f".collab: {rel} is not a recognizable review artifact")
        elif str(f.resolve()) not in indexed:
            errors.append(f".collab: {rel} is not in any workstream review index")
    if base and repo != GATEWAY and not pin:
        errors.append("AGENTS.md has no 'Standards: reviewer-agent-gateway@<commit>' pin")
    check_links(repo, errors)
    check_budgets(repo, errors)
    return errors


def owner_heads(ws):
    """The owners an Owner line names, lower case ("sponsor's GitHub Copilot agent" -> copilot)."""
    heads = set()
    for value in ws.header.get("Owner", []):
        head = re.split(r"[(;,]", value, maxsplit=1)[0].strip()
        m = re.fullmatch(r"(?:the )?(?:sponsor|user)'s (?:github )?(\w+) agent", head, re.I)
        heads.add((m.group(1) if m else head).lower())
    return heads


def legacy_owner_map(repo, sets, errors):
    """The date of the one user Decisions entry, across the repository's workstreams,
    that maps legacy '--owner codex' artifacts of Copilot work to Copilot (D10)."""
    found = [(day, ws.path.relative_to(repo)) for ws in sets for day, text in decision_entries(ws)
             if LEGACY_MAP.search(text)]
    if len(found) > 1:
        errors.append(f"more than one 'Legacy owner map' Decisions entry: {', '.join(str(w) for _, w in found)}")
    return found[0][0] if found else None


def first_added(repo, rel):
    """Date of the commit that first added rel, following renames; None if unknown."""
    code, out = git(repo, "log", "--follow", "--diff-filter=A", "--format=%cs", "--", rel)
    return out.split()[-1] if code == 0 and out.split() else None


def is_integration(tid):
    return bool(INTEGRATION_ID.match(tid))


def task_errors(ws, registry):
    """Task-table rows are complete and resolvable (D2); a batch row carries its
    members' identity (D6); an integration row I<n> reviews main@<commit> and
    carries the identity of the merged tasks it covers (D7)."""
    errors = []
    for tid, row in ws.tasks.items():
        if not row["authors"] or not row["models"]:
            errors.append(f"task {tid} needs an Author and Author-models")
        for a in row["authors"]:
            if a not in registry["channels"]:
                errors.append(f"task {tid}: unknown author {a!r}")
        for m in row["models"]:
            try:
                agents.model_vendor(registry, m)
            except agents.IdentityError as exc:
                errors.append(f"task {tid}: {exc}")
        state, integ = row["state"], is_integration(tid)
        if state not in TASK_STATES:
            errors.append(f"task {tid}: state must be one of {', '.join(TASK_STATES)} (got {state!r})")
        if integ:
            if state == "batch" or not row["covers"]:
                errors.append(f"integration task {tid} needs Covers and may not be a batch")
            if not re.fullmatch(r"main@[0-9a-f]{7,40}", row["branch"]):
                errors.append(f"integration task {tid}: Branch must be main@<commit reviewed>")
        else:
            if row["covers"] and state != "batch":
                errors.append(f"task {tid}: only batch rows and integration rows (I<n>) have Covers")
            if state not in ("planned", "batch") and not row["branch"].strip("-— "):
                errors.append(f"task {tid}: a {state} task needs its Branch")
            if state in ("draft", "ready", "merged") and not row["pr"].strip("-— "):
                errors.append(f"task {tid}: a {state} task needs its PR")
        missing = set()
        for c in row["covers"]:
            other = ws.tasks.get(c)
            if not other or is_integration(c) or other["state"] == "batch" or c == tid:
                errors.append(f"task {tid} covers {c!r}, which is not a task row")
                continue
            if integ and other["state"] != "merged":
                errors.append(f"task {tid} covers {c}, which is not merged")
            missing |= set(other["models"]) - set(row["models"])
            missing |= {"author " + a for a in set(other["authors"]) - set(row["authors"])}
        if missing:
            errors.append(f"task {tid} omits {', '.join(sorted(missing))} of the tasks it covers")
    return errors


def copilot_artifact_errors(ws, rnd, art, owner, authors, models, mapped_before):
    """Artifact identity matches the workstream for Copilot work (D10). Any
    artifact naming a task in the Tasks table must match that row, whoever
    the recorded owner is."""
    heads = owner_heads(ws)
    task = artifact_task(art)
    row = ws.tasks.get(task) if task else None
    copilot = owner == "copilot" or "copilot" in authors
    if not copilot and not row and "copilot" not in heads:
        return []
    errors = []
    tag = f"r{rnd:02d}"
    effective = owner
    if owner == "codex" and "codex" not in heads and "copilot" in heads:
        # Owner record only: a mapped legacy artifact predates --task and
        # --author-model, so its author models stay unknown (D10).
        added = first_added(ws.repo, str(art.relative_to(ws.repo)))
        if mapped_before and added and added <= mapped_before:
            effective = "copilot"
    if effective and effective not in heads:
        errors.append(f"{tag} owner {owner!r} is not an owner named in the workstream's Owner lines")
    if copilot and not task:
        errors.append(f"{tag} is Copilot work but records no --task")
    elif copilot and not row:
        errors.append(f"{tag} task {task!r} has no row in the Tasks table")
    if row:
        if set(models) != set(row["models"]):
            errors.append(f"{tag} author models {sorted(models)} != task {task} Author-models {sorted(row['models'])}")
        if not set(row["authors"]) <= set(authors) | {owner}:
            errors.append(f"{tag} authors {sorted(set(authors) | {owner})} omit task {task} Author {row['authors']}")
    return errors


def integration_errors(ws):
    """Merged tasks not yet covered by an accepted, committed integration review
    whose row's Covers is unchanged since that review was committed (D7)."""
    errors, covered = [], set()
    wrel = str(ws.path.relative_to(ws.repo))
    for rnd, rel in sorted(ws.reviews.items()):
        art = ws.repo / rel
        tid = artifact_task(art) if art.is_file() else None
        if not tid or not is_integration(tid) or tid not in ws.tasks or verdict(art) != "accept":
            continue
        code, out = git(ws.repo, "log", "--diff-filter=A", "--format=%H", "--", rel)
        commit = out.split()[-1] if code == 0 and out.split() else None
        code, then = git(ws.repo, "show", f"{commit}:{wrel}") if commit else (1, "")
        if code != 0:
            errors.append(f"r{rnd:02d} integration review is not committed with its workstream")
            continue
        old_rows = Workstream.parse_tasks(then)
        if tid not in old_rows or old_rows[tid]["covers"] != ws.tasks[tid]["covers"] \
                or old_rows[tid]["branch"] != ws.tasks[tid]["branch"]:
            errors.append(f"r{rnd:02d}: task {tid} Covers or Branch changed after its review; add a new integration row")
            continue
        covered |= set(ws.tasks[tid]["covers"])
    errors += [f"task {tid} is merged but no accepted integration review covers it"
               for tid, row in sorted(ws.tasks.items())
               if row["state"] == "merged" and not is_integration(tid) and tid not in covered]
    return errors


def transfer(repo, wrel):
    errors = record(repo)
    ws = Workstream(repo, repo / wrel)
    _, dirty = git(repo, "status", "--porcelain", "--untracked-files=no")
    if dirty:
        errors.append("transfer: uncommitted tracked changes")
    code, upstream = git(repo, "rev-parse", "@{u}")
    _, head = git(repo, "rev-parse", "HEAD")
    if code != 0 or upstream != head:
        errors.append("transfer: branch is not equal to its pushed upstream")
    blocks = re.split(r"(?m)^### Handoff", ws.text)
    if len(blocks) < 2:
        errors.append(f"transfer: {wrel} has no '### Handoff' block")
        return errors
    block = blocks[-1]
    inv = re.search(r"(?m)^Inventory: `([^`]+)`; (\d+) untracked, (\d+) ignored; needed by next owner: (.+)$", block)
    if not inv:
        errors.append("transfer: Inventory must read 'Inventory: `<command>`; <n> untracked, <n> ignored; needed by next owner: <paths> | none'")
    else:
        code, status = git(repo, "status", "--porcelain", "--ignored", "--untracked-files=all")
        if code != 0:
            errors.append("transfer: git status failed")
        lines = status.splitlines()
        actual = (sum(l.startswith("?? ") for l in lines), sum(l.startswith("!! ") for l in lines))
        if (int(inv.group(2)), int(inv.group(3))) != actual:
            errors.append(f"transfer: inventory says {inv.group(2)} untracked, {inv.group(3)} ignored; git status shows {actual[0]} and {actual[1]}")
    if inv and inv.group(4).strip() != "none":
        for path in [x.strip() for x in inv.group(4).split(",")]:
            if git(repo, "ls-files", "--error-unmatch", path)[0] != 0:
                errors.append(f"transfer: needed file {path} is not committed")
    obs = re.search(r"(?m)^Runtime observation: (.+)$", block)
    operational = (ws.header.get("Operational") or ["yes"])[-1].strip().lower() != "no"
    if not obs:
        errors.append("transfer: latest handoff block lacks 'Runtime observation:'")
    elif obs.group(1).strip() == "n/a (not operational)":
        if operational:
            errors.append("transfer: 'n/a (not operational)' needs 'Operational: no' in the workstream header")
    else:
        t = re.match(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}) `[^`]+` -> \S", obs.group(1))
        if not t:
            errors.append("transfer: Runtime observation must read 'YYYY-MM-DD HH:MM `<command>` -> <result>'")
        else:
            try:
                age = (datetime.now() - datetime.strptime(t.group(1), "%Y-%m-%d %H:%M")).total_seconds()
            except ValueError:
                errors.append(f"transfer: Runtime observation time {t.group(1)} is not a valid date")
                return errors
            if age < -60:
                errors.append("transfer: Runtime observation time is in the future")
            elif age > MAX_OBSERVATION_AGE:
                errors.append("transfer: Runtime observation is older than two hours; observe again immediately before handoff")
    if not re.search(r"(?m)^Restart sequence: \S", block):
        errors.append("transfer: latest handoff block lacks 'Restart sequence:'")
    return errors


def decision_entries(ws):
    """Dated Decisions entries: '- YYYY-MM-DD, user, scope: ...' plus continuation lines."""
    entries, current = [], None
    for line in ws.sections.get("Decisions", []):
        m = re.match(r"^- (\d{4}-\d{2}-\d{2}), user, scope: (.+)$", line)
        if m:
            current = [m.group(1), line]
            entries.append(current)
        elif current and line.startswith("  "):
            current[1] += " " + line.strip()
        elif not line.strip():
            current = None
    return entries


def disposition_errors(ws, rid):
    """Errors for one row's final disposition (v6 §3.4, tightened by r06/r07)."""
    row = ws.rows[rid]
    rnd = int(ROW_ID.match(rid).group(1))
    sev, disp = row["severity"], row["disposition"]
    strict = sev in ("blocker", "condition")
    m = re.match(r"^verified r(\d+)$", disp)
    if m:
        # The later review must contain the exact status line "<ID> is resolved."
        # at the start of a line: affirmative, specific, and in the reviewer's words.
        # Trailing spaces, tabs or a carriage return are ignored (Codex r03 of
        # 2026-11-21-api-validator-reason ended the line with two spaces; a JSON
        # artifact's response may keep CRLF); any other trailing text still fails.
        later = int(m.group(1))
        if later <= rnd or later not in ws.reviews:
            return [f"{rid}: verified cites r{later:02d}, which is not a later indexed round"]
        text = artifact_text(ws.repo / ws.reviews[later])
        if not re.search(rf"(?m)^{re.escape(rid)} is resolved\.[ \t\r]*$", text):
            return [f"{rid}: r{later:02d} has no line '{rid} is resolved.'"]
        if re.search(rf"(?m)^\W*{re.escape(rid)} remains open", text):
            return [f"{rid}: r{later:02d} also says {rid} remains open"]
        return []
    m = re.match(r'^user-decided (\d{4}-\d{2}-\d{2}) "(.+)"$', disp)
    if m:
        # The quote must sit in a Decisions entry of the same date with a stated
        # scope, and name this item. Authenticity of the transcription is policy.
        day, quote = m.group(1), m.group(2)
        if not re.search(rf"\b{re.escape(rid)} accepted\b", quote, re.I):
            return [f"{rid}: user-decided quote must say '{rid} accepted'"]
        if not any(d == day and norm(quote) in norm(text) for d, text in decision_entries(ws)):
            return [f"{rid}: no Decisions entry dated {day} with a scope contains the quote"]
        return []
    if strict:
        return [f"{rid}: a {sev} closes only by 'verified rNN' or 'user-decided <date> \"<quote>\"' (got {disp!r})"]
    m = re.match(r"^fixed ([0-9a-f]{7,40})$", disp)
    if m:
        if git(ws.repo, "cat-file", "-e", m.group(1) + "^{commit}")[0] != 0:
            return [f"{rid}: fixed commit {m.group(1)} does not exist"]
        if git(ws.repo, "merge-base", "--is-ancestor", m.group(1), "@{u}")[0] != 0:
            return [f"{rid}: fixed commit {m.group(1)} is not in pushed history"]
        return []
    m = re.match(r"^rejected: (.+)$", disp)
    if m and len(m.group(1)) >= 20:
        return []
    return [f"{rid}: no valid final disposition (got {disp!r})"]


def done(repo, wrel):
    errors = record(repo)
    ws = Workstream(repo, repo / wrel)
    for rid in sorted(ws.rows):
        if ws.rows[rid]["status"] != "closed":
            errors.append(f"{rid}: status is {ws.rows[rid]['status']!r}, not 'closed'")
        errors.extend(disposition_errors(ws, rid))
    errors.extend(integration_errors(ws))
    log = ws.section("Log")
    for rnd in sorted(ws.reviews):
        if f"r{rnd:02d}: {CLOSURE}" not in log:
            errors.append(f"closure: log lacks 'r{rnd:02d}: {CLOSURE}'")
    return errors


# ------------------------------------------------------------------- report

def report(repo, write=False, lower=False, memory=None):
    files = tiers(repo)
    totals = {}
    for rel, (tier, chars, cap) in files.items():
        totals[tier] = totals.get(tier, 0) + chars
        flag = f" (cap {cap})" if cap else ""
        print(f"{tier}  {chars:>9}  {rel}{flag}")
    for tier in sorted(totals):
        print(f"total {tier}: {totals[tier]}")
    mem = None
    if memory:
        sizes, total = memory_sizes(memory)
        print(f"total A (agent cache {memory}): {total}")
        mem = {"dir": str(Path(memory).expanduser()), "files": sizes, "total": total}
    path = repo / BASELINE
    if write:
        if path.exists():
            raise SystemExit(f"{BASELINE} exists; baselines are never raised (use --lower)")
        code, untracked = git(repo, "ls-files", "--others", "--exclude-standard", "--", ".collab")
        if code != 0 or untracked:
            raise SystemExit("refusing baseline: .collab has untracked files (or Git failed); commit or index them first")
        _, tracked = git(repo, "ls-files", "--", ".collab")
        base = {"created": date.today().isoformat(),
                "files": {r: c for r, (_, c, cap) in files.items() if cap and c > cap},
                "tiers": {"T2": totals.get("T2", 0)},
                "t2_files": {r: c for r, (t, c, _) in files.items() if t == "T2"},
                "legacy_collab": sorted(tracked.splitlines())}
        if mem:
            base["agent_cache"] = mem
        path.write_text(json.dumps(base, indent=1, sort_keys=True) + "\n")
        print(f"wrote {path}")
    elif "--add-memory" in sys.argv:
        base = load_baseline(repo)
        if not mem:
            raise SystemExit("--add-memory needs --memory DIR")
        if "agent_cache" in base:
            raise SystemExit("agent cache already in baseline; use --lower")
        base["agent_cache"] = mem
        path.write_text(json.dumps(base, indent=1, sort_keys=True) + "\n")
        print(f"added agent cache to {path}")
    elif lower:
        base = load_baseline(repo)
        for rel in list(base.get("files", {})):
            if rel in files:
                base["files"][rel] = min(base["files"][rel], files[rel][1])
        if "T2" in base.get("tiers", {}):
            base["tiers"]["T2"] = min(base["tiers"]["T2"], totals.get("T2", 0))
        for rel in list(base.get("t2_files", {})):
            base["t2_files"][rel] = min(base["t2_files"][rel], files[rel][1]) if rel in files else 0
        if mem and "agent_cache" in base:
            old = base["agent_cache"]
            old["total"] = min(old["total"], mem["total"])
            old["files"] = {n: min(c, old["files"].get(n, c)) for n, c in mem["files"].items()}
        path.write_text(json.dumps(base, indent=1, sort_keys=True) + "\n")
        print(f"lowered {path}")


def dispositions(artifact, rnd):
    items, _ = labeled_items(Path(artifact))
    for item, (sev, _) in sorted(items.items(), key=lambda x: (x[0][0] != "F", int(x[0][1:]))):
        print(f"| R{int(rnd):02d}-{item} | {sev} | | open |")


def main(argv):
    if len(argv) < 2:
        raise SystemExit(__doc__)
    mode = argv[1]
    if mode == "dispositions" and len(argv) == 4:
        return dispositions(argv[2], argv[3].lstrip("r"))
    if mode == "report" and len(argv) >= 3:
        mem = argv[argv.index("--memory") + 1] if "--memory" in argv else None
        return report(Path(argv[2]).resolve(), "--write-baseline" in argv, "--lower" in argv, mem)
    if mode == "record" and len(argv) == 3:
        errors = record(Path(argv[2]).resolve())
    elif mode == "integration" and len(argv) == 4:
        repo = Path(argv[2]).resolve()
        errors = record(repo) + integration_errors(Workstream(repo, repo / argv[3]))
    elif mode in ("transfer", "done") and len(argv) == 4:
        errors = (transfer if mode == "transfer" else done)(Path(argv[2]).resolve(), argv[3])
    else:
        raise SystemExit(__doc__)
    for e in errors:
        print(e)
    print(f"docs-check {mode}: {'FAIL' if errors else 'PASS'} ({len(errors)} errors)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv) or 0)
