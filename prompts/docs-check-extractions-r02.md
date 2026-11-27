Follow-up review (r02) of the docs-check extraction exception. Your r01 returned REJECT with R01-F1, R01-F2, R01-F3, R01-C1. docs-check-extractions-r01-to-r02.diff is the delta since r01 (docs-check.py and tests only).

Owner's response:
- R01-F1: the exception now requires all of: `<stem>.diagnostic.json` beside the file whose JSON `exit_code` is a non-zero integer (not bool, not string); a sidecar whose first field equals the file's SHA-256; and a workstream in the repository whose text contains the exact `.collab/<name>.extracted.md` path (the owner's classification on the record). An arbitrary note renamed to .extracted.md fails unless a workstream names it beside a real failure diagnostic. A real review cannot hide this way unless the owner names it as an extraction, which is a recorded, reviewable act.
- R01-F2: diagnostic and sidecar reads catch OSError, UnicodeDecodeError, ValueError (JSON) and AttributeError (non-object JSON) and report a failed match.
- R01-F3: every failure assertion checks exit status 1; a correct sidecar followed by an edit to the extraction is rejected; scope tests: no naming workstream, missing/malformed/zero/bool/string/absent exit code, missing/undecodable/empty/wrong sidecar, and another unrecognized file still flagged.
- R01-C1: one message per failed check (e.g. "no workstream names its path", "checksum sidecar is malformed or does not match").

Evidence (script output): `python3 -m unittest tests.test_docs_check` -> Ran 34 tests, OK. The new test fails against main's docs-check.py. kalshi-temperature-bot, after naming both extraction paths literally in its workstream: changed checker "docs-check record: PASS (0 errors)"; main's checker "FAIL (2 errors)".

For each of R01-F1, R01-F2, R01-F3, R01-C1 write either "<ID> is resolved." or "<ID> remains open: <reason>". Report any new defect as F<n> [severity].
