Follow-up review (r04) of the docs-check extraction exception. r03 returned REJECT: R03-F1 (classification line matched inside Markdown comments or fenced examples), with R01-F1 and R02-F1 open through it; R01-F2 and R02-F2 resolved. docs-check-extractions-r03-to-r04.diff is the delta since r03.

Owner's response:
- R03-F1 (and R01-F1, R02-F1): the classification line is now read only from a workstream's `## Reviews` section, the section where owners index review artifacts, after removing fenced code blocks (``` or ~~~) and HTML comments (single- and multi-line). The exact-line regex is unchanged. Tests: the line in the Log section, in a fenced block, in a multi-line comment and in a one-line comment are each rejected; the same line as plain text in the Reviews section is accepted. Script check: making `review_statements` return the whole Reviews section unfiltered fails the test.
- Scope note: the classification is a committed owner statement in the record that also requires a failed-exit diagnostic and a matching checksum beside the file; it cannot alter any indexed review's checks.

Evidence (script output): `python3 -m unittest tests.test_docs_check` -> OK (34 tests). kalshi-temperature-bot (both lines in its Reviews section): "docs-check record: PASS (0 errors)".

For each of R01-F1, R02-F1, R03-F1 write either "<ID> is resolved." or "<ID> remains open: <reason>". Report any new defect as F<n> [severity].
