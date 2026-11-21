# docs-check Owner-line regression fix

Workstream: 2026-11-20-owner-line-fix
Owner: Claude (2026-11-20, assigned by the user in this session)
Status: active
Branch: owner-line-fix
Operational: no
Links: [Copilot owner workstream](2026-11-20-copilot-owner.md)

## Brief

Phase 1 made `docs-check.py record` require each workstream `Owner:` line to
start with an owner agent. trading-strategies' T4 workstream, merged earlier
on 2026-11-20, reads `Owner: sponsor's GitHub Copilot agent (user-assigned
2026-11-20)` and began failing. Earlier Owner lines are never rewritten, so
the checker accepts that form: only the head of the line (before the first
"(", ";" or ",") counts, and it must be exactly one owner agent, or exactly
"sponsor's GitHub <owner agent> agent" (with optional "the", "user" for "sponsor", and no "GitHub"). All Owner lines in the
six adopted repositories pass; the vendor check on artifacts is unchanged.

## Decisions

- 2026-11-20, user, scope: this fix. Quote: "fix gateway bug". Supersedes:
  none.

## Reviews

| Round | Reviewer | Tier | Artifact | Verdict |
| :--- | :--- | :--- | :--- | :--- |
| r01 | Codex API (`gpt-6.1-terra`) | routine; small checker change | `.collab/codex-2026-11-20-owner-line.md` (SHA-256 `c7b94c97576172b32fe673c12e5cc983f209dcb464d78f7c0d5cfccdf2e6599a`) | REJECT |
| r02 | Codex API (`gpt-6.1-terra`) | routine; follow-up | `.collab/codex-2026-11-20-owner-line-r02.md` (SHA-256 `602ff6d629ebd97b219746bb04a8fa857123494bc39d9526957a7c4df2695c89`) | REJECT |
| r04 | Kimi API (`kimi-k2.6`) | routine; follow-up after Codex reached its daily cap | `.collab/kimi-2026-11-20-owner-line-r04.md` (SHA-256 `195472463f560349576957d49b791a13d1c430155a4a66188fc8a3d0e16d8a6a`) | ACCEPT |

r03 (`.collab/codex-2026-11-20-owner-line-r03.diagnostic.json`) was refused by
the daily Codex cap (8) before any model call; not a review.

## Findings and conditions

| ID | Severity | Disposition | Status |
| :--- | :--- | :--- | :--- |
| R01-F1 | major | verified r04 | resolved |
| R01-F2 | major | verified r02 | resolved |
| R01-F3 | major | verified r02 | resolved |
| R01-C1 | condition | verified r04 | resolved |
| R02-F1 | minor | verified r04 | resolved |
| R02-C1 | condition | verified r04 | resolved |

## Log

- 2026-11-20: regression found from Copilot's T5 report; fix and tests
  written; Codex r01 and r02 REJECT on looseness, then Kimi r04 ACCEPT.
  Commit, push and merge await the sponsor.
