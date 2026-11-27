Backup review (r06) of a small docs-check change after the Codex topic budget (five rounds) was used. Packets: docs-check-extractions-full-for-gemini.diff (complete change against main: docs-check.py and tests) and codex-2026-11-27-docs-check-extractions-r05.md (the last Codex review).

Purpose. `docs-check.py record` flags any `.collab/` file that is not a review artifact. An owner's hand extraction of a failed reviewer invocation's text, `<stem>.extracted.md`, must be allowed only when: `<stem>.diagnostic.json` beside it records a non-zero integer `exit_code`; `<stem>.extracted.md.sha256` exists with a first field equal to the file's SHA-256; and some workstream's `## Reviews` section contains the exact line `Owner extraction of a failed invocation: `<path>`` (optional "- " and trailing "."). Raw `.collab/` files are never edited.

History. Codex r01–r04 drove: failed-exit requirement, read-error handling, exact-line classification, restriction to the Reviews section. r05 found four Markdown-parsing bypasses (indented fence delimiters, unequal backtick runs, multi-line inline code, inline code inside comments). The owner replaced all parsing with a refusal: if the Reviews section contains any of ```, ~~~, <!-- or -->, no line in it counts as a classification. Tests include every r04 and r05 example; reverting the refusal fails the test (script check). `python3 -m unittest tests.test_docs_check` -> OK (34 tests). The one real repository using it (kalshi-temperature-bot) passes.

Questions:
1. Does the marker refusal close R05-F1 to R05-F4 and the earlier fence/comment findings? Is any quoted, commented or example line still able to count?
2. Any other way the exception can hide a file that should be flagged, or crash the checker?
3. Is the change now proportionate, or is any remaining open item a policy choice for the user?

For each of R01-F1, R02-F1, R03-F1, R04-F1, R04-F2, R05-F1, R05-F2, R05-F3, R05-F4 write either "<ID> is resolved." or "<ID> remains open: <reason>". Report any new defect as F<n> [severity]; conditions as C<n>:. Review only; no edits.
