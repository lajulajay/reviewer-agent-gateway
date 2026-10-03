#!/usr/bin/env python3
"""Check workspace documentation against the framework (proposal v6).

  docs-check.py record REPO                 records complete, budgets hold
  docs-check.py transfer REPO WORKSTREAM    record + safe to hand off
  docs-check.py done REPO WORKSTREAM        record + every obligation closed
  docs-check.py dispositions ARTIFACT ROUND print empty disposition rows
  docs-check.py report REPO [--write-baseline | --lower] [--memory DIR]

WORKSTREAM is a path relative to REPO (e.g. workstreams/2026-10-03-x.md).
Exit status 0 means pass; 1 means at least one error was printed.
"""

import hashlib
import json
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
REVIEW_HEADERS = ("# Claude review", "# Codex review", "# Kimi review")
FINDING = re.compile(r"^\s*(?:[-*]\s*)?\**F(\d+)\**\s*\[(blocker|major|minor)\]")
CONDITION = re.compile(r"^\s*(?:[-*]\s*)?\**C(\d+)\**\s*:")
OPEN_WORDS = re.compile(r"(?i)\b(remains?|still|open|partial(?:ly)?|unresolved|not (?:yet )?(?:resolved|satisfied|met|addressed)|cannot|unmet)\b")
VALIDATOR = GATEWAY / "reviewer-validate.py"
ROW_ID = re.compile(r"^R(\d+)-([FC]\d+)$")
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
    mem = base.get("agent_cache")
    if mem:
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


def standards_pin(repo):
    agents = repo / "AGENTS.md"
    m = re.search(r"(?m)^Standards: reviewer-agent-gateway@([0-9a-f]{7,40})\s*$", agents.read_text()) if agents.is_file() else None
    return m.group(1) if m else None


def record(repo):
    errors = []
    base = load_baseline(repo)
    legacy = set(base.get("legacy_collab", []))
    indexed = set()
    pin = standards_pin(repo)
    for wpath in workstreams(repo):
        ws = Workstream(repo, wpath)
        name = wpath.relative_to(repo)
        if not ws.header.get("Owner"):
            errors.append(f"{name}: no Owner line")
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
                if git(repo, "ls-files", "--error-unmatch", frel)[0] == 0:
                    if git(repo, "diff", "--quiet", "HEAD", "--", frel)[0] != 0:
                        errors.append(f"{name}: {frel} has uncommitted changes (artifacts are never edited)")
                    if git(repo, "log", "--format=%H", "--diff-filter=M", "--", frel)[1]:
                        errors.append(f"{name}: {frel} was modified after its first commit")
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
            rev = wrapper_revision(art)
            if post_adoption and rev is None:
                errors.append(f"{name}: r{rnd:02d} has no wrapper revision (post-adoption reviews need provenance)")
            if rev is not None and post_adoption:
                if rev == "unversioned" or rev.endswith("(dirty)"):
                    errors.append(f"{name}: r{rnd:02d} captured from an unversioned or dirty wrapper ({rev})")
                elif pin:
                    code, _ = git(GATEWAY, "merge-base", "--is-ancestor", pin, rev.split()[0])
                    if code != 0:
                        errors.append(f"{name}: r{rnd:02d} wrapper revision {rev[:12]} is not the standards pin {pin[:12]} or a descendant")
        for rid in ws.rows:
            if int(ROW_ID.match(rid).group(1)) not in ws.reviews:
                errors.append(f"{name}: row {rid} refers to a round missing from the review index")
    collab = repo / ".collab"
    for f in sorted(collab.iterdir()) if collab.is_dir() else []:
        if not f.is_file() or f.name.endswith((".sha256", ".diagnostic.json")) or f.name.startswith("."):
            continue
        rel = str(f.relative_to(repo))
        if rel in legacy:
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
    elif inv.group(4).strip() != "none":
        for path in [x.strip() for x in inv.group(4).split(",")]:
            if git(repo, "ls-files", "--error-unmatch", path)[0] != 0:
                errors.append(f"transfer: needed file {path} is not committed")
    obs = re.search(r"(?m)^Runtime observation: (.+)$", block)
    if not obs:
        errors.append("transfer: latest handoff block lacks 'Runtime observation:'")
    elif obs.group(1).strip() != "n/a (not operational)":
        t = re.match(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2})", obs.group(1))
        if not t:
            errors.append("transfer: Runtime observation must start with 'YYYY-MM-DD HH:MM' or be 'n/a (not operational)'")
        elif (datetime.now() - datetime.strptime(t.group(1), "%Y-%m-%d %H:%M")).total_seconds() > MAX_OBSERVATION_AGE:
            errors.append("transfer: Runtime observation is older than two hours; observe again immediately before handoff")
    if not re.search(r"(?m)^Restart sequence: \S", block):
        errors.append("transfer: latest handoff block lacks 'Restart sequence:'")
    return errors


def item_text(ws, rid):
    rnd, item = int(ROW_ID.match(rid).group(1)), ROW_ID.match(rid).group(2)
    items, _ = labeled_items(ws.repo / ws.reviews[rnd])
    return items.get(item, ("", ""))[1]


def disposition_errors(ws, rid, seen=(), strict_from=None):
    """Errors for one row. strict_from carries the original strict item through
    a carried chain, so the chain's end must satisfy the original's severity."""
    row = ws.rows[rid]
    rnd = int(ROW_ID.match(rid).group(1))
    sev, disp = row["severity"], row["disposition"]
    strict = sev in ("blocker", "condition") or strict_from is not None
    m = re.match(r'^verified r(\d+) "(.+)"$', disp)
    if m:
        later, quote = int(m.group(1)), m.group(2)
        if later <= rnd or later not in ws.reviews:
            return [f"{rid}: verified cites r{later:02d}, which is not a later indexed round"]
        if norm(quote) not in norm(artifact_text(ws.repo / ws.reviews[later])):
            return [f"{rid}: verified quote does not occur in r{later:02d}"]
        if rid not in quote or OPEN_WORDS.search(quote):
            return [f"{rid}: verified quote must name {rid} and affirm resolution without open-status words"]
        return []
    m = re.match(r'^user-decided (\d{4}-\d{2}-\d{2}) "(.+)"$', disp)
    if m:
        if norm(m.group(2)) not in norm(ws.section("Decisions")):
            return [f"{rid}: user-decided quote does not occur in the Decisions section"]
        if rid not in m.group(2):
            return [f"{rid}: user-decided quote must name {rid}"]
        return []
    m = re.match(r"^carried (R\d+-[FC]\d+)$", disp)
    if m:
        target = m.group(1)
        if target == rid or target not in ws.rows or int(ROW_ID.match(target).group(1)) < rnd:
            return [f"{rid}: carried target {target} is not this or a later round's row"]
        if target in seen:
            return [f"{rid}: carried chain loops"]
        # Explicit mapping, checked in the reviewer's own words: within a round
        # the restating item cites the target's short ID ("C1: ... under F1");
        # across rounds the re-raised target cites this item's full ID
        # ("R01-F1 is partially resolved").
        if int(ROW_ID.match(target).group(1)) == rnd:
            cite, where, text = ROW_ID.match(target).group(2), rid, item_text(ws, rid)
        else:
            cite, where, text = rid, target, item_text(ws, target)
        if not re.search(rf"\b{re.escape(cite)}\b", text):
            return [f"{rid}: carried requires {where}'s review text to cite {cite}"]
        origin = strict_from or (rid if sev in ("blocker", "condition") else None)
        sub = disposition_errors(ws, target, seen + (rid,), origin)
        return [f"{rid}: carried target is not closed ({e})" for e in sub]
    if strict:
        label = f"{sev} (carried from {strict_from})" if strict_from else sev
        return [f"{rid}: a {label} closes only by verified, user-decided, or carried (got {disp!r})"]
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
