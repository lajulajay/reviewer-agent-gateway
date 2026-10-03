# Workspace knowledge and collaboration framework — proposal v4

Owner: Claude · Reviewer: Codex (primary), Gemini (backup) · Status: draft for
review round 4 · 2026-10-03 · Supersedes v3 (kept unchanged). Reviews r01–r03
(all REJECT, converging) and every disposition are in
`workstreams/2026-10-03-workspace-framework.md`. User decisions D1–D5 are
recorded there.

## 1. Constraint and scope

Sprawl is a central problem (user, 2026-10-03). Every mechanism must reduce or
bound text and must not add a file per event; where a single user can own a
policy, the policy replaces machinery. v4's scope is a **single-session pilot
in one clean, paused repository** (`kalshi-finance-agent`). Guarantees are
stated for that scope only; wider claims wait for pilot evidence.

## 2. Tiers and budgets (D2; R03-F7, F9)

| Tier | Files | Budget | Kind |
| :--- | :--- | :--- | :--- |
| T0 Working set ("RAM") | `STATUS.md` | ≤ 4,000 characters | **capped** |
| T1 Rules | `AGENTS.md`; `CLAUDE.md` stub (`@AGENTS.md` + Claude-only quirks) | `AGENTS.md` ≤ 12,000; stub ≤ 1,500 | **capped** |
| T1 Shared rules | gateway `PROTOCOL.md` | ≤ 12,000 | **capped** |
| T2 Knowledge | `docs/` and today's `CLAUDE.md` body | ≤ 60,000 per repo | **ratcheted** (§2.2) |
| T3 Records | active `workstreams/*.md`; `experiments/<id>/` | active workstream ≤ 30,000 | **capped** for active workstreams; experiments reported |
| T4 Cold storage | `.collab/`, packets, prompts, `workstreams/closed/`, legacy `COLLAB.md` | none | **reported** |
| A Agent cache | Claude auto-memory (Codex memories disabled) | index ≤ 2,000; entry ≤ 1,500; total ≤ 15,000 | **capped** |

1. **No downward eviction.** A tier over budget is brought back by shortening
   and deduplicating in the text's authoritative home. A rule is never moved
   out of T1 to save space, and an open obligation never leaves its active
   workstream record.
2. **Ratchet for existing overages.** `docs-check report` records a baseline
   per file at adoption. A file already over budget fails the check only if it
   grows beyond its baseline; compaction (§6) brings it down and lowers the
   baseline. New files must meet the budget from creation.
3. **Uncapped tiers are reported, not hidden.** `docs-check report` prints
   character totals for every tier, capped or not.

**`STATUS.md` (T0)** is a **branch-scoped snapshot**: it opens with its
revision and observation time, then fixed sections — active workstreams (one
line each: ID, owner, state, next action, link) · live-system observations
(time, how observed) · blockers waiting on the user · pending items (each at a
committed location). It never authorizes anything (§5); assignments and
obligations are authoritative only in workstream records (R03-F8).

## 3. Review obligations (D1; R03-F1, F3, F4, F5, F6)

1. **Labeled output, no sidecar.** Reviewers label findings `F<n>
   [blocker|major|minor]: …` and conditions `C<n>: …`, and end with
   `ATTESTATION: all actionable findings and conditions are labeled.` The
   wrapper fails closed when labels or attestation are missing. There is no
   sidecar file: `docs-check` parses labeled items from the committed raw
   artifact. Round 3 followed this format exactly.
2. **Round identity.** A review round's key is its artifact path in `.collab/`.
   `docs-check` considers only review artifacts (`.collab/<reviewer>-*.md` and
   `.json`), never prompts or packets.
3. **Disposition rows.** `docs-check dispositions <artifact>` prints one row
   per labeled item with its exact text for the owner to paste into the
   workstream's findings table. Prose verbatim transcription into `COLLAB.md`
   ends (D1).
4. **Valid final dispositions.**
   - Blocker or condition: `verified <round>` (a later review round confirms
     the resolution) or `user-decided <date> <finding ID>: <quote>` naming
     that finding.
   - Major or minor: either of the above, or `fixed <commit>` (in pushed
     history) or `rejected: <reason>`.
   - At transfer only: `open` with current state.
5. **Closure attestation by the owner.** Before `done`, the owner adds one log
   line per round: "raw review re-read; no unlabeled actionable item." The
   framework guarantees tracing of labeled items only.
6. **Legacy rounds.** Reviews captured before adoption (including r01–r03 of
   this workstream) are indexed and reconciled manually; no capture evidence
   is recreated.

## 4. Ownership and handoff (R03-F2, F10)

- **Pilot policy:** one session per workstream. The user assigns the owner by a
  committed, pushed `Owner:` line naming the revision, and stops any older
  session before reassigning. A session confirms the remote `Owner:` line
  before starting; if it names the other agent, it reviews or stops. No claim
  of general serialization is made.
- **`docs-check` modes** (one tool):
  - `record` — every review artifact is in a review index; every labeled item
    has a row; links resolve; budgets and ratchets hold; the standards
    revision recorded in each new review matches the branch pin (mismatch
    fails, R03-F11).
  - `transfer` — `record` passes; no uncommitted tracked changes; branch equals
    its pushed upstream; any pending content needed by the next owner is
    committed at a stated location (listing a local file is not enough);
    legacy reviews triaged; for operational workstreams, a runtime observation
    taken **immediately before** the handoff (time, commands, result).
  - `done` — `record` passes and every labeled item has a valid final
    disposition (§3.4) and the closure attestation (§3.5).
- **Handoff block** in the workstream file: current state · decisions (scope,
  supersession) · open obligations · runtime observation · restart sequence.
  The new owner re-verifies the runtime observation before acting.

## 5. Authority

| Claim | Source | Rule |
| :--- | :--- | :--- |
| Runtime fact | the live system, now | Re-verify before acting |
| User decision | dated quote in a workstream or experiment spec, with scope and supersession | Required for every stop-for-user action |
| Review obligation | raw artifact + disposition rows | `done` governs |
| Research claim | `experiments/<id>/` | Status changes need a dated results entry |
| Orientation | `STATUS.md`, `AGENTS.md`, indexes | Never authorizes |

## 6. Cleanup (D3, D4)

- **Continuous:** the check fails on cap breaches and ratchet growth.
- **At transfer and done:** prune `STATUS.md` to live items; at `done` add a
  ≤ 1,500-character outcome summary and move the file to
  `workstreams/closed/`.
- **Compaction pass:** monthly and on any breach (D3), as its own reviewed
  workstream. It shortens and deduplicates T1–T2 in their authoritative homes,
  moves `CLAUDE.md` bodies into `docs/`, reconciles experiment indexes with
  results, rewrites or deletes agent-memory entries that conflict with the
  repositories, lists stale branches and worktrees, and **prunes legacy
  `COLLAB.md` in place** (D4): verbatim review copies that duplicate a
  `.collab/` artifact become links; resolved threads become dated summaries;
  git history keeps the full text. The reviewer's question: "was anything lost
  or changed in meaning?"

## 7. Standards and shared resources (R03-F11)

- `AGENTS.md` pins `Standards: reviewer-agent-gateway@<commit>`. Each wrapper
  writes `Standards revision: <gateway HEAD>[ (dirty)]` into the artifact
  header it already produces; `record` fails when that differs from the branch
  pin for reviews captured after adoption.
- Shared-resource facts (Modal cron allocation, shared Supabase project and
  schemas, secret locations) live once in gateway `PROTOCOL.md` as the command
  that verifies them, never as a count.

## 8. Pilot plan

1. Gateway: wrapper changes (labels, attestation, standards revision);
   `docs-check` (`record`, `transfer`, `done`, `dispositions`, `report`) with
   provider-free tests; templates. This workstream reaches `done` first.
2. Before adoption: baseline `docs-check report` for `kalshi-finance-agent` and
   for Claude's agent memory; clear memory entries that conflict with the
   repositories (fixed-owner wording, renamed-file pointers, the July pivot
   snapshot) so the pilot session does not load them.
3. Adoption in `kalshi-finance-agent` (paused, clean): confirm a single
   session; preserve a working-tree inventory; verify what each agent loads
   before and after adding `@AGENTS.md`; add the standards pin, `STATUS.md`,
   and `workstreams/`; mark `COLLAB.md` legacy in place.
4. First compaction pass on the pilot after one workstream completes under the
   framework; it includes legacy `COLLAB.md` pruning and the memory budget.
5. Evaluate after 30 days: check failures, budget trends, time to resume after
   a transfer. Other repositories adopt only at their next transfer, never in a
   dirty working tree. `trading-strategies` git stays a separate decision (D5).

## 9. Remaining risks

- Unlabeled items rely on reviewer and owner attestations.
- The single-session rule is a user policy, not enforced.
- Runtime observations are attested by the owner.
- Tamper-evidence starts at first push; force-pushes defeat it.
- Character caps can be met by terse but less clear text; compaction review is
  the control for meaning.
