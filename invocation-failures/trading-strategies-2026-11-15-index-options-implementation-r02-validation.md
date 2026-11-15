# Reviewer invocation failure report

Date: 2026-11-15 (America/New_York)
Invoked from: `trading-strategies`
Canonical wrapper repository: `~/Developer/reviewer-agent-gateway`
Owner / caller: Codex
Review topic: Index-options implementation r02 correction review

## Packet

Prompt: `reviewers/prompts/index-options-implementation-r02.md`

Sanitized explicit packet files:

- `.collab/claude-2026-11-15-index-options-implementation-r01.md`
- `research/index_options_audit/model.py`
- `research/index_options_audit/ledger.py`
- `research/index_options_audit/holdout.py`
- `research/index_options_audit/tests/test_model.py`
- `research/index_options_audit/tests/test_boundaries.py`

The packet contains frozen review findings, source-independent implementation
and invented tests. It excludes account records, credentials, API keys, broker
identifiers, licensed market data and outcomes. The user explicitly authorized
Claude review through `api.anthropic.com` and waived review limits this session.

## Claude invocation

Command submitted from the consumer repository:

```text
reviewers/claude-review.sh --owner codex sonnet \
  reviewers/prompts/index-options-implementation-r02.md \
  .collab/claude-2026-11-15-index-options-implementation-r02.md \
  .collab/claude-2026-11-15-index-options-implementation-r01.md \
  research/index_options_audit/model.py \
  research/index_options_audit/ledger.py \
  research/index_options_audit/holdout.py \
  research/index_options_audit/tests/test_model.py \
  research/index_options_audit/tests/test_boundaries.py
```

Delegation path:

```text
trading-strategies/reviewers/claude-review.sh
  -> ~/Developer/reviewer-agent-gateway/claude-review.sh
```

The gateway selected `claude-sonnet-5` and Claude completed one turn, but the
wrapper exited **70** after 37 seconds because the required approved verdict
was not the final non-empty line. It reported $0.079728 of subscription usage.
The immutable diagnostic is:

`trading-strategies/.collab/claude-2026-11-15-index-options-implementation-r02.diagnostic.json`

The diagnostic preserves Claude's response and the validation reason. The r02
name is reserved. No accepted review artifact or SHA-256 sidecar was produced,
and the diagnostic response is not treated as an independent completed review.

## Outcome

The correction review remained open after this invocation. A retry must use a
new output name and make the gateway's final-line verdict requirement explicit.
