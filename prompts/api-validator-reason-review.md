Review a small change to the reviewer gateway's paid API route (`api-call.py`).

Problem: when `reviewer-validate.py` rejected a model reply, `api-call.py` reported only "API reply rejected: substance validation failed" and discarded the validator's stderr, so refused rounds had to be diagnosed by guessing.

Change (see change.diff): on a non-zero validator exit, take the last non-empty stderr line, pass it through `redact()` (removes the API key in raw and JSON-escaped forms), drop non-printable characters, truncate to 200 characters, and append it as "substance validation failed: <reason>". The problem string goes to stderr via `Refusal` (the wrapper `api-route.sh` quotes the last stderr line into its `.diagnostic.json`) and into the meta file's `problem` field (written through `redact(json.dumps(meta))`). The ledger settle note stays the fixed text "reply rejected: full bound kept"; settlement amount is unchanged.

Invariants: the key never appears in argv, logs, artifacts or the ledger; no server-supplied value reaches the ledger.

Evidence (script output): `python3 -m unittest discover -s tests` -> "Ran 116 tests ... OK"; the two new tests are in change.diff.

Questions:
1. Can any reply content or key material reach stderr, the diagnostic or the meta file through this change in a way it could not before? (Note the validator prints only fixed text, but the change treats its output as untrusted.)
2. Is taking the last non-empty line correct for every validator exit path in reviewer-validate.py (including an uncaught Python exception traceback)?
3. Do the tests establish the behaviour claimed?

Prohibited: do not propose unrelated refactors. Label findings F<n> [blocker|major|minor] and conditions C<n>.
