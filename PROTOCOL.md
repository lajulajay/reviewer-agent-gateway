# Reviewer protocol

This is the canonical collaboration and review protocol for every repository
under `~/Developer`. Repository `AGENTS.md`, `CLAUDE.md`, and
`reviewers/PROTOCOL.md` files point here and add only repository-specific
rules. If repository wording differs from this file, this file wins.

## Roles

| Role | Who | Does |
| :--- | :--- | :--- |
| Owner | Codex **or** Claude, assigned by the user per workstream | Investigates, implements, tests, and commits/pushes/deploys within the user's escalation boundary |
| Primary reviewer | Whichever of Codex/Claude is not the owner | Read-only adversarial review of substantive work |
| Backup reviewer | Gemini, always | Read-only review when the primary reviewer is unavailable or a decision-material disagreement remains unresolved |
| Inactive | Kimi | Not invoked until the user explicitly reactivates it |

Codex and Claude are interchangeable owners; neither is the default.

- **Recording the owner.** Each workstream entry in the repository's
  `COLLAB.md` starts with an `Owner: Codex` or `Owner: Claude` line. Only the
  user assigns or changes the owner. A change is recorded as a new dated line,
  e.g. `Owner: Claude (from Codex, 2026-10-03, Codex limit reached)`; earlier
  entries are never rewritten.
- **No self-review.** A change is reviewed only by an agent that did not
  author it. Pass `--owner codex|claude` on every reviewer call: the Claude
  wrapper refuses `--owner claude`, the Codex wrapper refuses `--owner codex`,
  and every wrapper records the owner in its artifact.
- **Ownership changes mid-workstream.** After a handoff, the new owner's
  changes go to the other agent as usual. A packet that mixes both agents'
  unreviewed work has no independent primary reviewer, so split it by author
  or send it to Gemini.
- **Escalation.** Use the primary reviewer for substantive work. Use Gemini
  when the primary reviewer is unavailable (usage limit, outage, failed
  invocation after diagnosis) or when a substantive primary review leaves the
  same decision-material disagreement unresolved. Do not use reviewers for
  routine agreement, style, or model voting. Empirical disputes return to
  evidence or a frozen test; unresolved policy choices return to the user.

## Invocation

Run from the repository root through the repository's `reviewers/` shims,
which delegate to this gateway:

```bash
reviewers/claude-review.sh --owner codex  <sonnet|opus>    <prompt> .collab/claude-YYYY-MM-DD-topic.md <packet>...
reviewers/codex-review.sh  --owner claude <routine|hard>   <prompt> .collab/codex-YYYY-MM-DD-topic.md  <packet>...
reviewers/gemini-review.sh --owner <codex|claude> <hard|routine> <prompt> .collab/gemini-YYYY-MM-DD-topic.json <packet>...
```

Add `--packet-root <dir>` to use a shared prompt or packet from outside the
repository (e.g. `~/Developer/reviewer-agent-gateway/prompts`). Options go
before the model or tier.

Choose the smallest sufficient tier and record the requested tier, selected
and resolved model(s), and a one-sentence rationale. The higher tier
(`opus`, `hard`) is for materially harder reasoning: a new or changed
strategy/experiment or its result classification; a risk, execution,
data-validity, security, or production decision with material downside;
cross-system architecture, concurrency, or causal timing; competing
root-cause explanations; or a decision-material disagreement or inconclusive
lower-tier round. Model mappings and per-provider details are in
[README.md](README.md).

## Packets and isolation

- Reviewers are read-only. They receive only explicit, sanitized packet
  files and may not edit the repository, mutate production or external
  services, trigger agent runs, place orders, or deploy. The wrappers enforce
  this: no reviewer has working tools.
- Give the smallest sufficient packet: exact files or line ranges, the diff
  or commit range, relevant evidence and invariants, the competing claims,
  the exact decision, prohibited actions, and named questions. Do not ask for
  repository-wide rediscovery.
- Never include `.env` files, credentials, keys, production data, private or
  raw exports, or unsealed outcomes. Secret paths and symlinks are rejected.

## Artifacts and records

- Capture the wrapper exit code, stdout, and stderr. Success requires the
  requested output and its `.sha256` sidecar; failure leaves a sibling
  `.diagnostic.json` when the output location is usable. Check those paths
  before writing any separate failure record.
- Caller timeouts must exceed the wrapper timeout by at least 60 seconds.
- A successful review is substantive and ends with exactly one
  `VERDICT: ACCEPT`, `VERDICT: ACCEPT WITH CONDITIONS`, or `VERDICT: REJECT`.
- **Never edit a `.collab/` file after it is written.**
- Reviews are not transcribed into `COLLAB.md` (user decision 2026-10-03).
  Each review is indexed in its workstream file (`workstreams/`, template in
  `templates/workstream.md`) and every labeled finding and condition gets a
  compact disposition row; the exact text stays in the committed raw artifact.
  `docs-check.py record|transfer|done` verifies completeness, closure evidence,
  checksums, and budgets. Reviewers label findings `F<n> [severity]:` and
  conditions `C<n>:` and attest to it (`output-contract.txt`); wrappers fail
  closed otherwise.
- The owner independently verifies findings and requests another round only
  after a material design or implementation change, providing the delta
  rather than replaying history.
