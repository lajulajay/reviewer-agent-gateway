# Reviewer protocol

This is the canonical collaboration and review protocol for every repository
under `~/Developer`. Repository `AGENTS.md`, `CLAUDE.md`, and
`reviewers/PROTOCOL.md` files point here and add only repository-specific
rules. If repository wording differs from this file, this file wins.

## Roles

| Role | Who | Does |
| :--- | :--- | :--- |
| Owner | Claude, Codex, or Copilot, assigned by the user per workstream | Investigates, implements, tests, and commits/pushes/deploys within the user's escalation boundary |
| Official reviewers | Active Kimi, Claude, and Codex reviewers other than the owner | Read-only adversarial review of substantive work |
| Fallback reviewer | Gemini, always | Read-only review when no eligible subscription reviewer is available or a decision-material disagreement remains unresolved |

Claude, Codex, and Copilot are interchangeable owners; none is the default.
Kimi and Gemini are reviewer-only and never own work. `agents.json` is the
registry of agents and the model vendors each one runs.

- **Recording the owner.** Each workstream file in the repository's
  `workstreams/` starts with an `Owner: <agent>` line
  (legacy `COLLAB.md` entries before adoption kept theirs). Only the
  user assigns or changes the owner. A change is recorded as a new dated line,
  e.g. `Owner: Claude (from Codex, 2026-10-03, Codex limit reached)`; earlier
  entries are never rewritten.
- **No self-review, by vendor.** No model vendor reviews work it owns or
  wrote, whatever the model version (user decision 2026-11-20). Pass
  `--owner` on every reviewer call, one `--author` per additional agent, and
  one `--author-model` per model that wrote the work; Copilot ownership or
  authorship requires `--author-model`, and a router such as Copilot Fusion
  may not author reviewed work. Every wrapper and automatic selection refuse
  a reviewer that shares a vendor with any of them, and record the identity
  in the artifact.
- **Subscription roster.** `reviewer-roster.json` lists the currently active
  Claude, Codex, and Kimi subscriptions. Update it when a subscription starts
  or lapses; automatic selection never chooses an inactive reviewer. Gemini is
  deliberately absent because it is fallback-only.
- **Ownership changes mid-workstream.** After a handoff, the new owner's
  changes go to another eligible reviewer as usual. For a packet that mixes
  both owners' unreviewed work, use an active reviewer that authored none of
  it (Kimi can review a Claude/Codex mixture), split it by author, or use
  Gemini when no independent subscription reviewer is eligible.
- **Escalation.** Use automatic subscription-reviewer selection for
  substantive work unless a particular reviewer is required. Use Gemini when
  all eligible subscription reviewers are unavailable (usage limit, outage,
  or failed invocation after diagnosis). Do not use reviewers for routine
  agreement, style, or model voting.
- **Disagreement escalation (mandatory order).** When the owner and the
  subscription reviewer still disagree on a decision-material point after a
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
reviewers/claude-review.sh --owner <agent> [--author-model M]... <sonnet|opus>    <prompt> .collab/claude-YYYY-MM-DD-topic.md <packet>...
reviewers/codex-review.sh  --owner <agent> [--author-model M]... <routine|hard>   <prompt> .collab/codex-YYYY-MM-DD-topic.md  <packet>...
reviewers/kimi-review.sh   --owner <agent> [--author-model M]... <hard|routine> <prompt> .collab/kimi-YYYY-MM-DD-topic.md <packet>...
reviewers/auto-review.sh   --owner <agent> [--author-model M]... <hard|routine> <prompt> .collab/auto-YYYY-MM-DD-topic.md <packet>...
reviewers/gemini-review.sh --owner <agent> [--author-model M]... <hard|routine> <prompt> .collab/gemini-YYYY-MM-DD-topic.json <packet>...
```

Add `--packet-root <dir>` to use a shared prompt or packet from outside the
repository (e.g. `~/Developer/reviewer-agent-gateway/prompts`). Options go
before the model or tier. For automatic selection of mixed-authorship work,
repeat `--author <agent>` for every author besides the owner; add `--task <id>` for a delegated task.

For automatic selection, the `auto-` output name is a template; the artifact
uses the chosen provider's prefix. New topics go to the active, non-owner
and non-author reviewer with the fewest spent review rounds in that repository
today and room
under that provider's daily cap, with roster order breaking ties. Follow-ups
stay with the topic's latest eligible reviewer when round records establish one
unambiguous reviewer; otherwise selection falls back to daily balancing. An
existing artifact or diagnostic is never retried under the same name. This
local-history rule balances known gateway usage without pretending to measure
incomparable provider quotas. The dispatcher fails over only after preflight
exit 69 or 78, never after a model call, timeout, validation failure, or budget
refusal; if all candidates fail preflight, use Gemini. The template date must
be today's local date.

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
  count together, including failed calls that reached or may have reached the
  model. After five, only `gemini-review.sh` may run, at most twice: an
  assessment and, if the owner fixes what it finds, a check of those fixes.
  After that the owner brings the open points to the user in one packet, as in
  the disagreement escalation above: the competing claims, the evidence,
  Gemini's assessment, and the exact decision needed. No further review runs
  unless the user approves an override.
- **One hard-tier round per topic** (Claude `opus`, Codex `hard`, or any Kimi
  call classified as hard by requested tier, K3-family alias, or `high`
  effort); use it where it matters most.
- **Eight reviews per provider per repository per day.**
- **Claude follow-up rounds run at low effort**; the first round runs at
  medium. A follow-up packet lists the open IDs and the owner's response to
  each, and asks only whether each is resolved.
- **Only the user may lift a limit.** `REVIEW_BUDGET_OVERRIDE=<reason>`
  records the reason in the artifact, and `docs-check.py record` fails until
  a user Decisions entry approves a "budget override" for that round (`rNN`).
- **Output names** must be `<provider>-YYYY-MM-DD-<topic>[-rNN].md|json`;
  the daily cap reads the date from the name. Automatic selection also accepts
  an `auto-` template but writes the actual artifact with the provider prefix.
  A refused attempt reserves its name, including budget refusals. If the user
  approves a budget override, use a new `rNN` name and cite that round in the
  Decisions entry.

Before requesting another round, the owner checks each finding against the
evidence. A finding that a script or test disproves is dispositioned
`rejected:` with that evidence; it does not justify another round. A
`Mechanical check` line gives a quoted value's measured length, not a
verdict: the owner reads the finding to see which number it claims for the
value. A note that a finding cites a `file://` path means the link verifies
nothing; the owner checks any quoted code against the packet before acting.

## Packets and isolation

- Reviewers are read-only. They receive only explicit, sanitized packet
  files and may not edit the repository, mutate production or external
  services, trigger agent runs, place orders, or deploy. The wrappers launch
  reviewers with provider-specific tool restrictions; Kimi's custom agent
  disables tools and subagents, and its wrapper rejects emitted tool events.
- Give the smallest sufficient packet: exact files or line ranges, the diff
  or commit range, relevant evidence and invariants, the competing claims,
  the exact decision, prohibited actions, and named questions. Do not ask for
  repository-wide rediscovery.
- Reviewers cannot count characters. Write every hash or long identifier in
  8-character groups next to a script-produced length (e.g.
  `len=64 groups=ca71fc6a 71fca61d ...`), and give script output for any
  check the reviewer cannot run.
- Keep hard-tier Gemini packets small: send the delta and the targeted
  context, not full source. Above about 150 KB the hard model runs out of
  output tokens before it writes the review, and the wrapper refuses it.
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
