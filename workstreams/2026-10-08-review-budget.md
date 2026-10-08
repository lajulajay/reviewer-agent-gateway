# Review budget

Workstream: 2026-10-08-review-budget
Owner: Claude (2026-10-08, assigned by the user)
Status: active
Branch: review-budget
Operational: no
Links: [failure report](../invocation-failures/kalshi-temperature-bot-2026-10-07-h5-sha256-review-errors.md), [protocol](../PROTOCOL.md#review-budget)

## Brief

The H5 final-analysis review in `kalshi-temperature-bot` ran 23 Claude rounds
(r02–r24) on 2026-10-07, 32 Claude reviews in that repository that day, and
the user reports it used about 20% of a 5-hour Claude session limit. Three
rounds were triggered by false SHA-256 length findings from a reviewer that
cannot count characters. Nothing limited rounds, and the Claude wrapper set no
effort and recorded no usage.

Change: `review-budget.py` + `review-budget.json` enforced by the Claude,
Codex, and Gemini wrappers before the model call (exit 79); Claude effort
medium for the first round, low for follow-ups; usage recorded in every
artifact; `reviewer-claims.py` notes false hex-length claims in the artifact
header; output-contract and packet rules against character counting;
`docs-check.py record` requires a user decision for any budget override.

## Decisions

- 2026-10-08, user, scope: review round limits.
  Quote: "like the idea of limits but 3 feels stringent for hard topics. let's make it 5 after which it must be escalated to Gemini and then owner". Supersedes: the proposed 3-round cap.
- 2026-10-08, user, scope: which wrappers carry the limits.
  Quote: "Other wrappers: yes". Supersedes: none.
- 2026-10-08, user, scope: who decides after the Gemini escalation.
  Quote: "by then owner, i meant me not the repo owner". Supersedes: the owner-agent reading of the first decision.

## Reviews

| Round | Reviewer | Tier | Artifact | Verdict |
| :--- | :--- | :--- | :--- | :--- |

## Findings and conditions

| ID | Severity | Disposition | Status |
| :--- | :--- | :--- | :--- |

## Log

- 2026-10-08: implemented on branch `review-budget`; after the Gemini round the open points go to the user (user correction). Committed with the user's approval.
