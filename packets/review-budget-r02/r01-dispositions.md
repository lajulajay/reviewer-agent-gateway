## Findings and conditions

| ID | Severity | Disposition | Status |
| :--- | :--- | :--- | :--- |
| R01-F1 | blocker | fix pending r02: daily cap reads the date from the output name; mtime only for undated names | open |
| R01-F2 | blocker | fix pending r02: note gives every stated hex length and the measured one, without attributing; PROTOCOL says it is not a verdict | open |
| R01-F3 | major | rejected: a retry under the same name is a second model call, so counting the diagnostic and the artifact counts two real calls | open |
| R01-F4 | major | fix pending r02 (partial): `returned`/`did not succeed` reasons now count; `invocation failed` stays uncounted because it includes usage-limit refusals that never ran (Codex r01 attempt, 2026-10-08) | open |
| R01-F5 | major | fix pending r02: diagnostics carry their requested/selected model into the hard-tier count | open |
| R01-F6 | major | fix pending r02: output names that do not parse, or whose provider prefix differs, are refused | open |
| R01-F7 | minor | fix pending r02: Claude effort keys on Claude's own earlier rounds | open |
| R01-F8 | minor | fix pending r02: claims must say hex/hexadecimal | open |
| R01-F9 | minor | fix pending r02 (partial): entry must name the round; the user-actor part is rejected because decision_entries already accepts only `- <date>, user, scope:` lines | open |
| R01-F10 | minor | rejected: counting a topic across dates is deliberate so a date change cannot reset the cap (user decision 2026-10-08); a reused name gets a refusal that names the topic | open |
| R01-C1 | condition | fix pending r02 (F1) | open |
| R01-C2 | condition | fix pending r02 (F2, F8) | open |
| R01-C3 | condition | rejected with F3 | open |
| R01-C4 | condition | partial with F4 | open |
| R01-C5 | condition | fix pending r02 (F5); the existing diagnostic already records the requested model | open |
| R01-C6 | condition | fix pending r02 (F6) | open |
| R01-C7 | condition | fix pending r02 (F7) | open |
| R01-C8 | condition | partial with F9 | open |

## Log
