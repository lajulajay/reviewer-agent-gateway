Follow-up review (r02) of the docs-check trailing-whitespace change. Your r01 returned ACCEPT WITH CONDITIONS with R01-F1, R01-F2, R01-F3, R01-C1, R01-C2. change-r02.diff is the full current diff against main; artifact-text-excerpt.py is `artifact_text()`.

Owner's response:
- R01-F1 [minor]: this states the change does not weaken the check; it reports no defect, so no change was made.
- R01-F2, R01-F3, R01-C1: checked. `artifact_text()` reads `.md` artifacts with `Path.read_text()` (universal newlines), so CRLF never reaches the regex for them. A `.json` artifact's review is the JSON string `response`, decoded by `json.loads`, which keeps `\r`. The pattern is now `is resolved\.[ \t\r]*$`. Two new tests: a CRLF `.md` artifact passes `done`; a `.json` artifact whose `response` uses CRLF passes `done`. Script check: with the r01 pattern `[ \t]*` restored, the JSON test fails and the `.md` test passes; with `[ \t\r]*` both pass. The earlier test still rejects trailing " but see below", ".", "  x" and a non-breaking space.
- R01-C2: no change. The comment cites the real motivating case, Codex r03 of workstream 2026-11-21-api-validator-reason, whose line "R02-F1 is resolved." ended in two spaces. The tests' "r02" is the test fixture's synthetic review round, not the motivating one, so the two are not meant to match. The comment now also mentions the JSON CRLF case.

Evidence (script output): `python3 -m unittest discover -s tests` -> OK; `tests/wrapper-failure-smoke.zsh` -> "wrapper failure smoke tests passed".

For each of R01-F1, R01-F2, R01-F3, R01-C1, R01-C2 write either "<ID> is resolved." or "<ID> remains open: <reason>". Report any new defect as F<n> [severity].
