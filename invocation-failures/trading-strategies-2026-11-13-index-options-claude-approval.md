# Reviewer invocation failure report

Date: 2026-11-13 (America/New_York)
Invoked from: `trading-strategies`
Canonical wrapper repository: `~/Developer/reviewer-agent-gateway`
Owner / caller: Codex
Review topic: Index-options research planning

## Packet

Prompt: `reviewers/prompts/index-options-plan-r01.md`

Sanitized explicit packet files:

- `workstreams/2026-11-13-index-options-research.md`
- `research/index-options/README.md`
- `research/index-options/DATA_INTERFACE.md`
- `reviewers/packets/index-options-plan-context-r01.md`

The packet contains private repository planning material. It excludes
credentials, broker identifiers, licensed raw market data and unsealed results.
Intended external destination: `api.anthropic.com` through the Claude gateway.

## Claude invocation

Command submitted from the consumer repository:

```text
reviewers/claude-review.sh --owner codex opus \
  reviewers/prompts/index-options-plan-r01.md \
  .collab/claude-2026-11-13-index-options-plan-r01.md \
  workstreams/2026-11-13-index-options-research.md \
  research/index-options/README.md \
  research/index-options/DATA_INTERFACE.md \
  reviewers/packets/index-options-plan-context-r01.md
```

Delegation path:

```text
trading-strategies/reviewers/claude-review.sh
  -> ~/Developer/reviewer-agent-gateway/claude-review.sh
```

Budget preflight returned `0 0` for this topic and provider. The first
attempt, from the staging session, was blocked by automatic approval review
before the wrapper ran. After the user asked to attempt the review again, the
same command was submitted from the installed repository and automatic
approval review rejected it before process creation. The reported reason was:

```text
This sends private repository planning materials to the untrusted external
api.anthropic.com destination; the user requested a Claude review but did not
specifically authorize this exact sensitive payload and destination.
```

The rejection also instructed the caller not to bypass it through a workaround
or indirect execution. The tool reported a `CreateProcess` rejection, not a
shell exit code. No provider call, review artifact, SHA-256 sidecar, gateway
diagnostic, or reviewer usage record was produced. No alternate route was
attempted.

## Authorized retry and authentication failure

After the user explicitly authorized transmission to `api.anthropic.com`, the
same bounded command was allowed to run. The gateway selected
`claude-opus-5-5` and exited 70 after approximately two seconds. Its immutable
diagnostic is:

`trading-strategies/.collab/claude-2026-11-13-index-options-plan-r01.diagnostic.json`

The diagnostic reports `reason: "Claude invocation failed"`. Claude's JSON
stdout reports `terminal_reason: "api_error"`, `total_cost_usd: 0`, zero input
and output tokens, and:

```text
Failed to authenticate: OAuth session expired and could not be refreshed
```

The independent local `claude auth status` check exited 1 and reported
`loggedIn: false`, `authMethod: none`, `apiProvider: firstParty`. The user must
restore the Claude subscription login before another gateway review can run.
Per the gateway protocol, the failed r01 name and diagnostic remain reserved;
any later retry requires a new r02 artifact name. The diagnostic was not
edited or deleted.

## Outcome of initial attempts

No independent review was completed by those attempts. The owner recorded the approval rejections
and auth failure in the `trading-strategies` workstream. No requested review
artifact or SHA-256 sidecar was produced, and no alternate provider or paid
API-key route was used.

## Later r04 packet approval rejection

After successful r02 Sonnet and r03 Opus reviews, the user specified IBKR as
the intended broker. The owner prepared a targeted r04 Sonnet check of the
IBKR-aware plan and remaining wording fixes. Budget preflight returned `3 3`,
and the r04 path was unused. The command submitted from `trading-strategies`
was:

```text
reviewers/claude-review.sh --owner codex sonnet \
  reviewers/prompts/index-options-plan-r04.md \
  .collab/claude-2026-11-13-index-options-plan-r04.md \
  .collab/claude-2026-11-13-index-options-plan-r02.md \
  .collab/claude-2026-11-13-index-options-plan-r03.md \
  workstreams/2026-11-13-index-options-research.md \
  research/index-options/README.md HYPOTHESES.md
```

Automatic approval review rejected the process before the gateway ran:

```text
This sends an expanded private packet, including HYPOTHESES.md and prior review
artifacts, to api.anthropic.com; the user authorized Claude review and the
destination but did not specifically approve this exact expanded payload.
```

The rejection instructed the caller not to bypass it through a workaround or
indirect execution. No r04 review, checksum, diagnostic, provider usage or
shell exit code was produced. The user must explicitly authorize the expanded
r04 file list and destination before that call is retried.

The user subsequently approved that exact expanded packet. The same r04
command then completed successfully and produced an immutable review and
matching SHA-256 sidecar in `trading-strategies/.collab/`. The earlier approval
rejection remains an invocation failure; it produced no gateway artifact or
provider usage.
