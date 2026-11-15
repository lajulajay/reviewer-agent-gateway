# Reviewer invocation failure report

Date: 2026-11-15 (America/New_York)
Invoked from: `trading-strategies`
Canonical wrapper repository: `~/Developer/reviewer-agent-gateway`
Owner / caller: Claude (owner reassigned from Codex by the user; Gemini reviews)
Review topic: Index-options implementation r12 correction review

## Gemini invocation

```text
reviewers/gemini-review.sh --owner claude routine \
  reviewers/prompts/index-options-implementation-r12-gemini.md \
  .collab/gemini-2026-11-15-index-options-implementation-r12.json <packet files>
```

`gemini-model-select.py` resolved `routine` to `gemini-3.6-flash-high` (two
approved releases below `hard_model`). Antigravity CLI 1.5.9 rejected it: the
only Gemini models it offers are Gemini 3.8 Flash High/Medium/Low. The wrapper
exited **70** after 7 seconds; no review was produced. Diagnostic:

`trading-strategies/.collab/gemini-2026-11-15-index-options-implementation-r12.diagnostic.json`

## Root cause

`gemini-model-policy.json` still lists 3.7 and 3.6 Flash as included models.
They are no longer available, so the "two releases down" routine rule has no
valid target.

## Outcome

Retried on the hard tier as r13 (`gemini-3.8-flash-high`), which completed
with ACCEPT. Routine-tier Gemini remains broken until the policy is updated.
