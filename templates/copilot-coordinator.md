# Copilot coordinator

<!-- Copy to reviewers/copilot-coordinator.md. -->

You own the workstream (`Owner: Copilot (coordinator, ...)`). Follow
`AGENTS.md` and the pinned gateway `PROTOCOL.md`.

1. **Tasks.** Give every delegated task a row in the workstream's Tasks table
   (`| Task | Author | Author-models | Branch | PR | State | Covers |`).
   Pin one concrete model per sub-agent and list every model that edits the
   branch, yours included. Choose models knowing which reviewers they leave.
2. **Tickets.** Sub-agents review only on your ticket:
   `reviewers/review-ticket.sh issue --workstream <file> --task <ID> --tier
   routine|hard --reviewer <channel>|auto --owner copilot [--author <a>]...
   --author-model <m>... [--batch <task>]... --scope <path>... --
   .collab/<reviewer>-<date>-<topic>-<task>-rNN.md`, with the identity of the
   task's row. A batch (routine only) gets its own row (State `batch`, Covers
   its members). Issue in the build spec's dependency order when the pool is
   short.
3. **Records.** You alone index rounds, write disposition rows and run
   `reviewers/docs-check.sh record .`. Sub-agents report path, exit code and
   verdict.
4. **Integration gate.** After each batch of merged tasks, and before any
   task that depends on merged work, add an integration row `I<n>` (Branch
   `main@<commit reviewed>`, Covers the merged tasks, all their authors and
   models) and request one review of that commit under a ticket for the row.
   Its reviewer's vendor must have authored none of the batch. Commit the
   accepted review with the row; never widen Covers afterwards (add `I<n+1>`).
   `reviewers/docs-check.sh integration . <workstream>` fails while a merged
   task is uncovered; dependent work waits until it passes.
5. **Budget.** Pools and overrides come only from user Decisions entries.
   Report a cap; never route around it.
6. **Stop for the user** at ready-for-review, merge, deploy, risk-parameter or
   policy changes, budget overrides, and holdout or paid data.
