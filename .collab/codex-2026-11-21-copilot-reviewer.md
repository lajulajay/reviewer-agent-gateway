# Codex review

Owner: claude
Task: phase2a
Wrapper revision: 556384f04dbe9e2e1774c41d6dc25a24f8eb51f2
Route: api
Requested model: hard
Selected model: gpt-6.1-sol
Reasoning effort: high
Resolved model(s): gpt-6.1-sol
Usage: {"input_tokens":19064,"output_tokens":8038}
API cost: $0.118508 (ledger committed $0.305652 of $18.0 cap)

F1 [major]: `--owner` is advertised as required but is not enforced. With no owner, `identity` omits it, both eligibility checks accept `owner=None`, and selection can choose Anthropic for Claude-owned work. The artifact also omits `Owner`. Require a nonempty owner in this wrapper before selection; preserve legacy ownerless-artifact handling separately. Add a regression proving an ownerless invocation refuses before calling Copilot.

F2 [major]: Reply completeness is not enforced consistently. Extraction checks only the first sorted chunk’s `chunkCount`. Two chunks with indices 0 and 1 and respective counts 2 and 3 pass, despite the second chunk declaring a missing third chunk; omitting the first chunk’s count bypasses completeness checking altogether. Additionally, selecting the last assistant message with nonempty content can fall back to an earlier complete reply when a newer reply contains only an empty initial chunk. Validate consistent positive counts and complete indices within each reply group, and reject an incomplete final reply rather than falling back to earlier text. Test both inconsistent counts and a newer empty, incomplete reply.

F3 [major]: Missing model identities can bypass the resolved-model guarantee. The `resolved` expression silently drops assistant messages without `.data.model`. A stream containing an earlier empty message labeled with the selected model, followed by a substantive final reply with no model field, resolves to the selected model and passes. Thus the accepted review’s vendor is unknown. Require explicit, consistent model evidence for every assistant reply group, including the accepted final reply, and reject missing identity with a spent-attempt diagnostic. Add a mixed labeled/unlabeled-reply regression.

F4 [major]: Not every post-invocation failure produces a spent-attempt diagnostic. For example, `checks="$(python3 .../reviewer-claims.py ...)"` is unguarded: if that helper fails, `set -e` exits with its raw status, cleanup deletes the stream, and neither artifact nor diagnostic remains. The spent call is then invisible to budget accounting and the same name can be reused. Guard post-invocation operations with `fail 70`, or add a fallback error handler backed by a durable invocation record. Test an injected helper/finalization failure, not just CLI failures.

F5 [major]: Successful-result validation is existential rather than authoritative. `any(... result ... exitCode == 0)` accepts a stream containing both a successful result and a later failed result, provided the CLI process exits zero. Require the expected result cardinality and a successful terminal result, rejecting contradictory or unsuccessful results. Add a success-then-failure stream case.

The shown budget changes correctly add Copilot to provider accounting and classify its requested `hard` tier as a hard round. The docs-check change also passes `Selected model` in the correct argument position. These integrations need end-to-end regression coverage beyond metadata extraction.

C1: Add Copilot budget/docs-check integration tests demonstrating that accepted reviews and exit-70/74 diagnostics consume the appropriate provider/topic/hard budgets; preflight failures do not; a Copilot hard round prevents another hard round across providers; and existing artifact/diagnostic names cannot be reused. The added smoke cases check individual exit codes but do not assert these accounting transitions.

C2: Establish isolation from arbitrary user-configured MCP servers. The invocation disables built-ins and four named servers but inherits the user’s configuration environment. Test an additional, differently named user-configured server and demonstrate that it cannot start or connect before stream validation; otherwise isolate MCP configuration or use a supported disable-all mechanism. Rejecting an enabled-server event afterward does not undo startup activity.

C3: Record sponsor approval of the shipped tier/vendor/model policy before merge; the policy currently explicitly marks that decision as pending.

ATTESTATION: all actionable findings and conditions are labeled.
VERDICT: REJECT