# Streamed replies on the API route

Workstream: 2026-11-20-api-streaming
Owner: Claude (2026-11-20, assigned by the user in this session)
Status: active
Branch: api-streaming
Operational: no
Links: [Copilot owner workstream](2026-11-20-copilot-owner.md), [README API route](../README.md)

## Brief

A non-streamed Kimi hard-tier review (`kimi-k3.1-pro`, T5 r09 in
trading-strategies) was closed by Moonshot after 601 s with no reply. Both API
request styles now ask for a streamed reply; `api-call.py` rebuilds the same
reply object from the events, so every existing check (completion, one
choice, no tool use, redaction, substance validation, reserve-then-settle)
applies unchanged. Plain-JSON replies are still accepted. The overall call
deadline is now 1800 s by default, with up to 300 s of silence between lines.

## Decisions

- 2026-11-20, user, scope: this change. Quote: "yes" (to adding streaming to
  the gateway's API calls so long hard-tier reviews are not cut off).
  Supersedes: none.

## Reviews

| Round | Reviewer | Tier | Artifact | Verdict |
| :--- | :--- | :--- | :--- | :--- |
| r01 | Kimi API (`kimi-k2.6`) | routine; contained change to the API call path, Codex at its daily cap | `.collab/kimi-2026-11-20-api-streaming.md` (SHA-256 `3b4d05b0dfdddc01b93cd45a6c7450cefe3e0bd7408e3b78c44adf3422627b2d`) | ACCEPT |

## Findings and conditions

| ID | Severity | Disposition | Status |
| :--- | :--- | :--- | :--- |
| R01-C1 | condition | | open: test added for the plain-JSON fallback (leading blank lines) and the 32 MiB bound on both paths; unverified |

r01 also wrote an unbracketed "F1 minor" (a `function_call: null` delta is
treated as a tool call). Not a labeled item; kept deliberately: any present
`function_call` is a tool call (R03-F8 in the Copilot owner workstream), and
live Moonshot replies carry none.

## Log

- 2026-11-20: streaming implemented with 12 new tests; Kimi r01 ACCEPT with
  one condition, addressed by a test. Commit, push and merge await the sponsor.
