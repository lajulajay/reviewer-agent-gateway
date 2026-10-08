Review gateway commit 25c48e4, which adds a review budget to the Claude,
Codex, and Gemini reviewer wrappers. Owner: Claude. You are the backup
reviewer (Codex, the primary reviewer, is at its usage limit).

Background. On 2026-10-07 one review topic (H5 final analysis in
kalshi-temperature-bot) ran 23 Claude review rounds; the user reports it used
about 20% of a 5-hour Claude session limit. Three rounds were triggered by
false SHA-256 length findings from a tool-less reviewer.

User decisions (2026-10-08): at most 5 rounds per topic, then one Gemini
round, then the user decides (not the owning agent); the limits apply to the
Claude, Codex, and Gemini wrappers. Kimi is inactive and excluded.

Packets: `25c48e4-gateway.diff` (wrappers, review-budget.py/.json,
reviewer-claims.py, docs-check.py, PROTOCOL.md, README.md, output contract,
workstream) and `25c48e4-tests.diff` (provider-free tests; both suites pass).

Questions:
1. Can a call that exceeds a limit still reach a model? Consider topic
   parsing (names with and without dates or `-rNN`, `.json` vs `.md`), which
   failed calls are counted, ordering of the budget check relative to the
   model call, and the hard-tier detection for Claude and Codex.
2. Can the limits misfire and block legitimate work (topic collisions,
   mtime-based daily counting, diagnostics counted twice)?
3. Is the override path sound: recorded in the artifact and rejected by
   docs-check without a user decision?
4. Could reviewer-claims.py produce misleading notes?
5. Do the PROTOCOL.md rules match the code and the user decisions?

You have no tools; review only the text supplied.
