# docs-check: ignore trailing spaces on "is resolved." lines

Workstream: 2026-11-21-docs-check-trailing-space
Owner: Claude (2026-11-21, assigned by the user in this session)
Status: active
Branch: docs-check-trailing-space
Operational: no
Links: [validator-reason workstream](closed/2026-11-21-api-validator-reason.md)

## Brief

`docs-check.py` accepts a `verified rNN` disposition only when review rNN has
the exact line "<ID> is resolved.". Codex r03 of the validator-reason
workstream wrote "R02-F1 is resolved." followed by two spaces, so the check
missed it and that row had to cite the fix commit instead. Raw review
artifacts are never edited.

Change: the status-line match now allows trailing spaces, tabs or a carriage
return after "is resolved." (`is resolved\.[ \t\r]*$`). `.md` artifacts are
read with universal newlines, but a `.json` artifact's `response` string can
keep CRLF (Kimi r01). Any other trailing text, a quoted line ("> "), a
non-breaking space, or a "remains open" contradiction still fails. Tests in
`tests/test_docs_check.py`: trailing spaces and tab accepted, other tails
rejected; CRLF `.md` and CRLF `.json` artifacts pass `done` (the JSON test
fails with the r01 pattern). Closed records are not rewritten.

## Decisions

- 2026-11-21, user, scope: this fix. Quote: "go ahead with the docs-check
  trailing-space fix". Supersedes: none.

## Reviews

| Round | Reviewer | Tier | Artifact | Verdict |
| :--- | :--- | :--- | :--- | :--- |
| r01 | Kimi API (`kimi-k2.6`) | routine; one-line checker change; Codex at its daily cap | `.collab/kimi-2026-11-21-docs-check-trailing-space.md` (SHA-256 `1b79728b7662700d518d8c9a4f757224e65adedbdcee0940135fbdc81ff455f3`) | ACCEPT WITH CONDITIONS |
| r02 | Kimi API (`kimi-k2.6`) | routine; follow-up | `.collab/kimi-2026-11-21-docs-check-trailing-space-r02.md` (SHA-256 `550aedb1abbdd6b8f76daafc8187f074fe96e1a9ff1b75ee2730d16a141e6d6e`) | ACCEPT |

## Findings and conditions

| ID | Severity | Disposition | Status |
| :--- | :--- | :--- | :--- |
| R01-F1 | minor | verified r02 | resolved |
| R01-F2 | minor | verified r02 | resolved |
| R01-F3 | minor | verified r02 | resolved |
| R01-C1 | condition | verified r02 | resolved |
| R01-C2 | condition | verified r02 | resolved |

## Log

- 2026-11-21: fix and test written in worktree branch
  `docs-check-trailing-space`. Kimi r01 ACCEPT WITH CONDITIONS (JSON CRLF);
  `\r` added with CRLF tests; Kimi r02 ACCEPT. Unit suite and wrapper smoke
  test pass. Commit, push and merge await the user.
