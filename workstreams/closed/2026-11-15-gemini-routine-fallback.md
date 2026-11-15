# Gemini routine-tier fallback

Workstream: 2026-11-15-gemini-routine-fallback
Owner: Claude (2026-11-15, assigned by the user at d619470)
Status: closed
Branch: gemini-routine-fallback
Operational: no
Links: [r12 failure](../../invocation-failures/trading-strategies-2026-11-15-index-options-implementation-r12-gemini-model.md)

## Brief

`agy models` now lists only Gemini 3.8 Flash (High/Medium/Low). The routine
tier (second older approved release) selected the withdrawn
`gemini-3.6-flash-high`, and agy rejected it. Mark 3.7/3.6 not included, drop
the withdrawn `gemini-3.1-pro-high`, and add a `routine_fallback_model` limited
to the hard release at another effort.

## Decisions

- 2026-11-15, user, scope: update the gateway's Gemini model list so routine
  reviews work. Quote: "yes to both". Supersedes: none.
- 2026-11-15, user, scope: routine fallback model. Quote: "3.8 Flash Medium
  (Recommended)". Supersedes: none.

## Reviews

| Round | Reviewer | Tier | Artifact | Verdict |
| :--- | :--- | :--- | :--- | :--- |
| r01 | Gemini (`gemini-3.8-flash-medium`) | routine; small selector change, user-directed Gemini | `.collab/gemini-2026-11-15-gemini-routine-fallback-r01.json` (SHA-256 `a93f486b34626c05e976bd692e59448b684778a7bbe61ce29d8804a11c26d3de`) | ACCEPT |

## Findings and conditions

None; r01 raised no labeled items.

## Log

- 2026-11-15: implemented in 0e91369; 52 unit tests and wrapper smoke pass.
  r01 ran on the new routine tier (end-to-end check) and accepted.
