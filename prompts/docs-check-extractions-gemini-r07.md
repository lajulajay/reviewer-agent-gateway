Check (r07) of the owner's fixes for your r06 on the docs-check extraction exception. docs-check-extractions-r06-to-r07.diff is the delta since r06.

Owner's response:
- R06-F1 and R06-C1: the classification regex no longer allows leading whitespace: `^(?:- )?Owner extraction of a failed invocation: `<path>`\.?[ \t]*$`, so an indented-code-block line cannot match. `review_statements` also refuses (returns empty) when the Reviews section contains `<pre` or `<code` in any case, alongside ```, ~~~, <!-- and -->. Tests reject the line indented by four spaces, a tab and one space, inside `<pre>`, and inside `<CODE>`.

Evidence (script output): `python3 -m unittest tests.test_docs_check` -> OK (34 tests); kalshi-temperature-bot "docs-check record: PASS (0 errors)".

For R06-F1 and R06-C1 write either "<ID> is resolved." or "<ID> remains open: <reason>". Report any new defect as F<n> [severity]. Review only.
