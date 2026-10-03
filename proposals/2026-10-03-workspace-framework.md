# Workspace knowledge and collaboration framework — proposal v1

Owner: Claude · Reviewer: Codex (primary), Gemini (backup) · Status: draft for
adversarial review · 2026-10-03

## 1. Problem

Codex and Claude now own work interchangeably (gateway `PROTOCOL.md`,
2026-10-02). The documentation and memory system was built for a fixed owner,
and a full scan of `~/Developer` (1,040 Markdown files, both agents' memory
stores) shows it no longer fits. Evidence (details in §10):

1. **Duplicated facts drift.** Role text lived in ~15 files across 5 repos;
   `reviewers/PROTOCOL.md` existed in 3 diverging variants. `AGENTS.md`
   sections "Owner autonomy", "What proceeds automatically", and the review
   protocol are byte-identical (or ≥92% similar) across four repos, while
   "What stops for the user" and "Reviewing well here" are <10% similar — the
   shared and repo-specific parts are cleanly separable but are mixed today.
   Cross-repo lessons are copied ("Critical lessons from
   kalshi-temperature-bot" in polymarket `CLAUDE.md`; "Gotchas inherited from
   econ-agent" in finance), and the Grafana skill exists as two diverged copies
   (177 vs 326 lines).
2. **Agent-named files hold agent-neutral knowledge.** `CLAUDE.md` (418–1,146
   lines) is declared authoritative for architecture, but Codex reads
   `AGENTS.md`. A Claude owner must be redirected to `AGENTS.md`; a Codex owner
   to `CLAUDE.md`.
3. **State, record, and knowledge are mixed.** `CLAUDE.md` opens with dated
   handoffs ("Current H2 handoff (October 2, 2026)"); `COLLAB.md` files
   (3,594–6,142 lines, 0.26–0.55 MB) mix live status, briefs, verbatim reviews,
   and archives, each repo with a different structure (Part 1/2, numbered
   sections, flat append). Their "status" sections go stale (finance's opening
   status is dated 2026-07-26; latest work 2026-09-06). Verbatim transcription
   injects 38–56 H1 headings per file.
4. **Uncommitted documentation is invisible state.** At scan time econ had
   3,381 uncommitted `COLLAB.md` lines; the temperature bot had uncommitted
   notes from 2026-09-16; a prior session left stale uncommitted Gemini edits in
   three repos. `COLLAB.md` files have only 10–14 commits each.
5. **Agent memory is private, stale, and contradicts the repos.** Claude's
   memory still says "Codex is OWNER" (econ), points at renamed files
   (`CODEX_CLAUDE_COLLAB.md`), and keeps a July pivot snapshot whose decision
   date (Aug 1) has long passed; two entries were "restored after a
   concurrent-session wipe". Codex's memory is frozen at 2026-07-21 (its
   `memories` feature is now off) and instructs keeping the collaboration doc
   *untracked* — reversed on 2026-07-28. Neither agent can see the other's
   memory, so an ownership switch loses knowledge.
6. **No workspace layer exists.** `~/.claude/CLAUDE.md` is absent and
   `~/.codex/AGENTS.md` is empty, so every cross-repo rule is copied per repo.
7. **Review conditions are untracked.** 289 of ~420 review artifacts end
   `ACCEPT WITH CONDITIONS`; conditions are dispositioned in prose, if at all.
   Only 2 artifacts carry an `Owner:` line.
8. **Registries go stale.** The experiment registry is the best convention in
   the workspace (same lifecycle in three repos), but econ's `INDEX.md` still
   lists H1 as `proposed` while H1/H2 are in live cutover.

## 2. Goals and non-goals

Goals: any owner (Codex or Claude) can pick up any workstream from the
repository alone; each fact has one home; current state is small and fresh;
records stay immutable and auditable; drift is caught by a machine check.

Non-goals: rewriting history; changing reviewer isolation or wrapper
security; changing any trading, risk, or experiment decision; a big-bang
migration of active repos.

## 3. Principles

- **P1 One home per fact.** Choose the home by scope (workspace / platform /
  repo / workstream) and by volatility (state / record / knowledge). Elsewhere,
  link — never restate.
- **P2 Agent-neutral by default.** Agent-named files contain only genuinely
  agent-specific behavior.
- **P3 State ≠ record ≠ knowledge.** State is small and overwritten; records
  are append-only and immutable; knowledge is curated and edited in place.
- **P4 The repository is the memory.** Anything an owner needs is in git.
  Agent-private memory holds only working-style preferences, tool quirks, and
  pointers — never project state.
- **P5 Committed or declared.** At session end documentation is committed, or
  listed as pending in `STATUS.md`. Nothing is silently uncommitted.
- **P6 Freshness is checked, not hoped for.** Dates, owners, sizes, generated
  indexes, and forbidden phrases are verified by a script.
- **P7 Corrections are successors.** Frozen artifacts are never edited; a
  successor supersedes them and both remain.

## 4. Layers

| Layer | Scope | Home | Contents |
| :--- | :--- | :--- | :--- |
| L0 Workspace standards | all repos, all agents | gateway repo `standards/` | `PROTOCOL.md` (roles, review), `DOCS.md` (this framework's rules), `RESEARCH.md` (experiment lifecycle, evidence grades, gate rules), `SESSION.md` (start/end/handoff), templates |
| L0 entry points | per agent, user level | `~/.codex/AGENTS.md`, `~/.claude/CLAUDE.md` | generated stub: "In `~/Developer`, follow `<gateway>/standards/`"; nothing else |
| L1 Platform knowledge | a repo family | gateway `knowledge/prediction-markets.md` | shared Modal/Supabase/PostgREST facts, cron budget, secret stores, cross-venue lessons, fee economics (today in Claude memory and copied `CLAUDE.md` sections) |
| L2 Repo entry | one repo | `AGENTS.md` (≤150 lines) | purpose, read-first map, repo-specific stop-for-user list, repo-specific review and evidence rules, commands |
| L2 Agent stub | one repo | `CLAUDE.md` | `@AGENTS.md` import plus Claude-only quirks (target: <20 lines) |
| L2 Current state | one repo | `STATUS.md` (≤120 lines, overwritten) | as-of timestamp; workstream table; live-system state; pending uncommitted work; next safe actions |
| L2 Knowledge | one repo | `docs/ARCHITECTURE.md`, `docs/OPERATIONS.md`, `docs/LESSONS.md` | today's `CLAUDE.md` bodies, split by kind |
| L2 Research | one repo | `experiments/<id>/` (existing) | `SPEC`, `DATA_CONTRACT`, `RESULTS`, `manifest.json`; `INDEX.md` generated from manifests |
| L3 Workstream record | one unit of owned work | `workstreams/<YYYY-MM-DD>-<slug>.md` | `Owner:` history, briefs, review index, finding/condition dispositions, handoff blocks |
| L4 Raw artifacts | one review | `.collab/` (existing) | immutable reviewer output + `.sha256`; name `<reviewer>-<date>-<workstream>-r<NN>.<ext>` |
| Archive | frozen | `archive/COLLAB-<repo>-to-2026-10.md` | today's `COLLAB.md`, `REVIEW_FINDINGS_*`, frozen with a recorded hash |

Source precedence when documents disagree (generalized from the temperature
bot's rule): code, migrations, and verified production data → `STATUS.md` →
`experiments/` and `docs/` → workstream records → archive.

## 5. Workstreams

- A **workstream** is the unit of ownership: one goal, one owner at a time, one
  file. An experiment is the unit of research claim; a workstream may implement
  or operate an experiment and links to it.
- File header: `Workstream:`, `Owner:` (dated lines; history kept), `Status:`
  (`active`, `blocked`, `handed-off`, `done`), `Branch:`, `Links:`.
- Body sections: Brief · Decisions (user) · Reviews (index: artifact path,
  reviewer, tier, verdict) · Findings and conditions (table) · Handoffs · Log.
- **Findings and conditions table**: one row per reviewer finding or
  acceptance condition with a stable ID (`<workstream>-R<round>-F<n>`),
  severity, owner disposition (`fixed <commit>`, `rejected: <reason>`,
  `deferred: <where>`, `user-waived <date>`), and status. A workstream cannot
  be `done` with an open blocking row.
- **Proposed change to verbatim transcription (decision D1):** replace the
  verbatim copy into `COLLAB.md` with (a) the immutable, checksummed raw
  artifact, (b) a link and checksum in the review index, and (c) the
  per-finding table. Softening remains detectable because every row cites a
  finding ID in an immutable artifact, and `docs-check` verifies that each
  linked artifact's checksum matches its sidecar. This removes ~100% duplicated
  text and the heading-hierarchy breakage. If D1 is rejected, verbatim copies
  go into the workstream file under a fenced block, not as live headings.

## 6. Session protocol (both agents)

Start: read `AGENTS.md` → `STATUS.md` → the workstream file → `git status` and
branch. Confirm the session's role from the workstream `Owner:` line; if the
other agent owns it, act only as reviewer or ask the user. If an untracked
`.agent-session` lock (agent, PID, start time, workstream) names another live
session on the same working tree, do not edit; use a separate worktree or ask.

During: docs change in the same commit as the code they describe. Process and
standards files change only on `main` in dedicated commits; feature branches
change only their workstream file, `experiments/`, and their own `STATUS.md`
row.

End or handoff: update the `STATUS.md` row; append a handoff block (template
from the existing H5/H2 handoffs: Current state · Completed · Frozen decisions
· Remaining · Working tree · Restart sequence); commit documentation or list it
under "Pending uncommitted" in `STATUS.md`; remove the lock. An ownership
change is a new dated `Owner:` line written by the user's instruction.

## 7. Agent memory policy

- Allowed in agent memory: user working-style preferences and corrections;
  agent/tool-specific quirks (e.g. Claude auto-mode blocks, Codex config
  traps); pointers to repo files.
- Not allowed: project status, decisions, hypotheses, metrics, bug history,
  architecture — these move to L1/L2 and the memory entry is reduced to a
  pointer.
- Both agents' memories get a header pointing to `standards/` and a rule:
  "if memory conflicts with the repository, the repository wins; fix or delete
  the memory entry."
- Migration: Claude's `prediction-markets-ops` → `knowledge/prediction-markets.md`;
  `project-*` and the July pivot snapshot → repo `docs/`/`STATUS.md` (most
  content already exists there) then pointer-only; Codex's frozen store is
  marked superseded (decision D4).

## 8. Enforcement: `docs-check`

A gateway script (`docs-check.sh <repo>`), with provider-free tests, run by the
owner at session end, optionally as a pre-commit hook (decision D5), and by a
weekly read-only routine. It fails on:

- fixed-role phrases (`Codex is OWNER`, `Claude is PRIMARY`, …) outside
  `archive/` and `.collab/`;
- `AGENTS.md` over 150 lines, `CLAUDE.md` not an import stub, `STATUS.md` over
  120 lines or with an as-of date older than 7 days while any workstream is
  `active`;
- an `active` workstream without a valid `Owner:` or with an owner equal to a
  reviewer in its review index;
- `INDEX.md` not matching `experiments/*/manifest.json`;
- a `.collab/` artifact without a matching `.sha256`, or a checksum mismatch;
- a change to a frozen archive (hash recorded in `archive/MANIFEST`);
- missing reviewer shims; broken relative links in L0–L2 files.

Generated files (`INDEX.md`, L0 entry stubs) carry a "generated — do not edit"
header and are rebuilt by the same tool.

## 9. Migration

1. Gateway: `standards/` (move `PROTOCOL.md`; add `DOCS.md`, `RESEARCH.md`,
   `SESSION.md`, templates), `knowledge/prediction-markets.md`, `docs-check`
   with tests, L0 stub generator. Self-apply: the gateway gets its own
   `STATUS.md` and `workstreams/` (this proposal is its first workstream).
2. Pilot `kalshi-finance-agent` (paused, clean): freeze `COLLAB.md` to
   `archive/`, create `STATUS.md`, `workstreams/`, split `CLAUDE.md` into
   `docs/`, shrink `CLAUDE.md` to an import stub, run `docs-check`, review.
3. `trading-strategies` (no git — decision D6: initialize git first), then
   polymarket, the temperature bot, and econ last, each when no session is
   active and after its pending documentation is committed by its owner.
4. Agent memory migration (§7) after L1 exists.
5. Measure after 30 days: `STATUS.md` freshness, docs-check failures, time to
   resume after a handoff, uncommitted-doc incidents.

## 10. Evidence summary

- Markdown inventory: 1,040 files. Excluding `.worktrees/` copies (100
  files): `.collab/` 386 (4.3 MB), packets 167, prompts 263, documentation
  ~120.
- Review artifacts: ~420; verdicts ACCEPT WITH CONDITIONS 289, REJECT 32,
  ACCEPT 15, none 82; 2 contain `Owner:`.
- `COLLAB.md`: econ 5,432 lines / 56 H1 / 10 commits; finance 6,142 / 2 / 11;
  temperature 3,936 / 41 / 14; polymarket 4,979 / 38 / 11; trading-strategies
  3,594 / 1 / untracked (no git).
- `CLAUDE.md`: econ 418, finance 464, temperature 708, polymarket 1,146,
  migration 291 lines.
- `AGENTS.md` cross-repo section similarity (vs econ): review protocol and
  owner autonomy 1.00 (temperature, polymarket); what-proceeds 0.92; what-stops
  0.04–0.07; reviewing-well-here 0.01–0.07.
- Memory: Claude 8 entries (~77 KB), several stale or contradicting repos;
  Codex memory frozen 2026-07-21, feature disabled, contradicts current
  tracking decision.

## 11. Decisions for the user

- **D1** Replace verbatim transcription with checksummed link + finding table?
- **D2** Rename `reviewer-agent-gateway` (it now holds standards and platform
  knowledge)? Renaming breaks every shim path; default: keep the name.
- **D3** Freeze existing `COLLAB.md` files into `archive/` (default) or keep
  appending under the new structure?
- **D4** Reduce agent memories to pointers and mark Codex's frozen store
  superseded?
- **D5** `docs-check` as a blocking pre-commit hook or advisory?
- **D6** Put `trading-strategies` under git?

## 12. Risks and open questions

- Size limits on instruction files (Codex's project-doc byte cap) — keep
  `AGENTS.md` small; verify the cap.
- User-level stubs may reach reviewer sessions; the wrappers already isolate
  Claude (`--safe-mode`) and Codex (`--ignore-user-config`); verify neither
  loads the L0 stub during reviews.
- `.agent-session` locks are advisory; a crashed session leaves a stale lock
  (include PID and start time; `docs-check` reports locks whose PID is dead).
- Per-workstream files reduce but do not remove merge conflicts on
  `STATUS.md`; keep rows one line each.
- Migration of the econ repo competes with live cutover work; it goes last.
