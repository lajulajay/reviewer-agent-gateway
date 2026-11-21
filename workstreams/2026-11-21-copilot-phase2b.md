# Copilot coordinator support (Phase 2b)

Workstream: 2026-11-21-copilot-phase2b
Owner: Claude (2026-11-21, assigned by the user in this session)
Status: active
Branch: copilot-phase2b
Operational: no
Links: [Phase 2a](2026-11-21-copilot-reviewer.md), [proposal](../proposals/2026-11-20-copilot-owner.md), [README tickets](../README.md), [protocol](../PROTOCOL.md)

## Brief

The rest of proposal Phase 2 after the Copilot reviewer channel (2a):

- **Automatic selection (D3, D4).** `reviewer-roster.json` lists Copilot
  (active, last in tie order). `reviewer-select.py` treats Copilot as
  eligible when `copilot-model-policy.json` maps an eligible model for the
  tier, which `auto-review.sh` now passes; a channel that owns or wrote the
  work ranks after every other channel and does not keep a follow-up.
  `auto-review.sh` reserves the `copilot-` name with the others.
- **Escalation (D4).** When the escalation reviewer (Gemini) is ineligible
  because a Google model wrote the work, `copilot-review.sh` passes
  `--escalation-substitute <vendor>` and `review-budget.py` lets Copilot run
  the escalation rounds with a vendor that has not reviewed the topic.
- **Review requests.** `review-request.py` accepts `--reviewer copilot` and
  `--vendor`, records the resolved vendor and model at `create`, and passes
  `--vendor` at `run`.
- **Tickets (D5).** New `review-ticket.py issue|check|list`. Every wrapper
  calls `check` before any model call: a Copilot task needs a matching
  ticket (reviewer or `auto`, vendor, tier, identity, packet scope).
- **Pool and batches (D6).** A user Decisions line `Review pool: copilot
  20/day` in the ticket's workstream replaces the per-repository daily cap for
  that workstream's ticketed rounds; pooled rounds do not count against other
  work. A batch ticket (`--batch`, routine only) covers several tasks.

No production service changes; the live gateway is untouched until merge.

## Decisions

- 2026-11-21, user, scope: Phase 2b (automatic selection, Copilot review
  requests, tickets, review pool and batching). Quote: "proceed with phase
  2b". Supersedes: none.
- 2026-11-21, user, scope: R02-F1 (agents could forge a review-pool line).
  Quote: "i reverse myself and accept the risk" (after first choosing
  "Move pools to gateway", which was reverted before any commit).
  Supersedes: none.
- 2026-11-21, user, scope: this change. Quote: "Yes, commit and merge".
  Supersedes: none.

## Reviews

| Round | Reviewer | Tier | Artifact | Verdict |
| :--- | :--- | :--- | :--- | :--- |
| r02 | Copilot (`gpt-6-luna`, OpenAI) | routine; hard round already spent by r01 | `.collab/copilot-2026-11-21-copilot-phase2b-r02.md` (SHA-256 `7bd671ef875bcb9d2247b67e988b26a2d3f6207e65232a8567286d407b59fd7c`) | REJECT |
| r03 | Copilot (`gpt-6-luna`, OpenAI) | routine; follow-up of r02 | `.collab/copilot-2026-11-21-copilot-phase2b-r03.md` (SHA-256 `e5e46b96114f3c96b0cb0d02c4c40e04a128d694e54964c2c72be0f67d145244`) | ACCEPT |

Codex (`.collab/codex-2026-11-21-copilot-phase2b.diagnostic.json`) was refused
at preflight by the daily cap (9 of 8); no model call, not a round. Kimi hard
r01 (`.collab/kimi-2026-11-21-copilot-phase2b.diagnostic.json`, `kimi-k3.1-pro`)
reached the model and was rejected at its output limit after 25 minutes; it
counts as a spent round and as the topic's hard round.

## Findings and conditions

| ID | Severity | Disposition | Status |
| :--- | :--- | :--- | :--- |
| R02-F1 | major | user-decided 2026-11-21 "i reverse myself and accept the risk" | resolved: pools stay as user Decisions lines; risk documented in README |
| R02-F2 | major | verified r03 | resolved |
| R02-F3 | minor | verified r03 | resolved |
| R03-F1 | major | not a defect: the reviewer labeled its confirmation that R02-F1 is resolved | resolved |
| R03-F2 | major | not a defect: the reviewer labeled its confirmation that R02-F2 is resolved | resolved |
| R03-F3 | minor | not a defect: the reviewer labeled its confirmation that R02-F3 is resolved | resolved |

## Log

- 2026-11-21: implemented in worktree branch `copilot-phase2b`; 148 unit
  tests and the wrapper smoke test (new ticket, tier-mismatch and escalation
  cases) pass. Not committed.
- 2026-11-21: Codex refused (daily cap); Kimi hard r01 hit its output limit
  (spent). Copilot routine r02 REJECT: F2 and F3 fixed with tests (149 unit
  tests and smoke pass); F1 goes to the sponsor. PROTOCOL trimmed to its
  12000-character budget.
- 2026-11-21: sponsor accepted R02-F1's risk; a brief gateway-file pool
  (`review-pools.json`) was reverted uncommitted. 149 unit tests pass.
- 2026-11-21: Copilot r03 ACCEPT: R02-F2 and R02-F3 verified, R02-F1
  resolved by sponsor decision. Review complete.
