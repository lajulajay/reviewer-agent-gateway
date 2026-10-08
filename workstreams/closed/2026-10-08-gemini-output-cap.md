# Gemini output-token cap

Workstream: 2026-10-08-gemini-output-cap
Owner: Claude (2026-10-08, assigned by the user)
Status: done (2026-10-08)
Branch: gemini-output-cap (merged to main)
Operational: no
Links: [failure report](../../invocation-failures/kalshi-temperature-bot-2026-10-08-h5-paper-gemini-output-cap.md), [protocol](../../PROTOCOL.md#packets-and-isolation)

## Brief

On 2026-10-08 two hard-tier Gemini reviews of the H5 paper implementation in
`kalshi-temperature-bot` (r02, r06; 216k-227k input tokens) failed with exit
70: hidden reasoning used the output-token limit (65k-70k thinking tokens) and
`agy` returned `status: "ERROR"`. r06's returned review was complete and
valid; r02's stopped before its verdict (the report says both were complete;
r02 was not). The report also says the validator would have rejected r06's
`F1 [critical]`; it did not: findings with an unknown severity were ignored,
so Gemini's two most severe findings went untracked.

Change: `reviewer-validate.py` refuses unknown severities; `gemini-review.sh`
keeps a cut-off review only if it validates (recording
`truncation_warning`) and otherwise fails with its own reason, which the
budget counts; hard-tier packets over `GEMINI_HARD_MAX_PROMPT_BYTES` (150000)
are refused before the budget check; `--mode plan` dropped (no effect, warned
on every run); `reviewer-claims.py` notes `file://` citations, which mark
invented code. Report recommendations not taken: no `agy` thinking-budget
control exists (`--continue` would spend more quota), and cut-off runs keep
counting against the budget because they spent real quota.

## Decisions

- 2026-10-08, user, scope: fixes for the Gemini output-cap report.
  Quote: "approved" (to the validator fix, recommendations 1, 2 and 5, and the `file://` check). Supersedes: none.

## Reviews

| Round | Reviewer | Tier | Artifact | Verdict |
| :--- | :--- | :--- | :--- | :--- |
| r01 | Codex (primary) | routine | `.collab/codex-2026-10-08-gemini-output-cap-r01.md` | REJECT |
| r02 | Codex (primary) | routine | `.collab/codex-2026-10-08-gemini-output-cap-r02.md` | ACCEPT |

## Findings and conditions

| ID | Severity | Disposition | Status |
| :--- | :--- | :--- | :--- |
| R01-F1 | major | verified r02 | closed |
| R01-F2 | minor | verified r02 | closed |
| R01-F3 | minor | verified r02 | closed |

## Log

- 2026-10-08: implemented on branch `gemini-output-cap`; smoke tests and docs-check tests pass.
- 2026-10-08: the two kalshi-temperature-bot failure reports committed (the folder's other reports are tracked; user instruction).
- 2026-10-08: Codex r01 REJECT (3 findings), all fixed. Fixes in `2a57090`.
- r01: raw review compared with its rows; no unlabeled actionable item
- r02: raw review compared with its rows; no unlabeled actionable item
- 2026-10-08: Codex r02 ACCEPT, all r01 items resolved. Merged to main.
