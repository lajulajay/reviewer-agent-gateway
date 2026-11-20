# Codex review

Owner: claude
Wrapper revision: d96f4964633a533a23ea47771c3f2fe1a3ad3221
Route: api
Requested model: hard
Selected model: gpt-6.1-sol
Reasoning effort: high
Resolved model(s): gpt-6.1-sol
Usage: {"input_tokens":8416,"output_tokens":5995}
API cost: $0.076782 (ledger $0.076929 of $18.0 cap)

### 1. Key confidentiality and destination

F1 [blocker]: `api-call.py` uses urllib’s default redirect handling. For redirects such as 301/302/303, it can forward the explicitly supplied `Authorization` header to another host, including an HTTP destination. Checking only the initial URL’s `https://` prefix does not confine the key to the configured endpoint. Disable redirects or strictly enforce the approved HTTPS destination on every hop.

F2 [major]: The README’s provisioning command exposes the key in argv: `security ... -w "$k"`. Suppressing terminal echo and shell history does not prevent process-argument inspection. Provision long keys through a Keychain API/helper that does not receive the secret through argv or environment.

F3 [major]: Error handling does not guarantee secret-free diagnostics. Raw HTTP error bodies and exception strings reach stderr; transport exception strings also enter ledger notes. Additionally, a stored key containing an embedded invalid header character can cause an uncaught header-validation exception containing the complete Authorization value. Keep errors structured and sanitized, redact the loaded secret at diagnostic boundaries, and reject malformed key values without echoing them.

### 2. Spend cap and ledger

F4 [blocker]: `len(text) // 3 + 1` is an estimate, not an input-token upper bound. Unicode, code and other inputs can tokenize substantially above it, and request/message framing is omitted. A call can therefore pass the cap check while its permitted cost exceeds the remaining balance. Use a model-appropriate guaranteed bound, including billable framing, rather than an average characters-per-token assumption.

F5 [blocker]: There is no atomic, durable reservation before sending. Concurrent calls can all read the same balance and pass independently. A request can also spend without any entry if the process dies, JSON decoding or response parsing fails, reading an HTTP error body fails, or the eventual ledger write fails. Reserve the full bounded cost under a ledger lock before transmission; retain that reservation through crashes and ambiguous failures, then reconcile authoritative usage.

F6 [blocker]: Missing-usage and failure accounting undercharges. `record(..., worst_case=True)` substitutes zero for unknown input tokens rather than the preflight input allowance, so missing usage, transport failures and HTTP failures do not receive the advertised worst-case charge. Every HTTP 4xx is also assigned zero without establishing that it necessarily represents an unbilled rejection; an intermediary could return an error after forwarding work. Reconcile against a genuine full-cost reservation, releasing it only when non-billing is established.

F7 [major]: Accounting inputs and state are insufficiently constrained. Non-finite caps, negative prices and negative/non-finite ledger costs are accepted; NaN can defeat the cap comparison. Six-decimal rounding can also round recorded charges downward. Separately, `REVIEWER_API_STATE_DIR` can select an empty or repository-local ledger, resetting the effective allowance for the same account. Validate finite, appropriately positive values and ledger records, use conservatively rounded monetary units, and bind production accounting to an approved persistent location.

C1: Confirm the configured models, current first-party prices, and each API’s output-limit/usage semantics before enabling these policies. In particular, verify that all billable reasoning tokens fall within the configured output ceiling and reported completion/output usage. The Moonshot policy explicitly records unconfirmed third-party pricing; the diff alone cannot establish those billing guarantees.

### 3. Exit codes and Kimi diagnostics

F8 [major]: Invocation-state reporting and exit normalization are incomplete. `api_route` sets `model_invocation_started=1` before Python preflight; errors such as an invalid timeout value or unreadable/corrupt ledger can exit Python with 1 before `urlopen`, yet the wrapper reports 70 and leaves the invocation flag set. Conversely, unguarded post-call commands such as the claims assignment, artifact writes, `chmod`, `mv` or checksum generation can terminate under `set -e` with a status other than 70. Add explicit send-boundary signaling and consistently classify all failures according to whether transmission may have begun. As written, Kimi’s `model_invocation_began` cannot remain reliably truthful.

### 4. Reply handling and shared checks

F9 [major]: Nonempty text is accepted without checking completion status. OpenAI `incomplete`/`failed` responses and chat responses ending with `length`, `content_filter` or another non-success reason can become successful reviews. Tool detection is also incomplete: chat parsing examines only the first choice and only `tool_calls`, ignoring legacy `function_call` and tool-related finish reasons without populated tool data. Require a complete successful response, enforce or inspect every choice, and reject every tool-bearing form before accepting text.

The request construction offers no tools, and whitespace-only replies are rejected. The shown API wrapper retains the review-budget call, prompt/packet safety checks, appended output contract, substance/claims processing and checksum creation. The dirty-gateway check precedes the new branch; the earlier vendor-independence check is accepted as supplied context. Full parity with subscription checks outside the displayed context cannot be established from this diff alone.

### 5. Tests and documentation

F10 [major]: The tests do not substantiate the important guarantees. `urlopen` and key retrieval are mocked, so redirect/header leakage and Keychain exception behavior are untested. The missing-usage assertion checks only the output allowance, allowing the missing-input bug to pass; the 4xx test codifies unconditional zero charging. There are no supplied tests for concurrent reservations, crashes, malformed responses, failed ledger writes, incomplete replies, alternate tool forms or truthful invocation-state reporting. The wrapper smoke test explicitly forces subscription mode, leaving the new API branch’s shared-check parity and post-send exit handling untested. Add API-path integration tests and adversarial accounting/security cases before relying on this route.

F11 [minor]: README and PROTOCOL overstate the implementation’s guarantees: the input allowance is not a worst case, missing usage is not charged at the full bound, calls can spend without ledger entries, and the ledger is not necessarily outside repositories. README’s “70 means the request was sent” is also inaccurate; the intended distinction is that it may have been sent. PROTOCOL still describes `active_reviewers` as an active-subscription roster despite enabling API-only reviewers. Align these statements with the corrected implementation and roster semantics.

ATTESTATION: all actionable findings and conditions are labeled.
VERDICT: REJECT