# API route: surface the substance validator's reason

Workstream: 2026-11-21-api-validator-reason
Owner: Claude (2026-11-21, assigned by the user in this session)
Status: active
Branch: api-validator-reason
Operational: no
Links: [API streaming workstream](2026-11-20-api-streaming.md)

## Brief

On 2026-11-21 two Codex follow-up rounds in the Copilot-reviewer workstream
(`codex-2026-11-21-copilot-reviewer-r03` and `-r04`) were refused with only
"API reply rejected: substance validation failed". `api-call.py` discarded
`reviewer-validate.py`'s stderr, so the cause had to be guessed, and both
refused rounds counted against the five-rounds-per-topic budget.

Change: when the validator rejects a reply, `api-call.py` reports
"substance validation failed: <reason>", where `validator_reason()` maps the
validator's stderr to fixed text only: one of the eight fixed messages in
`VALIDATOR_REASONS` (exact match), "review is shorter than N characters" (N
from argv), the fixed text "a finding has a severity other than blocker,
major or minor" for the severity message (whose label and severity come from
the reply and are never echoed), and otherwise "unrecognized validator output
(exit N)". No reply-derived text reaches stderr, the wrapper's
`.diagnostic.json` (which quotes the last stderr line) or the meta file. The
ledger settle note stays the fixed text "reply rejected: full bound kept";
settlement and the kept bound are unchanged. (r01 echoed the redacted last
stderr line; Codex showed the severity message carries reply text, so r02
moved to the allow-list.)

Tests (`tests/test_api_call.py`): a rejected ACCEPT WITH CONDITIONS reply
surfaces the exact validator reason with the fixed ledger note and full bound;
a real severity rejection carrying a CR and a NUL-separated key echoes only the
fixed reason on one stderr line; tracebacks, extra lines, out-of-range lengths
and empty output fall back without echo; an `ast` check keeps
`VALIDATOR_REASONS` equal to the validator's fixed messages; and the two
formatted messages are checked by running the real validator and edited copies.

Invariants: keys never appear in argv, logs, artifacts or the ledger; no
server-supplied value reaches the ledger.

## Decisions

- 2026-11-21, user, scope: this change. Started the proposed session
  "Record validator reason in API-route diagnostics" from the proposal card
  (no written quote). Supersedes: none.

## Reviews

| Round | Reviewer | Tier | Artifact | Verdict |
| :--- | :--- | :--- | :--- | :--- |
| r01 | Codex API (`gpt-6.1-terra`) | routine; small API-route change | `.collab/codex-2026-11-21-api-validator-reason.md` (SHA-256 `a02ddd691595e4b5f0de02ca6caf694a75c7c0a07ffdf415bd23adc1820c47e5`) | REJECT |
| r02 | Codex API (`gpt-6.1-terra`) | routine; follow-up | `.collab/codex-2026-11-21-api-validator-reason-r02.md` (SHA-256 `409fee3818b62ecd3f470152e5d612538d964b84a07189ab072bd75e25534102`) | ACCEPT WITH CONDITIONS |
| r03 | Codex API (`gpt-6.1-terra`) | routine; follow-up | `.collab/codex-2026-11-21-api-validator-reason-r03.md` (SHA-256 `8aa632c8d1906524148b44504ed65bcd1587dee61c0c1926a934d74858048ab6`) | ACCEPT WITH CONDITIONS |
| r04 | Codex API (`gpt-6.1-terra`) | routine; follow-up | `.collab/codex-2026-11-21-api-validator-reason-r04.md` (SHA-256 `de7413c595f07aaedd4c1b2893c01a176d3cdcc89132ff64e6b4219e14fb639b`) | ACCEPT |

## Findings and conditions

| ID | Severity | Disposition | Status |
| :--- | :--- | :--- | :--- |
| R01-F1 | blocker | verified r02 | resolved |
| R01-F2 | major | verified r02 | resolved |
| R01-F3 | minor | verified r02 | resolved |
| R01-C1 | condition | verified r02 | resolved |
| R01-C2 | condition | verified r02 | resolved |
| R02-F1 | minor | verified r03 | resolved |
| R02-C1 | condition | verified r03 | resolved |
| R03-F1 | minor | verified r04 | resolved |
| R03-C1 | condition | verified r04 | resolved |

## Log

- 2026-11-21: fix and tests written in worktree branch
  `api-validator-reason`. Codex r01 REJECT (the severity message echoes reply
  text); moved to a fixed-reason allow-list. r02 and r03 ACCEPT WITH
  CONDITIONS on sync-test coverage; r04 ACCEPT. Unit suite, wrapper smoke
  test and `docs-check.py record .` pass. Commit, push and merge await the
  user.
