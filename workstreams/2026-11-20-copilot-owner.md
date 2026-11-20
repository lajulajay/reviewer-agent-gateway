# GitHub Copilot as owner and reviewer channel

Workstream: 2026-11-20-copilot-owner
Owner: Claude (2026-11-20, assigned by the user in this session)
Status: active
Branch: main
Operational: no
Links: [proposal](../proposals/2026-11-20-copilot-owner.md), [protocol](../PROTOCOL.md)

## Brief

Add GitHub Copilot (coordinator plus sub-agents) as an owner and as a
multi-vendor reviewer channel. Separate channel from model vendor and forbid
any vendor reviewing its own work across model versions. Design and phases
are in the proposal. No production service is changed.

## Decisions

- 2026-11-20, user, scope: this workstream's goal. Quote: "need to update
  agent-reviewer-gateway to include Copilot as an owner who can request
  reviews". Supersedes: none.
- 2026-11-20, user, scope: proposal approval and revisions. Quote: "draft
  approved after accounting for the above". The revisions: Copilot as a
  reviewer is "not opposed but should be informed by underlying model used";
  "we need logic to ensure a provider isn't reviewing itself if it's
  different model versions", corrected by the sponsor to "not reviewing
  itself even if it's different model versions". Supersedes: Gemini as default reviewer of
  Copilot work (based on an assumption the sponsor withdrew).
- 2026-11-20, user, scope: commit Phase 1. Quote: "yes commit phase 1".
  Committed as 9fff067 on branch `copilot-owner-phase1`; merge to `main`
  still needs the sponsor's approval.
- 2026-11-20, user, scope: Phase 1 Gemini review r02 only; run with
  `GEMINI_REVIEW_MIN_QUOTA=0.03` instead of the 0.15 floor (r01 was refused
  at 0.0799 remaining). Quote: "use the lowered Gemini floor". Accepted risk:
  if the quota runs out during the call, Antigravity may spend AI credits.
- 2026-11-20, user, scope: Copilot running reviewer wrappers. Quote: "if you
  mean am i ok with it, yes".

## Reviews

| Round | Reviewer | Tier | Artifact | Verdict |
| :--- | :--- | :--- | :--- | :--- |
| r02 | Gemini (`gemini-3.8-flash-high`) | hard; changes who may review whom in every repository | `.collab/gemini-2026-11-20-copilot-owner-phase1-r02.json` (SHA-256 `99fec6f5c65f9d9c90020c7a80c2573439345f22930beb35dc125ab18a612fe7`) | ACCEPT WITH CONDITIONS |

r01 (`.collab/gemini-2026-11-20-copilot-owner-phase1-r01.diagnostic.json`) was
refused at the quota floor before any model call; not a review. r02 ran under
the lowered floor (see Decisions) and left the weekly Gemini quota at 0.

## Findings and conditions

| ID | Severity | Disposition | Status |
| :--- | :--- | :--- | :--- |
| R02-F1 | minor | fixed 605cdc0 | proposal moves task-table checks to Phase 3 with the template; pending push |
| R02-F2 | minor | fixed 605cdc0 | PROTOCOL synopses list `--author` and `--task`; pending push |
| R02-C1 | condition | | open: fixed in 605cdc0; no Gemini quota for a check round, awaiting sponsor acceptance |

## Log

- 2026-11-20: proposal drafted, revised for the sponsor's answers and
  approved; Phase 1 (registry, `--owner copilot`, vendor rule, docs-check)
  next.
- 2026-11-20: Phase 1 implemented in the live checkout: `agents.json`,
  `agents.py`, all wrappers, `reviewer-select.py`, `docs-check.py`,
  README/PROTOCOL, roster (Claude only active). 65 Python tests and the
  wrapper smoke test pass; `record` on six repos shows no new errors.
- 2026-11-20 17:06 ET incident: the uncommitted wrapper edits tripped the
  gateway dirty check and refused Copilot's T5 Claude review
  (`copilot-worktrees/trading-strategies/lajulajay-supreme-robot/.collab/claude-2026-11-20-index-options-t5-r05.diagnostic.json`,
  exit 78, no model call). Phase 1 moved to stash
  `1c6b49372c37caa1328f7d46e50ec79a65ea578b` at 17:07 ET; the gateway is clean.
  Lesson: develop gateway changes in a separate worktree, never the live
  checkout.
- 2026-11-20: Gemini r02 ACCEPT WITH CONDITIONS (two minor findings, one
  condition); fixes committed as 605cdc0 on `copilot-owner-phase1`. Merge to
  `main` and push await the sponsor.
