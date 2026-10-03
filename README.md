# Reviewer Agent Gateway

Canonical isolated Kimi, Claude, and Gemini reviewer wrappers for the
prediction-market repositories and other projects. Consumer repositories keep
small tracked entrypoints that delegate here.

Kimi runs through Ollama, but the current signed-in account has no entitlement
to either Kimi cloud model. `ollama list` may show `kimi-k2.6:cloud` even when
`ollama run` is denied with a subscription-required 403, so list output is not
an access check. Kimi is unavailable until an explicit access and budget
change. `kimi-k3:cloud` remains a future option. The wrapper never uses
Moonshot API credentials or endpoints.

Invocation contract:

```text
reviewer.sh [--packet-root DIR] MODEL PROMPT OUTPUT PACKET...
```

For Kimi, use `OLLAMA_MAX_TIME_SECONDS` for the wrapper timeout; it defaults
to 900 seconds. The legacy `KIMI_MAX_TIME_SECONDS` setting no longer applies.

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

Canonical active escalation: Claude is the primary reviewer and Gemini is the
second reviewer when Claude is unavailable or a decision-material disagreement
remains unresolved. Kimi is inactive while Moonshot membership access is
pending; it may be reconsidered only after explicit reactivation.

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
the review artifact or its `COLLAB.md` disposition. `opus` does not replace the
Claude-to-Gemini escalation rule: unresolved empirical questions still return
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
release, `gemini-3.6-flash-high`. The tier names are kept for consumer
compatibility and do not imply the model family. `explicit_only_models`
(currently `gemini-3.1-pro-high`, which is older than every listed Flash
release) are accepted only when named by full ID. Run `agy models` to see what
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
commands and skill expansion are disabled, the call runs with `--mode plan
--sandbox`, and Google credential variables are removed before launch.

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

Run provider-free regression checks with:

```bash
tests/wrapper-failure-smoke.zsh
```

This includes a consumer-shim resolution fixture: each shim is invoked without
arguments and must reach the canonical gateway's argument validation (exit 64),
without starting a provider request.
