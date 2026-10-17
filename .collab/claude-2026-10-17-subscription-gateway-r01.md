# Claude review

Owner: codex
Wrapper revision: c654e4496daa19e2bcdb317023239162d2409243
Requested model: opus
Selected model: claude-opus-5-5
Resolved model(s): claude-opus-5-5
Effort: medium
Usage: {"usage":{"input_tokens":2,"output_tokens":8729,"cache_read_input_tokens":0,"cache_creation_input_tokens":42351},"total_cost_usd":0.513396,"duration_ms":91750,"num_turns":1}

F1 [major]: Proven gap: automatic selection can pick an agent that co-authored the work under review. `auto-review.sh` accepts only `--owner` set to `codex` or `claude` (`[[ $# -ge 2 && ( "$2" == codex || "$2" == claude ) ]]`). `reviewer-select.py` then excludes only that owner (`provider != owner`), and `tie_break_order` puts Kimi first (`"tie_break_order": ["kimi", "claude", "codex"]`). This commit is an example: Kimi began it and Codex completed it. `auto-review.sh --owner codex` would choose Kimi first (as the test `self.assertEqual(self.select("codex"), ["kimi", "claude"])` shows), so Kimi would review its own work. That violates PROTOCOL's "A change is reviewed only by an agent that did not author it." Separately, PROTOCOL says "Kimi and Gemini are reviewer-only and never own work," yet the gateway has no way to record Kimi as an author. For Claude/Codex mixtures, PROTOCOL says to "use an active reviewer that authored none of it," but auto mode cannot express more than one author. It will also pick the other co-author whenever Kimi is inactive or capped.

F2 [major]: Uncertain (the Claude and Codex wrappers are not in the packet). Failover safety depends on exit codes 69 and 78 only ever meaning "pre-invocation" in `claude-review.sh` and `codex-review.sh`. The dispatcher assumes this (`[[ $code -eq 69 || $code -eq 78 ]] || exit "$code"`, followed by the message "unavailable before model invocation"). The packet only shows this holds for Kimi, where `interrupted()` returns 70 once `model_invocation_started=1`. The removed Ollama wrapper did the opposite: it exited 78 after `ollama run` ("Ollama access denied…"). PROTOCOL also lists "usage limit" as an unavailability case, and the budget comment says "invocation failed" covers "calls refused at a usage limit". If either wrapper maps a post-invocation CLI result, such as a usage-limit or auth error from the run step, to 78, auto mode sends a second model call for the same request. The README promise "it never repeats a call after model invocation" would then be false for that wrapper.

F3 [major]: Uncertain (undocumented provider behavior). Tool isolation for Kimi rests on CLI behavior the gateway does not verify:
- the Markdown-frontmatter `--agent-file` format with `tools: []` / `subagents: []`;
- `KIMI_LOOP_MAX_STEPS_PER_TURN`, `KIMI_MODEL_THINKING_EFFORT`, `KIMI_DISABLE_CRON`, and the other environment knobs.

The wrapper does not neutralize user-level MCP server configuration or other `KIMI_CODE_HOME` configuration (for example approval or yolo defaults). It runs with the user's home directory reachable; only the cwd is empty. The stream check is post hoc (`tool_events=… || fail 70`), so any tool that runs has already executed before rejection. The smoke test checks only that the mock sees these arguments, not real CLI semantics. README hedges this ("documented to enforce"). PROTOCOL instead states flatly that "The wrappers launch reviewers with tool and subagent access disabled."

F4 [minor]: Proven doc overreach. PROTOCOL's "fail closed if a tool event appears in the provider stream" is written for all wrappers. Only the Kimi wrapper in this diff implements such a check. Similarly, README and PROTOCOL now say failed calls that "reached or may have reached the model" count for every provider. Only Kimi is conservative (`if "model_invocation_began" in d`). Other providers still depend on the `SPENT` regex and explicitly exclude "invocation failed".

F5 [minor]: Proven date mismatch. The selector computes daily counts using wall-clock `today = today or date.today()` and ignores the date parsed from the template (`return parsed[1]` discards `parsed[2]`). The budget's daily cap is documented as "count[ing] the daily cap by the date in the output name." When the template date is not today (a run after midnight, or a reused template), the selector can rank or filter providers against the wrong day's counts. A resulting budget refusal (79) is deliberately not failed over, so auto mode stops even when another eligible reviewer has room.

F6 [minor]: Proven workflow interaction. Every wrapper now refuses a name that already has a diagnostic (`! -e "$outdir/${base%.md}.diagnostic.json"`). Budget refusals (exit 79) write such a diagnostic, as `brefused` asserts. So after a refusal at `rNN`, the same `rNN` can never be rerun under a user-approved `REVIEW_BUDGET_OVERRIDE`. PROTOCOL ties approval to "that round (`rNN`)," and the docs do not say the approved rerun must use a new round number.

F7 [minor]: Proven. `REVIEWER_ROSTER` overrides the roster from the environment (`roster="${REVIEWER_ROSTER:-$gateway/reviewer-roster.json}"`). This bypasses the committed-roster guarantee that the dirty-tree check gives `reviewer-roster.json`, and it is undocumented. Unlike `KIMI_REVIEW_MODEL_POLICY`, the README does not label it as test-only.

F8 [minor]: Proven, conservative direction. `model_invocation_started=1` is set before `perl … exec kimi … --prompt "$(<"$combined")"`. With the 800000-byte default plus environment, the argv may hit macOS ARG_MAX. An exec failure (E2BIG) would then be recorded as a spent round that never reached the model. The full prompt in argv is also visible to local `ps` output.

F9 [minor]: Uncertain. Hard-tier accounting for Kimi relies on alias names (`selected.startswith("kimi-code/k3")`). If the managed `kimi-code/kimi-for-coding` alias is served by a K3-family model, routine Kimi calls would consume hard-class capacity without being counted against the hard cap. The artifact itself records "Resolved model(s): not reported."

C1: Resolve F1 before using auto mode on this commit or any other mixed-authorship work. Either add an author-set option (for example a repeatable `--author codex|claude|kimi`) that the selector excludes, or make PROTOCOL and README explicitly require direct, manual reviewer choice for any packet that includes Kimi-authored or mixed work. This commit's own review must go to Claude or Gemini, not Kimi.

C2: Provide the relevant lines of `claude-review.sh` and `codex-review.sh`, or a test, showing that exit codes 69 and 78 are produced only before the provider CLI's model call. Otherwise, narrow auto-review failover to an explicit pre-invocation signal (such as a diagnostic `model_invocation_began:false`) rather than exit codes alone.

C3: Record a live negative probe against the installed Kimi CLI. It must show that, with this agent file and environment, a prompt that explicitly requests a shell or file tool produces no tool execution. Also confirm whether user MCP and approval configuration under `KIMI_CODE_HOME` is loaded, and neutralize it if so. Until then, change PROTOCOL's isolation sentence to match README's hedged wording.

C4: Make the selector use the date parsed from the auto template, matching the budget's name-date rule. Add a test where the template date differs from wall-clock today.

C5: Correct the PROTOCOL and README statements identified in F4 so they describe per-provider behavior accurately. Document that `REVIEWER_ROSTER` is a test-only override, or remove it. Document how a budget-override rerun is named after a refusal has burned the `rNN` name.

ATTESTATION: all actionable findings and conditions are labeled.
VERDICT: ACCEPT WITH CONDITIONS
