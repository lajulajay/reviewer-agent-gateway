#!/bin/zsh
set -euo pipefail

source_root="$(cd "$(dirname "$0")/.." && pwd -P)"
test_root="$(mktemp -d "${TMPDIR:-/tmp}/reviewers-test.XXXXXX")"
trap 'rm -rf "$test_root"' EXIT INT TERM
# Wrappers refuse uncommitted changes, so run them from a committed snapshot
# of the working tree rather than through a bypass.
root="$test_root/gateway"; mkdir -p "$root"
cp -p "$source_root"/*.sh "$source_root"/*.py "$source_root"/*.json "$source_root"/output-contract.txt "$root"/
git -C "$root" init -q && git -C "$root" add -A && git -C "$root" -c user.email=t@t -c user.name=t commit -q -m snapshot
mkdir -p "$test_root/.collab" "$test_root/packet" "$test_root/shared" "$test_root/bin"
print 'Review prompt.' > "$test_root/prompt.md"
print 'Safe packet fixture.' > "$test_root/packet/source.md"
print 'Shared review prompt.' > "$test_root/shared/prompt.md"
print 'Shared packet fixture.' > "$test_root/shared/packet.md"
unset GEMINI_API_KEY GOOGLE_API_KEY

cat > "$test_root/bin/claude" <<'EOF'
#!/bin/zsh
if [[ "$1" == auth && "$2" == status ]]; then
  jq -n --arg method "${CLAUDE_MOCK_AUTH_METHOD:-claude.ai}" '{loggedIn:true,authMethod:$method,subscriptionType:"pro"}'
  exit 0
fi
if [[ "${CLAUDE_TEST_MODE:-}" == success ]]; then
  [[ -z "${CLAUDE_MOCK_ARGS:-}" ]] || print -r -- "$*" > "$CLAUDE_MOCK_ARGS"
  model=""
  while [[ $# -gt 0 ]]; do
    if [[ "$1" == --model ]]; then model="$2"; break; fi
    shift
  done
  [[ -z "${CLAUDE_MOCK_MARKER:-}" ]] || print -r -- "$model" > "$CLAUDE_MOCK_MARKER"
  body=""
  for i in {1..8}; do body+="The supplied packet is internally consistent and the proposed boundary is testable. "; done
  body+=$'The implementation preserves the reviewed input boundary and creates an auditable artifact.\n'"${CLAUDE_MOCK_EXTRA:-}"$'\n\nATTESTATION: all actionable findings and conditions are labeled.\n\nVERDICT: ACCEPT'
  jq -n --arg model "${CLAUDE_MOCK_RESOLVED:-$model}" --arg result "$body" '{is_error:false,result:$result,modelUsage:{($model):{}},usage:{input_tokens:10,output_tokens:20,cache_read_input_tokens:0,cache_creation_input_tokens:0},total_cost_usd:0.01,duration_ms:5,num_turns:1}'
  exit 0
fi
exit 42
EOF
cat > "$test_root/bin/kimi" <<'EOF'
#!/bin/zsh
if [[ "$1" == provider && "$2" == list && "$3" == --json ]]; then
  if [[ "${KIMI_MOCK_AUTH:-oauth}" == hang-provider ]]; then
    [[ -z "${KIMI_PROVIDER_HANG_MARKER:-}" ]] || : > "$KIMI_PROVIDER_HANG_MARKER"
    sleep 30
  fi
  case "${KIMI_MOCK_AUTH:-oauth}" in
    oauth) provider='{"type":"kimi","oauth":{"account":"subscription"}}' ;;
    empty_oauth) provider='{"type":"kimi","oauth":{}}' ;;
    api_key) provider='{"type":"kimi","api_key":"configured"}' ;;
    signed_out) provider='{"type":"kimi"}' ;;
    wrong_provider) provider='{"type":"custom","oauth":{"account":"other"}}' ;;
  esac
  jq -n --argjson provider "$provider" '{models:{"kimi-code/k3":{provider:"managed:kimi-code"},"kimi-code/kimi-for-coding":{provider:"managed:kimi-code"}},providers:{"managed:kimi-code":$provider}}'
  exit 0
fi
[[ "$1" != --version ]] || { print 'kimi 2.2.0'; exit 0; }
all_args="$*"; model=""; agent=""; skills=""; prompt=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --model) model="$2"; shift 2 ;;
    --agent-file) agent="$2"; shift 2 ;;
    --skills-dir) skills="$2"; shift 2 ;;
    --prompt) prompt="$2"; shift 2 ;;
    *) shift ;;
  esac
done
[[ -z "${KIMI_MOCK_ARGS:-}" ]] || print -r -- "$all_args" > "$KIMI_MOCK_ARGS"
[[ -z "${KIMI_MOCK_PROMPT:-}" ]] || print -r -- "$prompt" > "$KIMI_MOCK_PROMPT"
[[ -z "${KIMI_MOCK_MARKER:-}" ]] || print -r -- "model=$model effort=${KIMI_MODEL_THINKING_EFFORT:-}" > "$KIMI_MOCK_MARKER"
[[ -n "$model" && -n "$agent" && -n "$skills" && -n "$prompt" && " $all_args " == *" --output-format stream-json "* ]] || exit 77
[[ -z "$(ls -A)" && -d "$skills" && -z "$(ls -A "$skills")" ]] || exit 77
grep -Fx 'tools: []' "$agent" >/dev/null && grep -Fx 'subagents: []' "$agent" >/dev/null || exit 77
[[ "${KIMI_CODE_NO_AUTO_UPDATE:-}" == 1 && "${KIMI_DISABLE_CRON:-}" == 1 && "${KIMI_LOOP_MAX_STEPS_PER_TURN:-}" == 1 ]] || exit 77
[[ -z "${KIMI_API_KEY:-}" && -z "${MOONSHOT_API_KEY:-}" && -z "${KIMI_MODEL_NAME:-}" && -z "${KIMI_MODEL_BASE_URL:-}" ]] || exit 77
[[ "${KIMI_TEST_MODE:-}" != hang ]] || sleep 30
case "${KIMI_TEST_MODE:-}" in
  success|tool|schema-tool|incomplete)
    jq -nc '{role:"assistant",content:"draft"}'
    if [[ "${KIMI_TEST_MODE:-}" == tool ]]; then
      jq -nc '{role:"assistant",content:"",tool_calls:[{name:"shell"}]}'
      jq -nc '{role:"tool",name:"shell",content:"blocked"}'
    fi
    [[ "${KIMI_TEST_MODE:-}" != schema-tool ]] || jq -nc '{type:"tool_call",name:"shell"}'
    body=""
    if [[ "${KIMI_TEST_MODE:-}" == incomplete ]]; then
      body="partial"
    else
      for i in {1..8}; do body+="The supplied packet is internally consistent and the proposed boundary is testable. "; done
      body+=$'The implementation preserves the reviewed input boundary and creates an auditable artifact.\n\nATTESTATION: all actionable findings and conditions are labeled.\n\nVERDICT: ACCEPT'
    fi
    jq -nc --arg content "$body" '{role:"assistant",content:$content}'
    exit 0 ;;
esac
print -u2 'simulated Kimi invocation failure'
exit 42
EOF
cat > "$test_root/bin/agy" <<'EOF'
#!/bin/zsh
[[ "$1" != --version ]] || { print 1.2.15; exit 0; }
if [[ "$1" == -p && "$2" == /usage ]]; then
  [[ -z "${AGY_MOCK_SIGNED_OUT:-}" ]] || exit 1
  jq -n --argjson q "${AGY_MOCK_QUOTA:-0.9}" '{status:"SUCCESS",command:{name:"usage",data:{groups:[{name:"Gemini Models",buckets:[{id:"gemini-weekly",remaining_fraction:$q}]}]}}}'
  exit 0
fi
[[ -z "${AGY_MOCK_MARKER:-}" ]] || print -r -- "$*" > "$AGY_MOCK_MARKER"
# Every review call must be isolated: plan quota, pinned version, deny-all hook.
[[ -z "${GEMINI_API_KEY:-}" && "${AGY_CLI_DISABLE_AUTO_UPDATE:-}" == 1 && -x .agents/deny-tools.sh ]] || exit 77
jq -e '."reviewer-isolation".PreToolUse[0].matcher == "*"' .agents/hooks.json >/dev/null || exit 77
[[ " $* " == *" --sandbox "* && " $* " != *" --mode "* && " $* " == *" --disable-slash-commands "* ]] || exit 77
model=""; args=("$@")
for i in {1..$#args}; do [[ "${args[$i]}" != --model ]] || model="${args[$((i+1))]}"; done
[[ "${AGY_TEST_MODE:-}" != hang ]] || sleep 30
jq -nc --arg model "${AGY_MOCK_RESOLVED:-$model}" '{event:"init",conversation_id:"conv-test",init:{model:$model}}'
if [[ "${AGY_TEST_MODE:-}" == error ]]; then print -u2 'AGY_ERROR: simulated model failure'; exit 3; fi
if [[ "${AGY_TEST_MODE:-}" == tool ]]; then
  decision="$(cd .agents && print '{"toolCall":{"name":"run_command","args":{"CommandLine":"ls"}}}' | ./deny-tools.sh)"
  [[ "$(jq -r .decision <<< "$decision")" == deny ]] || exit 77
fi
if [[ "${AGY_TEST_MODE:-}" == success || "${AGY_TEST_MODE:-}" == tool ]]; then
  body=""
  for i in {1..8}; do body+="The supplied packet is internally consistent and the proposed boundary is testable. "; done
  body+=$'The implementation preserves the reviewed input boundary and creates an auditable artifact.\n\nATTESTATION: all actionable findings and conditions are labeled.\n\nVERDICT: ACCEPT'
  jq -nc --arg response "$body" '{event:"result",result:{conversation_id:"conv-test",status:"SUCCESS",response:$response,usage:{total_tokens:1}}}'
  exit 0
fi
# Output-token cutoff: agy exits 0 with status ERROR and whatever was written.
if [[ "${AGY_TEST_MODE:-}" == cutoff || "${AGY_TEST_MODE:-}" == cutoff-partial ]]; then
  body=""
  for i in {1..8}; do body+="The supplied packet is internally consistent and the proposed boundary is testable. "; done
  body+=$'\nF1 [major]: see [proxy](file:///tmp/reviewers-gemini.X/workspace/proxy.ts#L3) for the redirect.\nATTESTATION: all actionable findings and conditions are labeled.\n'
  [[ "$AGY_TEST_MODE" == cutoff-partial ]] || body+=$'\nVERDICT: REJECT'
  err=$'Your previous response was cut off because it exceeded the output token limit\nRetries remaining: 3'
  jq -nc --arg response "$body" --arg err "${AGY_MOCK_ERROR:-$err}" '{event:"result",result:{conversation_id:"conv-test",status:"ERROR",error:$err,response:$response,usage:{total_tokens:1}}}'
  exit 0
fi
exit 42
EOF
cat > "$test_root/bin/codex" <<'EOF'
#!/bin/zsh
[[ "$1" != --version ]] || { print codex-cli 0.159.3; exit 0; }
if [[ "$1" == login && "$2" == status ]]; then print "${CODEX_MOCK_LOGIN:-Logged in using ChatGPT}"; exit 0; fi
[[ "$1" == exec ]] || exit 64
[[ -z "${CODEX_MOCK_MARKER:-}" ]] || print -r -- "$*" > "$CODEX_MOCK_MARKER"
# Every review call must load no user config, persist nothing, and expose no tools.
[[ -z "${OPENAI_API_KEY:-}" ]] || exit 77
for flag in --ephemeral --ignore-user-config --ignore-rules "-s read-only" "--disable shell_tool" "--disable apps" "--disable code_mode_host" "--disable multi_agent"; do
  [[ " $* " == *" $flag "* ]] || { print -u2 "missing $flag"; exit 77; }
done
out=""; args=("$@")
for i in {1..$#args}; do [[ "${args[$i]}" != -o ]] || out="${args[$((i+1))]}"; done
input="$(cat)"; [[ -z "${CODEX_MOCK_STDIN:-}" ]] || print -r -- "$input" > "$CODEX_MOCK_STDIN"
[[ "${CODEX_TEST_MODE:-}" != hang ]] || sleep 30
print '{"type":"thread.started","thread_id":"t"}'
print '{"type":"item.completed","item":{"type":"error","message":"Code Mode is unavailable because code-mode host is disabled."}}'
print '{"type":"turn.started"}'
[[ "${CODEX_TEST_MODE:-}" != tool ]] || print '{"type":"item.completed","item":{"type":"error","message":"code-mode host is disabled"}}'
case "${CODEX_TEST_MODE:-}" in
  success|tool)
    body=""
    for i in {1..8}; do body+="The supplied packet is internally consistent and the proposed boundary is testable. "; done
    print -r -- "$body"$'\n\nATTESTATION: all actionable findings and conditions are labeled.\n\nVERDICT: ACCEPT' > "$out"
    print '{"type":"turn.completed","usage":{"input_tokens":1}}'
    exit 0 ;;
  incomplete) print -r -- "partial" > "$out"; exit 0 ;;
esac
exit 42
EOF
chmod 755 "$test_root/bin/claude" "$test_root/bin/kimi" "$test_root/bin/agy" "$test_root/bin/codex"
cat > "$test_root/claude-policy.json" <<'EOF'
{"hard_model":"claude-opus-5-5","routine_two_releases_down_scope":"all_models","models_newest_first":[
  {"id":"claude-sonnet-5-5","released_on":"2026-09-28","included_no_credits":true},
  {"id":"claude-opus-5-5","released_on":"2026-09-22","included_no_credits":true},
  {"id":"claude-opus-5","released_on":"2026-07-24","included_no_credits":true},
  {"id":"claude-sonnet-5","released_on":"2026-06-30","included_no_credits":true}
]}
EOF
cat > "$test_root/claude-policy-two-models.json" <<'EOF'
{"hard_model":"claude-opus-5-5","routine_two_releases_down_scope":"all_models","routine_fallback_model":"claude-sonnet-5-5","models_newest_first":[
  {"id":"claude-sonnet-5-5","released_on":"2026-09-28","included_no_credits":true},
  {"id":"claude-opus-5-5","released_on":"2026-09-22","included_no_credits":true}
]}
EOF
[[ "$(python3 "$root/claude-model-select.py" "$test_root/claude-policy-two-models.json" opus)" == claude-opus-5-5 ]]
[[ "$(python3 "$root/claude-model-select.py" "$test_root/claude-policy-two-models.json" sonnet)" == claude-sonnet-5-5 ]]

# Consumer shims must resolve the canonical gateway before argument validation.
# This fixture deliberately passes no arguments, so it cannot invoke a provider.
consumer_root="$test_root/prediction-markets/shim-consumer"
mkdir -p "$consumer_root/reviewers" "$test_root/reviewer-agent-gateway"
for wrapper in claude-review.sh codex-review.sh gemini-review.sh kimi-review.sh auto-review.sh; do
  cp "$root/$wrapper" "$test_root/reviewer-agent-gateway/$wrapper"
  cat > "$consumer_root/reviewers/$wrapper" <<EOF
#!/bin/zsh
set -euo pipefail
reviewer_root="\$(cd "\$(dirname "\$0")/../../../reviewer-agent-gateway" && pwd -P)"
exec "\$reviewer_root/$wrapper" "\$@"
EOF
  chmod 755 "$consumer_root/reviewers/$wrapper"
  set +e
  "$consumer_root/reviewers/$wrapper" >/dev/null 2>&1
  code=$?
  set -e
  [[ $code -eq 64 ]]
done

run_failure() {
  local wrapper="$1" model="$2" output="$3"; shift 3
  set +e
  PATH="$test_root/bin:$PATH" CLAUDE_REVIEW_MODEL_POLICY="$test_root/claude-policy.json" \
    "$root/$wrapper" "$model" "$test_root/prompt.md" "$test_root/.collab/$output" "$test_root/packet/source.md" >/dev/null 2>&1
  local code=$?
  set -e
  [[ $code -ne 0 ]]
  [[ -s "$test_root/.collab/${output%.md}.diagnostic.json" || -s "$test_root/.collab/${output%.json}.diagnostic.json" ]]
}

run_failure kimi-review.sh routine kimi.md
run_failure claude-review.sh sonnet claude.md
run_failure gemini-review.sh hard gemini.json
# A diagnostic from a previous attempt is refused before the provider runs.
claude_refused_args="$test_root/claude-refused-args"; : > "$claude_refused_args"
set +e
PATH="$test_root/bin:$PATH" CLAUDE_REVIEW_MODEL_POLICY="$test_root/claude-policy.json" CLAUDE_TEST_MODE=success \
  CLAUDE_MOCK_ARGS="$claude_refused_args" \
  "$root/claude-review.sh" sonnet "$test_root/prompt.md" \
  "$test_root/.collab/claude.md" "$test_root/packet/source.md" >/dev/null 2>&1
code=$?
set -e
[[ $code -eq 65 && ! -s "$claude_refused_args" ]]

# Tier selection pins a full model ID and checks what Claude reports using.
claude_marker="$test_root/claude-marker"
PATH="$test_root/bin:$PATH" CLAUDE_REVIEW_MODEL_POLICY="$test_root/claude-policy.json" \
  CLAUDE_TEST_MODE=success CLAUDE_MOCK_MARKER="$claude_marker" \
  "$root/claude-review.sh" opus "$test_root/prompt.md" \
  "$test_root/.collab/claude-opus.md" "$test_root/packet/source.md" >/dev/null
[[ "$(<"$claude_marker")" == claude-opus-5-5 ]]
grep -Fx 'Selected model: claude-opus-5-5' "$test_root/.collab/claude-opus.md" >/dev/null

PATH="$test_root/bin:$PATH" CLAUDE_REVIEW_MODEL_POLICY="$test_root/claude-policy.json" \
  CLAUDE_TEST_MODE=success CLAUDE_MOCK_MARKER="$claude_marker" \
  "$root/claude-review.sh" sonnet "$test_root/prompt.md" \
  "$test_root/.collab/claude-routine.md" "$test_root/packet/source.md" >/dev/null
[[ "$(<"$claude_marker")" == claude-sonnet-5 ]]

set +e
PATH="$test_root/bin:$PATH" CLAUDE_REVIEW_MODEL_POLICY="$test_root/claude-policy.json" \
  CLAUDE_TEST_MODE=success CLAUDE_MOCK_RESOLVED=claude-opus-5 \
  "$root/claude-review.sh" opus "$test_root/prompt.md" \
  "$test_root/.collab/claude-mismatch.md" "$test_root/packet/source.md" >/dev/null 2>&1
code=$?
set -e
[[ $code -eq 74 && -s "$test_root/.collab/claude-mismatch.diagnostic.json" ]]
[[ ! -e "$test_root/.collab/claude-mismatch.md" ]]

set +e
PATH="$test_root/bin:$PATH" CLAUDE_REVIEW_MODEL_POLICY="$test_root/claude-policy.json" \
  CLAUDE_TEST_MODE=success CLAUDE_MOCK_AUTH_METHOD=api_key \
  "$root/claude-review.sh" opus "$test_root/prompt.md" \
  "$test_root/.collab/claude-api-auth.md" "$test_root/packet/source.md" >/dev/null 2>&1
code=$?
set -e
[[ $code -eq 78 && -s "$test_root/.collab/claude-api-auth.diagnostic.json" ]]
[[ ! -e "$test_root/.collab/claude-api-auth.md" ]]

# Gemini (agy) policy pins both tiers, inlines the packet, and records metadata.
agy_marker="$test_root/agy-marker"
# GEMINI_OUT_ROOT puts the outputs in another repository, away from the daily cap.
gemini() {
  local output="$1"; shift
  PATH="$test_root/bin:$PATH" AGY_MOCK_MARKER="$agy_marker" "$@" "$root/gemini-review.sh" --packet-root "$test_root" \
    "${GEMINI_MODEL:-pro}" "$test_root/prompt.md" "${GEMINI_OUT_ROOT:-$test_root}/.collab/$output" "$test_root/packet/source.md"
}
gemini_fails() {
  local expected="$1" output="$2" out="${GEMINI_OUT_ROOT:-$test_root}/.collab"; shift 2
  set +e; gemini "$output" "$@" >/dev/null 2>&1; local code=$?; set -e
  [[ $code -eq $expected && -s "$out/${output%.json}.diagnostic.json" && ! -e "$out/$output" ]] \
    || { print -u2 "gemini $output: expected exit $expected, got $code"; exit 1; }
}
: > "$agy_marker"
gemini gemini-hard.json env AGY_TEST_MODE=success >/dev/null
grep -F -- '--model gemini-3.8-flash-high' "$agy_marker" >/dev/null
grep -F -- 'Safe packet fixture.' "$agy_marker" >/dev/null
jq -e '.reviewer_metadata | .cli == "agy" and .cli_version == "1.2.15" and .requested_model == "pro"
  and .preflight_selected_model == "gemini-3.8-flash-high" and .resolved_models == ["gemini-3.8-flash-high"]
  and .conversation_id == "conv-test" and .quota_remaining_before == 0.9 and .denied_tool_calls == []' \
  "$test_root/.collab/gemini-hard.json" >/dev/null
jq -e '.response | endswith("VERDICT: ACCEPT")' "$test_root/.collab/gemini-hard.json" >/dev/null
[[ -s "$test_root/.collab/gemini-hard.json.sha256" ]]

GEMINI_MODEL=flash gemini gemini-routine.json env AGY_TEST_MODE=success >/dev/null
grep -F -- '--model gemini-3.6-flash-high' "$agy_marker" >/dev/null
GEMINI_MODEL=gemini-3.1-pro-high gemini gemini-explicit-pro.json env AGY_TEST_MODE=success >/dev/null
grep -F -- '--model gemini-3.1-pro-high' "$agy_marker" >/dev/null

# Denied tool attempts go through the real hook script and are recorded.
gemini gemini-tool.json env AGY_TEST_MODE=tool >/dev/null
jq -e '.reviewer_metadata.denied_tool_calls == ["run_command"]' "$test_root/.collab/gemini-tool.json" >/dev/null

gemini_fails 74 gemini-mismatch.json env AGY_TEST_MODE=success AGY_MOCK_RESOLVED=gemini-3.7-flash-high
GEMINI_MODEL=gemini-3.8-flash-low gemini_fails 78 gemini-unapproved.json env AGY_TEST_MODE=success
gemini_fails 78 gemini-apikey.json env AGY_TEST_MODE=success GEMINI_API_KEY=test
gemini_fails 70 gemini-error.json env AGY_TEST_MODE=error
jq -e '.reason | contains("AGY_ERROR: simulated model failure")' "$test_root/.collab/gemini-error.diagnostic.json" >/dev/null
gemini_fails 78 gemini-signed-out.json env AGY_TEST_MODE=success AGY_MOCK_SIGNED_OUT=1
gemini_fails 64 gemini-bad-timeout.json env AGY_TEST_MODE=success GEMINI_MAX_TIME_SECONDS=abc
gemini_fails 65 gemini-oversize.json env AGY_TEST_MODE=success GEMINI_MAX_PROMPT_BYTES=10

# Low quota stops before the review call is made.
: > "$agy_marker"
gemini_fails 78 gemini-low-quota.json env AGY_TEST_MODE=success AGY_MOCK_QUOTA=0.1
[[ ! -s "$agy_marker" ]] || { print -u2 "agy review ran despite low quota"; exit 1; }

export GEMINI_OUT_ROOT="$test_root/cutoff"; mkdir -p "$GEMINI_OUT_ROOT/.collab"
# A cut-off run whose review is complete is kept with a warning; one whose
# review is incomplete fails with its own reason.
gemini gemini-cutoff.json env AGY_TEST_MODE=cutoff >/dev/null
jq -e '.status == "ERROR" and (.reviewer_metadata.truncation_warning | test("output-token limit"))
  and (.reviewer_metadata.mechanical_checks | length == 1 and (.[0] | startswith("F1 cites file:///tmp/reviewers-gemini.X/workspace/proxy.ts#L3")))' \
  "$GEMINI_OUT_ROOT/.collab/gemini-cutoff.json" >/dev/null
jq -e '.reviewer_metadata | has("truncation_warning") | not' "$test_root/.collab/gemini-hard.json" >/dev/null
gemini_fails 70 gemini-cutoff-partial.json env AGY_TEST_MODE=cutoff-partial
# Another ERROR that only mentions the limit is not treated as a cutoff.
gemini_fails 70 gemini-cutoff-other.json env AGY_TEST_MODE=cutoff AGY_MOCK_ERROR="quota check: output token limit unavailable"
jq -e '.reason == "Gemini invocation did not succeed"' "$GEMINI_OUT_ROOT/.collab/gemini-cutoff-other.diagnostic.json" >/dev/null
jq -e '.reason | startswith("Gemini hit the output-token limit")' "$GEMINI_OUT_ROOT/.collab/gemini-cutoff-partial.diagnostic.json" >/dev/null
# Hard-tier packets over the size guard are refused before agy runs; routine
# packets of the same size are not.
: > "$agy_marker"
gemini_fails 65 gemini-hard-oversize.json env AGY_TEST_MODE=success GEMINI_HARD_MAX_PROMPT_BYTES=10
[[ ! -s "$agy_marker" ]] || { print -u2 "agy ran despite the hard-tier size guard"; exit 1; }
jq -e '.reason | startswith("hard-tier prompt and packet are")' "$GEMINI_OUT_ROOT/.collab/gemini-hard-oversize.diagnostic.json" >/dev/null
GEMINI_MODEL=flash gemini gemini-routine-big.json env AGY_TEST_MODE=success GEMINI_HARD_MAX_PROMPT_BYTES=10 >/dev/null
unset GEMINI_OUT_ROOT
gemini_fails 70 gemini-timeout.json env AGY_TEST_MODE=hang GEMINI_MAX_TIME_SECONDS=1 GEMINI_TIMEOUT_GRACE_SECONDS=1
jq -e '.reason == "Gemini invocation timed out"' "$test_root/.collab/gemini-timeout.diagnostic.json" >/dev/null

# Codex reviewer: tiers pin model and effort; isolation flags are enforced by the mock.
codex_marker="$test_root/codex-marker"; codex_stdin="$test_root/codex-stdin"
codex_review() {
  local tier="$1" output="$2"; shift 2
  PATH="$test_root/bin:$PATH" CODEX_MOCK_MARKER="$codex_marker" CODEX_MOCK_STDIN="$codex_stdin" "$@" \
    "$root/codex-review.sh" --owner claude "$tier" "$test_root/prompt.md" "$test_root/.collab/$output" "$test_root/packet/source.md"
}
codex_fails() {
  local expected="$1" tier="$2" output="$3"; shift 3
  set +e; codex_review "$tier" "$output" "$@" >/dev/null 2>&1; local code=$?; set -e
  [[ $code -eq $expected && -s "$test_root/.collab/${output%.md}.diagnostic.json" && ! -e "$test_root/.collab/$output" ]] \
    || { print -u2 "codex $output: expected exit $expected, got $code"; exit 1; }
}
codex_review hard codex-hard.md env CODEX_TEST_MODE=success >/dev/null
grep -F -- '-m gpt-6-sol' "$codex_marker" >/dev/null
grep -F -- 'model_reasoning_effort="high"' "$codex_marker" >/dev/null
grep -F -- 'Safe packet fixture.' "$codex_stdin" >/dev/null
for line in 'Owner: claude' 'Selected model: gpt-6-sol' 'Reasoning effort: high' 'Blocked tool attempts: 0' 'VERDICT: ACCEPT'; do
  grep -Fx -- "$line" "$test_root/.collab/codex-hard.md" >/dev/null || { print -u2 "codex-hard.md missing: $line"; exit 1; }
done
[[ -s "$test_root/.collab/codex-hard.md.sha256" ]]
grep -E '^Wrapper revision: [0-9a-f]{40}$' "$test_root/.collab/codex-hard.md" >/dev/null
jq -e '.reviewer_metadata.wrapper_revision | test("^[0-9a-f]{40}")' "$test_root/.collab/gemini-hard.json" >/dev/null
codex_review routine codex-routine.md env CODEX_TEST_MODE=success >/dev/null
grep -F -- 'model_reasoning_effort="medium"' "$codex_marker" >/dev/null
codex_review hard codex-tool.md env CODEX_TEST_MODE=tool >/dev/null
grep -Fx 'Blocked tool attempts: 1' "$test_root/.collab/codex-tool.md" >/dev/null
codex_fails 78 pro codex-badtier.md env CODEX_TEST_MODE=success
codex_fails 78 hard codex-apikey.md env CODEX_TEST_MODE=success OPENAI_API_KEY=test
codex_fails 78 hard codex-apilogin.md env CODEX_TEST_MODE=success CODEX_MOCK_LOGIN='Logged in using an API key'
codex_fails 70 hard codex-failure.md env CODEX_TEST_MODE=fail
codex_fails 70 hard codex-incomplete.md env CODEX_TEST_MODE=incomplete
codex_fails 70 hard codex-timeout.md env CODEX_TEST_MODE=hang CODEX_MAX_TIME_SECONDS=1
jq -e '.reason == "Codex invocation timed out" and .owner == "claude"' "$test_root/.collab/codex-timeout.diagnostic.json" >/dev/null

# Uncommitted wrapper changes are refused (no bypass).
print '# local edit' >> "$root/codex-review.sh"
set +e; codex_review hard codex-dirty.md env CODEX_TEST_MODE=success >/dev/null 2>&1; code=$?; set -e
[[ $code -eq 78 ]] && jq -e '.reason == "gateway wrapper files have uncommitted changes"' "$test_root/.collab/codex-dirty.diagnostic.json" >/dev/null
git -C "$root" checkout -q -- codex-review.sh

# An agent never reviews work it owns; owner is recorded on every reviewer.
owner_rejects() {
  set +e; PATH="$test_root/bin:$PATH" "$@" >/dev/null 2>&1; local code=$?; set -e
  [[ $code -eq 64 ]] || { print -u2 "expected usage rejection (64), got $code: $*"; exit 1; }
}
owner_rejects "$root/claude-review.sh" --owner claude sonnet "$test_root/prompt.md" "$test_root/.collab/self-claude.md" "$test_root/packet/source.md"
owner_rejects "$root/codex-review.sh" --owner codex hard "$test_root/prompt.md" "$test_root/.collab/self-codex.md" "$test_root/packet/source.md"
owner_rejects "$root/gemini-review.sh" --owner gemini pro "$test_root/prompt.md" "$test_root/.collab/bad-owner.json" "$test_root/packet/source.md"
owner_rejects "$root/kimi-review.sh" --owner kimi routine "$test_root/prompt.md" "$test_root/.collab/bad-owner.md" "$test_root/packet/source.md"
[[ ! -e "$test_root/.collab/self-claude.diagnostic.json" && ! -e "$test_root/.collab/self-codex.diagnostic.json" ]]
PATH="$test_root/bin:$PATH" CLAUDE_REVIEW_MODEL_POLICY="$test_root/claude-policy.json" CLAUDE_TEST_MODE=success \
  "$root/claude-review.sh" --owner codex sonnet "$test_root/prompt.md" \
  "$test_root/.collab/claude-owned.md" "$test_root/packet/source.md" >/dev/null
grep -Fx 'Owner: codex' "$test_root/.collab/claude-owned.md" >/dev/null
PATH="$test_root/bin:$PATH" AGY_TEST_MODE=success "$root/gemini-review.sh" --packet-root "$test_root/shared" --owner claude pro \
  "$test_root/prompt.md" "$test_root/.collab/gemini-owned.json" "$test_root/packet/source.md" >/dev/null
jq -e '.reviewer_metadata.owner == "claude"' "$test_root/.collab/gemini-owned.json" >/dev/null

# Kimi uses managed subscription OAuth, explicit tier mappings, and an isolated
# no-tools CLI session. The mock checks its workspace, agent, skills, and env.
kimi_repo="$test_root/kimi-repo"; mkdir -p "$kimi_repo/.collab"
kimi_args="$test_root/kimi-args"; kimi_prompt="$test_root/kimi-prompt"; kimi_marker="$test_root/kimi-marker"
kimi_review() {
  local tier="$1" output="$2"; shift 2
  PATH="$test_root/bin:$PATH" KIMI_MOCK_ARGS="$kimi_args" KIMI_MOCK_PROMPT="$kimi_prompt" KIMI_MOCK_MARKER="$kimi_marker" "$@" \
    "$root/kimi-review.sh" --packet-root "$test_root" --owner codex "$tier" "$test_root/prompt.md" "$kimi_repo/.collab/$output" "$test_root/packet/source.md"
}
kimi_fails() {
  local expected="$1" tier="$2" output="$3"; shift 3
  set +e; kimi_review "$tier" "$output" "$@" >/dev/null 2>&1; local code=$?; set -e
  [[ $code -eq $expected && -s "$kimi_repo/.collab/${output%.md}.diagnostic.json" && ! -e "$kimi_repo/.collab/$output" ]] \
    || { print -u2 "kimi $output: expected exit $expected, got $code"; exit 1; }
}
kimi_review routine kimi-routine.md env KIMI_TEST_MODE=success >/dev/null
grep -F -- '--model kimi-code/kimi-for-coding' "$kimi_args" >/dev/null
grep -Fx 'model=kimi-code/kimi-for-coding effort=low' "$kimi_marker" >/dev/null
grep -F 'Safe packet fixture.' "$kimi_prompt" >/dev/null
for line in 'Owner: codex' 'Requested model: routine' 'Selected model: kimi-code/kimi-for-coding' 'Reasoning effort: low' \
  'Resolved model(s): not reported by Kimi Code stream-json' 'CLI version: kimi 2.2.0' 'Tool events: 0' \
  'Usage: not reported by Kimi Code stream-json' 'VERDICT: ACCEPT'; do
  grep -Fx -- "$line" "$kimi_repo/.collab/kimi-routine.md" >/dev/null || { print -u2 "kimi-routine.md missing: $line"; exit 1; }
done
! grep -Fx 'draft' "$kimi_repo/.collab/kimi-routine.md" >/dev/null
[[ -s "$kimi_repo/.collab/kimi-routine.md.sha256" ]]
kimi_review hard kimi-hard.md env KIMI_TEST_MODE=success >/dev/null
grep -F -- '--model kimi-code/k3' "$kimi_args" >/dev/null
grep -Fx 'model=kimi-code/k3 effort=high' "$kimi_marker" >/dev/null
kimi_fails 78 routine kimi-env-api.md env KIMI_TEST_MODE=success KIMI_API_KEY=test
jq -e '.reason | contains("API credentials")' "$kimi_repo/.collab/kimi-env-api.diagnostic.json" >/dev/null
kimi_fails 78 routine kimi-provider-api.md env KIMI_TEST_MODE=success KIMI_MOCK_AUTH=api_key
kimi_fails 78 routine kimi-empty-oauth.md env KIMI_TEST_MODE=success KIMI_MOCK_AUTH=empty_oauth
kimi_fails 78 routine kimi-signed-out.md env KIMI_TEST_MODE=success KIMI_MOCK_AUTH=signed_out
kimi_fails 78 routine kimi-wrong-provider.md env KIMI_TEST_MODE=success KIMI_MOCK_AUTH=wrong_provider
kimi_fails 78 pro kimi-badtier.md env KIMI_TEST_MODE=success
kimi_fails 70 routine kimi-tool.md env KIMI_TEST_MODE=tool
jq -e '.reason | contains("tool events")' "$kimi_repo/.collab/kimi-tool.diagnostic.json" >/dev/null
kimi_fails 70 routine kimi-schema-tool.md env KIMI_TEST_MODE=schema-tool
jq -e '.reason | contains("tool events")' "$kimi_repo/.collab/kimi-schema-tool.diagnostic.json" >/dev/null
kimi_fails 70 routine kimi-incomplete.md env KIMI_TEST_MODE=incomplete
kimi_fails 70 routine kimi-failure.md env KIMI_TEST_MODE=fail
jq -e '.reasoning_effort == "low" and (.reason | contains("returned nonzero"))' "$kimi_repo/.collab/kimi-failure.diagnostic.json" >/dev/null
jq -e '.model_invocation_began == true' "$kimi_repo/.collab/kimi-failure.diagnostic.json" >/dev/null
jq -e '.model_invocation_began == false' "$kimi_repo/.collab/kimi-env-api.diagnostic.json" >/dev/null
kimi_args_before="$(<"$kimi_args")"
set +e; kimi_review routine kimi-failure.md env KIMI_TEST_MODE=success >/dev/null 2>&1; code=$?; set -e
[[ $code -eq 65 && "$(<"$kimi_args")" == "$kimi_args_before" ]]
kimi_fails 65 routine kimi-oversize.md env KIMI_TEST_MODE=success KIMI_MAX_PROMPT_BYTES=10
kimi_fails 64 routine kimi-bad-timeout.md env KIMI_TEST_MODE=success KIMI_MAX_TIME_SECONDS=abc
kimi_fails 70 routine kimi-timeout.md env KIMI_TEST_MODE=hang KIMI_MAX_TIME_SECONDS=1
jq -e '.reason == "Kimi invocation timed out" and .owner == "codex"' "$kimi_repo/.collab/kimi-timeout.diagnostic.json" >/dev/null

KIMI_TEST_MODE=success KIMI_MOCK_PROMPT="$kimi_prompt" PATH="$test_root/bin:$PATH" \
  "$root/kimi-review.sh" --packet-root "$test_root/shared" --owner claude routine \
  "$test_root/shared/prompt.md" "$test_root/.collab/kimi-shared.md" \
  "$test_root/shared/packet.md" "$test_root/packet/source.md" >/dev/null
grep -F 'Shared packet fixture.' "$kimi_prompt" >/dev/null
grep -F 'Safe packet fixture.' "$kimi_prompt" >/dev/null
[[ -s "$test_root/.collab/kimi-shared.md" && -s "$test_root/.collab/kimi-shared.md.sha256" ]]

# Review budget: five rounds per topic across providers, then one Gemini
# round, then refusal; one hard-tier round per topic; a daily cap per provider.
today="$(date +%F)"; broot="$test_root/budget"; mkdir -p "$broot/.collab"; print 'Budget packet.' > "$broot/packet.md"
claude_args="$test_root/claude-args"; kimi_args="$test_root/kimi-budget-args"
breview() {
  local wrapper="$1" tier="$2" output="$3"; shift 3
  PATH="$test_root/bin:$PATH" CLAUDE_REVIEW_MODEL_POLICY="$test_root/claude-policy.json" CLAUDE_TEST_MODE=success \
    CODEX_TEST_MODE=success AGY_TEST_MODE=success CLAUDE_MOCK_ARGS="$claude_args" KIMI_MOCK_ARGS="$kimi_args" "$@" \
    "$root/$wrapper" --packet-root "$test_root" --owner codex "$tier" "$test_root/prompt.md" "$broot/.collab/$output" "$broot/packet.md"
}
brefused() {
  local pattern="$1" wrapper="$2" tier="$3" output="$4"; shift 4
  : > "$claude_args"; : > "$kimi_args"
  set +e; breview "$wrapper" "$tier" "$output" "$@" >/dev/null 2>&1; local code=$?; set -e
  [[ $code -eq 79 && ! -e "$broot/.collab/$output" && ! -s "$claude_args" && ! -s "$kimi_args" ]] \
    || { print -u2 "budget $output: expected refusal 79, got $code"; exit 1; }
  jq -e --arg p "$pattern" '.reason | contains($p)' "$broot/.collab/${${output%.md}%.json}.diagnostic.json" >/dev/null \
    || { print -u2 "budget $output: reason lacks '$pattern'"; exit 1; }
}
breview claude-review.sh sonnet claude-$today-topic-r01.md >/dev/null
grep -F -- '--effort medium' "$claude_args" >/dev/null
for line in 'Effort: medium' 'Usage: {"usage":{"input_tokens":10,"output_tokens":20,"cache_read_input_tokens":0,"cache_creation_input_tokens":0},"total_cost_usd":0.01,"duration_ms":5,"num_turns":1}'; do
  grep -Fx -- "$line" "$broot/.collab/claude-$today-topic-r01.md" >/dev/null || { print -u2 "missing: $line"; exit 1; }
done
breview claude-review.sh sonnet claude-$today-topic-r02.md >/dev/null
grep -F -- '--effort low' "$claude_args" >/dev/null
# A failed call that reached the model counts as a round.
set +e; breview claude-review.sh sonnet claude-$today-topic-r03.md env CLAUDE_MOCK_RESOLVED=claude-opus-5 >/dev/null 2>&1; set -e
[[ -s "$broot/.collab/claude-$today-topic-r03.diagnostic.json" ]]
PATH="$test_root/bin:$PATH" CODEX_TEST_MODE=success "$root/codex-review.sh" --packet-root "$test_root" --owner claude routine "$test_root/prompt.md" \
  "$broot/.collab/codex-$today-topic-r04.md" "$broot/packet.md" >/dev/null
breview claude-review.sh sonnet claude-$today-topic-r05.md >/dev/null
brefused 'escalate to gemini-review.sh' claude-review.sh sonnet claude-$today-topic-r06.md
set +e; PATH="$test_root/bin:$PATH" CODEX_TEST_MODE=success "$root/codex-review.sh" --packet-root "$test_root" --owner claude routine "$test_root/prompt.md" \
  "$broot/.collab/codex-$today-topic-r06.md" "$broot/packet.md" >/dev/null 2>&1; code=$?; set -e
[[ $code -eq 79 && ! -e "$broot/.collab/codex-$today-topic-r06.md" ]]
breview gemini-review.sh pro gemini-$today-topic-r06.json >/dev/null
breview gemini-review.sh pro gemini-$today-topic-r07.json >/dev/null
brefused 'bring the open points to the user' gemini-review.sh pro gemini-$today-topic-r08.json
breview claude-review.sh sonnet claude-$today-topic-r08.md env REVIEW_BUDGET_OVERRIDE='user approved r08' >/dev/null
grep -Fx 'Budget override: user approved r08' "$broot/.collab/claude-$today-topic-r08.md" >/dev/null
# One hard-tier round per topic; the routine tier still runs.
breview claude-review.sh opus claude-$today-hardtopic-r01.md >/dev/null
brefused 'hard-tier' claude-review.sh opus claude-$today-hardtopic-r02.md
# A false length claim about a quoted hex value is noted in the header.
digest=ca71fc6a71fca61d604705e0105298c4a7c52c8c2cdf22a9e25294cdddd483b1
breview claude-review.sh sonnet claude-$today-hardtopic-r03.md env CLAUDE_MOCK_EXTRA="F1 [minor]: \`$digest\` is 63 hex characters." >/dev/null
grep -Fx "Mechanical check: F1 states 63 hex characters; the quoted value measures 64 (ca71fc6a 71fca61d 604705e0 105298c4 a7c52c8c 2cdf22a9 e25294cd ddd483b1)" \
  "$broot/.collab/claude-$today-hardtopic-r03.md" >/dev/null
# Old reviews count on their own date, even after a checkout resets mtimes.
for i in {1..9}; do : > "$broot/.collab/claude-2020-01-0$i-old-r01.md"; done
# Seven Claude reviews and one counted failure ran here today: the next is refused.
breview claude-review.sh sonnet claude-$today-filler-r01.md >/dev/null
brefused 'reviews already ran in this repository today' claude-review.sh sonnet claude-$today-other-r01.md

# Fixes from review r01, in a fresh repository so the daily cap is not hit.
broot="$test_root/budget2"; mkdir -p "$broot/.collab"; print 'Budget packet.' > "$broot/packet.md"
cat > "$test_root/kimi-policy-override.json" <<'EOF'
{"tiers":{"hard":{"model":"kimi-code/k3","reasoning_effort":"high"},"routine":{"model":"kimi-code/k3","reasoning_effort":"high"}}}
EOF
# Codex ran this topic's first round; Claude's first round still gets medium effort.
PATH="$test_root/bin:$PATH" CODEX_TEST_MODE=success "$root/codex-review.sh" --packet-root "$test_root" --owner claude routine "$test_root/prompt.md" \
  "$broot/.collab/codex-$today-mixed-r01.md" "$broot/packet.md" >/dev/null
breview claude-review.sh sonnet claude-$today-mixed-r02.md >/dev/null
grep -F -- '--effort medium' "$claude_args" >/dev/null
# A hard-tier call that reached the model and failed still uses the hard round.
set +e; breview claude-review.sh opus claude-$today-hardfail-r01.md env CLAUDE_MOCK_RESOLVED=claude-opus-5 >/dev/null 2>&1; set -e
brefused 'hard-tier' claude-review.sh opus claude-$today-hardfail-r02.md
# Kimi hard rounds use the same per-topic cap and block another provider's hard round.
breview kimi-review.sh hard kimi-$today-kimihard-r01.md env KIMI_TEST_MODE=success >/dev/null
brefused 'hard-tier' kimi-review.sh hard kimi-$today-kimihard-r02.md env KIMI_TEST_MODE=success
brefused 'hard-tier' claude-review.sh opus claude-$today-kimihard-r02.md
# A failed Kimi hard call counts conservatively; a routine alias/effort override cannot bypass the hard cap.
set +e; breview kimi-review.sh hard kimi-$today-kimihardfail-r01.md env KIMI_TEST_MODE=fail >/dev/null 2>&1; code=$?; set -e
[[ $code -eq 70 && -s "$broot/.collab/kimi-$today-kimihardfail-r01.diagnostic.json" ]]
brefused 'hard-tier' kimi-review.sh hard kimi-$today-kimihardfail-r02.md env KIMI_TEST_MODE=success
breview kimi-review.sh routine kimi-$today-policy-r01.md env KIMI_TEST_MODE=success KIMI_REVIEW_MODEL_POLICY="$test_root/kimi-policy-override.json" >/dev/null
grep -Fx 'Reasoning effort: high' "$broot/.collab/kimi-$today-policy-r01.md" >/dev/null
# A routine call whose policy override resolves to the hard model/effort still
# consumes the hard round: the next routine call with the same override is refused.
brefused 'hard-tier' kimi-review.sh routine kimi-$today-policy-r02.md env KIMI_TEST_MODE=success KIMI_REVIEW_MODEL_POLICY="$test_root/kimi-policy-override.json"
# Interruption during the OAuth preflight is not a spent round.
hang_marker="$test_root/kimi-provider-hang"; rm -f "$hang_marker"
set +e
PATH="$test_root/bin:$PATH" KIMI_MOCK_AUTH=hang-provider KIMI_PROVIDER_HANG_MARKER="$hang_marker" \
  "$root/kimi-review.sh" --packet-root "$test_root" --owner codex routine "$test_root/prompt.md" \
  "$kimi_repo/.collab/kimi-$today-interrupt-r01.md" "$test_root/packet/source.md" >/dev/null 2>&1 &
kimi_pid=$!
for i in {1..50}; do [[ -e "$hang_marker" ]] && break; sleep 0.1; done
kill -TERM "$kimi_pid" 2>/dev/null
wait "$kimi_pid"; code=$?
set -e
[[ $code -eq 78 && ! -e "$kimi_repo/.collab/kimi-$today-interrupt-r01.md" ]]
jq -e '.reason == "Kimi invocation interrupted before model invocation began (SIGTERM)"' \
  "$kimi_repo/.collab/kimi-$today-interrupt-r01.diagnostic.json" >/dev/null
[[ "$(python3 "$root/review-budget.py" kimi routine "$kimi_repo/.collab/kimi-$today-interrupt-r02.md")" == "0 0" ]]
# A Kimi failure after invocation began counts as spent; its explicit
# model_invocation_began flag decides even when the reason text is unusual.
jq -n '{provider:"kimi",exit_code:70,reason:"Kimi assistant response extraction failed",requested_model:"routine",selected_model:"kimi-code/k3",reasoning_effort:"high",model_invocation_began:true}' \
  > "$broot/.collab/kimi-$today-extract-r01.diagnostic.json"
[[ "$(python3 "$root/review-budget.py" kimi routine "$broot/.collab/kimi-$today-extract-r02.md")" == "1 1" ]]
jq -n '{provider:"kimi",exit_code:78,reason:"Kimi invocation interrupted before model invocation began (SIGTERM)",model_invocation_began:false}' \
  > "$broot/.collab/kimi-$today-preflight-r01.diagnostic.json"
[[ "$(python3 "$root/review-budget.py" kimi routine "$broot/.collab/kimi-$today-preflight-r02.md")" == "0 0" ]]
# The flag is authoritative: a false flag never counts, whatever the reason says.
jq -n '{provider:"kimi",exit_code:70,reason:"Kimi invocation returned nonzero after model invocation began (exit 42)",model_invocation_began:false}' \
  > "$broot/.collab/kimi-$today-falseflag-r01.diagnostic.json"
[[ "$(python3 "$root/review-budget.py" kimi routine "$broot/.collab/kimi-$today-falseflag-r02.md")" == "0 0" ]]
jq -n '{provider:"claude",exit_code:70,reason:"Claude invocation failed",requested_model:"sonnet"}' \
  > "$broot/.collab/claude-$today-claudefail-r01.diagnostic.json"
[[ "$(python3 "$root/review-budget.py" claude routine "$broot/.collab/claude-$today-claudefail-r02.md")" == "1 1" ]]
jq -n '{provider:"codex",exit_code:70,reason:"Codex invocation failed (exit 1)",requested_model:"routine"}' \
  > "$broot/.collab/codex-$today-codexfail-r01.diagnostic.json"
[[ "$(python3 "$root/review-budget.py" codex routine "$broot/.collab/codex-$today-codexfail-r02.md")" == "1 1" ]]
jq -n '{provider:"gemini",exit_code:70,reason:"Gemini hit the output-token limit before finishing the review; split the packet or send a delta"}' \
  > "$broot/.collab/gemini-$today-cutoff-r01.diagnostic.json"
[[ "$(python3 "$root/review-budget.py" gemini routine "$broot/.collab/gemini-$today-cutoff-r02.json")" == "1 1" ]]
# Output names the budget cannot parse are refused.
brefused 'output name must be' claude-review.sh sonnet review-notes.md
brefused 'output name must be' claude-review.sh sonnet codex-$today-wrongprefix-r01.md

python3 - <<'PY' "$root/reviewer-validate.py"
import subprocess
import sys
validator = sys.argv[1]
body = "The review contains substantive findings. " * 20
text = body + "\n\nF1 [minor]: a finding.\n**C1:** a condition.\n\n**ATTESTATION: all actionable findings and conditions are labeled.**\n\n**VERDICT: ACCEPT WITH CONDITIONS**\n"
assert subprocess.run([validator], input=text, text=True).returncode == 0
labeled = body + "\nF1 [blocker]: broken.\nATTESTATION: all actionable findings and conditions are labeled.\nVERDICT: REJECT\n"
assert subprocess.run([validator], input=labeled, text=True).returncode == 0
short_verification = "R03-F1 is resolved.\nR03-C1 is resolved.\nATTESTATION: all actionable findings and conditions are labeled.\nVERDICT: ACCEPT\n"
assert subprocess.run([validator], input=short_verification, text=True).returncode == 0
assert subprocess.run([validator], input="Looks fine.\nVERDICT: ACCEPT\n", text=True, capture_output=True).returncode != 0
for invalid_label in (
    body + "\nATTESTATION: all actionable findings and conditions are labeled.\nVERDICT: REJECT\n",
    body + "\nF1 [minor]: x\nATTESTATION: all actionable findings and conditions are labeled.\nVERDICT: ACCEPT WITH CONDITIONS\n",
    body + "\nF1 [minor]: x\nF1 [major]: y\nATTESTATION: all actionable findings and conditions are labeled.\nVERDICT: REJECT\n",
    body + "\nF1 [blocker]: x\nVERDICT: REJECT\n",
    # An unknown severity would leave the finding untracked.
    body + "\nF1 [critical]: x\nF2 [major]: y\nATTESTATION: all actionable findings and conditions are labeled.\nVERDICT: REJECT\n",
):
    assert subprocess.run([validator], input=invalid_label, text=True, capture_output=True).returncode != 0
for invalid in (
    body + "\nVERDICT: CONDITIONAL\n",
    body + "\nVERDICT: ACCEPT\nVERDICT: REJECT\n",
    body + "\nVERDICT: ACCEPT\nFollow-up text.\n",
):
    assert subprocess.run([validator], input=invalid, text=True).returncode != 0
PY

print "wrapper failure smoke tests passed"
