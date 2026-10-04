Review a protocol change that makes a Gemini review mandatory before a
Codex/Claude disagreement is brought to the user. The packets are: the
gateway `PROTOCOL.md` diff (canonical; it wins over repository wording); the
`AGENTS.md` diffs for trading-strategies, polymarket-temperature-bot (both
the feature branch and `main`), and kalshi-temperature-bot (each also moves
its standards pin to the gateway commit that adds the rule); and the
workstream file. Documentation only. You have no tools; review only the
text.

The user's problem: they have been asked to settle disagreements without
Gemini having been consulted.

Check:
1. Does the new rule, read together with each repository's wording, leave
   any path that brings a Codex/Claude disagreement to the user without a
   Gemini review, other than Gemini being unavailable?
2. Is it clear and consistent with the rest of the protocol: the empirical-
   evidence-first rule, no voting, advisory status, user-reserved decisions,
   and agreed questions going straight to the user?
3. Are the repository edits consistent with the canonical rule and with each
   other, and did they remove anything a future owner needs?
4. Are the scope exclusions sound (kalshi-finance-agent unchanged;
   kalshi-econ-agent left out at the user's request)?
