# Reviewer Agent Gateway

Canonical isolated Claude, Codex, Gemini, and Kimi reviewer wrappers for the
prediction-market repositories and other projects. Consumer repositories keep
small tracked entrypoints that delegate here. Roles, escalation, and review
records are defined in [PROTOCOL.md](PROTOCOL.md).

Codex and Kimi each have two routes, chosen by `route` in their model policy:
`subscription` runs the provider's CLI (Kimi through the Kimi Code CLI's
managed OAuth provider, refusing API credentials and model/endpoint
overrides), and `api` sends the packet directly to the provider's API with a
Keychain key under a spend cap (see "API route for Codex and Kimi" below).
As of 2026-11-20 both providers use `api`. Sending a packet through these
wrappers to a registered reviewer vendor needs no per-task approval of the
destination; budget, packet-safety and override rules are unchanged (see
"Where packets may go" in [PROTOCOL.md](PROTOCOL.md)).

Invocation contract:

```text
reviewer.sh [--packet-root DIR] [--owner AGENT] [--author AGENT]... [--author-model MODEL]... [--task ID] MODEL PROMPT OUTPUT PACKET...
auto-review.sh [--packet-root DIR] --owner AGENT [--author AGENT]... [--author-model MODEL]... [--task ID] <hard|routine> PROMPT AUTO_OUTPUT PACKET...
```

The target repository is derived from the output path. Inputs outside it are
allowed only with explicit `--packet-root`; symlinks, secret/private paths,
and output overwrites remain rejected. Successful artifacts must be substantive
and end with exactly one approved, machine-detectable verdict line:
`VERDICT: ACCEPT`, `VERDICT: ACCEPT WITH CONDITIONS`, or `VERDICT: REJECT`.
The wrappers accept harmless Markdown emphasis around that line, but reject
ambiguous, multiple, or non-final verdicts instead of inferring a category from
review prose. Failed calls write a
non-overwritable `.diagnostic.json` beside the requested output whenever the
output location is usable.

`--owner` names the agent that owns the work under review (an owner in
`agents.json`: Claude, Codex, or Copilot). It is optional for compatibility on
direct provider calls but [PROTOCOL.md](PROTOCOL.md) requires it. Repeat
`--author` for each additional authoring agent and `--author-model` for each
model that wrote the work; `--task` records a delegated task ID. Every wrapper
records these in its artifact and runs `agents.py check` before any model call.

Vendor independence: `agents.json` maps each channel (CLI subscription) to the
model vendors it runs, and model IDs to vendors by prefix. A reviewer is
refused (exit 64) when any of its vendors is the vendor of the owner, an author,
or an authoring model, whatever the model version: Gemini cannot review work
written by Gemini 4 Hydrogen through Copilot; Claude cannot review Copilot work
written by any Claude model. Copilot's vendor depends on the model, so Copilot
ownership or authorship requires `--author-model`; routers (`auto`, Copilot
Fusion) and unknown prefixes fail closed. Automatic selection applies the same
rule. `docs-check.py record` re-checks every indexed artifact and every
workstream `Owner:` line against the registry.

Active roles: Claude, Codex, and Copilot own work; Kimi is reviewer-only.
Kimi, Claude, and Codex are official reviewers when active in
`reviewer-roster.json`, and Gemini is always the fallback reviewer, never an
owner. Copilot reviews only when called directly (`copilot-review.sh`); it is
not in `reviewer-roster.json` or automatic selection yet. Remove a reviewer from `active_reviewers` when its subscription lapses
and restore it when renewed; `tie_break_order` must continue to list all three
subscription reviewers.

`auto-review.sh` chooses among active subscription reviewers other than the
owner and additional authors, and not already at the repository's per-provider
daily cap. For a new
topic it selects the reviewer with the fewest spent gateway review rounds today,
using roster order to break ties. A follow-up stays with the topic's latest
eligible reviewer when round numbering establishes one unambiguous reviewer; if
the latest reviewer is inactive, capped, or ambiguous, selection falls back to
daily balancing. The `auto-YYYY-MM-DD-<topic>[-rNN].md` argument is a naming
template: the successful artifact uses the selected provider's prefix. Both the
template and candidate outputs reject an existing artifact or diagnostic, so a
failed request cannot be retried under the same name. The template date must
be today's local date. A user-approved budget override after a refusal uses a
new `rNN` name; the workstream Decisions entry must approve that new round.

This is deterministic local load balancing, not a claim to know each provider's
remaining quota. Claude and Kimi expose usage interactively and Codex exposes
status in an active session, so there is no cheap, comparable cross-provider
quota preflight. Review history is already available locally and includes failed
calls that reached or may have reached the model. Gemini is deliberately
excluded from this rotation. Automatic failover tries the next candidate only
after preflight exit 69 or 78; it never repeats a call after model invocation,
timeout, validation failure, or budget refusal. If every candidate fails
preflight, use Gemini.

## Kimi reviews through Kimi Code

`kimi-review.sh` accepts the `routine` and `hard` tiers. The explicit mappings
in `kimi-model-policy.json` are currently:

| Tier | Managed model alias | Requested reasoning effort |
| :--- | :--- | :--- |
| `routine` | `kimi-code/kimi-for-coding` | `low` |
| `hard` | `kimi-code/k3` | `high` |

Unlike the dated Claude and Gemini catalogs, these purpose-specific managed
aliases do not use a second-older-release rule. Update the policy when the
subscription's available aliases or desired effort change.
`KIMI_REVIEW_MODEL_POLICY` may point to another policy file for an isolated
test; selected K3-family aliases or `high` effort are still classified as
hard-tier use for budget accounting. Kimi Code does not report the serving
model, resolved effort, or token usage in its review stream, so the artifact
records the selected alias and requested effort and marks serving model and
usage as unreported.

Before every call the wrapper checks sanitized `kimi provider list --json`
output: the selected alias must belong to `managed:kimi-code`, use provider type
`kimi`, have nonempty OAuth metadata, and have no API-key configuration. API
credentials and model or endpoint environment overrides are refused. This
preflight establishes the managed OAuth configuration, not the account's live
remaining quota or an unexpired membership; sign in through Kimi Code's normal
subscription flow and check `/usage` interactively for current quota.

The review runs from an empty workspace with an agent whose `tools: []` and
`subagents: []` disable tool and delegation access, an empty replacement skills
directory, and cron, background steering, and automatic updates disabled. The
Kimi CLI is documented to enforce that agent allowlist before tool execution;
the wrapper does not independently verify session contents, and a reviewer that
never attempts a tool produces no observable denial. The wrapper therefore
fails closed if the JSONL stream contains an Assistant `tool_calls` event, Tool
message, or defensive tool-call field — a real emission, observed in positive
allow-tool probes, is rejected. The prompt and
packets are inlined, capped by `KIMI_MAX_PROMPT_BYTES` (default 100000 bytes),
and bounded by `KIMI_MAX_TIME_SECONDS` (default 900 seconds).
The inlined packet is passed as a CLI argument and can appear in local process
listings while the review runs.

Kimi Code is documented to persist session records under
`$KIMI_CODE_HOME/sessions/` (normally `~/.kimi-code/sessions/`); those records
may contain the inlined prompt and packet. The wrapper does not read or verify
session contents. Keep secrets and private data out of packets; the wrapper's
path checks remain mandatory.

## Claude review tier policy

Use the `sonnet` alias by default for a bounded, substantive adversarial review:
a routine implementation diff or follow-up delta, a focused regression or
operator-workflow check, or a review whose evidence and decision rule are
already clear. A focused packet and an explicit invariant remain required;
`sonnet` is not a substitute for review rigor.

Use the `opus` alias when the review itself requires materially harder
reasoning. This includes a new or changed strategy/experiment or its result
classification; a risk, execution, data-validity, security, or production
decision with material downside; a cross-system architecture, concurrency, or
causal-timing question; an ambiguous root cause with competing explanations; or
a decision-material disagreement or inconclusive `sonnet` round. Use it for a
final decision-bearing review only when one of those conditions applies—not as
a ceremonial second opinion or model vote.

The owner chooses the smallest sufficient tier before invocation and records
the requested alias, resolved model(s), and a one-sentence tier rationale in
the review artifact or its workstream's review index. `opus` does not replace the
escalation rule in PROTOCOL.md: unresolved empirical questions still return
to evidence or a frozen test, and unresolved policy choices return to the
sponsor.

The Claude wrapper maps `opus` to the explicitly approved `hard_model` and
`sonnet` to the second older approved release. These are review-tier names;
the wrapper sends a full model ID to Claude Code and verifies that ID in the
response metadata. Its `Selected model` artifact line records the choice.
The release-ordered list and whether each model is included in the account's
plan are stored in `claude-model-policy.json`. The selector checks that the
release dates descend strictly. `routine_two_releases_down_scope` determines
whether the two steps are counted within the hard model's family or across
all approved models. The current policy uses the latter: `opus` selects
`claude-opus-5-5`; `sonnet` selects `claude-sonnet-5`. The wrapper fails closed
if it has too few approved models or Claude reports a different model. An
explicit `CLAUDE_REVIEW_MODEL_POLICY` path may point to another policy file
for an isolated test.
If fewer than three models are approved in the chosen scope, an optional
`routine_fallback_model` may name another approved model; otherwise routine
selection fails. A fallback is a deliberate exception to the two-release
rule; the current policy has no fallback.

The Models API lists API-accessible releases but does not establish whether
Claude Code will charge usage credits on this account. Update the approved list
from the account's `/model` menu and plan usage settings. Keep
`ANTHROPIC_API_KEY` unset when using included Claude Code usage; the wrapper
rejects it and checks `claude auth status` for `claude.ai` authentication.
Disable usage credits in the Claude account if additional charges must be
impossible. An approved list is an account policy, not a live entitlement
check.

## Codex reviews

`codex-review.sh` runs `codex exec` on the ChatGPT plan. It refuses
`OPENAI_API_KEY`/`CODEX_API_KEY` and requires `codex login status` to report
ChatGPT sign-in. `codex-model-policy.json` maps the `routine` and `hard` tiers
to a model and reasoning effort (currently `gpt-6-sol` at `medium` and
`high`). Update it from the models the account offers.

The interactive Codex config is not used: it runs with
`danger-full-access`, never asks for approval, and enables plugins. The review
runs with `--ignore-user-config --ignore-rules --ephemeral -s read-only` from an
empty workspace, with web search off and the features that expose tools
disabled (apps, plugins, shell and exec, code-mode host, subagents,
browser/computer use, image generation, skill search, goals, hooks). The
prompt and packet are sent on stdin. Verified with codex-cli 0.159.3 on
2026-10-02: shell, file reads, `apply_patch` (still listed, but it runs
through the disabled code-mode host), app connectors, web, and image tools
all fail. Subagent spawn also fails, but only because `--ephemeral` leaves no
session to fork, so do not rely on that as a policy. Tool errors after the
turn starts are counted in the artifact's `Blocked tool attempts` line.

`codex exec` does not report the serving model, so the artifact records the
requested tier, selected model, and effort, and says the resolved model was
not reported. `CODEX_MAX_TIME_SECONDS` bounds the call (default 600).
`CODEX_REVIEW_MODEL_POLICY` may point to another policy file for an isolated
test.

## Copilot reviews through the Copilot CLI

`copilot-review.sh` reviews on the user's Copilot plan with a model chosen by
tier and vendor in `copilot-model-policy.json`. The reviewer's vendor is that
model's vendor, so the vendor rule applies per model: Copilot may review Claude
work through an OpenAI model, never through a Claude model. Without `--vendor`
the wrapper takes the first vendor in the tier's `vendor_order` that the rule
allows; with `--vendor V` it uses that vendor's model or refuses (exit 64).
Copilot-owned work needs `--author-model` for every model that wrote it, and
every one of those vendors is skipped. Mappings (sponsor-approved 2026-11-21):

| Tier | Vendor order and models | AI-credit cap per call |
| :--- | :--- | :--- |
| `hard` | Anthropic `claude-sonnet-5.5`, OpenAI `gpt-6.1-terra`, Google `gemini-4-hydrogen`, Moonshot `kimi-k3`, xAI `grok-4.7`, Microsoft `mai-code-2` | 60 |
| `routine` | Anthropic `claude-haiku-5.5`, OpenAI `gpt-6-luna`, Google `gemini-3.8-flash`, Microsoft `mai-code-2-flash`, xAI `grok-4.6`, Moonshot `kimi-k3` | 30 |

`copilot-model-select.py` checks that each mapped model belongs to its listed
vendor in `agents.json` (exit 78 otherwise). `--owner` is required. The CLI
runs with the prompt on stdin in an empty temporary directory and an empty
temporary `COPILOT_HOME` with plugin discovery off, so no user MCP
configuration, plugin, custom agent or saved session loads (sign-in comes from
the system credential store). Every tool is hidden and denied
(`--available-tools` plus `--deny-tool` for shell, write, read, memory and
url), built-in and named MCP servers are disabled, and custom instructions,
temp-dir access, questions, session sync and auto-update are off.
`--max-ai-credits` comes from the tier (the CLI's minimum is 30).
`COPILOT_PROVIDER_*` and `COPILOT_MODEL` overrides are refused.

The review fails with exit 70 on any tool event or tool request (a message's
`serverTools` may only name its provider), an enabled MCP server, anything
other than exactly one successful `result` as the final event, or a final reply
that is empty or incomplete. A reply arrives as chunk messages sharing
`originatingMessageId` and `apiCallId`; all `chunkCount` chunks must be present,
and an earlier reply is never used in place of an incomplete final one. Exit 74
means a message named no model or a model other than the selected one. Any exit
after the call began that left no artifact still writes a diagnostic, so the
attempt counts toward the budget. The artifact records the selected and
resolved model, reviewer vendor, CLI version, tool events, token usage, and AI
credits used against the cap. `COPILOT_MAX_TIME_SECONDS` (default 1800) bounds
the call. Copilot `hard` counts toward the one hard round per topic.

## API route for Codex and Kimi

`codex-model-policy.json` and `kimi-model-policy.json` carry a `route`:
`subscription` (the CLI paths described above) or `api`. On the API route the
wrapper keeps every shared check (identity and vendor rule, output naming,
review budget, packet safety, output contract, checksums, gateway provenance)
and replaces only the model call with `api-call.py`:

- **One tool-free request** to the policy's https host: OpenAI `/responses`
  (`tools: []`, `store: false`) or Moonshot `/chat/completions` (`n: 1`).
  The review is accepted only from a complete reply (`status: completed`, or
  exactly one choice with `finish_reason: stop`) with no tool item, tool
  call, or function call; anything else fails with exit 70.
- **Streaming.** The request asks for a streamed reply (`stream: true`) so
  long reasoning is not cut off by provider limits on silent connections
  (Moonshot closed a non-streamed hard-tier call at 600 s). The stream is
  reassembled into the same reply object and passes the same checks; a server
  that ignores the flag answers with plain JSON, which is accepted. A stream
  without a final event, an error event, or more than one choice is a
  rejected reply. The whole call may take `REVIEWER_API_TIMEOUT_SECONDS`
  (default 1800); up to 300 s of silence between lines is tolerated.
- **Key handling.** The key is read from the Keychain item named by
  `keychain_service` inside the process, checked for printable ASCII without
  being echoed, and sent only in the Authorization header. Redirects are
  refused and a reply from another host is rejected. Every message the script
  prints is redacted, and unexpected exceptions print no traceback.
- **Spend cap.** Under an exclusive lock on the ledger, the call reserves its
  bound before sending: every UTF-8 byte of the request body counted as one
  input token (tokenizers emit at most one token per byte) plus 1,024 framing
  tokens and `max_output_tokens`, at the policy's list prices, rounded up to
  the micro-dollar. It is refused (exit 79) unless settled spend plus open
  reservations plus that bound fit `spend_cap_usd`. The reservation is then
  settled at the reported usage. It is released to zero only for HTTP 400,
  401, 403, 404 and 422 (the provider rejected the request); missing usage,
  429, 5xx, transport errors, malformed replies and crashes keep the full
  reservation. The ledger is
  `~/.local/state/reviewer-gateway/api-spend-<ledger>.jsonl` (fixed location,
  outside every repository; a malformed line refuses all calls rather than
  guessing). Output ceilings include reasoning tokens on both APIs as
  documented by the providers; confirm when changing models.
- **Exit codes.** `api-call.py` creates a marker immediately before sending.
  Without the marker, the wrapper exits 64, 78 or 79 (nothing was sent; the
  dispatcher may fail over). With it, any failure is 70 (the request may have
  reached the model and counts), and Kimi's diagnostic sets
  `model_invocation_began` from the same marker.
- The artifact records `Route: api`, the served model, token usage and cost.

Store or replace a key with `python3 keychain-store.py <service>`
(`reviewer-gateway-openai`, `reviewer-gateway-moonshot`). It prompts with
echo off and writes through the Security framework, so the key never appears
in argv, the environment or shell history. (`security add-generic-password
-w` truncates typed input at 128 characters, and passing the key as its
argument exposes it in the process list.)

## Review requests

An owner that cannot send a packet itself (for example a Copilot sub-agent,
which refuses to transmit source to a third-party API) records a request
instead; the user, or an agent the user asks, runs it:

```text
review-request.py create [--packet-root DIR] --reviewer claude|codex|kimi|gemini --tier T
    --owner O [--author A]... [--author-model M]... [--task ID] [--override-reason TEXT]
    PROMPT .collab/<provider>-YYYY-MM-DD-<topic>[-rNN].md PACKET...
review-request.py list [REPO]
review-request.py run [--apply-override] reviewers/requests/<output name>.request.json
```

`create` applies the identity and vendor rule, refuses an output or
diagnostic that already exists, hashes the prompt and every packet file, and
writes `reviewers/requests/<output name>.request.json`; it sends nothing.
`run` refuses a request whose files changed or whose output exists, then calls
the normal wrapper from the repository root with the recorded arguments, so
every gateway check applies. It ignores any `REVIEW_BUDGET_OVERRIDE` in the
runner's environment; a request's `--override-reason` is applied only with
`--apply-override`, which the runner passes only after the user approved that
round. A request runs at most once: `run` claims `<output name>.result.json`
before calling the wrapper (nothing is sent if it cannot) and records the
outcome there; another attempt needs a new request with a new `rNN` name.
The output must be exactly `.collab/<request name>` and packets must stay in
the repository or the recorded packet root. The embedded hashes detect files
changed after `create` but do not authenticate the request, an editable
record; the wrapper remains the control. Commit the request and result with
the review they produced.

## Gemini reviews through Antigravity CLI

The Gemini wrapper runs reviews through the Antigravity CLI (`agy`) on the
signed-in Google account's plan quota. Gemini CLI personal-account OAuth was
retired on 2026-10-02 and the API-key path that replaced it was billed per
call, so the wrapper now refuses to start if `GEMINI_API_KEY` or
`GOOGLE_API_KEY` is set (either would move `agy` onto billed API calls). Sign
in once by running `agy` interactively; the wrapper fails closed when signed
out.

Before each review the wrapper reads `agy -p /usage` and stops if the shared
weekly "Gemini Models" quota (Flash and Pro draw from one bucket, charged by
token cost) is below `GEMINI_REVIEW_MIN_QUOTA` (default `0.15`). This keeps
headroom for interactive use and keeps reviews from reaching the point where
`agy` starts spending AI credits. Each call carries a ~15k-token built-in
system prompt, so even small reviews consume measurable quota.

The `gemini-model-policy.json` catalog lists approved `agy` model IDs, which
carry an effort suffix, with release dates. The `pro`/`hard` tier selects
`gemini-3.8-flash-high`; `flash`/`routine` selects the second older approved
release. Since 2026-11-15 `agy` offers only Gemini 3.8 Flash, so 3.7 and 3.6
are marked not included and routine uses `routine_fallback_model`,
`gemini-3.8-flash-medium`. A fallback must be the hard model's own release at
another effort; it is used only when two older releases are not approved, and
may also be named by full ID. The tier names are kept for consumer
compatibility and do not imply the model family. `explicit_only_models`
(currently none; `gemini-3.1-pro-high` was withdrawn) are accepted only when
named by full ID. Run `agy models` to see what
the account offers and review the catalog when Google ships a model.

Isolation. `agy` is a full agent with shell, file, web, browser, scheduling,
and subagent tools, and plan mode does not remove them. The wrapper runs it
from a private empty workspace whose `.agents/hooks.json` holds a `PreToolUse`
hook matching every tool that returns `deny`. Verified against `agy` 1.2.15 on
2026-10-02: the hook blocks reads, writes, and commands, overrides user-level
permission allows, and blocks tools if the hook script itself fails. The
prompt and packet are therefore inlined into the prompt argument (`agy -p`
ignores stdin), capped at `GEMINI_MAX_PROMPT_BYTES` (default 800000). Denied
tool attempts are recorded in `reviewer_metadata.denied_tool_calls`. Slash
commands and skill expansion are disabled, the call runs with `--sandbox`,
and Google credential variables are removed before launch. (`--mode plan` was
dropped on 2026-10-08: `agy` 1.3.1 warns it has no effect with slash commands
disabled, and the deny-all hook already blocks every tool.)

The hard-tier model spends its output tokens on hidden reasoning when the
packet is large: on 2026-10-08 two runs with 215-245 KB packets hit the
output-token limit (one had written a complete review, the other stopped
before its verdict), while 40 KB packets succeeded. Hard-tier calls are therefore
refused above `GEMINI_HARD_MAX_PROMPT_BYTES` (default 150000), before the
budget check, so the refusal uses no round. When `agy` reports the
output-token limit (`status: "ERROR"`), the wrapper keeps the returned review
only if it passes `reviewer-validate.py` and records
`reviewer_metadata.truncation_warning`; otherwise it fails with "Gemini hit
the output-token limit before finishing the review", which counts as a round
because the quota was spent.

`agy` reports the session model only in its `stream-json` init event; the
wrapper requires it to equal the selected ID. That is the configured session
model, not proof of which backend served the request. Self-updates are
disabled for the call (`AGY_CLI_DISABLE_AUTO_UPDATE=1`) and the CLI version is
recorded. `GEMINI_MAX_TIME_SECONDS` (default 600) is passed as
`--print-timeout`, with a `GEMINI_TIMEOUT_GRACE_SECONDS` (default 30) alarm as
a backstop. Artifacts keep the top-level `response` field and add
`reviewer_metadata` with the CLI version, requested/selected/resolved model,
`conversation_id`, starting quota, and denied tool calls.

`agy` saves every run, including the inlined packet, under
`~/.gemini/antigravity-cli/conversations/<conversation_id>.db`. Neither
`ANTIGRAVITY_APP_DATA_DIR` nor a separate `HOME` avoids this (the latter loses
the sign-in), so the copy is left in place and traceable by the recorded ID.
Packets must still exclude secrets; the private-path rules above apply.

## Review budget and usage records

`review-budget.py` runs in every wrapper before the model call and applies
`review-budget.json`; the rules are in
[PROTOCOL.md](PROTOCOL.md#review-budget). It counts the topic's artifacts in
`.collab/`, plus diagnostics for failed calls that reached or may have reached
the model, and counts the daily cap by the date in the output name. Kimi calls
are classified as hard-tier when the requested tier is `hard`, the selected
alias is in the K3 family, or the artifact/diagnostic records `high` effort.
Changing the limits is a committed change to `review-budget.json`; the wrappers
refuse to run with it uncommitted.

Artifacts record what each call used: the Claude header has `Effort:` and
`Usage:` (tokens, `total_cost_usd` as Claude Code reports it, duration, and
turns), the Codex header has `Usage:` from `turn.completed`, Gemini artifacts
keep `agy`'s `usage` field, and Kimi explicitly marks usage and serving model
as unreported. `reviewer-claims.py` adds a `Mechanical check:` header line
(Gemini: `reviewer_metadata.mechanical_checks`) when a review says a quoted hex
value has a length it does not have, or cites a `file://` path (reviewers have
no file access, so the link does not verify any quoted code; the owner checks
the quote against the packet). `reviewer-validate.py` refuses a finding labeled
with a severity other than `blocker`, `major` or `minor`, which would otherwise
go untracked.

Run provider-free regression checks with:

```bash
tests/wrapper-failure-smoke.zsh
python3 tests/test_reviewer_select.py
python3 tests/test_docs_check.py
```

This includes a consumer-shim resolution fixture: each shim is invoked without
arguments and must reach the canonical gateway's argument validation (exit 64),
without starting a provider request.
