# Workspace knowledge and collaboration framework

Workstream: 2026-10-03-workspace-framework
Owner: Claude (2026-10-03, assigned by the user)
Status: active
Branch: main
Operational: no
Links: [proposal](../proposals/2026-10-03-workspace-framework.md)

## Brief

User goal (2026-10-03): scan every Markdown file and memory entry across
`~/Developer` and design a comprehensive documentation, memory, and
collaboration framework for interchangeable Codex/Claude owners, then review
it adversarially before any rollout. No repository other than this gateway is
changed by this workstream until the user approves a rollout.

## Decisions

- 2026-10-03, user, scope: this framework (v3 §9). Quote: "D1 yes D2 yes D3
  yes D4 yes but prune D5 yes and we should commit".
  - D1: replace prose verbatim transcription with committed raw artifacts plus
    exact-text disposition rows.
  - D2: tier budgets as proposed in v3 §2.
  - D3: compaction monthly and on any budget breach.
  - D4: legacy `COLLAB.md` stays in place, and is pruned by compaction
    (owner reading: duplicated verbatim reviews become links to `.collab/`
    raw artifacts; resolved threads become summaries; git history keeps the
    full text). Supersedes v3's "never edited" rule for legacy `COLLAB.md`.
  - D5: `trading-strategies` git initialization is a separate audited
    decision.
  - "we should commit": owner reading was "commit this workstream's gateway
    records" (done, `b0f2b0a`). **Superseded by user clarification
    2026-10-03:** "i meant put trading strategies under git b/c i thought
    that was the question". D5 therefore resolves to: put `trading-strategies`
    under git now, as its own audited step outside this framework's rollout.
- 2026-10-03, user, scope: framework design. "sprawl is a big part of the
  problem"; STATUS.md treated as RAM with character limits; occasional
  cleanup.

- 2026-10-03, user, scope: this workstream's next step. Quote: "agree on moving on
  to pilot". Paper review rounds stop at r05/v6; the next review covers the
  implementation.

## Reviews

| Round | Reviewer | Tier | Artifact | Verdict |
| :--- | :--- | :--- | :--- | :--- |
| r01 (v1) | Codex | hard (gpt-6-sol, high) | `.collab/codex-2026-10-03-workspace-framework-r01.md` | REJECT |
| r02 (v2) | Codex | hard (gpt-6-sol, high) | `.collab/codex-2026-10-03-workspace-framework-r02.md` | REJECT |
| r03 (v3) | Codex | hard (gpt-6-sol, high) | `.collab/codex-2026-10-03-workspace-framework-r03.md` | REJECT |
| r04 (v4) | Codex | hard (gpt-6-sol, high) | `.collab/codex-2026-10-03-workspace-framework-r04.md` | REJECT |
| r05 (v5) | Codex | hard (gpt-6-sol, high) | `.collab/codex-2026-10-03-workspace-framework-r05.md` | REJECT |
| r06 (implementation 4d3f7bc) | Codex | hard (gpt-6-sol, high) | `.collab/codex-2026-10-03-workspace-framework-r06.md` | REJECT |
| r07 (implementation daf4bb5 + status lines) | Codex | hard (gpt-6-sol, high) | `.collab/codex-2026-10-03-workspace-framework-r07.md` | REJECT |

## Findings and conditions

Compact rows (R05-F15): exact text stays in the indexed raw review.

| ID | Severity | Disposition | Status |
| :--- | :--- | :--- | :--- |
| R01-F1 | blocker | verified r07 | closed |
| R01-F2 | blocker | verified r07 | closed |
| R01-F3 | blocker | verified r07 | closed |
| R01-F4 | major | open: re-verify in r08 | open |
| R01-F5 | major | open: re-verify in r08 | open |
| R01-F6 | major | open: re-verify in r08 | open |
| R01-F7 | major | verified r07 | closed |
| R01-F8 | major | open: re-verify in r08 | open |
| R01-F9 | major | verified r07 | closed |
| R01-F10 | minor | verified r07 | closed |
| R01-F11 | minor | open: re-verify in r08 | open |
| R02-F1 | blocker | verified r07 | closed |
| R02-F2 | blocker | verified r07 | closed |
| R02-F3 | major | verified r07 | closed |
| R02-F4 | major | open: re-verify in r08 | open |
| R02-F5 | major | open: re-verify in r08 | open |
| R02-F6 | blocker | open: re-verify in r08 | open |
| R02-F7 | major | verified r07 | closed |
| R02-F8 | major | open: re-verify in r08 | open |
| R02-F9 | minor | verified r07 | closed |
| R02-F10 | minor | verified r07 | closed |
| R02-F11 | major | open: re-verify in r08 | open |
| R02-F12 | major | verified r07 | closed |
| R02-F13 | major | verified r07 | closed |
| R02-F14 | major | open: re-verify in r08 | open |
| R02-F15 | blocker | verified r07 | closed |
| R02-F16 | major | verified r07 | closed |
| R02-F17 | major | verified r07 | closed |
| R02-F18 | minor | verified r07 | closed |
| R02-C1 | condition | open: re-verify in r08 | open |
| R02-C2 | condition | open: re-verify in r08 | open |
| R02-C3 | condition | open: re-verify in r08 | open |
| R02-C4 | condition | verified r07 | closed |
| R02-C5 | condition | open: re-verify in r08 | open |
| R02-C6 | condition | verified r07 | closed |
| R03-F1 | major | verified r07 | closed |
| R03-F2 | major | verified r07 | closed |
| R03-F3 | blocker | open: re-verify in r08 | open |
| R03-F4 | major | open: re-verify in r08 | open |
| R03-F5 | blocker | open: re-verify in r08 | open |
| R03-F6 | major | verified r07 | closed |
| R03-F7 | major | verified r07 | closed |
| R03-F8 | major | verified r07 | closed |
| R03-F9 | major | open: re-verify in r08 | open |
| R03-F10 | major | open: re-verify in r08 | open |
| R03-F11 | major | verified r07 | closed |
| R03-C1 | condition | open: re-verify in r08 | open |
| R03-C2 | condition | open: re-verify in r08 | open |
| R03-C3 | condition | open: re-verify in r08 | open |
| R03-C4 | condition | verified r07 | closed |
| R03-C5 | condition | open: re-verify in r08 | open |
| R03-C6 | condition | verified r07 | closed |
| R04-F1 | minor | verified r07 | closed |
| R04-F2 | minor | verified r07 | closed |
| R04-F3 | blocker | open: re-verify in r08 | open |
| R04-F4 | minor | verified r07 | closed |
| R04-F5 | major | open: re-verify in r08 | open |
| R04-F6 | minor | verified r07 | closed |
| R04-F7 | major | verified r07 | closed |
| R04-F8 | minor | verified r07 | closed |
| R04-F9 | major | open: re-verify in r08 | open |
| R04-F10 | major | open: re-verify in r08 | open |
| R04-F11 | major | verified r07 | closed |
| R04-F12 | minor | verified r07 | closed |
| R04-C1 | condition | open: re-verify in r08 | open |
| R04-C2 | condition | open: re-verify in r08 | open |
| R04-C3 | condition | open: re-verify in r08 | open |
| R04-C4 | condition | verified r07 | closed |
| R04-C5 | condition | open: re-verify in r08 | open |
| R04-C6 | condition | verified r07 | closed |
| R05-F1 | minor | verified r07 | closed |
| R05-F2 | minor | verified r07 | closed |
| R05-F3 | blocker | open: re-verify in r08 | open |
| R05-F4 | major | verified r07 | closed |
| R05-F5 | major | open: re-verify in r08 | open |
| R05-F6 | minor | verified r07 | closed |
| R05-F7 | minor | verified r07 | closed |
| R05-F8 | minor | verified r07 | closed |
| R05-F9 | minor | open: re-verify in r08 | open |
| R05-F10 | minor | open: re-verify in r08 | open |
| R05-F11 | blocker | verified r07 | closed |
| R05-F12 | minor | verified r07 | closed |
| R05-F13 | major | open: re-verify in r08 | open |
| R05-F14 | major | verified r07 | closed |
| R05-F15 | major | verified r07 | closed |
| R05-C1 | condition | open: re-verify in r08 | open |
| R05-C2 | condition | open: re-verify in r08 | open |
| R05-C3 | condition | open: re-verify in r08 | open |
| R05-C4 | condition | verified r07 | closed |
| R05-C5 | condition | open: re-verify in r08 | open |
| R05-C6 | condition | verified r07 | closed |
| R06-F1 | blocker | verified r07 | closed |
| R06-F2 | blocker | open: re-verify in r08 | open |
| R06-F3 | blocker | open: re-verify in r08 | open |
| R06-F4 | major | open: re-verify in r08 | open |
| R06-F5 | major | open: re-verify in r08 | open |
| R06-F6 | major | open: re-verify in r08 | open |
| R06-F7 | major | open: re-verify in r08 | open |
| R06-F8 | minor | open: re-verify in r08 | open |
| R07-F1 | blocker | open: re-verify in r08 | open |
| R07-F2 | blocker | open: re-verify in r08 | open |
| R07-F3 | blocker | open: re-verify in r08 | open |
| R07-F4 | major | open: re-verify in r08 | open |
| R07-F5 | major | open: re-verify in r08 | open |
| R07-F6 | major | open: re-verify in r08 | open |
| R07-F7 | major | open: re-verify in r08 | open |
| R07-C1 | condition | open: re-verify in r08 | open |
| R07-C2 | condition | open: re-verify in r08 | open |
| R07-C3 | condition | open: re-verify in r08 | open |

## Log

- 2026-10-03: inventory and memory scan complete; proposal v1 drafted.
- 2026-10-03: r01 Codex REJECT (3 blockers). Verified F2 (worktrees have
  separate toplevels). Self-correction: Codex's `memories` feature is disabled,
  so its stale store is inert rather than actively contradicting repos.
  Proposal v2 (MVP) written as a successor; v1 kept unchanged.
- 2026-10-03: r02 Codex REJECT (4 blockers, 18 findings, 6 conditions; labeled
  format followed unprompted). User direction (2026-10-03): "sprawl is a big
  part of the problem"; treat STATUS.md as RAM with character limits; add
  occasional cleanup. Owner reading: prefer policy and narrower claims over new
  machinery that adds files. v3 written as successor.
- 2026-10-03: r03 Codex REJECT (2 blockers, 9 majors; converging). All
  findings accepted; F6 drops the sidecar in line with the sprawl constraint.
  v4 written as successor.
- 2026-10-03: D5 executed: `trading-strategies` audited (3.0 GB licensed raw data and sealed
  artifacts confirmed ignored via `experiment/.gitignore`; root ignore gained
  `.DS_Store`, `__pycache__/`, `*.py[cod]`) and initialized as git, first
  commit `0205f91` (95 files, 1.18 MB, secret scan clean). No remote yet.
- 2026-10-03: r04 Codex REJECT (1 blocker; 7 items satisfied within pilot scope). All
  accepted (F11 partially). v5 = v4 plus targeted edits tagged R04.
- 2026-10-03: r05 Codex REJECT (2 blockers, both refinements; 3 majors from v5's own
  edits). All accepted. v6 = v5 plus targeted edits tagged R05. Owner
  recommendation: stop paper rounds; next review is of the implementation.
- 2026-10-03: r06 (first implementation review) Codex REJECT: 3 blockers, 4
  majors, 1 minor, all accepted and fixed in `daf4bb5`. Legacy triage: the
  24 conditions of r02-r05, never dispositioned before docs-check existed,
  are now rows (open). Round-4/5 verdicts judged findings positionally without
  naming IDs, so their quotes cannot close rows under the strict closure rule;
  r07 is asked for one explicit status line per item ID.
- 2026-10-03: r07 Codex REJECT with explicit per-ID status lines for all 99
  items (about half resolved). The open items reduce to seven root causes,
  fixed together: exact "<ID> is resolved." lines for verified closures;
  `carried` removed; dated, scoped Decisions entries for user-decided; legacy
  list may only shrink and adopted repos need a baseline; review evidence
  must be tracked; deleted/re-added artifacts fail; handoff inventory counts
  checked against git status, observations need a command and result and may
  not be future-dated, and n/a requires `Operational: no`. Residual by
  design: authenticity of transcribed user quotes is policy, not machine-checked.
