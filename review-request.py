#!/usr/bin/env python3
"""Review requests: let an owner ask for a review it cannot send itself.

  review-request.py create [--packet-root DIR] --reviewer claude|codex|kimi|gemini --tier T --owner O
                           [--author A]... [--author-model M]... [--task ID]
                           [--override-reason TEXT] PROMPT OUTPUT PACKET...
  review-request.py run [--apply-override] REQUEST
  review-request.py list [REPO]

`create` checks the identity and vendor rule, hashes the prompt and every
packet file, and writes `reviewers/requests/<output name>.request.json` in the
repository that owns OUTPUT (`<repo>/.collab/...`). Nothing is sent.

`run` (the user, or an agent the user asks) re-checks the request: every file
must still have its recorded hash and the output must not exist. It then calls
the normal wrapper `<reviewer>-review.sh` with the recorded arguments from the
repository root, so every gateway check (budget, packet safety, output
contract, checksums) applies as if the owner had called it. A request that
carries a budget override is refused unless the runner passes
`--apply-override`, which it does only after the user has approved that round.
A request runs at most once: `run` claims `<name>.result.json` before calling
the wrapper (refusing if it exists) and writes the outcome there. Another
attempt needs a new request with a new rNN name, like any refused round.

The embedded hashes detect files changed after `create`; they do not
authenticate the request itself, which is an editable record. The wrapper
remains the control: it re-applies the vendor rule, budget, packet safety and
output naming whatever the request says.

`list` prints the requests in REPO (default: the current directory) that
have not been run.

Exit codes: 64 usage, identity or changed request; 66 missing file;
73 request already exists; otherwise the wrapper's own exit code.
"""

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

GATEWAY = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("agents", GATEWAY / "agents.py")
agents = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(agents)

REVIEWERS = ("claude", "codex", "kimi", "gemini")  # a request names one reviewer; no auto


class Fail(Exception):
    def __init__(self, code, msg):
        super().__init__(msg)
        self.code = code


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def regular(path, label):
    p = Path(path)
    if p.is_symlink() or not p.is_file():
        raise Fail(66, f"{label} is not a regular file: {path}")
    return p.resolve()


def repo_of(output):
    out = Path(output).expanduser()
    parent = out.parent.resolve()
    if parent.name != ".collab":
        raise Fail(64, "OUTPUT must be inside the repository's .collab/ directory")
    return parent.parent, parent / out.name


def diagnostic_of(out):
    """The wrappers name a failed call's record <output stem>.diagnostic.json."""
    return out.with_name(out.stem + ".diagnostic.json")


def result_of(req):
    return req.with_name(req.name[:-len(".request.json")] + ".result.json")


def request_path(repo, output_name):
    return repo / "reviewers" / "requests" / (output_name + ".request.json")


def create(args):
    opts = {"--packet-root": None, "--reviewer": None, "--tier": None, "--owner": None, "--task": None,
            "--override-reason": None}
    authors, models = [], []
    while args and args[0].startswith("--"):
        if len(args) < 2 or not args[1].strip():
            raise Fail(64, f"{args[0]} needs a value")
        flag, value, args = args[0], args[1], args[2:]
        if flag == "--author":
            authors.append(value)
        elif flag == "--author-model":
            models.append(value)
        elif flag in opts and opts[flag] is None:
            opts[flag] = value
        else:
            raise Fail(64, f"unknown or repeated option {flag}")
    if len(args) < 3:
        raise Fail(64, __doc__.strip().splitlines()[2].strip())
    reviewer, tier, owner = opts["--reviewer"], opts["--tier"], opts["--owner"]
    if reviewer not in REVIEWERS or not tier or not owner:
        raise Fail(64, f"--reviewer (one of {', '.join(REVIEWERS)}), --tier and --owner are required")
    registry = agents.load()
    try:
        agents.check(registry, reviewer, owner, authors, models)
    except agents.IdentityError as exc:
        raise Fail(64, f"identity: {exc}")
    prompt, output, packets = args[0], args[1], args[2:]
    repo, out = repo_of(output)
    for p in (out, diagnostic_of(out)):
        if p.exists():
            raise Fail(73, f"{p.name} already exists; use a new rNN name")
    files = [regular(prompt, "prompt")] + [regular(p, "packet") for p in packets]
    root = Path(opts["--packet-root"]).expanduser().resolve() if opts["--packet-root"] else None
    for f in files:
        if not (f.is_relative_to(repo) or (root and f.is_relative_to(root))):
            raise Fail(64, f"{f} is outside the repository; pass --packet-root")
    req = request_path(repo, out.name)
    if req.exists():
        raise Fail(73, f"request already exists: {req}")

    def rel(f):
        return str(f.relative_to(repo)) if f.is_relative_to(repo) else str(f)

    body = {"version": 1, "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "reviewer": reviewer, "tier": tier, "owner": owner, "authors": authors, "author_models": models,
            "task": opts["--task"], "packet_root": str(root) if root else None,
            "override_reason": opts["--override-reason"], "output": str(out.relative_to(repo)),
            "prompt": {"path": rel(files[0]), "sha256": sha256(files[0])},
            "packets": [{"path": rel(f), "sha256": sha256(f)} for f in files[1:]]}
    req.parent.mkdir(parents=True, exist_ok=True)
    with open(req, "x") as fh:
        json.dump(body, fh, indent=2)
        fh.write("\n")
    print(f"request written: {req.relative_to(repo)} (nothing was sent)")
    return 0


def load_request(path):
    req = Path(path).resolve()
    repo = req.parent.parent.parent
    if req.parent != repo / "reviewers" / "requests" or not req.name.endswith(".request.json"):
        raise Fail(64, "REQUEST must be reviewers/requests/<name>.request.json inside a repository")
    try:
        body = json.loads(req.read_text())
    except (OSError, ValueError) as exc:
        raise Fail(64, f"cannot read the request: {exc}")
    strs = ("reviewer", "tier", "owner", "output")
    ok = (isinstance(body, dict) and body.get("version") == 1 and body.get("reviewer") in REVIEWERS
          and all(isinstance(body.get(k), str) and body[k] for k in strs)
          and all(isinstance(body.get(k), list) and all(isinstance(v, str) for v in body[k])
                  for k in ("authors", "author_models"))
          and all(body.get(k) is None or isinstance(body[k], str) for k in ("task", "packet_root", "override_reason"))
          and isinstance(body.get("prompt"), dict) and isinstance(body.get("packets"), list)
          and all(isinstance(e, dict) and isinstance(e.get("path"), str) and isinstance(e.get("sha256"), str)
                  for e in [body.get("prompt")] + body.get("packets")))
    if not ok:
        raise Fail(64, "malformed request")
    # The output is fixed by the request's own name: no absolute or traversal edits.
    if body["output"] != ".collab/" + req.name[:-len(".request.json")] or "/" in req.name:
        raise Fail(64, "request name does not match its output")
    return req, repo, body


def command(repo, body):
    root = Path(body["packet_root"]).resolve() if body.get("packet_root") else None

    def resolve(entry):
        p = Path(entry["path"])
        p = p if p.is_absolute() else repo / p
        f = regular(p, "request file")
        if not (f.is_relative_to(repo) or (root and f.is_relative_to(root))):
            raise Fail(64, f"{entry['path']} is outside the repository and the packet root")
        if sha256(f) != entry["sha256"]:
            raise Fail(64, f"{entry['path']} changed since the request was written; write a new request")
        return str(f)

    files = [resolve(body["prompt"])] + [resolve(e) for e in body["packets"]]
    cmd = [str(GATEWAY / f"{body['reviewer']}-review.sh")]
    if body.get("packet_root"):
        cmd += ["--packet-root", body["packet_root"]]
    cmd += ["--owner", body["owner"]]
    for a in body.get("authors") or []:
        cmd += ["--author", a]
    for m in body.get("author_models") or []:
        cmd += ["--author-model", m]
    if body.get("task"):
        cmd += ["--task", body["task"]]
    return cmd + [body["tier"], files[0], body["output"]] + files[1:]


def run(args):
    apply_override = False
    if args and args[0] == "--apply-override":
        apply_override, args = True, args[1:]
    if len(args) != 1:
        raise Fail(64, "usage: review-request.py run [--apply-override] REQUEST")
    req, repo, body = load_request(args[0])
    out = repo / body["output"]
    result_path = result_of(req)
    for p in (out, diagnostic_of(out), result_path):
        if p.exists():
            raise Fail(73, f"{p.name} already exists; this request has already run (a new attempt needs a new request)")
    cmd = command(repo, body)
    env = {k: v for k, v in os.environ.items() if k != "REVIEW_BUDGET_OVERRIDE"}
    if body.get("override_reason"):
        if not apply_override:
            raise Fail(64, "this request carries a budget override; rerun with --apply-override only after "
                           "the user has approved that round")
        env["REVIEW_BUDGET_OVERRIDE"] = body["override_reason"]
    started = datetime.now(timezone.utc).isoformat(timespec="seconds")
    # Claim the result before sending: if the outcome cannot be recorded, nothing is sent.
    with open(result_path, "x") as fh:
        json.dump({"request": req.name, "started": started, "exit_code": None}, fh)
        fh.write("\n")
    code = subprocess.run(cmd, cwd=repo, env=env).returncode
    result = {"request": req.name, "started": started,
              "finished": datetime.now(timezone.utc).isoformat(timespec="seconds"), "exit_code": code,
              "artifact": body["output"] if out.exists() else None,
              "diagnostic": str(diagnostic_of(Path(body["output"]))) if diagnostic_of(out).exists() else None}
    tmp = result_path.with_name(result_path.name + ".tmp")
    tmp.write_text(json.dumps(result, indent=2) + "\n")
    tmp.replace(result_path)
    return code


def list_requests(args):
    repo = Path(args[0] if args else ".").resolve()
    found = 0
    for req in sorted((repo / "reviewers" / "requests").glob("*.request.json")):
        try:
            _, _, body = load_request(req)
        except Fail as exc:
            print(f"{req.name}: unreadable ({exc})")
            continue
        out = repo / body["output"]
        if out.exists() or diagnostic_of(out).exists() or result_of(req).exists():
            continue
        found += 1
        extra = "; budget override requested" if body.get("override_reason") else ""
        print(f"{req.relative_to(repo)}: {body['reviewer']} {body['tier']} for {body['owner']}"
              f" -> {body['output']}{extra}")
    if not found:
        print("no pending review requests")
    return 0


def main(argv):
    try:
        if len(argv) >= 2 and argv[1] == "create":
            return create(argv[2:])
        if len(argv) >= 2 and argv[1] == "run":
            return run(argv[2:])
        if len(argv) >= 2 and argv[1] == "list":
            return list_requests(argv[2:])
        raise Fail(64, __doc__.strip().splitlines()[2].strip())
    except Fail as exc:
        print(f"review-request: {exc}", file=sys.stderr)
        return exc.code
    except (OSError, ValueError, KeyError) as exc:
        print(f"review-request: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 78


if __name__ == "__main__":
    sys.exit(main(sys.argv))
