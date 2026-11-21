#!/usr/bin/env python3
"""Review tickets: the Copilot coordinator's grant of one review round.

  review-ticket.py issue --workstream FILE --task ID --tier hard|routine
                         --reviewer CHANNEL|auto [--vendor V] --owner O
                         [--author A]... [--author-model M]... [--batch ID]...
                         [--packet-root DIR] --scope PATH... -- OUTPUT
  review-ticket.py check PROVIDER REQUESTED OUTPUT [--owner O] [--author A]...
                         [--author-model M]... [--task ID] [--vendor V]
                         [--packet-root DIR] -- PACKET...
  review-ticket.py list [REPO]

A Copilot sub-agent may run a reviewer wrapper only on a ticket its
coordinator issued (proposal D5). `issue` writes
`<repo>/reviewers/tickets/<output name>.ticket.json` in the repository whose
`.collab/` holds OUTPUT. The ticket fixes the output name (and so the round
number), tier, reviewer channel (or `auto`), Copilot vendor, identity and the
packet scope. `--batch` lists the tasks a routine round covers when several
small tasks share one packet (D6); the ticket's own `--task` is the batch ID.

Every wrapper calls `check` before any model call. When the owner is copilot
and a task is given, a ticket is required; any ticket that exists for the
output is enforced whoever the owner is. For an `auto-` ticket the candidate
output `<channel>-<rest>` is covered. `check` exits 0 when the call matches,
64 when it does not, 66 when a required ticket is missing.

A ticket is a coordination record in the repository, not a credential: it
stops parallel sub-agents racing for names, tiers and the daily pool; it does
not authenticate the coordinator. The wrappers still apply the vendor rule,
budget, packet safety and output checks whatever the ticket says.

`list` prints tickets in REPO whose output has neither artifact nor
diagnostic.
"""

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

GATEWAY = Path(__file__).resolve().parent
CHANNELS = ("claude", "codex", "copilot", "gemini", "kimi")
IDENT = re.compile(r"^[A-Za-z0-9._-]+$")
_ITEM = r"(?:claude|codex|copilot|gemini|kimi)\s+\d+\s*/\s*day"
POOL_LINE = re.compile(r"(?i)\bReview pool:\s*(%s(?:\s*,\s*%s)*)" % (_ITEM, _ITEM))
POOL_ITEM = re.compile(r"(?i)(claude|codex|copilot|gemini|kimi)\s+(\d+)\s*/\s*day")


class Fail(Exception):
    def __init__(self, code, msg):
        super().__init__(msg)
        self.code = code


def _load(name):
    import importlib.util
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), GATEWAY / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def repo_of(output):
    parent = Path(output).expanduser().parent.resolve()
    if parent.name != ".collab":
        raise Fail(64, "OUTPUT must be inside the repository's .collab/ directory")
    return parent.parent


def ticket_dir(repo):
    return Path(repo) / "reviewers" / "tickets"


def output_names(base):
    """The ticket names that may cover an output: its own, then its auto- template."""
    names = [base]
    m = re.match(r"^(claude|codex|copilot|kimi)-(.+\.md)$", base)
    if m:
        names.append("auto-" + m.group(2))
    return names


def find(repo, base):
    """Return (path, body) of the ticket covering output BASE in REPO, or (None, None).

    An unreadable ticket raises Fail(64): a damaged grant never silently lapses.
    """
    for name in output_names(base):
        path = ticket_dir(repo) / (name + ".ticket.json")
        if path.is_symlink():
            raise Fail(64, f"ticket {path.name} is a symbolic link")
        if path.is_file():
            try:
                body = json.loads(path.read_text())
            except (OSError, ValueError) as exc:
                raise Fail(64, f"cannot read ticket {path.name}: {exc}")
            validate(body, path)
            return path, body
    return None, None


def validate(body, path):
    strs = ("owner", "task", "tier", "reviewer", "workstream", "output", "issued")
    lists = ("authors", "author_models", "batch", "scope")
    ok = (isinstance(body, dict) and body.get("version") == 1
          and all(isinstance(body.get(k), str) and body[k] for k in strs)
          and all(isinstance(body.get(k), list) and all(isinstance(v, str) and v for v in body[k]) for k in lists)
          and (body.get("vendor") is None or (isinstance(body["vendor"], str) and re.fullmatch(r"[a-z]+", body["vendor"])))
          and (body.get("packet_root") is None or isinstance(body["packet_root"], str)))
    if not ok:
        raise Fail(64, f"malformed ticket {path.name}")
    if path.name != body["output"] + ".ticket.json":
        raise Fail(64, f"ticket {path.name} does not match its output {body['output']}")
    if body["tier"] not in ("hard", "routine") or (body["batch"] and body["tier"] != "routine"):
        raise Fail(64, f"ticket {path.name}: tier must be hard or routine, and a batch is routine only")
    if body["reviewer"] not in CHANNELS + ("auto",):
        raise Fail(64, f"ticket {path.name}: unknown reviewer {body['reviewer']!r}")
    if body["vendor"] and body["reviewer"] != "copilot":
        raise Fail(64, f"ticket {path.name}: --vendor applies only to copilot")
    if not body["scope"]:
        raise Fail(64, f"ticket {path.name}: empty packet scope")
    return body


def workstream_path(repo, body):
    p = Path(body["workstream"])
    p = (Path(repo) / p) if not p.is_absolute() else p
    return p.resolve()


def decisions_section(text):
    m = re.search(r"(?ms)^## Decisions[ \t]*\n(.*?)(?=^## |\Z)", text)
    return m.group(1) if m else ""


def pool(repo, body, provider):
    """The daily pool for PROVIDER set by a user decision in the ticket's workstream, or None.

    Only `- <date>, user, ...` entries count; the last pool line naming the
    provider wins. The workstream is repository text, so a pool is as
    trustworthy as any other recorded user decision (sponsor-accepted risk,
    2026-11-21).
    """
    try:
        text = workstream_path(repo, body).read_text()
    except OSError:
        return None
    found = None
    for entry in re.split(r"(?m)^- ", decisions_section(text))[1:]:
        if not re.match(r"\d{4}-\d{2}-\d{2},\s*user,", entry):
            continue
        for line in POOL_LINE.finditer(" ".join(entry.split())):
            items = {c.lower(): int(n) for c, n in POOL_ITEM.findall(line.group(1))}
            if provider in items:
                found = items[provider]
    return found


def tier_of(provider, requested):
    if provider == "claude":
        return "hard" if "opus" in requested.lower() else "routine"
    if provider == "gemini":
        return "routine"
    return requested


def _parse(args, multi=("--author", "--author-model", "--scope", "--batch")):
    opts, lists = {}, {k: [] for k in multi}
    while args and args[0] != "--":
        if not args[0].startswith("--") or len(args) < 2 or not args[1].strip():
            raise Fail(64, f"{args[0]} needs a value")
        flag, value, args = args[0], args[1], args[2:]
        if flag in lists:
            lists[flag].append(value)
        elif flag in opts:
            raise Fail(64, f"repeated option {flag}")
        else:
            opts[flag] = value
    if not args or args[0] != "--":
        raise Fail(64, "missing -- before the file arguments")
    return opts, lists, args[1:]


def _within(path, roots):
    return any(path == r or path.is_relative_to(r) for r in roots)


def issue(args):
    opts, lists, rest = _parse(args)
    unknown = set(opts) - {"--workstream", "--task", "--tier", "--reviewer", "--vendor", "--owner", "--packet-root"}
    if unknown:
        raise Fail(64, f"unknown option {sorted(unknown)[0]}")
    if len(rest) != 1:
        raise Fail(64, "issue takes exactly one OUTPUT after --")
    for k in ("--workstream", "--task", "--tier", "--reviewer", "--owner"):
        if not opts.get(k):
            raise Fail(64, f"{k} is required")
    if not IDENT.match(opts["--task"]) or any(not IDENT.match(b) for b in lists["--batch"]):
        raise Fail(64, "--task and --batch must be short identifiers")
    output = Path(rest[0])
    repo = repo_of(output)
    base = output.name
    reviewer = opts["--reviewer"]
    if reviewer == "auto":
        if not (base.startswith("auto-") and base.endswith(".md")):
            raise Fail(64, "an auto ticket needs an auto-*.md output")
    elif not base.startswith(reviewer + "-"):
        raise Fail(64, f"output must start with {reviewer}-")
    budget = _load("review-budget")
    probe = base if reviewer != "auto" else "kimi-" + base[len("auto-"):]
    if not budget.parse(probe):
        raise Fail(64, "output must be <reviewer>-YYYY-MM-DD-<topic>[-rNN].md (or .json for gemini)")
    ws = Path(opts["--workstream"]).expanduser()
    ws = (Path.cwd() / ws) if not ws.is_absolute() else ws
    ws = ws.resolve()
    if not ws.is_file() or not ws.is_relative_to(repo):
        raise Fail(64, "--workstream must be a file inside the repository")
    root = Path(opts["--packet-root"]).expanduser().resolve() if opts.get("--packet-root") else None
    scope = []
    for s in lists["--scope"]:
        p = Path(s).expanduser().resolve()
        if not p.exists() or not (p.is_relative_to(repo) or (root and p.is_relative_to(root))):
            raise Fail(64, f"scope {s} does not exist inside the repository or the packet root")
        scope.append(str(p.relative_to(repo)) if p.is_relative_to(repo) else str(p))
    body = {"version": 1, "issued": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "workstream": str(ws.relative_to(repo)), "task": opts["--task"], "batch": lists["--batch"],
            "tier": opts["--tier"], "reviewer": reviewer, "vendor": opts.get("--vendor"),
            "owner": opts["--owner"], "authors": lists["--author"], "author_models": lists["--author-model"],
            "packet_root": str(root) if root else None, "scope": scope, "output": base}
    path = ticket_dir(repo) / (base + ".ticket.json")
    validate(body, path)
    agents = _load("agents")
    sel = _load("copilot-model-select")
    registry = agents.load()
    try:
        if reviewer == "copilot":
            policy = json.loads((GATEWAY / "copilot-model-policy.json").read_text())
            sel.select(policy, body["tier"], registry, body["vendor"], body["owner"], body["authors"], body["author_models"])
        elif reviewer != "auto":
            agents.check(registry, reviewer, body["owner"], body["authors"], body["author_models"])
        else:
            agents.excluded_vendors(registry, body["owner"], body["authors"], body["author_models"])
    except (agents.IdentityError, sel.agents.IdentityError) as exc:
        raise Fail(64, f"identity: {exc}")
    for name in [base] + ([] if reviewer != "auto" else [f"{c}-{base[len('auto-'):]}" for c in ("claude", "codex", "copilot", "kimi")]):
        out = repo / ".collab" / name
        if out.exists() or out.with_name(Path(name).stem + ".diagnostic.json").exists():
            raise Fail(73, f"{name} already has an artifact or diagnostic; issue a ticket for a new rNN")
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(path, "x") as fh:
            json.dump(body, fh, indent=2)
            fh.write("\n")
    except FileExistsError:
        raise Fail(73, f"ticket already exists: {path.relative_to(repo)}")
    print(f"ticket written: {path.relative_to(repo)}")
    return 0


def check(args):
    if len(args) < 3:
        raise Fail(64, "usage: review-ticket.py check PROVIDER REQUESTED OUTPUT [identity...] -- PACKET...")
    provider, requested, output, args = args[0], args[1], Path(args[2]), args[3:]
    opts, lists, packets = _parse(args, multi=("--author", "--author-model"))
    unknown = set(opts) - {"--owner", "--task", "--vendor", "--packet-root"}
    if unknown:
        raise Fail(64, f"unknown option {sorted(unknown)[0]}")
    repo = repo_of(output)
    path, body = find(repo, output.name)
    if body is None:
        if opts.get("--owner") == "copilot" and opts.get("--task"):
            raise Fail(66, f"Copilot task {opts['--task']} has no review ticket for {output.name}; "
                           "the coordinator issues one with review-ticket.py issue")
        return 0
    problems = []
    if body["reviewer"] == "auto":
        if path.name == output.name + ".ticket.json":
            problems.append("an auto ticket covers the candidate outputs, not the auto- name itself")
        if provider not in ("claude", "codex", "copilot", "kimi"):
            problems.append(f"{provider} is not an automatic-selection channel")
    elif body["reviewer"] != provider:
        problems.append(f"ticket names reviewer {body['reviewer']}, not {provider}")
    if body["vendor"] and opts.get("--vendor") != body["vendor"]:
        problems.append(f"ticket names Copilot vendor {body['vendor']}, not {opts.get('--vendor') or 'none'}")
    if tier_of(provider, requested) != body["tier"]:
        problems.append(f"ticket tier is {body['tier']}, not {tier_of(provider, requested)}")
    if opts.get("--owner") != body["owner"]:
        problems.append(f"ticket owner is {body['owner']}, not {opts.get('--owner') or 'none'}")
    if opts.get("--task") != body["task"]:
        problems.append(f"ticket task is {body['task']}, not {opts.get('--task') or 'none'}")
    if sorted(lists["--author"]) != sorted(body["authors"]):
        problems.append("authors differ from the ticket")
    if sorted(set(lists["--author-model"])) != sorted(set(body["author_models"])):
        problems.append("author models differ from the ticket")
    root = Path(body["packet_root"]).resolve() if body.get("packet_root") else None
    scope = [(Path(s) if Path(s).is_absolute() else repo / s).resolve() for s in body["scope"]]
    # Resolved now, so a scope path replaced by a symbolic link after issue cannot widen the scope.
    if not all(s.is_relative_to(repo) or (root and s.is_relative_to(root)) for s in scope):
        problems.append("ticket scope leaves the repository and its packet root")
    if not packets:
        problems.append("no packet files")
    for f in packets:
        p = Path(f).expanduser().resolve()
        if not _within(p, scope):
            problems.append(f"packet {f} is outside the ticket scope")
    if problems:
        raise Fail(64, f"review ticket {path.name}: " + "; ".join(problems))
    return 0


def list_tickets(args):
    repo = Path(args[0] if args else ".").resolve()
    found = 0
    for path in sorted(ticket_dir(repo).glob("*.ticket.json")):
        try:
            body = validate(json.loads(path.read_text()), path)
        except (Fail, OSError, ValueError) as exc:
            print(f"{path.name}: unreadable ({exc})")
            continue
        names = [body["output"]]
        if body["reviewer"] == "auto":
            names = [f"{c}-{body['output'][len('auto-'):]}" for c in ("claude", "codex", "copilot", "kimi")]
        used = any((repo / ".collab" / n).exists() or (repo / ".collab" / (Path(n).stem + ".diagnostic.json")).exists()
                   for n in names)
        if used:
            continue
        found += 1
        batch = f" (batch {', '.join(body['batch'])})" if body["batch"] else ""
        print(f"{path.relative_to(repo)}: {body['task']}{batch} {body['tier']} {body['reviewer']}"
              f"{'/' + body['vendor'] if body['vendor'] else ''} -> .collab/{body['output']}")
    if not found:
        print("no open review tickets")
    return 0


def main(argv):
    try:
        if len(argv) >= 2 and argv[1] == "issue":
            return issue(argv[2:])
        if len(argv) >= 2 and argv[1] == "check":
            return check(argv[2:])
        if len(argv) >= 2 and argv[1] == "list":
            return list_tickets(argv[2:])
        raise Fail(64, __doc__.strip().splitlines()[2].strip())
    except Fail as exc:
        print(f"review-ticket: {exc}", file=sys.stderr)
        return exc.code
    except (OSError, KeyError, TypeError, ValueError) as exc:
        print(f"review-ticket: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 78


if __name__ == "__main__":
    sys.exit(main(sys.argv))
