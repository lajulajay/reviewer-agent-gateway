Review gateway commit d5f4ecf, which changes how the Gemini reviewer wrapper
handles output-token cutoffs and tightens the review validator. Owner: Claude.
You are the primary reviewer.

Background (failure report supplied): on 2026-10-08 two hard-tier Gemini
reviews (216k-227k input tokens) failed with exit 70 because hidden reasoning
used the output-token limit; agy returned `status: "ERROR"` with the
`response` it had written. One response was a complete, valid review; the
other stopped before its verdict. The validator also passed a review whose
`F1 [critical]` and `F2 [critical]` findings it did not recognize. Gemini
cited an invented file through a `file://` link into its empty sandbox.

User decision (2026-10-08): implement the validator fix, keep a cut-off
review only if it validates, add a hard-tier packet-size guard, drop
`--mode plan`, and add the `file://` note. Cut-off runs keep counting
against the review budget because they used real quota.

Packets: `d5f4ecf-gateway.diff` (wrapper, validator, claims check, budget,
docs, workstream), `d5f4ecf-tests.diff` (provider-free tests; both suites
pass), and the failure report.

Questions:
1. Can the cut-off path keep an incomplete or invalid review, or accept an
   ERROR status that is not an output-token cutoff?
2. Can the hard-tier size guard be bypassed or misfire (which model counts as
   hard; refusal ordering relative to the budget check and quota preflight)?
3. Does the severity check refuse anything legitimate (status lines such as
   `R03-F1 is resolved.`, emphasis, conditions) or miss unknown labels?
4. Could the `file://` note be misleading?
5. Do README.md and PROTOCOL.md match the code?

You have no tools; review only the text supplied.
