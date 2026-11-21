Review a one-line change to the gateway's documentation checker (`docs-check.py`).

Context: a workstream row may be dispositioned `verified rNN` only when review artifact rNN contains the line "<ID> is resolved." at the start of a line. The check used `(?m)^<ID> is resolved\.$`. A Codex review wrote "R02-F1 is resolved." followed by two spaces, so the check rejected a genuine resolution. Review artifacts are immutable, so the checker must tolerate it.

Change (change.diff; surrounding function in docs-check-excerpt.py): the pattern becomes `(?m)^<ID> is resolved\.[ \t]*$`, i.e. only trailing spaces or tabs are allowed. The separate contradiction check (`^\W*<ID> remains open`) is unchanged.

The new test accepts trailing two spaces and a tab, and still rejects trailing " but see below", ".", "  x", and a non-breaking space; the existing test still rejects a quoted "> " line and a contradiction.

Evidence (script output): `python3 -m unittest tests.test_docs_check` -> "Ran 27 tests ... OK".

Questions:
1. Does allowing trailing [ \t] weaken the check in any way that matters (could a non-affirmative or ambiguous line now pass)?
2. Should other trailing whitespace (e.g. "\r" from CRLF files) also be accepted, or is rejecting it the safer default?
3. Do the tests establish the behaviour?

Label findings F<n> [blocker|major|minor] and conditions C<n>.
