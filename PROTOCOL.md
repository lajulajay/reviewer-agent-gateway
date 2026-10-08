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

- **Recording the owner.** Each workstream file in the repository's
  `workstreams/` starts with an `Owner: Codex` or `Owner: Claude` line
  (legacy `COLLAB.md` entries before adoption kept theirs). Only the
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
  invocation after diagnosis). Do not use reviewers for routine agreement,
  style, or model voting.
- **Disagreement escalation (mandatory order).** When the owner and the
  primary reviewer still disagree on a decision-material point after a
  substantive round, the owner must obtain a Gemini review before bringing
  the disagreement to the user, including policy disagreements and
  disagreements about decisions reserved to the user. Empirical disputes
  first go to evidence or a frozen test; Gemini reviews what that leaves
  open. The user then receives one packet: the competing claims, the
  evidence, Gemini's assessment, and the exact decision needed. Skip Gemini
  only when it is unavailable (quota below the wrapper floor, outage, or
  failed invocation after diagnosis), and say so in that packet. Gemini's
  view is advisory; it never decides by vote, and the decision stays with the
  user. A question that is the user's to decide but on which the agents
  agree goes to the user directly.

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

## Review budget

Every review call spends the user's plan usage, so the wrappers enforce
`review-budget.json` before calling a model (exit 79 when refused):

- **Five rounds per topic, then Gemini, then the user.** The topic is the
  output name without provider, date, and `-rNN`; rounds from every provider
  count together, including failed calls that reached the model. After five,
  only `gemini-review.sh` may run, once. After that the owner brings the open
  points to the user in one packet, as in the disagreement escalation above:
  the competing claims, the evidence, Gemini's assessment, and the exact
  decision needed. No further review runs unless the user approves an
  override.
- **One hard-tier round per topic** (`opus` or Codex `hard`); use it where it
  matters most.
- **Eight reviews per provider per repository per day.**
- **Claude follow-up rounds run at low effort**; the first round runs at
  medium. A follow-up packet lists the open IDs and the owner's response to
  each, and asks only whether each is resolved.
- **Only the user may lift a limit.** `REVIEW_BUDGET_OVERRIDE=<reason>`
  records the reason in the artifact, and `docs-check.py record` fails until
  a Decisions entry quotes the user's "budget override" approval.

Before requesting another round, the owner checks each finding against the
evidence. A finding that a script, test, or the artifact's `Mechanical check`
line disproves is dispositioned `rejected:` with that evidence; it does not
justify another round.

## Packets and isolation

- Reviewers are read-only. They receive only explicit, sanitized packet
  files and may not edit the repository, mutate production or external
  services, trigger agent runs, place orders, or deploy. The wrappers enforce
  this: no reviewer has working tools.
- Give the smallest sufficient packet: exact files or line ranges, the diff
  or commit range, relevant evidence and invariants, the competing claims,
  the exact decision, prohibited actions, and named questions. Do not ask for
  repository-wide rediscovery.
- Reviewers cannot count characters. Write every hash or long identifier in
  8-character groups next to a script-produced length (e.g.
  `len=64 groups=ca71fc6a 71fca61d ...`), and give script output for any
  check the reviewer cannot run.
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
