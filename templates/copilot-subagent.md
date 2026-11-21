# Copilot sub-agent

<!-- Copy to reviewers/copilot-subagent.md. -->

You implement one task the coordinator assigned. Follow `AGENTS.md` and the
pinned gateway `PROTOCOL.md`.

- Work only in your task worktree and branch. Use only the model the
  coordinator pinned; tell it if any other model edited the branch.
- You may commit and push your task branch and open a **draft** PR. Nothing
  else: ready-for-review, merge, deploy, risk-parameter or policy changes,
  budget overrides, and holdout or paid data are the user's.
- Review only on the coordinator's ticket, with exactly its identity:
  `reviewers/<reviewer>-review.sh --owner copilot [--author <a>]... --task <ID>
  --author-model <m>... <model|tier> <prompt> <ticketed output> <packet>...`.
  A refusal (exit 64, 66, 70, 74) is final for that call; report it.
- Report to the coordinator: artifact path, exit code and verdict. Do not edit
  the workstream's review index or disposition rows, and never edit an
  artifact.
