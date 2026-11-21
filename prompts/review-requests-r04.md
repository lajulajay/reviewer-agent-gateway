# Follow-up: review requests (gateway)

Owner: Claude. Reviewer: Kimi via the Moonshot API. Read-only; no tools.
Attached: the current review-request.py and its tests, the full PROTOCOL and
README diff, and your r03 review. Your r03 IDs are R03-F1..F5, R03-C1..C5.

Owner's response:
- R03-F1/C1: `auto` removed; a request names claude, codex, kimi or gemini
  (create refuses auto; load refuses it as malformed). Test added.
- R03-F2/C2: one run per request. `run` refuses if the output, diagnostic or
  result exists, then claims `<name>.result.json` (open mode "x") BEFORE
  calling the wrapper, so nothing is sent if the outcome cannot be recorded;
  the final result replaces it atomically. `list` treats a request with a
  result as done. Another attempt needs a new request and rNN. Tests: a
  preflight failure with no artifact or diagnostic is recorded, is not
  pending, and refuses a rerun without calling the wrapper; a pre-existing
  result stops the run before the wrapper.
- R03-F3/C3: load validates the schema and requires output to equal exactly
  ".collab/<request basename>" (absolute and `..` edits refused); packets are
  re-confined to the repository or the recorded packet root at run time. The
  docstring and README state that the hashes detect changed files but do not
  authenticate the request; the wrapper stays the control. Tests cover
  absolute, traversal and other-name outputs, outside and `..` packets,
  malformed fields and auto.
- R03-F4/C4: list assertions now check that the request name is absent and a
  pending one present.
- R03-F5/C5: PROTOCOL now reads "Sending a packet through a gateway wrapper
  (CLI or API route) to a reviewer vendor in agents.json needs no per-task
  approval of the destination ...; all else holds." README matches and says
  "the user, or an agent the user asks".

For each ID reply with exactly the line `<ID> is resolved.` when resolved, or
a labeled finding naming what remains: R03-F1, R03-F2, R03-F3, R03-F4,
R03-F5, R03-C1, R03-C2, R03-C3, R03-C4, R03-C5. Answer briefly; do not
re-review unrelated parts.
Label findings `F1 [blocker|major|minor]: ...` and conditions `C1: ...`.
Include `ATTESTATION: all actionable findings and conditions are labeled.`
The last non-empty line must be exactly one of `VERDICT: ACCEPT`,
`VERDICT: ACCEPT WITH CONDITIONS` or `VERDICT: REJECT`.
