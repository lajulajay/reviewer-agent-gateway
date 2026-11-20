# Codex review

Owner: claude
Wrapper revision: 961b844d2b438378d46ee832afda28fe9ed588a6
Route: api
Requested model: routine
Selected model: gpt-6.1-terra
Reasoning effort: medium
Resolved model(s): gpt-6.1-terra
Usage: {"input_tokens":16061,"output_tokens":3390}
API cost: $0.033011 (ledger committed $0.10994 of $18.0 cap)

R01-F1 is resolved.

F1 [major]: R01-F2: `getpass.getpass()` can fall back to echoed input when terminal echo cannot be disabled. Refuse that fallback rather than accepting a key that may be exposed.

F2 [major]: R01-F3: Redaction covers printed errors, but model text and metadata are written unredacted to artifacts. Also, a JSON-escaped key in an HTTP error body can evade exact-string replacement. Avoid emitting untrusted error bodies and redact artifact fields.

R01-F4 is resolved.

F3 [major]: R01-F5: The ledger file is fsynced, but newly created ledger and state-directory entries are not directory-fsynced. A system crash can lose the reservation’s pathname after a request is sent, allowing later calls to overlook it.

F4 [major]: R01-F6 and R01-F11: Usage is settled before reply validation. For example, a completed response with empty output and zero usage releases the reservation, then fails for missing text. This contradicts the documented full reservation for malformed replies. Validate the reply before settling failures.

F5 [major]: R01-F7: `committed()` converts ledger amounts with `int()`, so a negative fractional amount such as `-0.5` becomes zero rather than refusing the ledger. Fractional positive amounts can likewise be understated. Require non-negative integer amounts without coercion.

F6 [major]: R01-F8: The prompt assembly group checks only its final command, so an earlier failed `cat` can still lead to sending an incomplete packet. The artifact group similarly masks failed intermediate commands, including `jq` substitutions. Check each step explicitly.

F7 [minor]: R01-F8: A zero exit without a marker maps to 70, contrary to the stated rule that every unmarked exit maps to 64, 78, or 79.

F8 [minor]: R01-F9: `msg.get("function_call") is not None` accepts a present `function_call: null`, although the specified rule rejects a present field.

R01-F10 is resolved.

C1: The sponsor must confirm the configured first-party prices and reasoning-token ceiling semantics for both APIs.

ATTESTATION: all actionable findings and conditions are labeled.
VERDICT: REJECT