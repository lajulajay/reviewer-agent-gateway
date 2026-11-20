# Follow-up: API route r02 items (gateway commit ec02287)

Owner: Claude. Reviewer: Codex via the OpenAI API. Read-only; review only the
attached delta (961b844..ec02287). No tools, repository access, commit or push.

Your r02 findings and the owner's response (numbering is yours from r02):

- F1 (R01-F2): keychain-store.py refuses non-tty stdin and turns
  getpass.GetPassWarning (the echo fallback) into a refusal.
- F2 (R01-F3): HTTP error bodies are never echoed; only error.type/error.code
  strings (40 chars max) are reported. redact() also replaces the JSON-escaped
  form of the key. Reply text and metadata pass through redact() before being
  written. (The key is never placed in the prompt, so the model cannot echo it
  unless a packet carried it, which packet rules forbid.)
- F3 (R01-F5): the state directory's parent and the state directory are
  fsynced when the directory or ledger file is created.
- F4 (R01-F6, R01-F11): the reply is validated (including empty text) before
  settling; a rejected reply settles at the full bound regardless of usage.
- F5 (R01-F7): ledger amounts must be JSON integers >= 0; bool, float and
  string amounts refuse the ledger.
- F6 (R01-F8): prompt assembly checks each step; artifact values are computed
  and checked before the artifact is written.
- F7 (R01-F8): exit 0 without the marker maps to 78.
- F8 (R01-F9): any present function_call key, even null, is a tool call. A
  live Moonshot reply carried keys content, reasoning_content, role only.

For each of R01-F2, R01-F3, R01-F5, R01-F6, R01-F7, R01-F8, R01-F9 and
R01-F11, reply with exactly the line `R01-Fn is resolved.` when the combined
fixes resolve it, or a new labeled finding naming what remains. Do not reopen
settled design choices or raise new topics beyond these items.
Label new findings `F1 [blocker|major|minor]: ...` and conditions `C1: ...`.
Include `ATTESTATION: all actionable findings and conditions are labeled.`
The last non-empty line must be exactly one of `VERDICT: ACCEPT`,
`VERDICT: ACCEPT WITH CONDITIONS` or `VERDICT: REJECT`.
