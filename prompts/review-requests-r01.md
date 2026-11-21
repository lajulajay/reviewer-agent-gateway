# Review: review requests and packet-destination rule (gateway, based on cd0ad50)

Owner: Claude. Reviewer: Kimi via the Moonshot API. Read-only; review only
the attached material. No tools.

Background: a GitHub Copilot sub-agent (owner of a trading-strategies task)
refused to run kimi-review.sh because it would send repository source to
Moonshot's API, citing a "data-sharing restriction" found in no written
instruction; a sponsor approval did not change its answer. The gateway README
also still said Kimi "does not use ... direct Moonshot API configuration",
which became false when the API route was added.

Change (attached diff and full review-request.py):
1. README: Kimi/Codex routes described accurately; a "Review requests"
   section.
2. PROTOCOL: "Where packets may go" (registered reviewer vendors are approved
   destinations within the packet rules, user decision 2026-11-20) and
   "Review requests"; wording trimmed elsewhere to stay under the 12,000
   character budget (no rule removed).
3. review-request.py: `create` applies the identity/vendor rule, refuses an
   existing output or diagnostic, hashes prompt and packets, and writes
   reviewers/requests/<output>.request.json without sending anything; `run`
   re-verifies hashes and output absence, drops any ambient
   REVIEW_BUDGET_OVERRIDE, applies a request's override only with
   --apply-override, and calls the normal wrapper from the repo root so every
   gateway check still applies; `list` shows pending requests. 9 tests.

Check: can a request bypass any gateway control (vendor rule, budget and its
user-only override, packet safety, output naming, immutability), e.g. by
editing the request file, swapping files after create, path tricks, or the
runner's environment? Is the PROTOCOL rule correctly scoped? Are the trims
faithful? Are the tests adequate?
Label findings `F1 [blocker|major|minor]: ...` and conditions `C1: ...`.
Include `ATTESTATION: all actionable findings and conditions are labeled.`
The last non-empty line must be exactly one of `VERDICT: ACCEPT`,
`VERDICT: ACCEPT WITH CONDITIONS` or `VERDICT: REJECT`.
