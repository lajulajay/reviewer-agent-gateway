# Reviewer invocation failure report

Date: 2026-10-08
Invoked from: `prediction-markets/kalshi-temperature-bot`
Canonical wrapper repository: `~/Developer/reviewer-agent-gateway` at `e1f29e5`
(the consumer repository's `AGENTS.md` still pins `312a4b7`)
CLI: `agy` 1.3.1
Owner / caller: Claude (workstream `2026-10-08-h5-paper-implementation`;
Gemini was the adversarial reviewer while Codex was at its usage limit)
Review topic: H5 successor paper-trading implementation (Python, SQL migration
050, Next.js dashboard)

## Summary

Two hard-tier Gemini reviews (r02, r06) failed with exit 70. Each failed
because Gemini's **hidden reasoning tokens consumed the output-token limit**.
Both streams still contained a **complete** review ending in a valid verdict
line, which the wrapper discarded as an `ERROR` result. Smaller routine-tier
rounds on compact delta packets (r03, r04, r05, r07) succeeded. A follow-up
(r08) was then refused by the review budget (exit 79), partly because the two
failed hard runs counted toward the daily cap of eight.

## Packet

All packets were sanitized source and diffs. No credentials, `.env` files,
production data or private exports were supplied.

| Round | Tier → model | Packet files | Approx. prompt size |
|---|---|---|---|
| r02 | hard → gemini-3.8-flash-high | `reviewers/packets/h5-paper-implementation-r02-r01-findings-2026-10-08.md`, `…-r02-claude-delta-2026-10-08.diff`, `…-r02-source-2026-10-08.md` | about 215 KB (227k input tokens) |
| r06 | hard → gemini-3.8-flash-high | `reviewers/packets/h5-paper-implementation-r06-r01-findings-2026-10-08.md`, `…-r06-claude-delta-2026-10-08.diff`, `…-r06-source-2026-10-08.md` | about 245 KB (216k input tokens) |

Prompts: `reviewers/prompts/h5-paper-implementation-r02-2026-10-08.md` and
`…-r06-2026-10-08.md`. The r06 prompt explicitly capped the written response
at 2,500 words and asked for no narrated reasoning. That did not help, because
the overflow was reasoning, not visible text.

## Gemini invocation

Command shape, from the consumer repository root:

```text
reviewers/gemini-review.sh --owner claude hard \
  reviewers/prompts/h5-paper-implementation-r06-2026-10-08.md \
  .collab/gemini-2026-10-08-h5-paper-implementation-r06.json \
  reviewers/packets/h5-paper-implementation-r06-r01-findings-2026-10-08.md \
  reviewers/packets/h5-paper-implementation-r06-claude-delta-2026-10-08.diff \
  reviewers/packets/h5-paper-implementation-r06-source-2026-10-08.md
```

The caller ran it in the background without an outer timeout. The wrapper
default `GEMINI_MAX_TIME_SECONDS=600` applied.

Delegation path:

```text
kalshi-temperature-bot/reviewers/gemini-review.sh
  -> ~/Developer/reviewer-agent-gateway/gemini-review.sh
```

Observed failure (both rounds), from the diagnostic JSON:

```text
reason: "Gemini invocation did not succeed"   exit_code: 70
r02: elapsed 531 s; result.status "ERROR"; usage output_tokens 76,410 of which thinking_tokens 70,141
r06: elapsed 501 s; result.status "ERROR"; usage output_tokens 70,072 of which thinking_tokens 64,963
result.error: "Your previous response was cut off because it exceeded the output
token limit\nPlease continue from where you left off, keeping your response
shorter\nRetries remaining: 3"
stderr: "warning: --mode plan has no effect while slash command expansion is disabled."
```

The failing check is `jq -e '.status == "SUCCESS" and (.response | type == "string")'`
(wrapper "did not succeed" branch). agy reports `Retries remaining: 3`, but
the wrapper does not continue or retry, so the agent turn ends as `ERROR`.

Artifacts:

- No `.json` review artifact or `.sha256` was created for r02 or r06.
- Diagnostics (immutable, 0444):
  `.collab/gemini-2026-10-08-h5-paper-implementation-r02.diagnostic.json`
  (279,900 B) and `…-r06.diagnostic.json` (221,330 B).
- Each diagnostic's `stdout` stream contains the final `response` string: a
  complete review with labeled items and a verdict (r02: ACCEPT WITH
  CONDITIONS; r06: REJECT, with `F<n> [severity]` labels and an ATTESTATION
  line). The owner extracted it verbatim to `…-r02.extracted.md` and
  `…-r06.extracted.md`, with SHA-256 sidecars covering both the extraction and
  the diagnostic. `docs-check` correctly does not recognize these as review
  artifacts.
- The r06 response's first finding used the severity `critical`, which is
  outside the contract's `blocker|major|minor`. The substance validator would
  have rejected it even without the token cutoff.
- No repository, database or production mutation occurred.

Secondary content defect: in both r02 and r06, Gemini quoted
`dashboard/src/proxy.ts` code that is **not in the packet**
(`NEXT_PUBLIC_SUPABASE_ANON_KEY`, a bare `NextResponse.redirect(url)` without
cookie copying). It built a finding on that invented code. r07, given the
file again in a small packet, verified the actual code and withdrew the
finding. This looks like degraded fidelity with very large inline packets.

## Budget interaction (exit 79, not a wrapper defect)

After r07, the r08 follow-up was refused:

```text
review budget exceeded: topic 'h5-paper-implementation' has had 7 review rounds
(5 plus 2 gemini escalation) …; 8 gemini reviews already ran in this repository
today (cap 8). Only the user may authorize REVIEW_BUDGET_OVERRIDE=<reason>.
```

The two cut-off hard runs (about 17 minutes and about 140k output tokens
between them) counted toward the cap even though they produced no accepted
artifact. The open dispute went to the user per protocol.

## Outcome and protocol assessment

- Hard-tier Gemini cannot currently review a full-source packet of roughly
  200k+ input tokens. The model spends the output budget on reasoning before
  writing, regardless of prompt instructions.
- Routine-tier rounds with packets under about 40 KB (deltas plus targeted
  context) succeeded every time today (r03, r04, r05, r07), and r07 produced
  a conforming artifact with `R06-F<n> is resolved.` lines.
- The owner's r02 prompt also asked for custom `G<n>` labels. That was an
  owner error against the output contract, and the user ordered the r06
  re-run because of it.

## Recommended fixes

1. In `gemini-review.sh`, when `result.status == "ERROR"` and the error is the
   output-token cutoff, check whether the final `response` string passes
   `reviewer-validate.py`. If it does, either accept it with a recorded
   `truncation_warning`, or fail with a distinct exit code and reason
   (`output_token_cap_with_complete_response`) instead of the generic
   "did not succeed".
2. Add a hard-tier packet-size guard. Refuse, or warn and suggest splitting,
   above an input-token or byte threshold (empirically, 215–245 KB failed and
   40 KB succeeded), before spending quota and budget.
3. Investigate whether agy exposes a thinking-budget or "continue" control
   (`Retries remaining: 3` suggests continuation is possible) that the
   wrapper can enable for review runs.
4. Consider not counting a run against the daily cap when the provider
   returns no accepted artifact through no reviewer-content fault, or record
   it separately, so a capped topic still has an independent round
   available.
5. Silence or address the `--mode plan has no effect` warning so real stderr
   is easier to read.
