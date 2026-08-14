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

Run provider-free regression checks with:

```bash
tests/wrapper-failure-smoke.zsh
```

This includes a consumer-shim resolution fixture: each shim is invoked without
arguments and must reach the canonical gateway's argument validation (exit 64),
without starting a provider request.
