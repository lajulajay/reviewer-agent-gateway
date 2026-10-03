# Workspace knowledge and collaboration framework — proposal v3

Owner: Claude · Reviewer: Codex (primary), Gemini (backup) · Status: draft for
review round 3 · 2026-10-03 · Supersedes v2 (kept unchanged). Reviews:
`.collab/codex-2026-10-03-workspace-framework-r01.md`, `-r02.md` (both
REJECT); dispositions in `workstreams/2026-10-03-workspace-framework.md`.

## 1. Direction

The user's direction for v3: **sprawl is a central problem** (1,040 Markdown
files; five `COLLAB.md` files of 3,600–6,100 lines; `CLAUDE.md` files up to
1,146 lines; ~77 KB of agent memory that partly contradicts the repositories).
`STATUS.md` should be treated as **RAM with a character limit**, and the system
needs **periodic cleanup**.

Design rule that follows: **every mechanism must reduce or bound text, not add
files.** Where round 2 asked for new machinery (capture receipts, digest
enforcement, atomic locking), v3 uses a policy owned by the single user, or
narrows the guarantee instead.

## 2. The memory hierarchy

Every piece of text lives in exactly one tier. Each tier has a budget; a tier
over budget must evict to the tier below.

| Tier | Like | Files | Budget | Lifecycle |
| :--- | :--- | :--- | :--- | :--- |
| T0 Working set | RAM | `STATUS.md` (per repo) | **≤ 4,000 characters** | Overwritten; read at every session start; holds only what is live now |
| T1 Rules | ROM | `AGENTS.md` (repo rules) and gateway `PROTOCOL.md` (shared rules) | `AGENTS.md` ≤ 12,000 characters | Edited in place; changes are reviewed |
| T2 Knowledge | Disk | `docs/` (architecture, operations, lessons; today's `CLAUDE.md` bodies) | ≤ 60,000 characters per repo, reported | Edited in place; deduplicated at compaction |
| T3 Records | Disk, append | `workstreams/*.md`, `experiments/<id>/` | active workstream ≤ 30,000 characters | Appended while active; compacted at close |
| T4 Cold storage | Tape | `.collab/` raw reviews, packets, prompts, legacy `COLLAB.md`, `workstreams/closed/` | measured, uncapped | Never edited; rarely read |
| A Agent cache | Per-agent | Claude auto-memory; Codex memories (disabled) | index ≤ 2,000; entry ≤ 1,500; total ≤ 15,000 characters | Preferences, tool quirks, pointers only; the repository wins every conflict |

`CLAUDE.md` becomes a T1 stub: `@AGENTS.md` plus Claude-only quirks
(≤ 1,500 characters). Its current body is T2 content and moves to `docs/` in a
compaction pass, not at adoption.

**`STATUS.md` contents (T0), fixed sections:** as-of timestamp and revision ·
active workstreams (one line each: ID, owner, state, next action, link) ·
live-system observations (each with time and how observed) · blockers waiting
on the user · pending items (each with a durable location). Nothing historical,
nothing explanatory — link to T2/T3 instead. `STATUS.md` is orientation only
and never authorizes an action (§5).

## 3. Review obligations (resolves R01-F1/F6, R02-F1/F6/F12/F14/F15)

1. **Labeled output.** Findings are `F<n> [blocker|major|minor]: …`, conditions
   `C<n>: …` (round 2 followed this format unprompted). The output contract
   also requires the line `ATTESTATION: all actionable findings and conditions
   are labeled.` Validation fails closed if the verdict needs labels and they
   are absent, or the attestation is missing.
2. **Sidecar.** The wrapper writes `<artifact>.findings.json` (verdict, owner,
   reviewer, model, standards revision, findings and conditions with exact
   text) and includes it in the checksum.
3. **Disposition rows.** `docs-check dispositions <artifact>` prints one row per
   finding *and* condition with exact text; the owner fills disposition and
   status. Rejecting a blocker or condition requires `user-decided <date>:
   <quote>`; `fixed <commit>` must name a commit in pushed history.
4. **Guarantee, stated narrowly.** Omission or rewording of labeled items is
   detected mechanically; unlabeled prose is covered by the reviewer's
   attestation and the owner's reading of the raw artifact. Artifacts are
   tamper-evident only from their first push.

## 4. Ownership and handoff (resolves R01-F2/F3/F4/F11, R02-F2/F3/F4/F8/F11/F16)

- **Assignment is a user act.** The user is the only assigner. An assignment is
  a committed, pushed `Owner:` line in the workstream header naming the
  revision it was made against. A session confirms that line on the remote
  before starting work; if it names the other agent, the session reviews or
  stops.
- **Three checks, one tool** (`docs-check`):
  - `record` — every `.collab/` artifact appears in a review index; every
    labeled item has a row; links resolve; budgets respected.
  - `transfer` — `record` passes; no uncommitted tracked changes; branch equals
    its pushed upstream; untracked and ignored-but-relevant files are listed in
    the handoff block; open obligations are listed, not hidden; for
    operational workstreams, a runtime observation from the same day is
    recorded. Legacy reviews of an active workstream are triaged before its
    first transfer.
  - `done` — `transfer` passes and every blocker and condition is resolved.
- **Handoff block** (appended to the workstream file): current state ·
  decisions (with scope and supersession) · open obligations · runtime
  observation (time, commands, result) · restart sequence. The new owner
  re-verifies the runtime observation on resume.
- **Concurrency.** One owner per workstream, enforced by the assignment rule;
  concurrent workstreams use separate worktrees and separate files. No lock
  file.

## 5. Authority (resolves R01-F5, R02-F5)

| Claim | Source | Rule |
| :--- | :--- | :--- |
| Runtime fact | the live system, now | Re-verify before acting; documents say how to check |
| User decision | dated quote in a workstream or experiment spec, with scope and supersession | Required for every stop-for-user action |
| Review obligation | sidecar + disposition rows | `done` check governs |
| Research claim | `experiments/<id>/` | Status changes need a dated results entry |
| Orientation | `STATUS.md`, `AGENTS.md`, indexes | Never authorizes |

## 6. Cleanup: eviction and compaction (user direction)

- **Eviction (continuous).** When `STATUS.md` exceeds its cap, the owner moves
  the oldest non-live content to the workstream file or `docs/` before
  committing. The same applies to every capped tier. `docs-check record` fails
  on any cap breach, so eviction cannot be skipped silently.
- **At every transfer or `done`.** The departing owner prunes `STATUS.md` to
  live items only. At `done`, the workstream gets a ≤ 1,500-character outcome
  summary at its top and moves to `workstreams/closed/`; its line leaves
  `STATUS.md`.
- **Compaction pass (periodic).** A workstream of its own, assigned by the user
  monthly or when `docs-check report` shows any tier over budget. It:
  deduplicates facts across T1–T2 (a fact found in two places keeps one home,
  the other becomes a link); moves `CLAUDE.md` bodies into `docs/`; reconciles
  experiment indexes against results; checks agent memory against the
  repositories and deletes or rewrites conflicting entries; lists stale
  branches and worktrees for the user. It is reviewed like any other
  workstream; the reviewer's question is "was anything lost or changed in
  meaning?"
- **Sprawl report.** `docs-check report` prints character totals per tier per
  repository, so growth is visible and compaction is triggered by numbers, not
  judgement.

## 7. Standards and shared resources (resolves R01-F7, R02-F7/F17)

- `AGENTS.md` pins `Standards: reviewer-agent-gateway@<commit>`. Each review
  sidecar records the standards revision actually used; a mismatch with the
  branch pin is reported by `docs-check record`, not blocked.
- Shared-resource facts (the Modal cron allocation, the shared Supabase project
  and schemas, secret locations) live once in gateway `PROTOCOL.md` as
  pointers to the live command that verifies them, never as counts that go
  stale.

## 8. Rollout (resolves R01-F3/F9, R02-F3/F9)

1. Gateway: wrapper contract (labels, attestation, sidecar, standards
   revision); `docs-check` (`record`, `transfer`, `done`, `dispositions`,
   `report`) with provider-free tests; templates. This workstream is the first
   user; its own `docs-check done` must pass before rollout.
2. Pilot: `kalshi-finance-agent` (paused, clean, no session). Adoption: inventory
   and preserve the working tree; verify what each agent loads before and after
   adding `@AGENTS.md`; create `STATUS.md` and `workstreams/`; mark `COLLAB.md`
   legacy (T4) in place.
3. Other repositories adopt at their next transfer event, never in a dirty
   working tree.
4. The first compaction pass runs after the pilot and includes Claude's agent
   memory (today ~77 KB against a 15,000-character budget).
5. `trading-strategies` git initialization stays a separate, audited decision.

## 9. Decisions for the user

- **D1** Replace prose verbatim transcription with committed raw artifacts plus
  exact-text disposition rows (§3)? Recommended: yes.
- **D2** Budgets as proposed (§2), or different numbers?
- **D3** Compaction cadence: monthly plus on budget breach?
- **D4** Leave legacy `COLLAB.md` in place as cold storage? Recommended: yes.
- **D5** `trading-strategies` git: separate decision? Recommended: yes.

## 10. Remaining risks

- Character caps can push content into the wrong tier to pass the check; the
  compaction review is the control for meaning, not the script.
- The reviewer attestation is a promise, not a proof.
- Runtime observations are attested by the owner.
- Force-pushes would defeat tamper-evidence; branch protection is not
  configured.
