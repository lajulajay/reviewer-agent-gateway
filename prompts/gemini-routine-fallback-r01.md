# Review: Gemini routine-tier fallback (gateway commit 0e91369)

Owner: Claude. Reviewer: Gemini (user-directed). Read-only; review only the
attached diff and files. No tools, repository access, commit or push.

Context: `agy models` on 2026-11-15 lists only gemini-3.8-flash-high, -medium
and -low. The old routine rule (second older approved release) picked
gemini-3.6-flash-high, which agy rejected. The user chose 3.8 Flash Medium as
the routine model.

Answer only:

1. Is `routine_fallback_model` validated tightly enough (ID shape, same
   release/family as hard, different effort) and used only when fewer than two
   older approved releases exist? Can a malformed or hostile policy make the
   selector return an unvetted model?
2. Is allowing the fallback to be requested by full ID consistent with the
   rest of the selector?
3. Do the unit and smoke tests actually detect regressions in those rules?
4. Is the README accurate?

Label new findings `F1 [blocker|major|minor]: ...` and conditions `C1: ...`.
Include `ATTESTATION: all actionable findings and conditions are labeled.`
The last non-empty line must be exactly one of `VERDICT: ACCEPT`,
`VERDICT: ACCEPT WITH CONDITIONS` or `VERDICT: REJECT`.
