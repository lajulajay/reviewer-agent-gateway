Verify your r01 items for the review-budget change (gateway commits 25c48e4,
875d644, now f9013ba). You are the backup reviewer; Codex is at its usage
limit. Owner: Claude.

Packets: `f9013ba-fixes.diff` (the fixes), `f9013ba-tests.diff` (new
provider-free tests; both suites pass), and `r01-dispositions.md` (the
owner's disposition of each r01 item, including the reasons F3 and F10 were
rejected and F4 and F9 partly rejected). The r01 items were:
R01-F1 [blocker]: In `review-budget.py`, daily review counting uses `datetime.fromtimestamp(f.stat().st_mtime).date()` rather than the date formatted in the artifact filename. Git operations (`git clone`, `git checkout`, `git worktree`) set the filesystem modification time of all checked-out files to the checkout date; any repository with 8 or more historical reviews in `.collab/` will immediately have its daily budget exhausted upon checkout, blocking all reviews across the repository for the entire day.
R01-F2 [blocker]: `reviewer-claims.py` produces inverted mechanical checks on legitimate findings about malformed or truncated identifiers. When a reviewer identifies a truncated hash (e.g. stating a quoted hex string is 62 characters while 64 was expected), `lengths` contains only 62; the script evaluates the expected claim (64), finds `abs(62 - 64) <= 3`, and emits a note claiming the reviewer stated the quoted value was 64 characters. Under PROTOCOL.md rules, this causes valid blocker findings to be falsely rejected.
R01-F3 [major]: In `review-budget.py`, when a review fails after invoking the model and writing a `.diagnostic.json`, retrying the review with the same output target creates the completed artifact without removing the diagnostic. `rounds()` yields both the diagnostic file and the completed artifact, double-counting the single invocation against both `max_rounds_per_topic` and `max_reviews_per_provider_per_day`.
R01-F4 [major]: The `SPENT` regex in `review-budget.py` omits post-model failure diagnostics produced by the wrappers, including `"Claude invocation failed"` (exit 70), `"Claude returned invalid JSON"` (exit 70), `"Gemini returned no valid response"` (exit 70), and `"Gemini returned no resolved model metadata"` (exit 74). These spent calls are ignored by `rounds()`, allowing excess rounds beyond the budget to reach the models.
R01-F5 [major]: In `review-budget.py`, diagnostic processing in `rounds()` hardcodes `hard=False` for all `.diagnostic.json` files. If a hard-tier review contacts the model and fails substance validation or times out, its quota expenditure is not counted against `max_hard_rounds_per_topic`, allowing subsequent hard-tier calls to reach the model.
R01-F6 [major]: In `review-budget.py`, `rounds()` skips all files in `.collab/` whose names do not match `NAME`. If a review is invoked with a non-standard output filename (such as omitting the provider prefix or using an alternate separator), `parse()` returns `None`, `prior` evaluates to empty, and the call bypasses round and daily budget caps.
R01-F7 [minor]: In `claude-review.sh`, `effort_round` is set to `follow_up` whenever `prior_rounds` on the topic is non-zero, regardless of provider. If the initial round on a topic was performed by Codex, Claude's first round on that topic runs at `low` effort instead of `medium`.
R01-F8 [minor]: In `reviewer-claims.py`, `CLAIM` does not require the word `hex` and matches general counts of characters or digits. Unrelated metrics on the same line as a hex string (such as line length limits or buffer write lengths within 3 of the hex length) trigger false mechanical check warnings.
R01-F9 [minor]: In `docs-check.py`, `record()` verifies only that some Decisions entry in the workstream contains the substring `"budget override"`. It does not check that the decision author was `user`, nor does it tie the approval to the specific round number or recorded override reason.
R01-F10 [minor]: In `review-budget.py`, topic history accumulates indefinitely across `.collab/` without date or workstream isolation. If a generic topic name is reused across different workstreams weeks or months apart, earlier rounds are counted, blocking the new topic from routine review.
R01-C1: Modify `review-budget.py` to determine daily review dates using the date parsed from the artifact filename via `NAME`, falling back to filesystem `st_mtime` only when no filename date is present, preventing git checkouts from exhausting the daily quota.
R01-C2: Fix `reviewer-claims.py` to eliminate inverted checks on truncated hex values by ensuring assertions about expected lengths are not misattributed as claims about the quoted hex value, and ensure unrelated character counts on the line do not trigger false notes.
R01-C3: Update `review-budget.py` so that a `.diagnostic.json` is ignored when an artifact with the matching base output name already exists in `.collab/`, preventing retried rounds from double-counting.
R01-C4: Expand `SPENT` in `review-budget.py` to cover all wrapper exit 70/74 failure messages occurring after model invocation (`"invocation failed"`, `"returned invalid JSON"`, `"returned no valid response"`, `"returned no resolved model metadata"`).
R01-C5: Record the requested tier in `.diagnostic.json` and have `rounds()` yield the actual tier so that spent hard-tier attempts count against `max_hard_rounds_per_topic`.
R01-C6: Require output filenames passed to wrappers and `review-budget.py` to conform strictly to `NAME`, failing immediately with an error rather than bypassing budget enforcement when an unparseable filename is provided.
R01-C7: Update `claude-review.sh` to determine `effort_round` based on prior Claude rounds on the topic rather than cross-provider topic rounds.
R01-C8: Update `docs-check.py` to verify that budget override decisions record `user` as the author and cite the specific round being overridden.

Write exactly one line per ID, using the full ID: either `<ID> is resolved.`
or `<ID> remains open: <reason>`. A rejected item is resolved if the stated
reason holds. Then label any new defect in the fixes, following the output
contract. You have no tools; review only the text.
