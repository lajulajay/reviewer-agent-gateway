# Follow-up: API route hardening after r01 (gateway commit 961b844)

Owner: Claude. Reviewer: Codex via the OpenAI API. Read-only; review only the
attached delta (d96f496..961b844). No tools, repository access, commit or push.

Your r01 returned REJECT. The owner's response to each item:

- R01-F1: urllib redirects refused by a handler that raises; the reply's host
  must equal the configured host or the call fails (reservation kept).
- R01-F2: new keychain-store.py reads with getpass and writes through
  SecKeychainAddGenericPassword via ctypes; deletion of an old item uses only
  service/account names. README no longer suggests `-w "$k"`.
- R01-F3: every emitted message passes through redact(); key validated as
  printable ASCII without echo; unexpected exceptions print a redacted one-line
  message and no traceback; transport errors report only the exception class.
- R01-F4: bound = len(UTF-8 JSON body) + 1,024 framing tokens as input, plus
  max_output_tokens, at list price, rounded up.
- R01-F5: under flock, committed = settled + open reservations; the bound is
  appended (fsync) as a reservation before the marker and the send; settled
  afterwards. A crash leaves the reservation.
- R01-F6: missing usage settles at the full bound; only HTTP 400/401/403/404/422
  release to zero; 429, 5xx, transport, parse errors and wrong host keep it.
- R01-F7: finite positive policy numbers; integer micro-dollars rounded up;
  malformed or negative ledger lines refuse all calls; the state-dir
  environment override was removed.
- R01-F8: api-call.py touches a marker immediately before sending. The wrapper
  sets model_invocation_started only if the marker exists; without it, exits
  are 64/78/79 (anything else maps to 78); with it, every failure is 70.
  Post-send artifact steps are guarded with `|| fail 70`.
- R01-F9: OpenAI requires status "completed"; chat requires exactly one choice
  with finish_reason "stop"; any tool item, non-empty tool_calls, present
  function_call, or tool finish reason fails.
- R01-F10: 16 unit tests (redirect, foreign host, redaction, malformed key,
  bound per byte, cap with open reservations, 4-thread concurrency, missing
  usage, transport, 4xx/429/5xx, malformed ledger and numbers, incomplete and
  tool replies) and wrapper smoke cases on the API branch (marker-driven exits,
  Kimi began flag, output naming, vendor rule).
- R01-F11: README and PROTOCOL rewritten to match.
- R01-C1: left to the sponsor (first-party prices and reasoning-token semantics).

For each of R01-F1 to R01-F11, reply with exactly the line `R01-Fn is resolved.`
if the delta resolves it, or a new labeled finding explaining what remains.
Do not reopen settled design choices. Label new findings `F1 [blocker|major|minor]: ...`
and conditions `C1: ...`. Include `ATTESTATION: all actionable findings and conditions are labeled.`
The last non-empty line must be exactly one of `VERDICT: ACCEPT`,
`VERDICT: ACCEPT WITH CONDITIONS` or `VERDICT: REJECT`.
