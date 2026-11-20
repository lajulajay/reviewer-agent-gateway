# Review: spend-capped API route for Codex and Kimi (gateway commit d96f496)

Owner: Claude. Reviewer: Codex via the OpenAI API (independent vendor; this
review is also the first live use of the route). Read-only; review only the
attached diff. No tools, repository access, commit or push.

Context: Codex and Kimi subscriptions lapsed; the sponsor has prepaid API
credit (OpenAI $20, Kimi $11, auto-recharge off) and chose gateway caps of
$18 and $10. Keys are in the macOS Keychain. Earlier in the same branch,
`agents.py` added a vendor-independence check that runs before this code.

Answer only:

1. Can the API key leak (argv, environment, stderr, diagnostics, ledger,
   artifact, exception text) or be sent anywhere but the configured https
   endpoint?
2. Is the spend cap sound: is the pre-call worst case really an upper bound
   (character-based token estimate, reasoning tokens, missing usage, HTTP
   and transport failures, concurrent calls racing the ledger)? Can any path
   spend without a ledger entry?
3. Are exit codes right for automatic failover (78/79/64 only before a
   request is sent; 70 once it may have reached the model), and does the
   Kimi diagnostic's `model_invocation_began` stay truthful?
4. Is the reply handling tool-free and complete (tool items, truncated or
   incomplete responses, empty text), and does `api-route.sh` keep every
   shared check of the subscription path (budget, packet safety, output
   contract, checksum, dirty-gateway provenance)?
5. Do the tests detect regressions in these rules? Are README and PROTOCOL
   accurate?

Label new findings `F1 [blocker|major|minor]: ...` and conditions `C1: ...`.
Include `ATTESTATION: all actionable findings and conditions are labeled.`
The last non-empty line must be exactly one of `VERDICT: ACCEPT`,
`VERDICT: ACCEPT WITH CONDITIONS` or `VERDICT: REJECT`.
