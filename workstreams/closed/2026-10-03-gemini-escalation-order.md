# Mandatory Gemini step before user escalation

Workstream: 2026-10-03-gemini-escalation-order
Owner: Claude (2026-10-03, assigned by the user at efc1333)
Status: done (2026-10-03)
Branch: main (gateway); repository branches listed below
Operational: no
Links: [canonical protocol](../../PROTOCOL.md)

## Outcome

Done 2026-10-03. `PROTOCOL.md` (47f6d27) requires a Gemini review before a
decision-material Codex/Claude disagreement reaches the user, unless Gemini
is unavailable. Repository `AGENTS.md` wording points to it and pins
47f6d27: trading-strategies 01f9bd8, polymarket-temperature-bot cec4223
(feature branch) and dc740cf (`main`), kalshi-temperature-bot 07ea262 (H5
branch). Finance and econ follow the canonical rule without edits. Two Codex
rounds; 4 items, all verified in r02.

## Brief

The user has been asked to settle Codex/Claude disagreements without Gemini
having been consulted. The protocol allowed that: Gemini was optional for an
unresolved disagreement ("Escalate to Gemini only when…" in three repos),
"unresolved policy choices return to the user" routed policy disputes
straight to the user, and trading-strategies listed "accepting an unresolved
reviewer disagreement" as a direct stop-for-user item.

Change: `PROTOCOL.md` gains a mandatory order. A decision-material
disagreement that survives a substantive round goes to Gemini before the
user, including policy disagreements and user-reserved decisions. The user
gets one packet with both positions, the evidence, Gemini's view, and the
decision. Gemini is skipped only when unavailable, and the packet says so.
Repository `AGENTS.md` escalation wording points to this rule, and each
touched repository's standards pin moves to the gateway commit that adds it.

Scope: gateway; `polymarket-temperature-bot` (both branches),
`kalshi-temperature-bot` (H5 branch), `trading-strategies` (main).
`kalshi-finance-agent` already defers to the gateway with no escalation
wording of its own, so it is unchanged. The canonical `PROTOCOL.md` governs
every repository as soon as it changes ("If repository wording differs from
this file, this file wins"); a repository's standards pin does not select
the governing protocol. The pin only bounds which wrapper revisions its
review artifacts may use, so finance's pin moves at its next review, when it
first needs a newer wrapper. The same holds for `kalshi-econ-agent`.
`kalshi-econ-agent` is excluded: the user asked to leave it for now.
Documentation only; pushes deploy nothing in the touched repositories.

## Decisions

- 2026-10-03, user, scope: make Gemini review mandatory before a
  Codex/Claude disagreement reaches the user, in the gateway and the repos.
  Quote: "yes". Context (the owner's proposal the user approved): "When the
  owner and the primary reviewer still disagree on a decision-material point
  after a substantive round, the owner must get a Gemini review before
  bringing the disagreement to the user."

## Reviews

| Round | Reviewer | Tier | Artifact | Verdict |
| :--- | :--- | :--- | :--- | :--- |
| r01 | Codex | routine (gpt-6-sol, medium) | `.collab/codex-2026-10-03-gemini-escalation-order-r01.md` | ACCEPT WITH CONDITIONS |
| r02 | Codex | routine (gpt-6-sol, medium) | `.collab/codex-2026-10-03-gemini-escalation-order-r02.md` | ACCEPT |

## Findings and conditions

| ID | Severity | Disposition | Status |
| :--- | :--- | :--- | :--- |
| R01-F1 | major | verified r02 | closed |
| R01-F2 | major | verified r02 | closed |
| R01-C1 | condition | verified r02 | closed |
| R01-C2 | condition | verified r02 | closed |

## Log

- 2026-10-03: `PROTOCOL.md` edited (47f6d27); repository edits made,
  uncommitted, pending review. The trading-strategies edit also removes its
  note that the gateway's `COLLAB.md` owner-location sentence awaited
  correction: efc1333 made that correction earlier today.
- 2026-10-03: r01 Codex ACCEPT WITH CONDITIONS. F1/C1: the gateway sentence
  was already corrected in efc1333, which was outside the r01 packet; r02
  receives that diff. F2/C2: the brief now states that `PROTOCOL.md` governs
  every repository immediately and that pins only bound review provenance.
- r01: raw review compared with its rows; no unlabeled actionable item
- 2026-10-03: r02 Codex ACCEPT: all four r01 items verified. Repository
  commits made; docs-check done passed; closed.
- r02: raw review compared with its rows; no unlabeled actionable item
