# Copilot review

Owner: claude
Task: phase2b
Wrapper revision: 123d559a4c2e5a672540f840039407e25e68bb27
Requested model: routine
Selected model: gpt-6-luna
Reviewer vendor: openai
Resolved model(s): gpt-6-luna
CLI version: GitHub Copilot CLI 1.0.114.
Tool events: 0
Usage: {"input":{"tokenCount":3},"cache_read":{"tokenCount":0},"cache_write":{"tokenCount":28161},"output":{"tokenCount":7945}}
AI credits: 0.749 AI credits (cap 30)

F1 [major]: **An agent can self-grant a pool and bypass the repository daily cap.** `review-ticket.py: pool()` treats any matching `- YYYY-MM-DD, user, ... Review pool: ...` text in a workstream’s Decisions section as authorization; `issue()` does not verify that the entry was actually written or approved by a user. An agent can add a fabricated user entry, issue a ticket pointing to that workstream, and have pooled rounds excluded from the repository cap. This contradicts the requirement that pool lines come from user decisions.

F2 [major]: **A changed symlink can escape ticket packet scope.** `issue()` resolves scope paths, but `check()` resolves them again and only checks that resolved scopes remain under the repository or packet root when the ticket has a `packet_root`. With no packet root, replacing an in-repository scope directory with a symlink to an external directory lets packets under that target pass `_within()`. Recheck containment under the repository even when no packet root is set.

F3 [minor]: **Escalation can treat an unknown prior Copilot vendor as uninvolved.** `review-budget.py: round_vendors()` returns `{"unknown"}` when a Copilot artifact has no readable vendor, while the substitute check only refuses vendors present in `involved`. Any selected vendor therefore passes despite the artifact not establishing which vendor reviewed the topic. Refuse substitution when a prior round’s vendor cannot be determined.

ATTESTATION: all actionable findings and conditions are labeled.
VERDICT: REJECT
