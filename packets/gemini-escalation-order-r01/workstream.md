# Mandatory Gemini step before user escalation

Workstream: 2026-10-03-gemini-escalation-order
Owner: Claude (2026-10-03, assigned by the user at efc1333)
Status: active
Branch: main (gateway); repository branches listed below
Operational: no
Links: [canonical protocol](../PROTOCOL.md)

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
wording of its own, so it is unchanged (its pin moves at its next review).
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

## Findings and conditions

| ID | Severity | Disposition | Status |
| :--- | :--- | :--- | :--- |

## Log

- 2026-10-03: `PROTOCOL.md` edited; repository edits follow.
