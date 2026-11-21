# Review requests and packet destinations

Workstream: 2026-11-20-review-requests
Owner: Claude (2026-11-20, assigned by the user in this session)
Status: active
Branch: review-requests
Operational: no
Links: [Copilot owner workstream](2026-11-20-copilot-owner.md), [README](../README.md), [protocol](../PROTOCOL.md)

## Brief

A Copilot sub-agent refused to run `kimi-review.sh` for T5 in
trading-strategies because it would send repository source to Moonshot's
API, citing a data-sharing restriction found in no written instruction, and
held that position after the sponsor approved it. Its session log shows it
had read the gateway README, which still said Kimi "does not use ... direct
Moonshot API configuration". This change (1) corrects that README text,
(2) adds the "Where packets may go" rule to PROTOCOL (registered reviewer
vendors are approved destinations through the gateway wrappers; every other
rule holds), and (3) adds `review-request.py`, with which an owner that
cannot send a packet records a request that the user, or an agent the user
asks, runs through the normal wrapper. It also raises the Kimi routine
output limit from 16000 to 32000 tokens after the routine model exhausted it
on reasoning twice.

## Decisions

- 2026-11-20, user, scope: this change. Quote: "yes" (to the README fix, the
  packet-destination rule and review requests; Copilot-channel reviews stay
  Phase 2). Supersedes: none.

## Reviews

| Round | Reviewer | Tier | Artifact | Verdict |
| :--- | :--- | :--- | :--- | :--- |
| r03 | Kimi API (`kimi-k3.1-pro`) | hard; changes who may send what to which vendor in every repository | `.collab/kimi-2026-11-20-review-requests-r03.md` (SHA-256 `b01528143b042095caa8f34a5fd953eea21a5f0b41d996a78a65c06b464c89ac`) | ACCEPT WITH CONDITIONS |
| r04 | Kimi API (`kimi-k2.6`) | routine; follow-up | `.collab/kimi-2026-11-20-review-requests-r04.md` (SHA-256 `6b528804b887c1c771e2311d6bf973cecc16680767688d53cbd9159409cac698`) | ACCEPT |

r01 (`.collab/kimi-2026-11-20-review-requests.diagnostic.json`) was a trial of
`review-request.py run` from the uncommitted worktree copy, refused by the
gateway dirty check before any model call. r02
(`.collab/kimi-2026-11-20-review-requests-r02.diagnostic.json`, routine) reached
the model and was rejected at the 16000-token output limit. Neither is a
review.

## Findings and conditions

| ID | Severity | Disposition | Status |
| :--- | :--- | :--- | :--- |
| R03-F1 | major | verified r04 | resolved |
| R03-F2 | major | verified r04 | resolved |
| R03-F3 | major | verified r04 | resolved |
| R03-F4 | minor | verified r04 | resolved |
| R03-F5 | minor | verified r04 | resolved |
| R03-C1 | condition | verified r04 | resolved |
| R03-C2 | condition | verified r04 | resolved |
| R03-C3 | condition | verified r04 | resolved |
| R03-C4 | condition | verified r04 | resolved |
| R03-C5 | condition | verified r04 | resolved |

## Log

- 2026-11-20: implemented with 11 tests; the r01 trial exposed a diagnostic
  naming bug in `review-request.py` (fixed, tested). Kimi r03 ACCEPT WITH
  CONDITIONS (auto requests, retry state, tampering, test assertions,
  wording), all fixed; Kimi r04 ACCEPT. Commit, push and merge await the
  sponsor.
