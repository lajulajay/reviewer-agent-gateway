# Proposal: GitHub Copilot as owner and reviewer channel (2026-11-20)

Status: approved by the sponsor 2026-11-20, subject to the revisions in
"Sponsor answers" (now incorporated). Owner of the implementation workstream:
Claude. Reviews: any reviewer whose model vendor is not Anthropic (D3); until
Phase 2 lands, that means Gemini via `gemini-review.sh`.

## Problem

- `--owner` accepts only `codex|claude` (`auto-review.sh`, the four provider
  wrappers, `OWNERS` in `reviewer-select.py`). Copilot work is reviewed as
  `claude-review.sh --owner codex` (trading-strategies `AGENTS.md`), so every
  such artifact records the wrong owner; the true author survives only in
  prose.
- `reviewer-roster.json` still lists Kimi and Codex as active.
- Copilot's coordinator fans tasks out to parallel sub-agents, each in its own
  worktree (`~/Developer/copilot-worktrees/<repo>/<branch>`), and the
  sub-agents call the reviewer wrappers themselves. The daily cap
  (8 / provider / repo) and per-topic budget assume one owner working
  serially; T3 was refused on the cap and an unlimited-Gemini override was
  needed.
- Cross-task defects surface only after merge (post-merge check of
  T2/T3/T6/T7 found nine).
- Independence is enforced per *agent*, but Copilot is a channel to many
  vendors' models. A Claude review of work written by a Claude model through
  Copilot is self-review in substance; so is a Gemini review of work written
  by Gemini 4 Hydrogen through Copilot.

## Sponsor answers (2026-11-20)

1. Copilot running the wrappers: approved. Capability confirmed: Copilot
   sub-agents already invoke `claude-review.sh` and `gemini-review.sh`.
2. Copilot Pro model list (CLI `/model`, 2026-11-20), by vendor:
   - Microsoft: MAI Code 2 Flash, MAI Code 2, MAI-Code-1.1-Flash
   - OpenAI: GPT-5.6 Luna (default), GPT-6 Luna, GPT-6.1 Terra, GPT-5.3-Codex
   - Anthropic: Claude Sonnet 5.5, Sonnet 5, Haiku 5.5, Haiku 4.5
   - Google: Gemini 4 Hydrogen, Gemini 3.8 Flash
   - xAI: Grok 4.7, Grok 4.6
   - Moonshot: Kimi K3
   - Router: "Copilot Fusion" (picks a model per request)
   - Unavailable on this plan: gpt-6.1-sol, gpt-6-sol, gpt-6-astra,
     gpt-5.6-sol, gpt-5.6-terra, claude-fable-5.1, claude-fable-5,
     claude-opus-5.5, claude-opus-5
3. Copilot as a reviewer: not opposed, but eligibility must follow the
   underlying model used, not the Copilot label.
4. The earlier "Gemini reviews Copilot work" default assumed Copilot had no
   Gemini models; the list above disproves that. Disregard it. The gateway
   must stop a vendor reviewing its own work across model versions
   (e.g. Gemini 3.8 Flash must not review Gemini 4 Hydrogen's code).

## Design

### D1. Channels, vendors and one registry

Two separate ideas, which the current code conflates:

- **Channel**: the subscription and CLI that runs an agent (`claude`,
  `codex`, `kimi`, `gemini` via `agy`, `copilot`). Owners, budgets and daily
  caps are per channel.
- **Vendor**: the company whose model wrote or reviewed the work
  (`anthropic`, `openai`, `google`, `microsoft`, `xai`, `moonshot`).
  Independence is per vendor, across all versions and sizes.

`agents.json` replaces `reviewer-roster.json`:

```json
{
  "channels": {
    "claude":  {"vendors": ["anthropic"], "can_own": true,  "can_review": true,  "active": true},
    "copilot": {"vendors": "by-model",    "can_own": true,  "can_review": true,  "active": true},
    "gemini":  {"vendors": ["google"],    "can_own": false, "can_review": true,  "fallback_only": true},
    "codex":   {"vendors": ["openai"],    "can_own": true,  "can_review": true,  "active": false},
    "kimi":    {"vendors": ["moonshot"],  "can_own": false, "can_review": true,  "active": false}
  },
  "vendor_prefixes": {
    "anthropic": ["claude-"], "openai": ["gpt-", "o1", "o3", "o4", "codex-"],
    "google": ["gemini-"], "microsoft": ["mai-"], "xai": ["grok-"],
    "moonshot": ["kimi-"]
  },
  "unresolvable_models": ["auto", "copilot-fusion"]
}
```

A model ID whose prefix matches no vendor, or that is a router, fails closed
(exit 64). Wrappers, `reviewer-select.py` and `docs-check.py` read everything
from this file; adding a channel or vendor is data, not code.

### D2. Owner, task and author identity

- Workstream header: `Owner: Copilot (coordinator, assigned by the user ...)`.
- Each delegated task gets a structured entry and a task-table row
  (template update):

  ```
  Task: T7 | Author: copilot | Author-models: gpt-6.1-terra | Branch: lajulajay-... | PR: <url>
  ```

  `Author-models` lists every model that wrote code in the task, including
  the coordinator's model if it edited the branch.
- Wrappers take `--owner copilot`, `--task T7` (part of the topic:
  `<workstream>-t7`) and one `--author-model <id>` per authoring model, and
  record them in the artifact metadata.
- Owners other than Copilot have a fixed vendor (Claude → anthropic), so
  `--author-model` is optional for them; it is required whenever `copilot` is
  the owner or an author.
- Copilot Fusion / `auto` may not author reviewed work: the coordinator pins a
  model per sub-agent. Model provenance is the coordinator's record of the
  model it assigned; the reviewer cannot verify it.

### D3. Vendor-independent review (sponsor rule)

- A review is eligible only if the reviewer model's vendor is not the vendor
  of the owner or of any author model. Versions do not matter: Gemini 3.8
  Flash cannot review Gemini 4 Hydrogen; Claude (any) cannot review Claude
  Sonnet 5 via Copilot; Codex cannot review GPT-6 Luna.
- Enforced in two places: automatic selection drops ineligible candidates,
  and every wrapper (including `gemini-review.sh`) refuses an ineligible call
  with exit 64 before any model call.
- Same channel, different vendor is allowed (a Copilot sub-agent on GPT may be
  reviewed by Copilot on Gemini) but ranked after a different channel when
  both are eligible, to avoid shared harness instructions.
- The coordinator chooses author models knowing what reviewers that leaves:
  e.g. an Anthropic author still has Gemini, GPT, MAI, Grok and Kimi as
  reviewers via Copilot, so no single default is imposed.

### D4. Copilot as a reviewer channel

- New `copilot-review.sh --owner <o> [--author-model <m>]... --model <id>
  <routine|hard> <prompt> <out.md> <packet>...` running
  `copilot -p ... --model <id> --available-tools ''` (no tools; wrapper
  rejects any tool event, as the Kimi wrapper does) in a temporary
  directory holding only the sanitized packet.
- `copilot-model-policy.json` maps tier × vendor to a model, e.g. hard:
  GPT-6.1 Terra, Gemini 4 Hydrogen, Grok 4.7, Kimi K3, Claude Sonnet 5.5;
  routine: MAI Code 2 Flash, Gemini 3.8 Flash, GPT-5.6 Luna, Haiku 5.5. The
  exact mapping is a sponsor decision before Phase 2 merges.
- Automatic selection considers (channel, model) candidates, so Claude-owned
  work gets a non-Anthropic Copilot reviewer instead of relying on Gemini
  alone. Gemini via `agy` stays the fallback and the disagreement escalation;
  when the work under escalation has a Google author, escalation goes to a
  Copilot model of a vendor not yet involved.
- Copilot reviews spend Copilot credits; the daily cap is per channel
  (`copilot`), not per vendor.

### D5. Review tickets from the coordinator

Sub-agents may run the wrappers (approved), but only on a ticket the
coordinator issues in the task assignment: exact output name (`rNN`), tier,
reviewer channel and model or `auto`, and packet scope. The coordinator owns
budget, dispositions in the workstream file and the `docs-check.py record`
gate; sub-agents report the artifact path, exit code and verdict back. This
prevents parallel agents racing for names and the daily cap.

### D6. Budget for parallel work

- **Workstream pool:** a user Decisions entry may set a per-workstream daily
  review pool per channel (e.g. `review pool: copilot 20/day, claude
  12/day`) in place of per-round overrides. Five-rounds-per-topic and
  one-hard-round-per-topic still apply per task.
- **Batched routine rounds:** several small tasks may share one routine
  packet when all their authors share the same eligible reviewers; findings
  are labelled per task (`T3-F1`) and dispositioned per task.
- **Queue order:** when the pool is short, tickets follow the build spec's
  dependency order.

### D7. Integration gate

After each batch of merged tasks, and before any task that depends on merged
work, the coordinator requests one integration review of `main` (cross-task
contracts, shared fixtures, hashes) by a reviewer whose vendor authored none
of the batch.

### D8. Copilot's stop-for-user boundary

- A sub-agent may commit and push to its own task branch and open a **draft**
  PR.
- Ready-for-review, merge, deploy, risk-parameter or policy changes, budget
  overrides, and anything touching holdout or paid data stay with the user.

### D9. Instructions Copilot reads

- Gateway templates: `templates/copilot-instructions.md` (for
  `.github/copilot-instructions.md`) and coordinator / sub-agent role files,
  each a short pointer to `PROTOCOL.md` plus D2–D8.
- Repository `AGENTS.md` "Current exception" paragraphs are replaced by a
  pointer once `--owner copilot` works.

### D10. Enforcement in `docs-check.py`

- `Owner:` values must be registry owners.
- Copilot tasks need `Task`, `Author`, `Author-models` and a task-table row.
- Artifact metadata must match the workstream (owner, task, author models)
  and satisfy D3.
- Legacy `--owner codex` artifacts written for Copilot are never edited; one
  dated Decisions entry per repository maps them to Copilot.

## Phases

1. Registry (D1) with Kimi and Codex inactive; `--owner copilot`, `--task`,
   `--author-model` in the wrappers and selection (D2); vendor rule in
   selection and every wrapper (D3); `docs-check.py` checks (D10); tests.
   Reviewed by Gemini (hard).
2. `copilot-review.sh` and its model policy (D4), after a sponsor decision on
   the tier × vendor mapping and a live read-only smoke test; tickets (D5);
   budget pool and batching (D6).
3. Integration gate (D7), boundary (D8), templates (D9); repository shims and
   `Standards:` pins bumped; `AGENTS.md` exceptions replaced.

Each phase is committed only with the sponsor's approval.

## Open questions

- Exact Copilot CLI model IDs for Gemini, Grok and Kimi (confirm from the
  CLI before writing `copilot-model-policy.json`).
- Tier × vendor reviewer mapping for D4.
- Size of the default workstream pool for D6.
