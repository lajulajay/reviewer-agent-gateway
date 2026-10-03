#!/bin/zsh
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd -P)"
test_root="$(mktemp -d "${TMPDIR:-/tmp}/reviewers-test.XXXXXX")"
trap 'rm -rf "$test_root"' EXIT INT TERM
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
  model=""
  while [[ $# -gt 0 ]]; do
    if [[ "$1" == --model ]]; then model="$2"; break; fi
    shift
  done
  [[ -z "${CLAUDE_MOCK_MARKER:-}" ]] || print -r -- "$model" > "$CLAUDE_MOCK_MARKER"
  body=""
  for i in {1..8}; do body+="The supplied packet is internally consistent and the proposed boundary is testable. "; done
  body+=$'The implementation preserves the reviewed input boundary and creates an auditable artifact.\n\nVERDICT: ACCEPT'
  jq -n --arg model "${CLAUDE_MOCK_RESOLVED:-$model}" --arg result "$body" '{is_error:false,result:$result,modelUsage:{($model):{}}}'
  exit 0
fi
exit 42
EOF
cat > "$test_root/bin/ollama" <<'EOF'
#!/bin/zsh
if [[ "$1" == list ]]; then
  print 'NAME ID SIZE MODIFIED'
  print 'kimi-k2.6:cloud test - now'
  exit 0
fi
[[ "$1" == run && "$2" == kimi-k2.6:cloud ]] || exit 64
if [[ "${OLLAMA_TEST_MODE:-}" == success ]]; then
  cat >/dev/null
  for i in {1..8}; do
    print 'Finding: the supplied packet is internally consistent, its stated invariants are testable, no unsafe state mutation is requested, and the implementation should preserve the reviewed input boundaries and independently verifiable artifact contract.'
  done
  print 'VERDICT: ACCEPT'
  exit 0
fi
if [[ "${OLLAMA_TEST_MODE:-}" == subscription ]]; then
  print -u2 'Error: 403 Forbidden: this model requires a subscription, upgrade for access'
  exit 1
fi
print -u2 'simulated Ollama failure'
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
[[ " $* " == *" --sandbox "* && " $* " == *" --mode plan "* && " $* " == *" --disable-slash-commands "* ]] || exit 77
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
  body+=$'The implementation preserves the reviewed input boundary and creates an auditable artifact.\n\nVERDICT: ACCEPT'
  jq -nc --arg response "$body" '{event:"result",result:{conversation_id:"conv-test",status:"SUCCESS",response:$response,usage:{total_tokens:1}}}'
  exit 0
fi
exit 42
EOF
chmod 755 "$test_root/bin/claude" "$test_root/bin/ollama" "$test_root/bin/agy"
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
for wrapper in claude-review.sh gemini-review.sh kimi-review.sh; do
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

run_failure kimi-review.sh kimi-k2.6:cloud kimi.md
: > "$test_root/.collab/claude.md.diagnostic.json"
run_failure claude-review.sh sonnet claude.md
run_failure gemini-review.sh hard gemini.json

# Tier selection pins a full model ID and checks what Claude reports using.
claude_marker="$test_root/claude-marker"
PATH="$test_root/bin:$PATH" CLAUDE_REVIEW_MODEL_POLICY="$test_root/claude-policy.json" \
  CLAUDE_TEST_MODE=success CLAUDE_MOCK_MARKER="$claude_marker" \
  "$root/claude-review.sh" opus "$test_root/prompt.md" \
  "$test_root/.collab/claude-hard.md" "$test_root/packet/source.md" >/dev/null
[[ "$(<"$claude_marker")" == claude-opus-5-5 ]]
grep -Fx 'Selected model: claude-opus-5-5' "$test_root/.collab/claude-hard.md" >/dev/null

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
gemini() {
  local output="$1"; shift
  PATH="$test_root/bin:$PATH" AGY_MOCK_MARKER="$agy_marker" "$@" "$root/gemini-review.sh" \
    "${GEMINI_MODEL:-pro}" "$test_root/prompt.md" "$test_root/.collab/$output" "$test_root/packet/source.md"
}
gemini_fails() {
  local expected="$1" output="$2"; shift 2
  set +e; gemini "$output" "$@" >/dev/null 2>&1; local code=$?; set -e
  [[ $code -eq $expected && -s "$test_root/.collab/${output%.json}.diagnostic.json" && ! -e "$test_root/.collab/$output" ]] \
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

gemini_fails 70 gemini-timeout.json env AGY_TEST_MODE=hang GEMINI_MAX_TIME_SECONDS=1 GEMINI_TIMEOUT_GRACE_SECONDS=1
jq -e '.reason == "Gemini invocation timed out"' "$test_root/.collab/gemini-timeout.diagnostic.json" >/dev/null

set +e
PATH="$test_root/bin:$PATH" \
  "$root/kimi-review.sh" --packet-root "$test_root/shared" kimi-k2.6:cloud \
  "$test_root/shared/prompt.md" "$test_root/.collab/kimi-shared.md" \
  "$test_root/shared/packet.md" "$test_root/packet/source.md" >/dev/null 2>&1
code=$?
set -e
[[ $code -ne 0 ]]
[[ -s "$test_root/.collab/kimi-shared.diagnostic.json" ]]

set +e
OLLAMA_TEST_MODE=subscription PATH="$test_root/bin:$PATH" \
  "$root/kimi-review.sh" kimi-k2.6:cloud "$test_root/prompt.md" \
  "$test_root/.collab/kimi-subscription.md" "$test_root/packet/source.md" >/dev/null 2>&1
code=$?
set -e
[[ $code -eq 78 ]]
jq -e '.reason == "Ollama access denied: this Kimi model requires a subscription"' \
  "$test_root/.collab/kimi-subscription.diagnostic.json" >/dev/null

OLLAMA_TEST_MODE=success PATH="$test_root/bin:$PATH" \
  "$root/kimi-review.sh" kimi-k2.6:cloud "$test_root/prompt.md" \
  "$test_root/.collab/kimi-success.md" "$test_root/packet/source.md" >/dev/null
[[ -s "$test_root/.collab/kimi-success.md" ]]
[[ -s "$test_root/.collab/kimi-success.md.sha256" ]]

python3 - <<'PY' "$root/reviewer-validate.py"
import subprocess
import sys
validator = sys.argv[1]
body = "The review contains substantive findings. " * 20
text = body + "\n\n**VERDICT: ACCEPT WITH CONDITIONS**\n"
assert subprocess.run([validator], input=text, text=True).returncode == 0
for invalid in (
    body + "\nVERDICT: CONDITIONAL\n",
    body + "\nVERDICT: ACCEPT\nVERDICT: REJECT\n",
    body + "\nVERDICT: ACCEPT\nFollow-up text.\n",
):
    assert subprocess.run([validator], input=invalid, text=True).returncode != 0
PY

print "wrapper failure smoke tests passed"
