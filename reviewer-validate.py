#!/usr/bin/env python3
import re
import sys


# The wrappers make a decision from this value. Do not infer it from prose,
# headings, or a findings list: a review must finish with one explicit marker.
VERDICT = re.compile(
    r"(?im)^\s*(?:[-*>]\s*)?(?:\*{1,3}|_{1,3})?\s*verdict\s*"
    r"(?:\*{1,3}|_{1,3})?\s*:\s*"
    r"(accept with conditions|accept|reject)\s*"
    r"(?:\*{1,3}|_{1,3})?\s*$"
)

text = sys.stdin.read()
minimum = int(sys.argv[1]) if len(sys.argv) > 1 else 400
if len(text.strip()) < minimum:
    print(f"review is shorter than {minimum} characters", file=sys.stderr)
    raise SystemExit(1)
matches = list(VERDICT.finditer(text))
if not matches:
    print(
        "review must end with exactly one approved verdict: "
        "VERDICT: ACCEPT, VERDICT: ACCEPT WITH CONDITIONS, or VERDICT: REJECT",
        file=sys.stderr,
    )
    raise SystemExit(1)
if len(matches) != 1:
    print("review has multiple approved verdict lines", file=sys.stderr)
    raise SystemExit(1)
if text[matches[0].end() :].strip():
    print("approved verdict must be the final non-empty line", file=sys.stderr)
    raise SystemExit(1)
verdict = matches[0].group(1).lower()
# Labeled findings and conditions let docs-check trace every obligation from
# the raw artifact (workspace framework v6 §3). Accept harmless emphasis.
FINDING = re.compile(r"(?m)^\s*(?:[-*]\s*)?\**F(\d+)\**\s*\[(blocker|major|minor)\]")
CONDITION = re.compile(r"(?m)^\s*(?:[-*]\s*)?\**C(\d+)\**\s*:")
ATTESTATION = re.compile(r"(?im)^\s*\**\s*attestation\s*\**\s*:\s*all actionable findings and conditions are labeled\.?\s*\**\s*$")
findings = [int(m.group(1)) for m in FINDING.finditer(text)]
conditions = [int(m.group(1)) for m in CONDITION.finditer(text)]
if not ATTESTATION.search(text):
    print("review must include the line: ATTESTATION: all actionable findings and conditions are labeled.", file=sys.stderr)
    raise SystemExit(1)
if len(set(findings)) != len(findings) or len(set(conditions)) != len(conditions):
    print("finding and condition labels must be unique", file=sys.stderr)
    raise SystemExit(1)
if verdict == "reject" and not findings:
    print("a REJECT verdict needs at least one labeled F<n> [severity] finding", file=sys.stderr)
    raise SystemExit(1)
if verdict == "accept with conditions" and not conditions:
    print("an ACCEPT WITH CONDITIONS verdict needs at least one labeled C<n> condition", file=sys.stderr)
    raise SystemExit(1)
if re.search(r"(?i)^(?:i(?:'ll| will)\s+(?:write|record|present)|let me\s+(?:write|record|present))", text.strip()):
    print("review is procedural narration rather than review content", file=sys.stderr)
    raise SystemExit(1)
