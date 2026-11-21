# Copilot as a reviewer channel (Phase 2a)

Workstream: 2026-11-21-copilot-reviewer
Owner: Claude (2026-11-21, assigned by the user in this session)
Status: active
Branch: copilot-phase2
Operational: no
Links: [Copilot owner workstream](2026-11-20-copilot-owner.md), [README Copilot reviews](../README.md), [protocol](../PROTOCOL.md)

## Brief

Copilot becomes a direct-call reviewer channel. `copilot-review.sh` picks a
model by tier and vendor from `copilot-model-policy.json` through
`copilot-model-select.py`; the reviewer's vendor is that model's vendor, so
the vendor rule applies per model (Copilot never reviews work of a vendor
whose model it would use). The CLI runs in an empty directory with every
tool hidden and denied, MCP servers disabled, custom instructions off, and an
AI-credit cap per call; any tool event, enabled MCP server, missing result,
incomplete reply or other resolved model fails the review. `agents.json`
marks Copilot `can_review`; `review-budget.py` counts Copilot rounds and its
`hard` tier; `docs-check.py` re-checks Copilot artifacts by their selected
model. Automatic selection, review requests for Copilot, tickets and the
reviewer pool are Phase 2b.

A live routine review (`gpt-6-luna`, Claude-owned packet, in a scratch
repository) produced a valid artifact with zero tool events and 0.106 AI
credits. Two live findings were fixed before it: the CLI refuses
`--max-ai-credits` below 30, and every reply carries `serverTools:
{"provider": ...}` metadata and arrives as several chunk messages grouped by
`originatingMessageId`, not `messageId`.

## Decisions

- 2026-11-21, user, scope: Phase 2 (Copilot reviewer channel). Quote: "you
  proceed with phase 2". Supersedes: none.
- 2026-11-21, user, scope: open review items after five rounds (Gemini
  unavailable). Quote: "R01-F4, R05-F1, R05-F2 accepted". Supersedes: none.
- 2026-11-21, user, scope: the tier × vendor model mapping and per-call
  AI-credit caps (hard 60, routine 30) in `copilot-model-policy.json`.
  Quote: "recommendation accepted". Supersedes: none.
- 2026-11-21, user, scope: this change. Quote: "commit, push and merge
  approved". Supersedes: none.

## Reviews

| Round | Reviewer | Tier | Artifact | Verdict |
| :--- | :--- | :--- | :--- | :--- |
| r01 | Codex API (`gpt-6.1-sol`) | hard; new isolation boundary and vendor-rule path for a multi-vendor channel | `.collab/codex-2026-11-21-copilot-reviewer.md` (SHA-256 `abdb7090303eebe01e13c1c3204d8b51fc45626dda98360f4b2e6f306c7f61ef`) | REJECT |
| r02 | Codex API (`gpt-6.1-terra`) | routine; follow-up | `.collab/codex-2026-11-21-copilot-reviewer-r02.md` (SHA-256 `800523ee5d9972e94dbcba99ccde2734fadb0b859985dc1313316f0620c42dd0`) | REJECT |
| r05 | Codex API (`gpt-6.1-terra`) | routine; follow-up | `.collab/codex-2026-11-21-copilot-reviewer-r05.md` (SHA-256 `9b98e42e69f27507465661600e0e0eea651fd167ae9baae28f4c3e02ccb1aa9e`) | REJECT |

r03 and r04 (`.collab/codex-2026-11-21-copilot-reviewer-r03.diagnostic.json`,
`-r04.diagnostic.json`) reached the model and were refused by the gateway's
substance check, which does not record its reason on the API route; both count
as spent rounds. r05 added explicit output-labeling instructions and passed.
Gemini r06 (`.collab/gemini-2026-11-21-copilot-reviewer-r06.diagnostic.json`)
was refused at preflight (weekly quota 0, below the 0.15 floor); no model
call, not a round. The open items go to the user.

## Findings and conditions

| ID | Severity | Disposition | Status |
| :--- | :--- | :--- | :--- |
| R01-F1 | major | verified r02 | resolved |
| R01-F2 | major | verified r05 | resolved |
| R01-F3 | major | verified r05 | resolved |
| R01-F4 | major | user-decided 2026-11-21 "R01-F4 accepted" | resolved: signal window closed and smoke-tested after r05 |
| R01-F5 | major | verified r02 | resolved |
| R01-C1 | condition | verified r02 | resolved |
| R01-C2 | condition | verified r02 | resolved |
| R01-C3 | condition | user-decided 2026-11-21 "recommendation accepted" | resolved: sponsor accepted the mapping and caps |
| R02-F1 | minor | verified r05 | resolved |
| R02-C1 | condition | user-decided 2026-11-21 "recommendation accepted" | resolved: same decision as R01-C3 |
| R05-F1 | major | user-decided 2026-11-21 "R05-F1 accepted" | resolved: unique staging and no-clobber links, smoke-tested |
| R05-F2 | minor | user-decided 2026-11-21 "R05-F2 accepted" | resolved: same fix as R01-F4 |

## Log

- 2026-11-21: wrapper, selector, policy, registry, budget and docs-check
  changes with unit and smoke tests; live smoke review passed. Codex hard
  r01 REJECT (5 majors, 3 conditions); fixes and tests written. Codex r02
  REJECT (F2-F4 edge cases, one minor test gap); fixed. r03 and r04 refused by
  the format check; Codex r05 REJECT (publication window and concurrent
  staging); fixed with no-clobber links. Five rounds used; Gemini unavailable
  (quota), so R01-F4, R05-F1 and R05-F2 go to the user. Live runs after each
  fix passed. Sponsor accepted the open items and the mapping; commit,
  push and merge approved.
