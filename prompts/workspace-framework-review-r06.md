Round 6: implementation review. Packet: (1) proposal v6 (the design, final
after five paper rounds; the user approved moving to a pilot), (2) the
implementation diff: shared output contract, validator, wrapper provenance,
docs-check.py, templates, tests. You have no tools; review only the text.

1. Round-5 blockers: does v6 together with this implementation resolve
   R05-F3 (closure quote must name the finding and affirm resolution; the tool
   checks the quote occurs in the cited review) and R05-F11 (claim narrowed to
   wrapper provenance; wrapper refuses uncommitted wrapper changes and records
   its revision)? For each, say explicitly "R05-F3 is resolved" or "R05-F3
   remains open" (and likewise R05-F11), with the reason.
2. Round-5 conditions C1–C6: state for each whether it is now met.
3. Correctness and security of docs-check.py and the wrapper changes: false
   passes (an open obligation, missing row, tampered artifact, or over-budget
   file that passes), false failures that would block the pilot, parsing
   fragility, and any way the tool could be gamed.
4. Spec delta to judge: `carried <ID>` (a finding closes when the later
   round's re-raised finding, or a same-round finding a condition restates,
   closes) is not in v6. Is it sound?
5. Is the implementation ready for the single-session pilot in a clean,
   paused repository? If not, the smallest set of changes.
