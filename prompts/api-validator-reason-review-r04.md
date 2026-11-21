Follow-up review (r04) of the gateway API-route validator-reason change. Your r03 resolved R02-F1 and R02-C1 and returned ACCEPT WITH CONDITIONS with R03-F1 [minor] and R03-C1 (the two formatted validator messages were only counted, not checked). api-call.py and reviewer-validate.py are unchanged; tests-r04.diff is the full current test diff against main.

Owner's response to R03-F1 and R03-C1: new test `test_formatted_validator_messages_are_recognized` runs the real reviewer-validate.py on a short reply and on a reply with "F1 [critical]", and asserts `validator_reason()` maps the two outputs to "review is shorter than 400 characters" and the fixed severity reason. It then writes two edited copies of the validator (one rewording each f-string) to a temp directory, runs each the same way, and asserts the edited message now falls to "unrecognized validator output (exit 1)". So a change to either formatted message's text fails the test unless `validator_reason()` is updated with it. The test also asserts both original f-string source texts are present, so the edits cannot silently become no-ops.

Evidence (script output): `python3 -m unittest discover -s tests` -> OK; `tests/wrapper-failure-smoke.zsh` -> "wrapper failure smoke tests passed".

For R03-F1 and R03-C1 write either "<ID> is resolved." or "<ID> remains open: <reason>". Report any new defect as F<n> [severity].
