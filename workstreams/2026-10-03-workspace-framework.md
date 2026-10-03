# Workspace knowledge and collaboration framework

Workstream: 2026-10-03-workspace-framework
Owner: Claude (2026-10-03, assigned by the user)
Status: active
Branch: main
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
  - "we should commit": owner reading — commit this workstream's gateway
    records now (not pushed).
- 2026-10-03, user, scope: framework design. "sprawl is a big part of the
  problem"; STATUS.md treated as RAM with character limits; occasional
  cleanup.

## Reviews

| Round | Reviewer | Tier | Artifact | Verdict |
| :--- | :--- | :--- | :--- | :--- |
| r01 (v1) | Codex | hard (gpt-6-sol, high) | `.collab/codex-2026-10-03-workspace-framework-r01.md` | REJECT |
| r02 (v2) | Codex | hard (gpt-6-sol, high) | `.collab/codex-2026-10-03-workspace-framework-r02.md` | REJECT |

## Findings and conditions

| ID | Severity | Finding | Disposition | Status |
| :--- | :--- | :--- | :--- | :--- |
| R01-F1 | blocker | D1 checksum+table does not preserve anti-softening; owner can omit a condition | Accepted. v2: wrapper extracts labeled findings into a sidecar at capture; disposition table skeleton generated with exact text; check enforces completeness | resolved in v2 |
| R01-F2 | blocker | Untracked lock is per-worktree; PID host-local; concurrent sessions not serialized; main-only process docs race | Accepted (verified: worktrees have separate toplevels). v2: lock advisory only; serialization via handoff event; no hand-edited shared status row; standards pinned by revision | resolved in v2 |
| R01-F3 | blocker | Migration can erase uncommitted work or change live instructions | Accepted. v2: no archive moves or entry-point rewrites; repos adopt only at their next handoff from a clean, preserved revision; loader behavior verified first | resolved in v2 |
| R01-F4 | major | 'Committed or declared' still leaves invisible state | Accepted. v2: handoff requires committed and pushed content; a pending declaration never completes a handoff | resolved in v2 |
| R01-F5 | major | Source precedence lets stale STATUS authorize actions | Accepted. v2: authority by claim type; summaries never authorize; runtime facts re-verified live | resolved in v2 |
| R01-F6 | major | docs-check gameable; misses closure invariant; self-maintained hashes not immutability | Accepted. v2: closure check traces every finding to a disposition; immutability claims limited to git history of pushed commits | resolved in v2 |
| R01-F7 | major | Centralization creates new drift; repo no longer self-contained | Partially accepted. Volatile facts stay repo-local; only shared-resource facts (cron cap, shared database) get one home; standards pinned by revision | resolved in v2 (partial) |
| R01-F8 | major | Triage open obligations before restructuring; owner check per round | Accepted. v2: triage at each workstream's first handoff; owner≠reviewer checked per round | resolved in v2 |
| R01-F9 | major | git init of trading-strategies is a separate risk decision | Accepted. Removed from rollout; separate audited decision | resolved in v2 |
| R01-F10 | minor | Too large; propose minimum viable version | Accepted. v2 is an MVP; other layers deferred until a pilot shows need | resolved in v2 |
| R01-F11 | minor | Workflow failure needs a defined handoff event | Accepted. Handoff event is v2's central mechanism | resolved in v2 |
| R02-F1 | blocker | Reviewer could leave a condition unlabeled in prose | Accepted as policy: wrapper contract requires an attestation line that every actionable item is labeled; owner checks the raw artifact at closure | resolved in v3 |
| R02-F2 | blocker | Two sessions can pass handoff-check and both proceed | Accepted as policy: only the user assigns owners, via a committed and pushed Owner line naming the revision; sessions confirm it before starting | resolved in v3 |
| R02-F3 | major | Clean revision may hide un-inventoried dirty work; @AGENTS.md may change loader | Accepted: inventory of the working tree preserved before adoption; loader check per repo | resolved in v3 |
| R02-F4 | major | Untracked work escapes handoff-check | Accepted: handoff lists untracked and ignored-but-relevant files; pending items must have durable locations | resolved in v3 |
| R02-F5 | major | Superseded decisions could still be quoted | Accepted: decisions carry scope and a supersedes/superseded-by field | resolved in v3 |
| R02-F6 | blocker | Owner can reject a blocker unilaterally; fix commit unverified | Accepted: rejecting a blocker or condition requires a recorded user decision; fix commits must exist in the pushed history | resolved in v3 |
| R02-F7 | major | Pin vs loaded standards mismatch; static cron count goes stale | Partially accepted: reviews record the standards revision used; shared-resource facts become pointers to a live check, not counts | resolved in v3 |
| R02-F8 | major | Legacy triage waits for first handoff | Accepted: triage before transfer or done | resolved in v3 |
| R02-F9 | minor | Keep git-init boundary explicit | Accepted | resolved in v3 |
| R02-F10 | minor | Basic artifact and link check missing from core | Accepted: in core | resolved in v3 |
| R02-F11 | major | Runtime check can be stale | Accepted: operational workstreams require a same-day runtime observation at handoff and re-verification on resume | resolved in v3 |
| R02-F12 | major | Conditions lack generated rows | Accepted: conditions are records too | resolved in v3 |
| R02-F13 | major | Artifact and sidecar can both be altered before first push | Accepted by narrowing the claim; no separate receipt service (sprawl) | resolved in v3 |
| R02-F14 | major | Unlinked reviews escape closure | Accepted: every captured artifact in .collab/ must appear in some review index | resolved in v3 |
| R02-F15 | blocker | Handoff vs closure rules conflict | Accepted: separate record-complete, transfer (open items allowed, listed) and done (all resolved) checks | resolved in v3 |
| R02-F16 | major | Owner assignment can race or stay uncommitted | Accepted as policy (see R02-F2) | resolved in v3 |
| R02-F17 | major | Reviewer may apply newer standards than branch pin | Partially accepted: standards revision recorded with each review; no digest enforcement | resolved in v3 |
| R02-F18 | minor | Deferral triggers not observable | Accepted: triggers replaced by measurable caps and the periodic compaction pass | resolved in v3 |

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
