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

## Findings and conditions

| ID | Severity | Disposition | Status |
| :--- | :--- | :--- | :--- |

## Log

- 2026-11-27: change and test written on branch `docs-check-extractions`;
  unit suite passes (34); the new test fails on main's checker;
  kalshi-temperature-bot passes record with the change.
