# Codex review

Owner: claude
Wrapper revision: 39cf9d31fea18b68cecd5ccd2185ab97cb40f842
Requested model: hard
Selected model: gpt-6-sol
Reasoning effort: high
Resolved model(s): not reported by codex exec
CLI version: codex-cli 0.159.3
Blocked tool attempts: 0

**R05-F3 remains open.** V6 requires a later review quote to name the finding and affirm that its specific issue is resolved. `disposition_errors()` checks only that the quote appears in the later artifact. A row citing `"R01-F1 remains open"` would pass.

**R05-F11 remains open.** The wrappers record a revision, but `REVIEWER_ALLOW_DIRTY_WRAPPER` lets them run with uncommitted changes. A failed `git status` also produces an empty result and passes the guard. The `(dirty)` marker is useful, but it does not make the stated refusal true.

The packet does not include the wording of Round-5 conditions C1–C6, so I cannot judge any of them as met:

| Condition | Assessment |
| :--- | :--- |
| C1 | Cannot verify from this packet |
| C2 | Cannot verify from this packet |
| C3 | Cannot verify from this packet |
| C4 | Cannot verify from this packet |
| C5 | Cannot verify from this packet |
| C6 | Cannot verify from this packet |

F1 [blocker]: A clean `VERDICT: ACCEPT` review may correctly contain no findings or conditions, and the wrapper tests produce exactly that output. `record()` nevertheless fails every indexed artifact for which `labeled_items()` is empty. This blocks a normal pilot review.

F2 [blocker]: `done()` accepts a `verified` quote that says the issue remains open. It also accepts a `user-decided` quote merely because its words occur somewhere in Decisions, without checking that it names the finding, accepts its outcome, or has the stated scope. These allow open obligations to close.

F3 [blocker]: `carried <ID>` is unsound as implemented and conflicts with v6’s closure rule. A blocker can point to an unrelated closed minor finding, including one closed by `rejected:`, and then pass `done()`. There is no check that the target restates the same issue or that the eventual evidence resolves the original blocker. Permit carrying only with an explicit, reviewable mapping of the two items and closure evidence that satisfies the original item’s severity and identity.

F4 [major]: `record()` does not require either a standards pin or a wrapper revision. It also silently overwrites duplicate review rounds and disposition IDs while parsing, and `report --write-baseline` exempts every existing `.collab/` file from discovery. These paths can conceal a missing row or unindexed review. Require unique IDs and rounds, require provenance for post-adoption artifacts, and enumerate legacy artifacts explicitly.

F5 [major]: The ratchet checks T2’s total but not each existing T2 file. One file can grow while another shrinks and the total passes. The gateway `PROTOCOL.md` cap is not checked when `record` runs against the pilot repository; agent-memory checking is optional and a missing memory directory counts as empty. These leave stated budgets unenforced.

F6 [major]: A matching `.sha256` proves only that the sidecar matches the current artifact. Editing both passes `record()`, including after commit; the checker does not enforce the protocol’s “never edit” rule. An empty checksum file instead raises an uncaught exception. Check committed artifact immutability and handle malformed sidecars as ordinary failures.

F7 [major]: `transfer()` looks for the words `Inventory:`, `Runtime observation:`, and `Restart sequence:` anywhere in the last handoff block. The supplied test passes with `Inventory: none`, despite v6 requiring a command and untracked and ignored counts. It does not validate observation recency, needed-file locations, or legacy triage.

F8 [minor]: Parsing depends on particular Markdown table headings and inline path syntax; duplicate entries are lost, while some valid local link forms are skipped. `record()` also does not revalidate labeled output, so an artifact and checksum edited together can introduce duplicate labels. These are manageable if the template syntax is made mandatory and malformed input fails explicitly.

The implementation is **not ready for the single-session pilot**. The smallest gate is to fix the clean-ACCEPT failure; enforce identity and affirmative resolution for strict closures; remove the dirty-wrapper bypass from production behavior and fail on Git errors; make review, row, pin, and revision parsing fail closed; enforce the stated budget ratchets; and validate the required handoff fields. Add focused tests for those cases, then assess C1–C6 against their missing Round-5 text.

ATTESTATION: all actionable findings and conditions are labeled.

VERDICT: REJECT