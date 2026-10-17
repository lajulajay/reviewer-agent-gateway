# Subscription reviewer gateway

Workstream: 2026-10-17-subscription-gateway
Owner: Codex (2026-10-17, assigned by the user after Kimi reached its usage limit)
Status: active
Branch: main
Operational: no
Links: [protocol](../PROTOCOL.md), [implementation](../README.md)

## Brief

Complete Kimi's partial implementation of managed-OAuth Kimi Code reviews and
automatic subscription reviewer selection. Preserve independent review,
tool-free reviewer execution, and per-topic and daily budgets. No production
service is changed.

## Decisions

- 2026-10-17, user, scope: this gateway change. Quote: "Kimi began making
  changes to the reviewer-agent-gateway but hit its usage limit. i want you
  to take over as owner and complete its changes". Codex is the owner;
  Kimi remains an author of the initial change and cannot review it.

## Reviews

| Round | Reviewer | Tier | Artifact | Verdict |
| :--- | :--- | :--- | :--- | :--- |
| r01 | Claude | opus | `.collab/claude-2026-10-17-subscription-gateway-r01.md` | ACCEPT WITH CONDITIONS |
| r02 | Claude | sonnet | `.collab/claude-2026-10-17-subscription-gateway-r02.diagnostic.json` | invalid severity; no accepted artifact |

## Findings and conditions

| ID | Severity | Disposition | Status |
| :--- | :--- | :--- | :--- |
| F1 | major | fixed: explicit additional authors excluded by auto selection | pending r02 |
| F2 | major | rejected: Claude/Codex exits 69 and 78 occur before their model calls | pending r02 |
| F3 | major | narrowed claim to documented CLI controls; live probe unavailable at Kimi usage limit | pending r02 |
| F4 | minor | fixed: all non-Kimi exit 70/74 failures now count; protocol wording narrowed | pending r02 |
| F5 | minor | fixed: auto template date must be today's local date | pending r02 |
| F6 | minor | documented: budget override uses a fresh rNN name | pending r02 |
| F7 | minor | fixed: uncommitted roster environment override removed | pending r02 |
| F8 | minor | mitigated: prompt cap lowered to 100000 bytes; process-list exposure documented | pending r02 |
| F9 | minor | documented limitation: serving model is not reported | pending r02 |
| C1 | condition | fixed with additional author exclusions | pending r02 |
| C2 | condition | wrapper exit-code locations checked | pending r02 |
| C3 | condition | official Kimi docs checked; live negative probe unavailable at usage limit | pending r02 |
| C4 | condition | fixed with today-only template and test | pending r02 |
| C5 | condition | protocol and README corrected | pending r02 |

## Log

- 2026-10-17: Codex completed Kimi's partial changes, corrected follow-up
  selection for an ineligible latest reviewer, and committed c654e44. The
  provider-free suites passed.
- 2026-10-17: Claude r01 found budget accounting, author exclusion, and
  documentation issues. Codex fixed the code and tests and is preparing a
  routine follow-up review.
- 2026-10-17: Claude r02 reached the model but the gateway rejected its
  unsupported `[resolved]` severity labels. Its diagnostic raised a question
  about preflight failures; the budget code now guards exit codes explicitly,
  and provider-free tests cover exit 69 and 78 as unspent.
