Review (r01, routine) of a small docs-check change. Packet: docs-check-extractions-2026-11-27.diff (full diff against main).

Background. `docs-check.py record` flags every file in a repository's `.collab/` that is not a recognizable review artifact (legacy files excepted; the legacy list may only shrink). When a reviewer wrapper fails after the model returned a complete review (for example Gemini exit 70, output-token cutoff), the wrapper leaves `<stem>.diagnostic.json` (already skipped by the check). In kalshi-temperature-bot two such failures each have an owner extraction of the review text, `<stem>.extracted.md`, with a sidecar `<stem>.extracted.md.sha256`. By user decision these are recorded as failed invocations, not reviews, so they are not indexed and the check flags them. Raw `.collab/` files are never edited, renamed or deleted.

Change. A `.collab/` file named `<stem>.extracted.md` is skipped only when `<stem>.diagnostic.json` exists beside it and `<stem>.extracted.md.sha256` exists with a first field equal to the file's SHA-256; otherwise it is reported as an extraction without a matching diagnostic and checksum sidecar. Other files are unchanged. New test: flagged without the diagnostic; passes with diagnostic and correct sidecar; flagged with a wrong or missing sidecar; another unrecognized file is still flagged.

Evidence (script output): `python3 -m unittest tests.test_docs_check` -> Ran 34 tests, OK. The new test fails against the main-branch docs-check.py ("is not a recognizable review artifact" instead of the new message) and passes with the change. Running the changed checker on kalshi-temperature-bot: "docs-check record: PASS (0 errors)" (previously 2 errors, both these extractions).

Questions:
1. Can the exception hide a file that should be flagged (a real review left unindexed, an arbitrary note renamed to .extracted.md, a sidecar that does not bind the content)?
2. Is the error message accurate in every failure branch?
3. Is the test adequate, and would it fail under the suspected bugs?

Prohibited: no edits; review only. Label findings `F<n> [severity]:` and conditions `C<n>:`.
