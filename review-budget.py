#!/usr/bin/env python3
"""Refuse a review call that would exceed the review budget (review-budget.json).

  review-budget.py <provider> <hard|routine> <output-path>

A topic is the output name without its provider prefix, date, `-rNN` suffix,
and extension, so `claude-2026-10-07-h5-final-analysis-r22.md` and
`gemini-2026-10-08-h5-final-analysis.json` are rounds of `h5-final-analysis`.
Every provider's rounds count together, as do failed calls that reached the
model (a validation failure, model mismatch, or timeout). After
max_rounds_per_topic rounds only the escalation provider may run, for
escalation_rounds more; then the open points go to the user.

On success prints the number of earlier rounds on the topic and how many of
them this provider ran. On refusal
prints the reason and exits 1. REVIEW_BUDGET_OVERRIDE=<reason> skips every
limit; the wrapper records the reason in the artifact and docs-check requires
a matching user decision in the workstream.
"""

import json
import os
import re
import sys
from datetime import date, datetime
from pathlib import Path

PROVIDERS = ("claude", "codex", "gemini", "kimi")
NAME = re.compile(r"^(%s)-(?:(\d{4}-\d{2}-\d{2})-)?(.+?)(?:-r\d+)?\.(?:md|json)$" % "|".join(PROVIDERS))
# Failed calls in which the model ran and used quota. "invocation failed" is
# not counted: it includes calls refused at a usage limit before any work.
SPENT = re.compile(r"validation|timed out|resolved outside|returned|did not complete|did not succeed")


def parse(name):
    if name.endswith((".sha256", ".diagnostic.json")):
        return None
    m = NAME.match(name)
    return (m.group(1), m.group(3), m.group(2)) if m else None


def hard(provider, requested, selected):
    return provider in ("claude", "codex") and (requested in ("opus", "hard") or "opus" in selected)


def is_hard(path, provider):
    head = path.read_text(errors="replace")[:2000]
    m = re.search(r"(?m)^Requested model: (.+)$", head)
    sel = re.search(r"(?m)^Selected model: (.+)$", head)
    return hard(provider, m.group(1).strip() if m else "", sel.group(1) if sel else "")


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
            if d.get("exit_code") in (70, 74) and SPENT.search(d.get("reason", "")):
                yield parsed[0], parsed[1], f, day(f, parsed), hard(
                    parsed[0], d.get("requested_model") or "", d.get("selected_model") or "")
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
    if len(argv) != 4 or argv[1] not in PROVIDERS or argv[2] not in ("hard", "routine"):
        print("usage: review-budget.py <claude|codex|gemini|kimi> <hard|routine> <output-path>", file=sys.stderr)
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
    n, cap = len(prior), policy["max_rounds_per_topic"]
    esc, esc_n = policy["escalation_provider"], policy["escalation_rounds"]
    problems = []
    if n >= cap + esc_n:
        problems.append(f"topic '{topic}' has had {n} review rounds ({cap} plus {esc_n} {esc} escalation); "
                        f"bring the open points to the user (competing claims, evidence, the {esc} assessment, and the decision needed)")
    elif n >= cap and provider != esc:
        problems.append(f"topic '{topic}' has had {n} review rounds (cap {cap}); escalate to {esc}-review.sh, then to the user")
    hard_n = sum(1 for r in prior if r[4])
    if tier == "hard" and provider in ("claude", "codex") and hard_n >= policy["max_hard_rounds_per_topic"]:
        problems.append(f"topic '{topic}' already used {hard_n} hard-tier round(s) (cap {policy['max_hard_rounds_per_topic']}); use the routine tier")
    if len(today) >= policy["max_reviews_per_provider_per_day"]:
        problems.append(f"{len(today)} {provider} reviews already ran in this repository today (cap {policy['max_reviews_per_provider_per_day']})")
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
