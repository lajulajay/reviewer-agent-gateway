#!/usr/bin/env python3
"""Refuse a review call that would exceed the review budget (review-budget.json).

  review-budget.py <provider> <hard|routine> <output-path>

A topic is the output name without its provider prefix, date, `-rNN` suffix,
and extension, so `claude-2026-10-07-h5-final-analysis-r22.md` and
`gemini-2026-10-08-h5-final-analysis.json` are rounds of `h5-final-analysis`.
Every provider's rounds count together, including failed calls that reached or
may have reached the model. Calls refused before model invocation are not
counted. After max_rounds_per_topic rounds only the escalation provider may
run, for escalation_rounds more; then the open points go to the user.

When the escalation provider may not review the work under the vendor rule
(a Google author), the Copilot wrapper passes --escalation-substitute with its
model's vendor: Copilot then runs the escalation rounds with a vendor that has
not yet reviewed the topic.

A review ticket (review-ticket.py) for the output may point at a workstream
whose user Decisions set a daily review pool (`Review pool: copilot 20/day`).
The provider's rounds today under that workstream's tickets are then capped
by the pool instead of max_reviews_per_provider_per_day, and pooled rounds do
not count against the repository cap of other work.

On success prints the number of earlier rounds on the topic and how many of
them this provider ran. On refusal
prints the reason and exits 1. REVIEW_BUDGET_OVERRIDE=<reason> skips every
limit; the wrapper records the reason in the artifact and docs-check requires
a matching user decision in the workstream.
"""

import importlib.util
import json
import os
import re
import sys
from datetime import date, datetime
from pathlib import Path

PROVIDERS = ("claude", "codex", "copilot", "gemini", "kimi")
NAME = re.compile(r"^(%s)-(?:(\d{4}-\d{2}-\d{2})-)?(.+?)(?:-r\d+)?\.(?:md|json)$" % "|".join(PROVIDERS))
# Current wrappers reserve exits 70 and 74 for failures after invocation began.
# Preflight failures use other exit codes. Kimi also records the boundary
# explicitly, which takes precedence for interrupted calls.


GATEWAY = Path(__file__).resolve().parent


def _module(name):
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), GATEWAY / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def output_name(path, provider):
    """The output name a counted round was written for (diagnostics share it)."""
    if path.name.endswith(".diagnostic.json"):
        return path.name[: -len(".diagnostic.json")] + (".json" if provider == "gemini" else ".md")
    return path.name


def round_vendors(registry, r):
    """Vendors that reviewed in round R; a Copilot round names its model's vendor."""
    provider, path = r[0], r[2]
    spec = registry["channels"].get(provider, {})
    if spec.get("vendors") != "by-model":
        return set(spec.get("vendors") or [])
    try:
        text = path.read_text(errors="replace")
    except OSError:
        return {"unknown"}
    if path.name.endswith(".diagnostic.json"):
        try:
            v = json.loads(text).get("reviewer_vendor")
        except ValueError:
            v = None
    else:
        m = re.search(r"(?m)^Reviewer vendor: (\S+)$", text[:2000])
        v = m.group(1) if m else None
    return {v} if v else {"unknown"}


def spent_failure(d):
    # rounds() also filters these exits; keep this guard for direct callers.
    if d.get("exit_code") not in (70, 74):
        return False
    # A false flag with a model-sounding reason must not count.
    if "model_invocation_began" in d:
        return d.get("model_invocation_began") is True
    return True


def parse(name):
    if name.endswith((".sha256", ".diagnostic.json")):
        return None
    m = NAME.match(name)
    return (m.group(1), m.group(3), m.group(2)) if m else None


def hard(provider, requested, selected, effort=""):
    if provider == "kimi":
        return requested == "hard" or selected.startswith("kimi-code/k3") or effort == "high"
    if provider == "copilot":
        return requested == "hard"
    return provider in ("claude", "codex") and (requested in ("opus", "hard") or "opus" in selected)


def is_hard(path, provider):
    head = path.read_text(errors="replace")[:2000]
    m = re.search(r"(?m)^Requested model: (.+)$", head)
    sel = re.search(r"(?m)^Selected model: (.+)$", head)
    effort = re.search(r"(?m)^Reasoning effort: (.+)$", head)
    return hard(
        provider,
        m.group(1).strip() if m else "",
        sel.group(1).strip() if sel else "",
        effort.group(1).strip() if effort else "",
    )


def rounds(collab):
    """Yield (provider, topic, path, day, hard) for every counted round."""
    for f in sorted(collab.iterdir()):
        if not f.is_file():
            continue
        if f.name.endswith(".diagnostic.json"):
            parsed = parse(f.name[: -len(".diagnostic.json")] + ".md")
            if not parsed:
                continue
            try:
                d = json.loads(f.read_text())
            except (json.JSONDecodeError, OSError):
                continue
            if d.get("exit_code") in (70, 74) and spent_failure(d):
                yield parsed[0], parsed[1], f, day(f, parsed), hard(
                    parsed[0], d.get("requested_model") or "", d.get("selected_model") or "",
                    d.get("reasoning_effort") or "")
            continue
        parsed = parse(f.name)
        if parsed:
            yield parsed[0], parsed[1], f, day(f, parsed), is_hard(f, parsed[0])


def day(path, parsed):
    """The date in the name; checkouts reset mtimes, so mtime is only a fallback."""
    if parsed[2]:
        return date.fromisoformat(parsed[2])
    return datetime.fromtimestamp(path.stat().st_mtime).date()


def main(argv):
    usage = ("usage: review-budget.py <claude|codex|copilot|gemini|kimi> <hard|routine> <output-path> "
             "[--escalation-substitute VENDOR]")
    substitute = None
    if len(argv) == 6 and argv[4] == "--escalation-substitute" and argv[1] == "copilot" and re.fullmatch(r"[a-z]+", argv[5]):
        substitute, argv = argv[5], argv[:4]
    if len(argv) != 4 or argv[1] not in PROVIDERS or argv[2] not in ("hard", "routine"):
        print(usage, file=sys.stderr)
        return 64
    provider, tier, output = argv[1], argv[2], Path(argv[3])
    policy = json.loads((Path(__file__).resolve().parent / "review-budget.json").read_text())
    parsed = parse(output.name)
    if not parsed or parsed[0] != provider:
        print(f"output name must be {provider}-YYYY-MM-DD-<topic>[-rNN].{'json' if provider == 'gemini' else 'md'}, "
              "so the review budget can count it", file=sys.stderr)
        return 1
    topic = parsed[1]
    collab = output.parent
    prior = [r for r in rounds(collab) if r[1] == topic and r[2] != output]
    today = [r for r in rounds(collab) if r[0] == provider and r[3] == date.today()]
    tickets = _module("review-ticket")
    repo = collab.parent
    try:
        _, ticket = tickets.find(repo, output.name)
    except tickets.Fail as exc:
        print(f"review budget: {exc}", file=sys.stderr)
        return 1
    pool_ws = tickets.workstream_path(repo, ticket) if ticket and tickets.pool(repo, ticket, provider) else None

    def pooled_under(r):
        try:
            _, t = tickets.find(repo, output_name(r[2], provider))
        except tickets.Fail:
            return None
        return tickets.workstream_path(repo, t) if t and tickets.pool(repo, t, provider) else None

    if pool_ws:
        daily_cap = tickets.pool(repo, ticket, provider)
        today = [r for r in today if pooled_under(r) == pool_ws]
        cap_label = f"today under the {provider} review pool of {ticket['workstream']}"
    else:
        daily_cap = policy["max_reviews_per_provider_per_day"]
        today = [r for r in today if pooled_under(r) is None]
        cap_label = "in this repository today (outside review pools)"
    n, cap = len(prior), policy["max_rounds_per_topic"]
    esc, esc_n = policy["escalation_provider"], policy["escalation_rounds"]
    problems = []
    if n >= cap + esc_n:
        problems.append(f"topic '{topic}' has had {n} review rounds ({cap} plus {esc_n} {esc} escalation); "
                        f"bring the open points to the user (competing claims, evidence, the {esc} assessment, and the decision needed)")
    elif n >= cap and provider != esc:
        if substitute:
            registry = _module("agents").load()
            involved = set().union(*[round_vendors(registry, r) for r in prior]) if prior else set()
            if "unknown" in involved:
                problems.append(f"topic '{topic}' is in escalation and an earlier Copilot round does not name its "
                                "reviewer vendor; bring the open points to the user")
            elif substitute in involved:
                problems.append(f"topic '{topic}' is in escalation and {substitute} already reviewed it; "
                                f"choose a Copilot vendor not yet involved (involved: {', '.join(sorted(involved))})")
        else:
            problems.append(f"topic '{topic}' has had {n} review rounds (cap {cap}); escalate to {esc}-review.sh, then to the user")
    hard_n = sum(1 for r in prior if r[4])
    if tier == "hard" and provider in ("claude", "codex", "copilot", "kimi") and hard_n >= policy["max_hard_rounds_per_topic"]:
        problems.append(f"topic '{topic}' already used {hard_n} hard-tier round(s) (cap {policy['max_hard_rounds_per_topic']}); use the routine tier")
    if len(today) >= daily_cap:
        problems.append(f"{len(today)} {provider} reviews already ran {cap_label} (cap {daily_cap})")
    override = os.environ.get("REVIEW_BUDGET_OVERRIDE", "").strip()
    if problems and not override:
        print("review budget exceeded: " + "; ".join(problems)
              + ". Only the user may authorize REVIEW_BUDGET_OVERRIDE=<reason>.", file=sys.stderr)
        return 1
    # Earlier rounds on the topic, then this provider's own earlier rounds.
    print(n, sum(1 for r in prior if r[0] == provider))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
