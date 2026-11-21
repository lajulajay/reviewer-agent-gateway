# Kimi review

Owner: claude
Author models: claude-opus-5-5
Wrapper revision: cd0ad50f525b00e0ba6d48a73cf082614f6b929b
Route: api
Requested model: hard
Selected model: kimi-k3.1-pro
Reasoning effort: not set
Resolved model(s): kimi-k3.1-pro
Usage: {"input_tokens":13105,"output_tokens":23608}
API cost: $0.26229 (ledger committed $1.445504 of $10.0 cap)

F1 [major]: `auto` requests have incorrect artifact and lifecycle bookkeeping. PROTOCOL says an `auto-` output is a template and the artifact uses the selected provider’s prefix, but `create`, `run`, and `list` check only the literal `auto-...` output and diagnostic. After a successful automatic review, the result can therefore record `"artifact": null`, the request remains visibly pending, and a rerun does not see the real artifact or diagnostic. Existing provider-prefixed artifacts likewise do not make `create` refuse the request. This can produce repeated dispatcher invocations and inaccurate committed results.
F2 [major]: Result-file handling is unsafe across preflight failures and pre-existing results. A wrapper exit such as 69 or 78 can produce neither artifact nor diagnostic, yet `run` writes `.result.json` and `list` still calls the request pending. A subsequent run invokes the wrapper again and only then opens the old result with mode `"x"`; the resulting `FileExistsError` is reported as exit 78, potentially after a successful review was sent, while the stale result remains. Independently, pre-creating the result file does not prevent the wrapper call, so recording can be deliberately made to fail after transmission.
F3 [major]: The request-name check validates only `Path(body["output"]).name`. An edited request can retain that basename while changing the output to an absolute path or a `..` path in another repository’s `.collab`; `run` then performs its output/diagnostic existence checks and bookkeeping against that substituted location. `command()` also does not reapply create’s repository/packet-root confinement. The normal wrapper is a backstop, but the request tool’s own location and immutability guarantees are already bypassed. Moreover, hashes stored in the same editable request provide no tamper evidence when an editor replaces both an entry and its hash.
F4 [minor]: The completed-request test assertions are ineffective. A pending list line contains `t5-r08.md.request.json:` and later ends in `t5-r08.md`, but never contains the asserted substring `t5-r08.md:`. Consequently both `assertNotIn("t5-r08.md:", ...)` checks pass even if the completed request is still listed.
F5 [minor]: “By CLI or API” in the destination rule can be read in isolation as approving an ad-hoc direct API transmission rather than only approving the destination vendor. The user decision should explicitly waive per-task destination approval while preserving the gateway wrapper, budget, packet-safety, and user-only override requirements. README’s “someone else runs it” should likewise match PROTOCOL’s narrower “the user, or an agent they ask.”
C1: Either remove `auto` from review-request support and its usage documentation, or make create/run/list/result provider-prefix-aware. Add tests where the automatic wrapper actually writes a provider-prefixed artifact and, separately, a provider-prefixed diagnostic; verify accurate results, pending-list removal, and rerun refusal.
C2: Define coherent retry semantics and establish the run/result state before invoking the wrapper. Either refuse an existing result and stop listing that request as pending, or support uniquely recorded attempts; in either case, do not send when the outcome cannot be recorded. Test a no-artifact/no-diagnostic preflight failure followed by a retry and a pre-existing result file.
C3: At load/run, validate the request schema and require the canonical relative output `.collab/<exact request basename>`, resolving beneath the request repository’s `.collab`; reject same-basename absolute and traversal edits before any wrapper call. Reapply packet confinement, and either authenticate the committed request if tamper evidence is intended or document that its embedded hashes do not authenticate edits. Add these tamper cases to the tests.
C4: Strengthen the list assertions to match the complete request line or assert absence of `t5-r08.md` altogether, so the normal artifact and diagnostic cases genuinely prove removal from pending output.
C5: Tighten the PROTOCOL/README wording to scope the approval to registered gateway CLI/API routes and user-delegated runners, without changing the otherwise rule-preserving trims.
ATTESTATION: all actionable findings and conditions are labeled.
VERDICT: ACCEPT WITH CONDITIONS