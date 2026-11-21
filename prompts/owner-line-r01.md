# Review: docs-check Owner-line regression fix (gateway, based on f5098ee)

Owner: Claude. Reviewer: Codex via the OpenAI API. Read-only; review only the
attached material. No tools.

Context: Phase 1 (merged today) made `docs-check.py record` require every
workstream `Owner:` line to start with an owner agent (claude, codex,
copilot, from agents.json `can_own`). A trading-strategies workstream merged
earlier today reads `Owner: sponsor's GitHub Copilot agent (user-assigned
2026-11-20)` (attached header) and now fails. The protocol forbids rewriting
earlier Owner lines, so the checker must accept it.

Change (attached diff): `owner_named()` accepts a line whose first word is an
owner agent (unchanged behaviour), or else a line that names exactly one
registered agent as a whole word and that agent can own. Lines naming no
agent, a reviewer-only agent (kimi, gemini), or two agents are still refused.
Tests cover the accepted and refused forms.

Check: is the rule correct and tight enough (no line that misidentifies the
owner passes; whole-word matching; channel names vs owners), does it keep
the vendor rule intact (docs-check re-checks every artifact with
agents.check independently of this line), and are the tests adequate?
Label findings `F1 [blocker|major|minor]: ...` and conditions `C1: ...`.
Include `ATTESTATION: all actionable findings and conditions are labeled.`
The last non-empty line must be exactly one of `VERDICT: ACCEPT`,
`VERDICT: ACCEPT WITH CONDITIONS` or `VERDICT: REJECT`.
