# Codex review

Owner: claude
Task: phase2a
Wrapper revision: 556384f04dbe9e2e1774c41d6dc25a24f8eb51f2
Route: api
Requested model: routine
Selected model: gpt-6.1-terra
Reasoning effort: medium
Resolved model(s): gpt-6.1-terra
Usage: {"input_tokens":12969,"output_tokens":1298}
API cost: $0.019459 (ledger committed $0.599798 of $18.0 cap)

R01-F2 is resolved.
The extractor requires a nonempty final reply key, isolates its trailing run, rejects earlier reuse and duplicate message IDs, and checks chunk completeness within that run. The smoke cases cover missing IDs and separated key reuse.

R01-F3 is resolved.
Both model checks precede extraction. The incomplete-reply smoke case with an unlabeled chunk expects exit 74.

R01-F4 remains open: interruption during publication can leave an orphan checksum.
The normal failure handler removes the checksum when the artifact is absent, but the signal handler calls `fail` directly, and the EXIT cleanup removes only staging files.

R02-F1 is resolved.
The ownerless smoke case removes the spy file before invocation and asserts that it remains absent afterward.

F1 [major]: Concurrent calls for the same output use identical staging paths. One call can hash its staged artifact, the other can replace that stage, and the first can then publish the replacement with the original hash.

F2 [minor]: A signal after the checksum rename but before the artifact rename bypasses the publication failure handler, leaving the checksum alongside the spent diagnostic. Add interrupted-publication cleanup and a smoke case for that window.

ATTESTATION: all actionable findings and conditions are labeled.
VERDICT: REJECT