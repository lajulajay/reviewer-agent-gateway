# Copilot instructions

<!-- Copy to .github/copilot-instructions.md. Rules live in the repository's
     AGENTS.md and the gateway PROTOCOL.md; this file only points at them. -->

Read `AGENTS.md`, then the gateway `PROTOCOL.md` it pins
(`Standards: reviewer-agent-gateway@<commit>`). They govern every change.

- **Roles.** The coordinator follows `reviewers/copilot-coordinator.md`;
  each sub-agent follows `reviewers/copilot-subagent.md`.
- **Identity.** Copilot work is `--owner copilot --task <ID>` with one
  `--author-model <id>` per model that wrote code. Pin a concrete model per
  sub-agent; `auto` and Copilot Fusion may not author reviewed work.
- **Independence.** No reviewer whose model vendor matches the owner's or any
  author model's vendor, at any version. The wrappers enforce this.
- **Reviews.** Run reviewer wrappers only through `reviewers/` shims and
  only on a ticket from the coordinator (`reviewers/review-ticket.sh`).
- **Stop for the user.** Agents may commit and push their own task branch and
  open a **draft** PR. Ready-for-review, merge, deploy, risk-parameter or
  policy changes, budget overrides, and anything touching holdout or paid
  data are the user's.
