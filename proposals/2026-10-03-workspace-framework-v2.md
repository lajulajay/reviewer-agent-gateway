# Workspace knowledge and collaboration framework — proposal v2

Owner: Claude · Reviewer: Codex (primary), Gemini (backup) · Status: draft for
review round 2 · 2026-10-03 · Supersedes v1
(`2026-10-03-workspace-framework.md`, kept unchanged). Round-1 review:
`.collab/codex-2026-10-03-workspace-framework-r01.md` (REJECT); dispositions in
`workstreams/2026-10-03-workspace-framework.md`.

## 1. What changed from v1

v1 restructured files. Round 1 showed that the failures in the evidence are
workflow failures: work changes hands without a verified handoff, review
conditions are not traced to dispositions, and uncommitted text is treated as
state. v2 is built around three mechanisms — **a verified handoff event**,
**machine-traced review obligations**, and **explicit authority rules** — plus
a small entry-point change. Everything else from v1 is deferred behind a
named trigger (§8). v1's evidence summary (§10 of v1) still applies, with one
correction: Codex's `memories` feature is disabled, so its stale memory store
is inert rather than an active contradiction.

## 2. Core mechanism A — review obligations are traced by machine (R01-F1, F6, F8)

1. **Labeled output.** Each wrapper's output contract requires every finding as
   a line `F<n> [blocker|major|minor]: <text>` and every acceptance condition as
   `C<n>: <text>`. Validation fails closed when `ACCEPT WITH CONDITIONS` has no
   `C` line or `REJECT` has no `F` line, exactly as it does today for the
   verdict line.
2. **Wrapper-written sidecar.** At capture, before the owner touches anything,
   the wrapper writes `<artifact>.findings.json` (IDs, severities, exact text,
   verdict, owner, reviewer, model, artifact digest) and checksums it with the
   artifact. The owner commits and pushes artifact and sidecar in the same
   commit as the workstream update that records the round.
3. **Generated disposition skeleton.** `review-dispositions <artifact>` prints
   one table row per finding with its ID, severity, and **exact text**; the
   owner fills only the disposition and status columns.
4. **Closure check.** For a workstream, every finding and condition ID in every
   linked sidecar must appear in its table with unchanged text and a
   disposition of the form `fixed <commit>`, `rejected: <reason>`,
   `deferred: <location>`, or `user-decided <date>: <quote>`. Blockers and
   conditions cannot be closed by `deferred`. A workstream cannot record a
   handoff or `done` while this check fails.
5. **What this guarantees and what it does not.** Omission and rewording are
   detected mechanically. A wholesale replacement of artifact plus sidecar is
   detectable only through git history of pushed commits; the framework claims
   tamper-evidence via pushed history, not immutability.
6. **Ownership per round.** Each review-index row records the owner at that
   round; the check rejects a round where the reviewer equals that round's
   owner, rather than comparing against the current owner.
7. **Legacy triage.** Existing reviews are not migrated. When an active
   workstream reaches its first handoff under this framework, its owner lists
   the open obligations from its legacy reviews in the new table (quoted
   exactly, linked to the raw artifact). Closed historical work is untouched.

This replaces prose verbatim transcription (decision D1). The raw review stays
committed and linked; the sidecar and generated table carry the exact text
into the record without duplicating whole reviews or breaking heading
structure.

## 3. Core mechanism B — the handoff event (R01-F2, F3, F4, F11)

A workstream changes owner only through a handoff event. `handoff-check <repo>
<workstream>` passes only when:

1. the working tree has no uncommitted tracked changes and the branch equals
   its pushed upstream (work in progress is committed on the workstream branch
   and pushed — a declaration of pending work never completes a handoff);
2. the closure check (§2.4) passes for blockers and conditions, or each open
   item is listed in the handoff block with its current state;
3. the workstream file has a dated handoff block — Current state · Completed ·
   Decisions (with user quotes) · Open obligations · Runtime check (commands
   run, time, observed result) · Restart sequence — modeled on the existing
   H5/H2 handoff documents.

Only after the check passes does the new `Owner:` line get written, on the
user's instruction, naming the repository revision it was assigned against.

**Concurrency.** One owner per workstream at a time, enforced by the handoff
event rather than a lock. Concurrent sessions on different workstreams use
separate worktrees. An untracked `.agent-session` file is a same-worktree
warning only (it cannot see other worktrees or hosts). There is no
hand-edited shared status row: each workstream's state lives in its own file
header, so concurrent workstreams edit different files.

## 4. Core mechanism C — authority by claim type (R01-F5)

| Claim | Authoritative source | Rule |
| :--- | :--- | :--- |
| Runtime fact (what is deployed, scheduled, open) | live system, checked now | Re-verify before any operational action; documents only say where and how to check |
| User decision or authorization | dated quote in a workstream `Decisions` section or an experiment spec | Required for every stop-for-user action; summaries cannot authorize |
| Review obligation | sidecar + disposition table (§2) | Closure check governs |
| Research claim | `experiments/<id>/` frozen spec and append-only results | Status changes require a dated results entry |
| Summary / orientation | `AGENTS.md`, indexes, handoff "Current state" | Never authoritative; may be stale |

## 5. Entry points (R01-F10, minimal)

- `AGENTS.md` stays the repository's agent-neutral entry point (already
  owner-neutral since 2026-10-02) and gains one line pinning the standards it
  follows: `Standards: reviewer-agent-gateway@<commit>`. A check warns when
  the gateway's standards files changed after the pin; a branch adopts a
  change by updating the pin in a commit after reading the diff (R01-F2, F7).
- `CLAUDE.md` gains `@AGENTS.md` as its first line at adoption; its body is
  not split or moved now.
- `COLLAB.md` stays in place. At adoption it gains a header line: new
  workstreams go in `workstreams/`; this file is the legacy record.
- New work uses `workstreams/<YYYY-MM-DD>-<slug>.md` (header: Workstream,
  Owner history, Status, Branch, Links; sections: Brief, Decisions, Reviews,
  Findings and conditions, Handoffs, Log).

## 6. Shared resources and memory (R01-F7)

- Volatile, repo-owned facts stay in the owning repo.
- Only resources that are physically shared get one home in the gateway,
  `knowledge/shared-resources.md`: the Modal cron allocation (5 of 5 slots
  across four repos), the shared Supabase project and schemas, and where each
  repo's secrets live. Repos link to it.
- Agent memory holds working-style preferences, agent-specific tool quirks, and
  pointers. Project state belongs in the repository; when memory and the
  repository disagree, the repository wins and the memory entry is fixed.
  Claude's contradictory entries (fixed-owner wording, renamed-file pointers,
  the July pivot snapshot) are corrected now; Codex's disabled store is left
  alone.

## 7. Rollout (R01-F3, F9)

1. Gateway: labeled-output contract and sidecar in all wrappers;
   `review-dispositions`; closure check; `handoff-check`; workstream and
   handoff templates; `knowledge/shared-resources.md`; provider-free tests.
   This workstream is the first user.
2. No repository is migrated in bulk. Each repository adopts §5 at its next
   handoff event, from a clean pushed revision, by its owner — no edits to a
   dirty working tree and no change to what a running session loads.
3. `kalshi-finance-agent` is the pilot (paused, clean, no active session).
4. Before any user-level entry stub is added, verify that reviewer wrappers do
   not load it.
5. `trading-strategies` git initialization is a separate decision after an
   audit of its contents and ignore rules; it is not part of this rollout.

## 8. Deferred, with triggers

| Deferred item | Adopt when |
| :--- | :--- |
| Generated `STATUS.md` (from workstream headers and manifests) | a repo has more than three active workstreams, or an owner misses state that a summary would have shown |
| Splitting `CLAUDE.md` into `docs/` | an instruction file nears Codex's project-doc size cap, or a fact is found duplicated and drifted |
| Wider platform knowledge layer | a cross-repo fact drifts between two repos twice |
| User-level entry stubs | loader behavior verified and a cross-repo rule drifts again |
| Blocking pre-commit hook | advisory checks are ignored in practice |
| Archiving legacy `COLLAB.md` | a legacy file blocks tooling or exceeds a size that tools truncate |

## 9. Decisions for the user

- **D1** Replace prose verbatim transcription with committed raw artifacts plus
  wrapper-generated exact-text finding tables (§2)?
- **D2** Keep the gateway name (default yes).
- **D3** Leave legacy `COLLAB.md` files in place (default yes).
- **D4** Correct Claude's contradictory memory entries now (default yes).
- **D5** Closure and handoff checks required; other checks advisory (default).
- **D6** `trading-strategies` git: separate audited decision (default).

## 10. Risks that remain

- Reviewers may not follow the labeled format; the wrapper then fails closed
  and the review must be re-run, costing quota. Mitigation: the format is a
  small extension of the existing verdict contract; measure the failure rate.
- The runtime-check field in a handoff is attested by the owner, not verified
  by machine.
- Pushed history is tamper-evident only if the remote is not force-pushed;
  branch protection is not configured on these repositories.
