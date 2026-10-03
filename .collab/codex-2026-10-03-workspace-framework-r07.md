# Codex review

Owner: claude
Wrapper revision: d2a4aeff131691c6f9f9f62cb9875381859ce454
Requested model: hard
Selected model: gpt-6-sol
Reasoning effort: high
Resolved model(s): not reported by codex exec
CLI version: codex-cli 0.159.3
Blocked tool attempts: 0

## Part A — item status

R01-F1 is resolved.
R01-F2 is resolved.
R01-F3 is resolved.
R01-F4 remains open: transfer can pass while an indexed review artifact exists only as an untracked local file.
R01-F5 remains open: the checker does not establish that a quoted user decision is authentic, scoped, and still applicable.
R01-F6 remains open: weak verification and carried dispositions can still close an unresolved blocker.
R01-F7 is resolved.
R01-F8 remains open: tracked reviews can be classified as legacy without being discovered and reconciled.
R01-F9 is resolved.
R01-F10 is resolved.
R01-F11 remains open: transfer accepts an unverified runtime observation, including a future timestamp.

R02-F1 is resolved.
R02-F2 is resolved.
R02-F3 is resolved.
R02-F4 remains open: transfer does not compare the recorded inventory counts with the working tree.
R02-F5 remains open: `user-decided` closure checks neither the decision’s scope nor supersession.
R02-F6 remains open: a blocker can still close through evidence that does not establish its resolution.
R02-F7 is resolved.
R02-F8 remains open: the legacy exemption can hide a tracked review from reconciliation.
R02-F9 is resolved.
R02-F10 is resolved.
R02-F11 remains open: the runtime observation is not checked for an actual command and result or for a future timestamp.
R02-F12 is resolved.
R02-F13 is resolved.
R02-F14 remains open: baseline creation can exempt every tracked `.collab/` file, including an unindexed review.
R02-F15 is resolved.
R02-F16 is resolved.
R02-F17 is resolved.
R02-F18 is resolved.

R03-F1 is resolved.
R03-F2 is resolved.
R03-F3 remains open: disposition evidence can name an item without affirming its specific resolution or authorized outcome.
R03-F4 remains open: `done` can accept a nominally final disposition that leaves its issue unresolved.
R03-F5 remains open: the broad legacy exemption permits an unindexed review to escape the first `done` gate.
R03-F6 is resolved.
R03-F7 is resolved.
R03-F8 is resolved.
R03-F9 remains open: agent-memory measurement is optional when the baseline is written.
R03-F10 remains open: an untracked artifact needed by the next owner can pass transfer and disappear from the next checkout.
R03-F11 is resolved.

R04-F1 is resolved.
R04-F2 is resolved.
R04-F3 remains open: a quote that names an ID can pass without affirming that its specific issue was resolved.
R04-F4 is resolved.
R04-F5 remains open: the legacy exemption undermines complete artifact discovery and reconciliation.
R04-F6 is resolved.
R04-F7 is resolved.
R04-F8 is resolved.
R04-F9 remains open: omitting agent memory from baseline creation leaves its aggregate ratchet unenforced.
R04-F10 remains open: transfer accepts stated inventory counts without checking them.
R04-F11 is resolved.
R04-F12 is resolved.

R05-F1 is resolved.
R05-F2 is resolved.
R05-F3 remains open: the new word filter rejects some open-status quotes but does not require an affirmative finding-specific resolution.
R05-F4 is resolved.
R05-F5 remains open: a baseline can classify any tracked `.collab/` file as legacy and exempt it from discovery.
R05-F6 is resolved.
R05-F7 is resolved.
R05-F8 is resolved.
R05-F9 remains open: the agent-cache total is unchecked when baseline creation omits memory.
R05-F10 remains open: the recorded inventory is not checked against the files present at transfer.
R05-F11 is resolved.
R05-F12 is resolved.
R05-F13 remains open: the effective agent-cache limit is absent if the optional memory baseline is omitted.
R05-F14 is resolved.
R05-F15 is resolved.

R02-C1 remains open: baseline exemption and untracked artifacts break complete capture-to-index tracing.
R02-C2 remains open: blocker closure can pass without evidence accepting or resolving the specific issue.
R02-C3 remains open: legacy triage is not reliable when the baseline can exempt unindexed reviews.
R02-C4 is resolved.
R02-C5 remains open: transfer can leave needed review evidence uncommitted and accepts unchecked inventory claims.
R02-C6 is resolved.

R03-C1 remains open: the legacy exemption and untracked-artifact path defeat complete review tracing.
R03-C2 remains open: closure does not establish an effective, specifically authorized resolution.
R03-C3 remains open: the legacy reconciliation gate can miss exempted reviews.
R03-C4 is resolved.
R03-C5 remains open: transfer does not verify inventory accuracy or the substance of runtime observations.
R03-C6 is resolved.

R04-C1 remains open: a tracked but unindexed review can be exempted as legacy.
R04-C2 remains open: verification can pass on a quote that does not affirm the specific issue’s resolution.
R04-C3 remains open: legacy reconciliation can miss reviews classified by the broad baseline.
R04-C4 is resolved.
R04-C5 remains open: transfer does not validate its inventory counts against the working tree.
R04-C6 is resolved.

R05-C1 remains open: the baseline can exempt an unindexed review artifact from discovery.
R05-C2 remains open: the verified-quote check does not require affirmative resolution.
R05-C3 remains open: broad legacy exemption makes the reconciliation gate incomplete.
R05-C4 is resolved.
R05-C5 remains open: needed local evidence can remain untracked despite a passing transfer.
R05-C6 is resolved.

R06-F1 is resolved.
R06-F2 remains open: `verified` lacks an affirmative-resolution test and `user-decided` lacks outcome, scope, and source checks.
R06-F3 remains open: a textual citation permits a carried chain to end in evidence about a different issue.
R06-F4 remains open: a pin is required only when a baseline exists, while baseline creation exempts all tracked `.collab/` files.
R06-F5 remains open: agent-memory checking remains optional and a missing gateway protocol file is not reported.
R06-F6 remains open: the history check detects modifications but can miss a later delete-and-add replacement of an artifact.
R06-F7 remains open: transfer does not verify inventory counts, operational applicability, or the content of runtime observations.
R06-F8 remains open: parsing still depends on unrequired Markdown forms and the legacy exemption bypasses output-contract validation.

## Part B — findings

F1 [blocker]: `record()` requires an indexed artifact and checksum to exist but does not require either to be tracked; `transfer()` checks tracked cleanliness and upstream equality, so it can pass while the next checkout lacks the review evidence.

F2 [blocker]: A `verified` quote such as “R01-F1 was discussed” passes if it appears in the later artifact and lacks `OPEN_WORDS`; `user-decided` likewise accepts an ID-bearing sentence in Decisions without checking that it is the user’s dated, scoped acceptance of the outcome.

F3 [blocker]: `carried` checks only that one review line cites another ID, then checks final evidence against the target ID; a re-raised item can cite an original blocker while resolving a different issue, and the blocker will pass `done()`.

F4 [major]: `report --write-baseline` puts every tracked `.collab/` path into `legacy_collab`; writing or rewriting a baseline after reviews exist can exempt unindexed or post-adoption reviews from discovery and output-contract checks.

F5 [major]: The standards pin is required only when a baseline exists, and agent-memory enforcement requires an optional `agent_cache` entry; a pilot can therefore omit both checks by omitting or incompletely writing its baseline.

F6 [major]: `transfer()` accepts arbitrary inventory counts, `n/a (not operational)` for any workstream, and future observation times; its observation field also need not contain a command or result.

F7 [major]: The immutability check searches Git history only for modifications, so deleting and re-adding an artifact with a matching new checksum can evade the “never edit” rule.

C1: Require indexed artifacts and sidecars to be committed before transfer, and test the next checkout against the pushed revision.

C2: Require finding-specific affirmative verification, or a dated user quote that explicitly accepts the item’s outcome and scope; carry the original item’s identity through any carried chain.

C3: Enumerate legacy review paths explicitly, require the pilot’s pin and agent-memory baseline, and compare inventory and runtime fields with the evidence they claim to record.

ATTESTATION: all actionable findings and conditions are labeled.

The tooling is **not ready for the single-session pilot**.

VERDICT: REJECT