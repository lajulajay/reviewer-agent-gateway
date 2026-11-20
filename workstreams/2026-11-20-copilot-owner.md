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
- 2026-11-20, user, scope: Copilot running reviewer wrappers. Quote: "if you
  mean am i ok with it, yes".

## Reviews

| Round | Reviewer | Tier | Artifact | Verdict |
| :--- | :--- | :--- | :--- | :--- |

## Findings and conditions

| ID | Severity | Disposition | Status |
| :--- | :--- | :--- | :--- |

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
