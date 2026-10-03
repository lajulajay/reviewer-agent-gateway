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

Before a Gemini review, the gateway uses the configured API key to paginate
`models.list` and requires the requested model to support `generateContent`.
This is fail-closed and happens before the CLI request. Callers may pass a
concrete available model, or the stable `pro` / `flash` capability profiles.
The profiles choose the first account-available candidate from
`GEMINI_REVIEW_PRO_MODELS` or `GEMINI_REVIEW_FLASH_MODELS` (comma-separated);
their defaults are maintained by the gateway. `auto` routing is refused for
review reproducibility. Artifacts record the requested value, the preflight
selection, and the model(s) the CLI reports as resolved.

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

Run provider-free regression checks with:

```bash
tests/wrapper-failure-smoke.zsh
```

This includes a consumer-shim resolution fixture: each shim is invoked without
arguments and must reach the canonical gateway's argument validation (exit 64),
without starting a provider request.
