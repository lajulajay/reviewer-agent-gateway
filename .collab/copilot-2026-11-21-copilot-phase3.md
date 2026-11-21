# Copilot review

Owner: claude
Task: phase3
Wrapper revision: ec85df13a970c14daeb54b98487eb6c4c533e7a0
Requested model: hard
Selected model: gpt-6.1-terra
Reviewer vendor: openai
Resolved model(s): gpt-6.1-terra
CLI version: GitHub Copilot CLI 1.0.114.
Tool events: 0
Usage: {"input":{"tokenCount":3},"cache_read":{"tokenCount":0},"cache_write":{"tokenCount":13873},"output":{"tokenCount":4256}}
AI credits: 3.862 AI credits (cap 60)

F1 [major]: `integration` runs `integration_errors` without `record` or `task_errors`. An arbitrary file containing an accepted verdict and matching task ID can open the standalone gate without a valid artifact, independent reviewer, matching models, or valid coverage row. Run the record and identity checks as part of this command.

F2 [major]: Even through `done`, an accepted ordinary batch review can count as integration: any row with `Covers` qualifies, regardless of its `batch` state or branch. Nothing establishes that the review was of `main` after merging.

F3 [major]: Coverage is not bound to the reviewed snapshot. After an accepted review of `I1` covering T6, adding a newly merged T7 with the same authors/models to `I1.Covers` makes it covered without another review. Bind the accepted review to the covered tasks and merged revision.

F4 [major]: A merged task with a nonempty `Covers` cell is excluded from the set of tasks requiring integration. For example, merged T7 can cover merged T6 and itself escape the gate entirely. Distinguish task rows from integration rows and require every merged task to be covered.

F5 [major]: Task identity checks can be bypassed by recording a non-Copilot owner and omitting Copilot from artifact authors. In a workstream naming both Claude and Copilot, a Claude-owned artifact can reference a Copilot task while omitting its models; `copilot_artifact_errors` returns before checking the task row. The reviewer can consequently share a vendor with the omitted author model.

F6 [major]: The legacy map changes only the local owner-membership check; `agents.check` has already received the original `codex` identity. Mapped artifacts therefore are not checked for reviewer independence as Copilot work, and the map alone supplies no historical author models. Also, mapping is not applied when both Codex and Copilot are named owners.

F7 [major]: Batch rows cannot accurately record unmerged members in `Covers`: `task_errors` rejects every covered row that is not merged. Leaving `Covers` empty avoids that failure but also leaves the batch row’s claimed authors and models unchecked against its members.

F8 [minor]: Task-row completeness does not check `Branch` or `PR` at all; even a merged task with both blank passes. Validate applicable fields by state without requiring a PR for planned tasks or integration rows.

F9 [minor]: `first_added` does not follow renames, so a valid legacy artifact moved to its current path can appear newly added or have no addition date and be rejected despite having been first committed before the map. Shallow history can similarly make the date unavailable or misleading.

F10 [minor]: The coordinator and sub-agent command templates omit repeatable `--author` arguments, although integration rows can carry multiple authors and the ticket identity must match. The coordinator ticket example also omits `--batch` for shared batch reviews. Include these options so the templates support the documented duties.

ATTESTATION: all actionable findings and conditions are labeled.
VERDICT: REJECT
