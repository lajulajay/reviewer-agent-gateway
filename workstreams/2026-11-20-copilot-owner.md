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
- 2026-11-20, user, scope: Codex and Kimi API routes. Quote: "i have API
  credits with OpenAI ($20) and Kimi ($11). let's change the route for both
  from subscription to API or enable both if possible". Keys stored by the
  user in the Keychain; auto-recharge off; gateway caps $18 (OpenAI) and $10
  (Kimi) accepted ("done"). Models: OpenAI "revert OpenAi models to 6"
  corrected to "meant 6.1" (hard `gpt-6.1-sol`, routine `gpt-6.1-terra`);
  Kimi hard `kimi-k3.1-pro`, routine `kimi-k2.6`. Supersedes: Codex and Kimi
  inactive.
- 2026-11-20, user, scope: Copilot running reviewer wrappers. Quote: "if you
  mean am i ok with it, yes".

## Reviews

| Round | Reviewer | Tier | Artifact | Verdict |
| :--- | :--- | :--- | :--- | :--- |
| r01 | Codex API (`gpt-6.1-sol`) | hard; first review of the spend-capped API route, which handles keys and money | `.collab/codex-2026-11-20-api-route-r01.md` (SHA-256 `cd7f8ffcfa4b0777932fa480de1f66e9fc97d808b7ed3fa84c8168e720348241`) | REJECT |
| r03 | Codex API (`gpt-6.1-terra`) | routine; follow-up of r01 (file name `-r02`) | `.collab/codex-2026-11-20-api-route-r02.md` (SHA-256 `5806cc886f55296e7f064d693ec5808d7712fb51533852c092b867d2991ac8fb`) | REJECT |
| r04 | Codex API (`gpt-6.1-terra`) | routine; follow-up (file name `-r03`) | `.collab/codex-2026-11-20-api-route-r03.md` (SHA-256 `3f864ec92a67cc548e4c49cb86ce8dd902b1d2c7e542543fc5cf0b59f1dc976b`) | REJECT |
| r05 | Codex API (`gpt-6.1-terra`) | routine; follow-up | `.collab/codex-2026-11-20-api-route-r05.md` (SHA-256 `3d5f48bb5cbf2f96455d58d6cf845000065efe414a5528727db6ecd7d16654ac`) | REJECT |
| r02 | Gemini (`gemini-3.8-flash-high`) | hard; changes who may review whom in every repository | `.collab/gemini-2026-11-20-copilot-owner-phase1-r02.json` (SHA-256 `99fec6f5c65f9d9c90020c7a80c2573439345f22930beb35dc125ab18a612fe7`) | ACCEPT WITH CONDITIONS |

r01 (`.collab/gemini-2026-11-20-copilot-owner-phase1-r01.diagnostic.json`) was
refused at the quota floor before any model call; not a review. r02 ran under
the lowered floor (see Decisions) and left the weekly Gemini quota at 0.

## Findings and conditions

| ID | Severity | Disposition | Status |
| :--- | :--- | :--- | :--- |
| R01-F1 | blocker | verified r03 | resolved |
| R01-F2 | major | verified r04 | resolved |
| R01-F3 | major | | open: all output redacted, key validated without echo, no tracebacks; tests added; remainder tracked as R03-F2 |
| R01-F4 | blocker | verified r03 | resolved |
| R01-F5 | blocker | | open: locked, fsynced reserve-then-settle ledger; crash keeps reservation; concurrency test; remainder tracked as R03-F3 |
| R01-F6 | blocker | | open: failures and missing usage keep the full reservation; only 400/401/403/404/422 release; remainder tracked as R03-F4 |
| R01-F7 | major | verified r04 | resolved |
| R01-F8 | major | verified r05 | resolved |
| R01-F9 | major | verified r04 | resolved |
| R01-F10 | major | verified r03 | resolved |
| R01-F11 | minor | | open: README and PROTOCOL rewritten to match; roster wording covers API reviewers; remainder tracked as R03-F4 |
| R01-C1 | condition | | open: model, price and reasoning-token semantics need sponsor confirmation from first-party pages |
| R03-F1 | major | | open: keychain-store refuses non-tty input and the getpass echo fallback; awaiting r04 |
| R03-F2 | major | | open: error bodies never echoed (only error type/code); JSON-escaped key redacted; reply and metadata redacted before writing; awaiting r04 |
| R03-F3 | major | | open: state directory and new ledger file are directory-fsynced on creation; awaiting r04 |
| R03-F4 | major | | open: reply validated before settling; rejected replies keep the full bound; test added; awaiting r04 |
| R03-F5 | major | | open: ledger amounts must be JSON integers >= 0 (bool, float, string refused); test added; awaiting r04 |
| R03-F6 | major | | open: prompt assembly and artifact values checked step by step; awaiting r04 |
| R03-F7 | minor | | open: exit 0 without marker maps to 78; smoke case added; awaiting r04 |
| R03-F8 | minor | | open: any present `function_call`, even null, is a tool call (live Moonshot replies carry none); test added; awaiting r04 |
| R03-C1 | condition | | open: same as R01-C1; Moonshot evidence: reasoning tokens are inside `completion_tokens` and `max_tokens` |
| R04-F1 | major | | open: error type/code reported only if identifier-shaped and unchanged by redaction; awaiting r05 |
| R04-F2 | major | | open: parent and state directories fsynced under the lock on every reservation; awaiting r05 |
| R04-F3 | major | | open: api-call runs the substance validator before settling; rejected replies keep the full bound; awaiting r05 |
| R04-F4 | major | verified r05 | resolved |
| R05-F1 | major | | open: no field of an error body is printed; HTTP status only; awaiting r06 |
| R05-F2 | major | | open: STATE and every ancestor to / fsynced under the lock on each reservation; awaiting r06 |
| R05-F3 | major | | open: reply redacted first; that exact text is validated, settled and stored; awaiting r06 |
| R05-C1 | condition | | open: r06 packet includes the raw r02 review so R03-F1 can be checked |
| R05-C2 | condition | | open: r06 packet includes the raw r02 review so R03-F2 can be checked |
| R05-C3 | condition | | open: r06 packet includes the raw r02 review so R03-F3 can be checked |
| R05-C4 | condition | | open: r06 packet includes the raw r02 review so R03-F4 can be checked |
| R05-C5 | condition | | open: r06 packet includes the raw r02 review so R03-F5 can be checked |
| R05-C6 | condition | | open: r06 packet includes the raw r02 review so R03-F6 can be checked |
| R05-C7 | condition | | open: r06 packet includes the raw r02 review so R03-F7 can be checked |
| R05-C8 | condition | | open: r06 packet includes the raw r02 review so R03-F8 can be checked |
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
- 2026-11-20: API route committed (d96f496); Codex API r01 REJECT with five
  blockers on key confinement and spend accounting. All addressed in the next
  commit; ledgers migrated to the reserve/settle format (pre-migration copies
  kept beside them). Follow-up r02 to verify.
- 2026-11-20: Codex r02 (indexed r03): R01-F1, F4, F10 resolved; eight narrower findings fixed. Manual Moonshot reply-shape probe ($0.0002) entered in the ledger by hand.
- 2026-11-20: Codex r03 (indexed r04): R01-F2, F7, F9 resolved; four remaining items fixed.
- 2026-11-20: first round-4 attempt refused at preflight (packet copies named .py/.sh tripped the dirty check; `.collab/codex-2026-11-20-api-route-r04.diagnostic.json`, no model call). Codex r05: R01-F8 and R04-F4 resolved; three items fixed; R03 items need the r02 text, supplied in r06 (last round for this topic).
