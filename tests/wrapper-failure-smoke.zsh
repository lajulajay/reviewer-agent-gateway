#!/bin/zsh
set -euo pipefail

source_root="$(cd "$(dirname "$0")/.." && pwd -P)"
test_root="$(mktemp -d "${TMPDIR:-/tmp}/reviewers-test.XXXXXX")"
trap 'rm -rf "$test_root"' EXIT INT TERM
# Wrappers refuse uncommitted changes, so run them from a committed snapshot
# of the working tree rather than through a bypass.
root="$test_root/gateway"; mkdir -p "$root"
cp -p "$source_root"/*.sh "$source_root"/*.py "$source_root"/*.json "$source_root"/output-contract.txt "$root"/
# CLI mocks below exercise the subscription route; the API route has unit tests.
cat > "$root/api-call.py" <<'PYEOF'
#!/usr/bin/env python3
# Stand-in for api-call.py: exercises the wrapper's API branch without a network or key.
import json, os, sys
from pathlib import Path
policy, tier, prompt, out_text, out_meta, marker = sys.argv[1:]
mode = os.environ.get("API_MOCK_MODE", "ok")
if mode == "preflight":
    print("no Keychain item 'svc'", file=sys.stderr); sys.exit(78)
if mode == "cap":
    print("API spend cap: refused", file=sys.stderr); sys.exit(79)
if mode == "crash-before":
    sys.exit(1)
if mode == "zero-nomarker":
    sys.exit(0)
Path(marker).touch()
if mode == "sent-fail":
    print("API request failed: HTTP 500", file=sys.stderr); sys.exit(70)
if mode == "crash-after":
    sys.exit(1)
body = "The supplied packet is internally consistent and the proposed boundary is testable. " * 8
body += "\n\nATTESTATION: all actionable findings and conditions are labeled.\n\nVERDICT: ACCEPT"
Path(out_text).write_text(body)
Path(out_meta).write_text(json.dumps({"served_model": "mock-served", "input_tokens": 10, "output_tokens": 5,
                                      "cost_usd": 0.0001, "ledger_committed_usd": 0.0001, "spend_cap_usd": 18.0}))
PYEOF
for p in codex kimi; do jq '.route = "subscription"' "$root/$p-model-policy.json" > "$root/$p.tmp" && mv "$root/$p.tmp" "$root/$p-model-policy.json"; done
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
for wrapper in claude-review.sh codex-review.sh copilot-review.sh gemini-review.sh kimi-review.sh auto-review.sh; do
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
grep -F -- '--model gemini-3.8-flash-medium' "$agy_marker" >/dev/null
GEMINI_MODEL=gemini-3.8-flash-medium gemini gemini-explicit-medium.json env AGY_TEST_MODE=success >/dev/null
grep -F -- '--model gemini-3.8-flash-medium' "$agy_marker" >/dev/null

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

# Vendor independence (agents.json): no vendor reviews its own work, whatever the
# model version; multi-vendor owners (Copilot) must name every authoring model;
# routers and unknown models fail closed. All refusals happen before any model call.
owner_rejects "$root/claude-review.sh" --owner copilot sonnet "$test_root/prompt.md" "$test_root/.collab/copilot-nomodel.md" "$test_root/packet/source.md"
owner_rejects "$root/claude-review.sh" --owner copilot --author-model claude-sonnet-5 sonnet "$test_root/prompt.md" "$test_root/.collab/copilot-anthropic.md" "$test_root/packet/source.md"
owner_rejects "$root/claude-review.sh" --owner codex --author copilot --author-model claude-haiku-4.5 sonnet "$test_root/prompt.md" "$test_root/.collab/mixed-anthropic.md" "$test_root/packet/source.md"
owner_rejects "$root/gemini-review.sh" --owner copilot --author-model gemini-4-hydrogen pro "$test_root/prompt.md" "$test_root/.collab/copilot-google.json" "$test_root/packet/source.md"
owner_rejects "$root/gemini-review.sh" --owner copilot --author-model copilot-fusion pro "$test_root/prompt.md" "$test_root/.collab/copilot-router.json" "$test_root/packet/source.md"
owner_rejects "$root/codex-review.sh" --owner copilot --author-model gpt-6-luna hard "$test_root/prompt.md" "$test_root/.collab/copilot-openai.md" "$test_root/packet/source.md"
owner_rejects "$root/claude-review.sh" --owner copilot --task 'bad task' --author-model gpt-6-luna sonnet "$test_root/prompt.md" "$test_root/.collab/copilot-badtask.md" "$test_root/packet/source.md"
for f in copilot-nomodel copilot-anthropic mixed-anthropic copilot-google copilot-router copilot-openai copilot-badtask; do
  [[ ! -e "$test_root/.collab/$f.diagnostic.json" ]] || { print -u2 "identity refusal left a diagnostic: $f"; exit 1; }
done
PATH="$test_root/bin:$PATH" CLAUDE_REVIEW_MODEL_POLICY="$test_root/claude-policy.json" CLAUDE_TEST_MODE=success \
  "$root/claude-review.sh" --owner copilot --author-model gpt-6.1-terra --author-model mai-code-2-flash --task T7 sonnet "$test_root/prompt.md" \
  "$test_root/.collab/claude-copilot.md" "$test_root/packet/source.md" >/dev/null
grep -Fx 'Owner: copilot' "$test_root/.collab/claude-copilot.md" >/dev/null
grep -Fx 'Author models: gpt-6.1-terra, mai-code-2-flash' "$test_root/.collab/claude-copilot.md" >/dev/null
grep -Fx 'Task: T7' "$test_root/.collab/claude-copilot.md" >/dev/null
mkdir -p "$test_root/vendor/.collab"  # fresh repository: the shared one is at its Gemini daily cap
PATH="$test_root/bin:$PATH" AGY_TEST_MODE=success "$root/gemini-review.sh" --packet-root "$test_root" --owner copilot --author-model claude-sonnet-5.5 --task T8 pro \
  "$test_root/prompt.md" "$test_root/vendor/.collab/gemini-copilot.json" "$test_root/packet/source.md" >/dev/null
jq -e '.reviewer_metadata.owner == "copilot" and .reviewer_metadata.author_models == ["claude-sonnet-5.5"] and .reviewer_metadata.task == "T8" and .reviewer_metadata.authors == []' "$test_root/vendor/.collab/gemini-copilot.json" >/dev/null

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
jq -n '{provider:"claude",exit_code:78,reason:"Claude model selection failed",requested_model:"sonnet"}' \
  > "$broot/.collab/claude-$today-claudepreflight-r01.diagnostic.json"
[[ "$(python3 "$root/review-budget.py" claude routine "$broot/.collab/claude-$today-claudepreflight-r02.md")" == "0 0" ]]
jq -n '{provider:"codex",exit_code:69,reason:"codex CLI not found",requested_model:"routine"}' \
  > "$broot/.collab/codex-$today-codexpreflight-r01.diagnostic.json"
[[ "$(python3 "$root/review-budget.py" codex routine "$broot/.collab/codex-$today-codexpreflight-r02.md")" == "0 0" ]]
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


# API route (model policy "route": "api"): shared checks still run, exit codes
# follow the send marker, and Kimi diagnostics report model_invocation_began truthfully.
api_repo="$test_root/api"; mkdir -p "$api_repo/.collab"
for p in codex kimi; do jq '.route = "api" | .api = {style:"chat-completions", base_url:"https://x.test/v1", keychain_service:"svc", ledger:"t", spend_cap_usd:1, tiers:{routine:{model:"m", max_output_tokens:10, usd_per_1m_input:1, usd_per_1m_output:1}}}' "$root/$p-model-policy.json" > "$test_root/$p-api-policy.json"; done
api_run() { # mode provider output expected-exit
  local mode="$1" p="$2" out="$3" want="$4" envname
  envname="${(U)p}_REVIEW_MODEL_POLICY"
  set +e; env API_MOCK_MODE="$mode" "$envname=$test_root/$p-api-policy.json" "$root/$p-review.sh" --packet-root "$test_root" --owner claude routine "$test_root/prompt.md" "$api_repo/.collab/$out" "$test_root/packet/source.md" >/dev/null 2>"$test_root/api-last.err"; local code=$?; set -e
  [[ $code -eq $want ]] || { print -u2 "API route $p/$mode: expected $want, got $code: $(<"$test_root/api-last.err")"; exit 1; }
}
api_run ok codex codex-api-ok.md 0
grep -Fx 'Route: api' "$api_repo/.collab/codex-api-ok.md" >/dev/null
grep -Fx 'Resolved model(s): mock-served' "$api_repo/.collab/codex-api-ok.md" >/dev/null
shasum -a 256 -c "$api_repo/.collab/codex-api-ok.md.sha256" >/dev/null 2>&1 || (cd "$api_repo/.collab" && shasum -a 256 -c codex-api-ok.md.sha256 >/dev/null)
api_run preflight kimi kimi-api-pre.md 78
jq -e '.model_invocation_began == false and .exit_code == 78' "$api_repo/.collab/kimi-api-pre.diagnostic.json" >/dev/null
api_run cap kimi kimi-api-cap.md 79
jq -e '.model_invocation_began == false' "$api_repo/.collab/kimi-api-cap.diagnostic.json" >/dev/null
api_run crash-before kimi kimi-api-crash0.md 78
jq -e '.model_invocation_began == false' "$api_repo/.collab/kimi-api-crash0.diagnostic.json" >/dev/null
api_run zero-nomarker kimi kimi-api-zero.md 78
jq -e '.model_invocation_began == false' "$api_repo/.collab/kimi-api-zero.diagnostic.json" >/dev/null
api_run sent-fail kimi kimi-api-sent.md 70
jq -e '.model_invocation_began == true and .exit_code == 70' "$api_repo/.collab/kimi-api-sent.diagnostic.json" >/dev/null
api_run crash-after kimi kimi-api-crash1.md 70
jq -e '.model_invocation_began == true' "$api_repo/.collab/kimi-api-crash1.diagnostic.json" >/dev/null
api_run ok codex ../../outside.md 65
api_run ok kimi kimi-api-self.md 0
set +e; env API_MOCK_MODE=ok "KIMI_REVIEW_MODEL_POLICY=$test_root/kimi-api-policy.json" "$root/kimi-review.sh" --packet-root "$test_root" --owner claude --author-model kimi-k3 routine "$test_root/prompt.md" "$api_repo/.collab/kimi-api-vendor.md" "$test_root/packet/source.md" >/dev/null 2>&1; code=$?; set -e
[[ $code -eq 64 && ! -e "$api_repo/.collab/kimi-api-vendor.diagnostic.json" ]] || { print -u2 "API route skipped the vendor rule ($code)"; exit 1; }
# Copilot: the reviewer vendor is the selected model's vendor; any tool event,
# enabled MCP server or other resolved model fails the review.
cat > "$test_root/bin/copilot" <<'EOF'
#!/bin/zsh
[[ "$1" != --version ]] || { print 'GitHub Copilot CLI 1.0.114'; exit 0; }
[[ -z "${COPILOT_MOCK_ARGS:-}" ]] || print -r -- "$*" > "$COPILOT_MOCK_ARGS"
model=""; usage=""
while [[ $# -gt 0 ]]; do
  case "$1" in --model) model="$2"; shift ;; --usage-output-file) usage="$2"; shift ;; esac
  shift
done
cat > "${COPILOT_MOCK_PROMPT:-/dev/null}"
[[ -z "${COPILOT_MOCK_PWD:-}" ]] || print -r -- "$PWD home=${COPILOT_HOME:-} plugin_dir_only=${COPILOT_PLUGIN_DIR_ONLY:-}" > "$COPILOT_MOCK_PWD"
mode="${COPILOT_TEST_MODE:-success}"
[[ "$mode" != fail ]] || exit 3
[[ "$mode" != hang ]] || sleep 30
served="$model"; [[ "$mode" != mismatch ]] || served="claude-sonnet-5.5"
mcp=disabled; [[ "$mode" != mcp ]] || mcp=connected
body=""
for i in {1..8}; do body+="The supplied packet is internally consistent and the proposed boundary is testable. "; done
body+=$'\n\nATTESTATION: all actionable findings and conditions are labeled.\n\nVERDICT: ACCEPT'
half=$(( ${#body} / 2 ))
jq -nc --arg s "$mcp" '{type:"session.mcp_servers_loaded",data:{servers:[{name:"github-mcp-server",status:$s}]}}'
[[ "$mode" != tool ]] || jq -nc '{type:"tool.execution_start",data:{toolName:"read"}}'
reqs='[]'; [[ "$mode" != toolreq ]] || reqs='[{"name":"shell"}]'
server='{"provider":"openai-responses"}'; [[ "$mode" != servertool ]] || server='{"provider":"openai-responses","webSearch":{}}'
# One reply as three chunk messages (an empty one first), emitted out of order:
# the wrapper must group them by originatingMessageId and join by chunkIndex.
chunk() { jq -nc --arg id "$1" --argjson ci "$2" --argjson cc "${5:-$cc}" --arg m "$served" --arg c "$3" --argjson r "$4" --argjson st "$server" --arg o "${6:-u1}" \
  --argjson nomodel "$([[ "$mode" == nomodel* && "$1" == m3 ]] && print true || print false)" \
  --argjson nokey "$([[ "$mode" == nokey ]] && print true || print false)" \
  '{type:"assistant.message",data:{messageId:$id,originatingMessageId:$o,apiCallId:"a1",chunkIndex:$ci,chunkCount:$cc,model:$m,content:$c,toolRequests:$r,serverTools:$st}}
   | if $nomodel then del(.data.model) else . end | if $nokey then del(.data.messageId, .data.originatingMessageId) else . end'; }
cc=3; [[ "$mode" != incomplete && "$mode" != nomodel-incomplete ]] || cc=4
# An earlier chunk of the final reply's key, separated from it by another reply: never stitched in.
[[ "$mode" != splitkey ]] || { chunk m0 1 "${body:0:$half}" '[]'; chunk x1 0 "other reply" '[]' 1 u9; }
chunk m3 2 "${body:$half}" '[]' "$([[ "$mode" == countmismatch ]] && print 4 || print $cc)"
chunk m1 0 "" '[]'
chunk m2 1 "${body:0:$half}" "$reqs"
# A newer reply whose only chunk so far is empty: the wrapper must not fall back to the earlier reply.
[[ "$mode" != staleempty ]] || chunk m4 0 "" '[]' 2 u2
[[ "$mode" == noresult ]] || jq -nc '{type:"result",exitCode:0}'
[[ "$mode" != doubleresult ]] || jq -nc '{type:"result",exitCode:1}'
[[ "$mode" != afterresult ]] || jq -nc '{type:"assistant.idle",data:{}}'
[[ -z "$usage" ]] || print '{"totalNanoAiu":2500000000,"tokenDetails":{"input":10,"output":20}}' > "$usage"
exit 0
EOF
chmod 755 "$test_root/bin/copilot"
jq '.max_prompt_bytes = 10' "$root/copilot-model-policy.json" > "$test_root/copilot-small-policy.json"
copilot_repo="$test_root/copilot-repo"; copilot_fail_repo="$test_root/copilot-fail-repo"; mkdir -p "$copilot_repo/.collab" "$copilot_fail_repo/.collab"
copilot_args="$test_root/copilot-args"; copilot_prompt="$test_root/copilot-prompt"; copilot_pwd="$test_root/copilot-pwd"
copilot_review() {
  local repo="$1" tier="$2" output="$3"; shift 3
  : > "$copilot_args"
  PATH="$test_root/bin:$PATH" COPILOT_MOCK_ARGS="$copilot_args" COPILOT_MOCK_PROMPT="$copilot_prompt" COPILOT_MOCK_PWD="$copilot_pwd" \
    "$root/copilot-review.sh" --packet-root "$test_root" "$@" "$tier" "$test_root/prompt.md" "$repo/.collab/$output" "$test_root/packet/source.md"
}
copilot_fails() {
  # copilot_fails EXIT OUTPUT [VAR=value]...: a routine review owned by claude, with the mock's settings.
  local expected="$1" output="$2"; shift 2
  # A repository per case keeps the daily per-provider cap out of the way; checks after a call use this path.
  copilot_fail_repo="$test_root/copilot-fail-${output%.md}"; mkdir -p "$copilot_fail_repo/.collab"
  set +e; ( for kv in "$@"; do export "$kv"; done; copilot_review "$copilot_fail_repo" routine "$output" --owner claude ) >/dev/null 2>&1
  local code=$?; set -e
  [[ $code -eq $expected && ! -e "$copilot_fail_repo/.collab/$output" ]] \
    || { print -u2 "copilot $output: expected exit $expected, got $code"; exit 1; }
}
copilot_review "$copilot_repo" hard copilot-2026-11-21-hard.md --owner claude --task T9 >/dev/null
for flag in '--model gpt-6.1-terra' '--available-tools=gateway_no_tools' '--deny-tool=shell' '--deny-tool=read' '--deny-tool=url' \
  '--disable-builtin-mcps' '--no-custom-instructions' '--disallow-temp-dir' '--no-ask-user' '--max-ai-credits 60' '--output-format json'; do
  grep -F -- "$flag" "$copilot_args" >/dev/null || { print -u2 "copilot argv missing: $flag"; exit 1; }
done
grep -F 'Safe packet fixture.' "$copilot_prompt" >/dev/null
read -r copilot_cwd copilot_env_home copilot_env_plugins < "$copilot_pwd"
copilot_env_home="${copilot_env_home#home=}"
[[ "$copilot_cwd" == */workspace && "${copilot_env_home:a}" == "${${copilot_cwd%/workspace}:a}/home" && "$copilot_env_plugins" == plugin_dir_only=true ]] \
  || { print -u2 "copilot did not run in a private workspace and home: $(<"$copilot_pwd")"; exit 1; }
[[ ! -e "$copilot_cwd" ]] || { print -u2 "copilot temporary workspace was not removed"; exit 1; }
for line in 'Owner: claude' 'Task: T9' 'Requested model: hard' 'Selected model: gpt-6.1-terra' 'Reviewer vendor: openai' \
  'Resolved model(s): gpt-6.1-terra' 'CLI version: GitHub Copilot CLI 1.0.114' 'Tool events: 0' 'AI credits: 2.5 AI credits (cap 60)'; do
  grep -Fx -- "$line" "$copilot_repo/.collab/copilot-2026-11-21-hard.md" >/dev/null || { print -u2 "copilot-hard missing: $line"; exit 1; }
done
grep -F 'testable. The supplied' "$copilot_repo/.collab/copilot-2026-11-21-hard.md" >/dev/null
[[ -s "$copilot_repo/.collab/copilot-2026-11-21-hard.md.sha256" ]]
# Copilot-owned work: every author model's vendor is skipped.
copilot_review "$copilot_repo" routine copilot-2026-11-21-own.md --owner copilot --author-model gpt-6-luna >/dev/null
grep -F -- '--model claude-haiku-5.5' "$copilot_args" >/dev/null
copilot_review "$copilot_repo" routine copilot-2026-11-21-forced.md --owner claude --vendor xai >/dev/null
grep -Fx 'Selected model: grok-4.6' "$copilot_repo/.collab/copilot-2026-11-21-forced.md" >/dev/null
# Vendor refusals happen before any call and leave no diagnostic.
for args in "--owner claude --vendor anthropic" "--owner copilot" "--owner copilot --author-model claude-sonnet-5.5 --vendor anthropic"; do
  set +e; copilot_review "$copilot_fail_repo" routine copilot-2026-11-21-vendor.md ${=args} >/dev/null 2>&1; code=$?; set -e
  [[ $code -eq 64 && ! -s "$copilot_args" && ! -e "$copilot_fail_repo/.collab/copilot-2026-11-21-vendor.diagnostic.json" ]] \
    || { print -u2 "copilot vendor rule ($args): got $code"; exit 1; }
done
copilot_fails 70 copilot-2026-11-21-tool.md COPILOT_TEST_MODE=tool
jq -e '.model_invocation_began == true and .selected_model == "gpt-6-luna" and .reviewer_vendor == "openai" and (.reason | contains("tool events"))' \
  "$copilot_fail_repo/.collab/copilot-2026-11-21-tool.diagnostic.json" >/dev/null
copilot_fails 70 copilot-2026-11-21-toolreq.md COPILOT_TEST_MODE=toolreq
copilot_fails 70 copilot-2026-11-21-servertool.md COPILOT_TEST_MODE=servertool
copilot_fails 70 copilot-2026-11-21-mcp.md COPILOT_TEST_MODE=mcp
jq -e '.reason | contains("MCP server")' "$copilot_fail_repo/.collab/copilot-2026-11-21-mcp.diagnostic.json" >/dev/null
copilot_fails 74 copilot-2026-11-21-mismatch.md COPILOT_TEST_MODE=mismatch
copilot_fails 70 copilot-2026-11-21-noresult.md COPILOT_TEST_MODE=noresult
copilot_fails 70 copilot-2026-11-21-doubleresult.md COPILOT_TEST_MODE=doubleresult
copilot_fails 70 copilot-2026-11-21-afterresult.md COPILOT_TEST_MODE=afterresult
copilot_fails 70 copilot-2026-11-21-countmismatch.md COPILOT_TEST_MODE=countmismatch
copilot_fails 70 copilot-2026-11-21-staleempty.md COPILOT_TEST_MODE=staleempty
copilot_fails 74 copilot-2026-11-21-nomodel.md COPILOT_TEST_MODE=nomodel
jq -e '.reason | contains("did not name its model")' "$copilot_fail_repo/.collab/copilot-2026-11-21-nomodel.diagnostic.json" >/dev/null
copilot_fails 74 copilot-2026-11-21-nomodel-incomplete.md COPILOT_TEST_MODE=nomodel-incomplete
jq -e '.reason | contains("did not name its model")' "$copilot_fail_repo/.collab/copilot-2026-11-21-nomodel-incomplete.diagnostic.json" >/dev/null
copilot_fails 70 copilot-2026-11-21-nokey.md COPILOT_TEST_MODE=nokey
copilot_fails 70 copilot-2026-11-21-splitkey.md COPILOT_TEST_MODE=splitkey
jq -e '.reason | contains("extraction")' "$copilot_fail_repo/.collab/copilot-2026-11-21-splitkey.diagnostic.json" >/dev/null
copilot_fails 70 copilot-2026-11-21-incomplete.md COPILOT_TEST_MODE=incomplete
jq -e '.reason | contains("extraction")' "$copilot_fail_repo/.collab/copilot-2026-11-21-incomplete.diagnostic.json" >/dev/null
copilot_fails 70 copilot-2026-11-21-nonzero.md COPILOT_TEST_MODE=fail
copilot_fails 70 copilot-2026-11-21-timeout.md COPILOT_TEST_MODE=hang COPILOT_MAX_TIME_SECONDS=1
jq -e '.reason == "Copilot invocation timed out"' "$copilot_fail_repo/.collab/copilot-2026-11-21-timeout.diagnostic.json" >/dev/null
copilot_fails 78 copilot-2026-11-21-envmodel.md COPILOT_MODEL=gpt-6-luna
copilot_fails 78 copilot-2026-11-21-envprovider.md COPILOT_PROVIDER_BASE_URL=http://127.0.0.1:1
jq -e '.model_invocation_began == false' "$copilot_fail_repo/.collab/copilot-2026-11-21-envprovider.diagnostic.json" >/dev/null
copilot_fails 65 copilot-2026-11-21-oversize.md COPILOT_REVIEW_MODEL_POLICY="$test_root/copilot-small-policy.json"
set +e; copilot_review "$copilot_fail_repo" routine kimi-2026-11-21-name.md --owner claude >/dev/null 2>&1; code=$?; set -e
[[ $code -eq 65 && ! -s "$copilot_args" ]] || { print -u2 "copilot accepted a non-copilot output name ($code)"; exit 1; }
# --owner is required; refused before any call.
rm -f "$copilot_args"
set +e; ( PATH="$test_root/bin:$PATH" COPILOT_MOCK_ARGS="$copilot_args" "$root/copilot-review.sh" --packet-root "$test_root" routine \
  "$test_root/prompt.md" "$copilot_fail_repo/.collab/copilot-2026-11-21-noowner.md" "$test_root/packet/source.md" ) >/dev/null 2>&1; code=$?; set -e
[[ $code -eq 64 && ! -e "$copilot_args" && ! -e "$copilot_fail_repo/.collab/copilot-2026-11-21-noowner.diagnostic.json" ]] || { print -u2 "copilot ran without --owner ($code)"; exit 1; }
# A helper failing after the call still leaves a spent-attempt diagnostic.
claims_root="$test_root/gateway-claims"; cp -Rp "$root" "$claims_root"
print 'import sys; sys.exit(3)' > "$claims_root/reviewer-claims.py"
git -C "$claims_root" -c user.email=t@t -c user.name=t commit -qam 'failing claims helper'
claims_repo="$test_root/copilot-claims-repo"; mkdir -p "$claims_repo/.collab"
set +e; PATH="$test_root/bin:$PATH" "$claims_root/copilot-review.sh" --packet-root "$test_root" --owner claude routine "$test_root/prompt.md" \
  "$claims_repo/.collab/copilot-2026-11-21-claims.md" "$test_root/packet/source.md" >/dev/null 2>&1; code=$?; set -e
[[ $code -eq 70 && ! -e "$claims_repo/.collab/copilot-2026-11-21-claims.md" ]] || { print -u2 "copilot claims failure: got $code"; exit 1; }
jq -e '.model_invocation_began == true and .exit_code == 70' "$claims_repo/.collab/copilot-2026-11-21-claims.diagnostic.json" >/dev/null
# A checksum failure at publish leaves no artifact, checksum or staging file, and a spent diagnostic.
failbin="$test_root/failbin"; mkdir -p "$failbin"; print '#!/bin/sh\nexit 9' > "$failbin/shasum"; chmod 755 "$failbin/shasum"
sum_repo="$test_root/copilot-sum-repo"; mkdir -p "$sum_repo/.collab"
set +e; PATH="$failbin:$test_root/bin:$PATH" "$root/copilot-review.sh" --packet-root "$test_root" --owner claude routine "$test_root/prompt.md" \
  "$sum_repo/.collab/copilot-2026-11-21-sum.md" "$test_root/packet/source.md" >/dev/null 2>&1; code=$?; set -e
[[ $code -eq 70 && -z "$(ls -A "$sum_repo/.collab" | grep -v '^copilot-2026-11-21-sum.diagnostic.json$')" ]] \
  || { print -u2 "copilot checksum failure: got $code, left: $(ls -A "$sum_repo/.collab")"; exit 1; }
jq -e '.model_invocation_began == true and (.reason | contains("checksum"))' "$sum_repo/.collab/copilot-2026-11-21-sum.diagnostic.json" >/dev/null
# Publication: a signal between linking the checksum and the artifact leaves no
# orphan checksum; a concurrent writer's files are never replaced or removed.
lnbin="$test_root/lnbin"; mkdir -p "$lnbin"
cat > "$lnbin/ln" <<'EOF'
#!/bin/zsh
n=$(( $(cat "$LN_MOCK_COUNTER" 2>/dev/null || print 0) + 1 )); print $n > "$LN_MOCK_COUNTER"
case "$LN_MOCK_MODE" in
  signal) [[ $n -eq 2 ]] && { kill -TERM $PPID; sleep 2; exit 1; } ;;
  race) [[ $n -eq 1 ]] && print 'other writer' > "$2" ;;
esac
exec /bin/ln "$@"
EOF
chmod 755 "$lnbin/ln"
for mode in signal race; do
  pub_repo="$test_root/copilot-pub-$mode"; mkdir -p "$pub_repo/.collab"; out="$pub_repo/.collab/copilot-2026-11-21-pub.md"
  set +e; LN_MOCK_MODE=$mode LN_MOCK_COUNTER="$test_root/ln-$mode" PATH="$lnbin:$test_root/bin:$PATH" "$root/copilot-review.sh" --packet-root "$test_root" \
    --owner claude routine "$test_root/prompt.md" "$out" "$test_root/packet/source.md" >/dev/null 2>&1; code=$?; set -e
  left="$(ls -A "$pub_repo/.collab" | grep -v '^copilot-2026-11-21-pub.diagnostic.json$' || true)"
  if [[ $mode == signal ]]; then
    [[ $code -eq 70 && -z "$left" ]] || { print -u2 "copilot interrupted publication: got $code, left: $left"; exit 1; }
    jq -e '.reason | contains("SIGTERM")' "$pub_repo/.collab/copilot-2026-11-21-pub.diagnostic.json" >/dev/null
  else
    [[ $code -eq 70 && "$left" == copilot-2026-11-21-pub.md.sha256 && "$(<"$out.sha256")" == 'other writer' ]] \
      || { print -u2 "copilot concurrent publication: got $code, left: $left"; exit 1; }
  fi
done
# Budget: a spent Copilot failure counts as a round; a preflight refusal does not;
# a Copilot hard round uses the topic's one hard round for every provider.
[[ "$(python3 "$root/review-budget.py" copilot routine "$claims_repo/.collab/copilot-2026-11-21-claims-r02.md")" == "1 1" ]] \
  || { print -u2 "spent Copilot failure was not counted"; exit 1; }
pre_repo="$test_root/copilot-fail-copilot-2026-11-21-envmodel"
[[ "$(python3 "$root/review-budget.py" copilot routine "$pre_repo/.collab/copilot-2026-11-21-envmodel-r02.md")" == "0 0" ]] \
  || { print -u2 "Copilot preflight refusal was counted"; exit 1; }
[[ "$(python3 "$root/review-budget.py" copilot routine "$copilot_repo/.collab/copilot-2026-11-21-hard-r02.md")" == "1 1" ]]
for provider in copilot codex kimi; do
  set +e; python3 "$root/review-budget.py" $provider hard "$copilot_repo/.collab/$provider-2026-11-21-hard-r02.md" >/dev/null 2>&1; code=$?; set -e
  [[ $code -eq 1 ]] || { print -u2 "$provider hard round allowed after a Copilot hard round"; exit 1; }
done
set +e; copilot_review "$copilot_repo" hard copilot-2026-11-21-hard-r02.md --owner claude >/dev/null 2>&1; code=$?; set -e
[[ $code -eq 79 && ! -s "$copilot_args" ]] || { print -u2 "second Copilot hard round on a topic: got $code"; exit 1; }
jq -e '.reason | contains("hard-tier")' "$copilot_repo/.collab/copilot-2026-11-21-hard-r02.diagnostic.json" >/dev/null
# A spent name is never reused.
set +e; copilot_review "$copilot_repo" routine copilot-2026-11-21-hard.md --owner claude >/dev/null 2>&1; code=$?; set -e
[[ $code -eq 65 && ! -s "$copilot_args" ]] || { print -u2 "Copilot reused an artifact name ($code)"; exit 1; }
set +e; copilot_review "$claims_repo" routine copilot-2026-11-21-claims.md --owner claude >/dev/null 2>&1; code=$?; set -e
[[ $code -eq 65 && ! -s "$copilot_args" ]] || { print -u2 "Copilot reused a diagnostic name ($code)"; exit 1; }
print "wrapper failure smoke tests passed"
