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
| r01 | Gemini (backup; Codex at usage limit) | pro | `.collab/gemini-2026-10-08-review-budget-r01b.json` | REJECT |

## Findings and conditions

| ID | Severity | Disposition | Status |
| :--- | :--- | :--- | :--- |
| R01-F1 | blocker | fix pending r02: daily cap reads the date from the output name; mtime only for undated names | open |
| R01-F2 | blocker | fix pending r02: note gives every stated hex length and the measured one, without attributing; PROTOCOL says it is not a verdict | open |
| R01-F3 | major | rejected: a retry under the same name is a second model call, so counting the diagnostic and the artifact counts two real calls | open |
| R01-F4 | major | fix pending r02 (partial): `returned`/`did not succeed` reasons now count; `invocation failed` stays uncounted because it includes usage-limit refusals that never ran (Codex r01 attempt, 2026-10-08) | open |
| R01-F5 | major | fix pending r02: diagnostics carry their requested/selected model into the hard-tier count | open |
| R01-F6 | major | fix pending r02: output names that do not parse, or whose provider prefix differs, are refused | open |
| R01-F7 | minor | fix pending r02: Claude effort keys on Claude's own earlier rounds | open |
| R01-F8 | minor | fix pending r02: claims must say hex/hexadecimal | open |
| R01-F9 | minor | fix pending r02 (partial): entry must name the round; the user-actor part is rejected because decision_entries already accepts only `- <date>, user, scope:` lines | open |
| R01-F10 | minor | rejected: counting a topic across dates is deliberate so a date change cannot reset the cap (user decision 2026-10-08); a reused name gets a refusal that names the topic | open |
| R01-C1 | condition | fix pending r02 (F1) | open |
| R01-C2 | condition | fix pending r02 (F2, F8) | open |
| R01-C3 | condition | rejected with F3 | open |
| R01-C4 | condition | partial with F4 | open |
| R01-C5 | condition | fix pending r02 (F5); the existing diagnostic already records the requested model | open |
| R01-C6 | condition | fix pending r02 (F6) | open |
| R01-C7 | condition | fix pending r02 (F7) | open |
| R01-C8 | condition | partial with F9 | open |

## Log

- 2026-10-08: implemented on branch `review-budget`; after the Gemini round the open points go to the user (user correction). Committed with the user's approval.
- 2026-10-08: Codex r01 not run: ChatGPT usage limit (diagnostic committed). First Gemini attempt refused (exit 78) because the wrapper dirty check matched `.collab/*.diagnostic.json`; fixed by excluding `.collab` from that check.
- 2026-10-08: Gemini r01 REJECT (10 findings). The output was named `-r01b` by mistake, so the budget counts it under its own topic. Fixes for F1, F2, F4–F9 applied; F3 and F10 rejected; F4 and F9 partly rejected (see rows). Review r02 pending.
