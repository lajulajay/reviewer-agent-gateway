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
from datetime import date
from pathlib import Path

GATEWAY = Path(__file__).resolve().parent
BASELINE = "docs-baseline.json"
BUDGET = {"STATUS.md": 4000, "AGENTS.md": 12000, "PROTOCOL.md": 12000,
          "CLAUDE.md:stub": 1500, "workstream": 30000, "T2": 60000,
          "memory:index": 2000, "memory:entry": 1500, "memory:total": 15000}
REVIEW_HEADERS = ("# Claude review", "# Codex review", "# Kimi review")
FINDING = re.compile(r"(?m)^\s*(?:[-*]\s*)?\**F(\d+)\**\s*\[(blocker|major|minor)\]")
CONDITION = re.compile(r"(?m)^\s*(?:[-*]\s*)?\**C(\d+)\**\s*:")
ROW_ID = re.compile(r"^R(\d+)-([FC]\d+)$")
CLOSURE = "raw review compared with its rows; no unlabeled actionable item"


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
    """Return {ID: severity} for a review; conditions have severity 'condition'.

    Labeled output (F<n> [severity]: / C<n>:) is parsed directly. A legacy review
    without labels is parsed from numbered items under Blocker/Major/Minor
    headings, numbered continuously as F<n>.
    """
    text = artifact_text(path)
    items = {f"F{m.group(1)}": m.group(2) for m in FINDING.finditer(text)}
    items.update({f"C{m.group(1)}": "condition" for m in CONDITION.finditer(text)})
    if items:
        return items
    severity = None
    for line in text.splitlines():
        heading = re.match(r"^#+\s*(.*)", line)
        if heading:
            h = heading.group(1).lower()
            severity = ("blocker" if "blocker" in h else "major" if "major" in h
                        else "minor" if "minor" in h else None)
            continue
        num = re.match(r"^(\d+)\.\s", line)
        if num and severity:
            items[f"F{num.group(1)}"] = severity
    return items


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
        self.reviews = {}
        for line in self.sections.get("Reviews", []):
            c = cells(line) if line.startswith("|") else []
            m = re.search(r"`([^`]*\.collab/[^`]+)`", line)
            if c and m and re.match(r"^r\d+", c[0]):
                self.reviews[int(re.match(r"^r(\d+)", c[0]).group(1))] = m.group(1)
        self.rows = {}
        for line in self.sections.get("Findings and conditions", []):
            c = cells(line) if line.startswith("|") else []
            if c and ROW_ID.match(c[0]):
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
    if t2 > limit(BUDGET["T2"], base.get("tiers", {}).get("T2")):
        errors.append(f"budget: T2 knowledge totals {t2} characters (limit {limit(BUDGET['T2'], base.get('tiers', {}).get('T2'))})")
    mem = base.get("agent_cache")
    if mem:
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
        for rnd, rel in sorted(ws.reviews.items()):
            art = (repo / rel)
            indexed.add(str(art.resolve()))
            if not art.is_file():
                errors.append(f"{name}: r{rnd:02d} artifact {rel} does not exist")
                continue
            side = art.with_name(art.name + ".sha256")
            if not side.is_file() or side.read_text().split()[0] != hashlib.sha256(art.read_bytes()).hexdigest():
                errors.append(f"{name}: r{rnd:02d} artifact {rel} checksum missing or mismatched")
            items = labeled_items(art)
            if not items:
                errors.append(f"{name}: r{rnd:02d} artifact {rel} has no labeled or legacy-numbered items")
            expect = {f"R{rnd:02d}-{i}": s for i, s in items.items()}
            have = {k: v for k, v in ws.rows.items() if int(ROW_ID.match(k).group(1)) == rnd}
            for rid in sorted(set(expect) - set(have)):
                errors.append(f"{name}: no disposition row for {rid} ({expect[rid]})")
            for rid in sorted(set(have) - set(expect)):
                errors.append(f"{name}: row {rid} matches no item in r{rnd:02d}")
            for rid in sorted(set(have) & set(expect)):
                if have[rid]["severity"] != expect[rid]:
                    errors.append(f"{name}: row {rid} severity {have[rid]['severity']!r} != review {expect[rid]!r}")
            rev = wrapper_revision(art)
            if rev is not None and str(art.relative_to(repo)) not in legacy:
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
    else:
        for field in ("Inventory:", "Runtime observation:", "Restart sequence:"):
            if field not in blocks[-1]:
                errors.append(f"transfer: latest handoff block lacks '{field}'")
    return errors


def disposition_errors(ws, rid, seen=()):
    row = ws.rows[rid]
    rnd, item = int(ROW_ID.match(rid).group(1)), ROW_ID.match(rid).group(2)
    sev, disp = row["severity"], row["disposition"]
    strict = sev in ("blocker", "condition")
    m = re.match(r'^verified r(\d+) "(.+)"$', disp)
    if m:
        later = int(m.group(1))
        if later <= rnd or later not in ws.reviews:
            return [f"{rid}: verified cites r{later:02d}, which is not a later indexed round"]
        if norm(m.group(2)) not in norm(artifact_text(ws.repo / ws.reviews[later])):
            return [f"{rid}: verified quote does not occur in r{later:02d}"]
        return []
    m = re.match(r'^user-decided (\d{4}-\d{2}-\d{2}) "(.+)"$', disp)
    if m:
        if norm(m.group(2)) not in norm(ws.section("Decisions")):
            return [f"{rid}: user-decided quote does not occur in the Decisions section"]
        return []
    m = re.match(r"^carried (R\d+-[FC]\d+)$", disp)
    if m:
        target = m.group(1)
        # A condition may restate a finding of the same round; a finding may be
        # carried into a later round's re-raised finding. Never backwards.
        if target == rid or target not in ws.rows or int(ROW_ID.match(target).group(1)) < rnd:
            return [f"{rid}: carried target {target} is not this or a later round's row"]
        if target in seen:
            return [f"{rid}: carried chain loops"]
        sub = disposition_errors(ws, target, seen + (rid,))
        return [f"{rid}: carried target is not closed ({e})" for e in sub]
    if strict:
        return [f"{rid}: a {sev} closes only by verified, user-decided, or carried (got {disp!r})"]
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
        collab = repo / ".collab"
        base = {"created": date.today().isoformat(),
                "files": {r: c for r, (_, c, cap) in files.items() if cap and c > cap},
                "tiers": {"T2": totals.get("T2", 0)},
                "legacy_collab": sorted(str(p.relative_to(repo)) for p in collab.iterdir()
                                        if p.is_file()) if collab.is_dir() else []}
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
        if mem and "agent_cache" in base:
            old = base["agent_cache"]
            old["total"] = min(old["total"], mem["total"])
            old["files"] = {n: min(c, old["files"].get(n, c)) for n, c in mem["files"].items()}
        path.write_text(json.dumps(base, indent=1, sort_keys=True) + "\n")
        print(f"lowered {path}")


def dispositions(artifact, rnd):
    for item, sev in sorted(labeled_items(Path(artifact)).items(), key=lambda x: (x[0][0] != "F", int(x[0][1:]))):
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
