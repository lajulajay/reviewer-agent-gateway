# docs-check: accept owner extractions of failed invocations in .collab

Workstream: 2026-11-27-docs-check-extractions
Owner: Claude (2026-11-27, assigned by the user in this session)
Status: active
Branch: docs-check-extractions
Operational: no
Links: [protocol](../PROTOCOL.md)

## Brief

kalshi-temperature-bot's H5 paper workstream re-recorded Gemini r02 and r06
(wrapper exit 70) as failed invocations, not reviews (user decision
2026-11-27). Their owner extractions, `<stem>.extracted.md` with a
`.sha256` sidecar, stay in `.collab/` beside `<stem>.diagnostic.json`, and
`docs-check.py record` flagged them as unrecognizable artifacts. Raw files are
never edited, renamed or deleted.

Change: a `.collab/` file `<stem>.extracted.md` is skipped only when
`<stem>.diagnostic.json` exists and its sidecar's first field is the file's
SHA-256; otherwise it is reported. Test added in `tests/test_docs_check.py`.

## Decisions

- 2026-11-27, user, scope: this change, chosen from the owner's options with
  a recommendation, context and pros/cons. Quote: "Gateway exception
  (Recommended)". Supersedes: none.

## Reviews

| Round | Reviewer | Tier | Artifact | Verdict |
| :--- | :--- | :--- | :--- | :--- |
| r01 | Codex API (`gpt-6.1-terra`) | routine; small checker exception with tests | `.collab/codex-2026-11-27-docs-check-extractions.md` (+ .sha256) | REJECT |
| r02 | Codex API (`gpt-6.1-terra`) | routine; follow-up | `.collab/codex-2026-11-27-docs-check-extractions-r02.md` (+ .sha256) | REJECT |
| r03 | Codex API (`gpt-6.1-terra`) | routine; follow-up | `.collab/codex-2026-11-27-docs-check-extractions-r03.md` (+ .sha256) | REJECT |

## Findings and conditions

| ID | Severity | Disposition | Status |
| :--- | :--- | :--- | :--- |
| R01-F1 | major | applied; open via R02-F1 then R03-F1; to r04 | open |
| R01-F2 | major | verified r03 | closed |
| R01-F3 | minor | verified r02 | closed |
| R01-C1 | condition | verified r02 | closed |
| R02-F1 | major | applied (exact line); open via R03-F1; to r04 | open |
| R02-F2 | minor | verified r03 | closed |
| R03-F1 | major | applied: the line counts only in a workstream's Reviews section, outside fenced code and HTML comments; tests; mutation check; to r04 | open |

## Log

- 2026-11-27: change and test written on branch `docs-check-extractions`;
  unit suite passes (34); the new test fails on main's checker;
  kalshi-temperature-bot passes record with the change.
- 2026-11-27: Codex r01 routine REJECT (F1, F2 major; F3 minor; C1). Repaired: the exception also needs a
  non-zero `exit_code` in the diagnostic and a workstream naming the exact path; read failures reported;
  one message per check; tests extended (exit status, stale checksum, malformed inputs). Suite passes;
  the new test fails on main. Next: Codex r02 on the delta.
- 2026-11-27: Codex r02 routine REJECT; R01-F3 and R01-C1 resolved. Repaired R02-F1 (exact classification
  line) and R02-F2 (RecursionError); tests extended; suite passes. Next: Codex r03 on the delta.
- 2026-11-27: Codex r03 routine REJECT; R01-F2 and R02-F2 resolved. Repaired R03-F1: classification read
  only from Reviews-section text outside fences and comments; tests (Log, fenced, comment rejected;
  Reviews accepted); removing the filter fails the test. Next: Codex r04.
