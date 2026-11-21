# Copilot integration gate, roles and task records (Phase 3)

Workstream: 2026-11-21-copilot-phase3
Owner: Claude (2026-11-21, assigned by the user in this session)
Status: done (2026-11-21)
Branch: copilot-phase3 (merged to main)
Operational: no
Links: [Phase 2b](2026-11-21-copilot-phase2b.md), [proposal](../../proposals/2026-11-20-copilot-owner.md), [README tickets](../../README.md), [protocol](../../PROTOCOL.md)

## Brief

Proposal Phase 3, gateway side:

- **Task table (D2, D10).** `templates/workstream.md` gains a `## Tasks`
  table (`Task | Author | Author-models | Branch | PR | State | Covers`). The
  row is the task's structured entry; the proposal's separate `Task: ... |`
  line would duplicate it. `docs-check.py record` checks rows (registry
  authors, models that resolve to a vendor, known state) and, for
  post-adoption artifacts of Copilot work, that the recorded owner is named in
  the Owner lines and that a Copilot artifact's `Task` has a row with equal
  author models.
- **Legacy owner map (D10).** One user Decisions entry per repository,
  `Legacy owner map: codex -> copilot`, makes `--owner codex` artifacts in a
  Copilot-owned workstream, first committed on or before its date, count as
  Copilot's. Artifacts are never edited.
- **Integration gate (D7).** An integration row (Branch `main`, `Covers` the
  merged tasks, carrying their authors and models) is reviewed under a ticket
  with `--task <row>`, so the vendor rule excludes every batch vendor. New
  `docs-check.py integration REPO WORKSTREAM` fails while a merged task lacks
  an accepted integration review; `done` includes it.
- **Boundary and roles (D8, D9).** `templates/copilot-instructions.md`,
  `copilot-coordinator.md` and `copilot-subagent.md`: pointers to
  `PROTOCOL.md` plus D2–D8. D8 is an instruction, not mechanically enforced:
  the gateway cannot see PR state.
- **Fix to Phase 2b text.** README said batch findings are labelled `T3-F1`;
  the contract and validator accept only `F<n>`. Now the finding text starts
  with its task; a batch has its own row (State `batch`).

Consumer repositories (after merge, with approval): `reviewers/review-ticket.sh`
and `reviewers/docs-check.sh` shims, role files, `Standards:` pin bump,
`AGENTS.md` "Current exception" paragraphs replaced by a pointer;
trading-strategies also needs the legacy owner map entry and a Tasks row for
T5 (r10 is `--owner copilot --task T5`), without which `record` gains 11
errors (measured against every adopted repository; the others are unchanged).

## Decisions

- 2026-11-21, user, scope: implement proposal Phase 3.
  Quote: "proceed with phase 3". Supersedes: none.

## Reviews

| Round | Reviewer | Tier | Artifact | Verdict |
| :--- | :--- | :--- | :--- | :--- |
| r01 | Copilot (gpt-6.1-terra, OpenAI) | hard | `.collab/copilot-2026-11-21-copilot-phase3.md` | REJECT |
| r02 | Copilot (gpt-6-luna, OpenAI) | routine | `.collab/copilot-2026-11-21-copilot-phase3-r02.md` | ACCEPT |

## Findings and conditions

| ID | Severity | Disposition | Status |
| :--- | :--- | :--- | :--- |
| R01-F1 | major | fixed f2bcd9e | closed |
| R01-F2 | major | fixed f2bcd9e | closed |
| R01-F3 | major | fixed f2bcd9e | closed |
| R01-F4 | major | fixed f2bcd9e | closed |
| R01-F5 | major | fixed f2bcd9e | closed |
| R01-F6 | major | rejected: owner record only; mapped artifacts predate --author-model so their authoring models are unknown and cannot be supplied by a map; independence stays as recorded then (README) | closed |
| R01-F7 | major | fixed f2bcd9e | closed |
| R01-F8 | minor | fixed f2bcd9e | closed |
| R01-F9 | minor | fixed f2bcd9e | closed |
| R01-F10 | minor | fixed f2bcd9e | closed |

## Log

- 2026-11-21: worktree `copilot-phase3` from ec85df1; implementation, 152
  unit tests pass; PROTOCOL 11,997 / 12,000.
- 2026-11-21: r01 Copilot hard REJECT, ten findings. Fixed F1–F5, F7–F10:
  `integration` runs `record`; integration rows are `I<n>` with
  `main@<commit>`, count only when the accepted review is committed with an
  unchanged row; batch rows cover members without merge; any artifact naming
  a task must match its row; Branch/PR by state; `--follow` for first-add
  dates; templates carry `--author`/`--batch`. F6 rejected (README note).
- 2026-11-21: r02 Copilot routine ACCEPT; all nine fixed findings resolved.
- 2026-11-21: merged as f2bcd9e and pushed. r02's resolution lines continue
  with evidence on the same line, so rows close as `fixed f2bcd9e`.
- r01: raw review compared with its rows; no unlabeled actionable item
- r02: raw review compared with its rows; no unlabeled actionable item
- 2026-11-21: consumer migration prepared: trading-strategies (legacy owner
  map in the T5 workstream, T5 task row, shims, role files, pin, AGENTS.md
  pointer, two link fixes) and market-data-platform main (T11 task row,
  Copilot reviewer shim, shims, role files, pin, AGENTS.md pointer). Both pass
  `record`; T5 and T11 await integration reviews (D7).
