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
# A real run requires a root-owned file; the explicit override path is exercised
# here, and the wrapper still validates its contents.
print '{"security":{"auth":{"selectedType":"gemini-api-key","enforcedType":"gemini-api-key"}}}' > "$test_root/gemini-settings.json"
print '{"security":{"auth":{"selectedType":"oauth-personal"}}}' > "$test_root/gemini-settings-weak.json"
export GEMINI_REVIEW_SYSTEM_SETTINGS="$test_root/gemini-settings.json" GEMINI_API_KEY=test

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
cat > "$test_root/bin/gemini" <<'EOF'
#!/bin/zsh
[[ -z "${GEMINI_MOCK_MARKER:-}" ]] || print -r -- "$*" > "$GEMINI_MOCK_MARKER"
[[ "${GEMINI_TEST_MODE:-}" != hang ]] || sleep 30
[[ "${GEMINI_TEST_MODE:-}" != skipped-settings ]] || print -u2 "Security Warning: Skipping system settings file '$GEMINI_CLI_SYSTEM_SETTINGS_PATH': Parent directory is insecure"
if [[ "${GEMINI_TEST_MODE:-}" == success || "${GEMINI_TEST_MODE:-}" == skipped-settings ]]; then
  [[ "${GEMINI_API_KEY:-}" == test && -z "${GOOGLE_API_KEY:-}" ]] || exit 77
  jq -e '.security.auth.selectedType == "gemini-api-key" and .security.auth.enforcedType == "gemini-api-key"' "$GEMINI_CLI_SYSTEM_SETTINGS_PATH" >/dev/null || exit 77
  model=""
  while [[ $# -gt 0 ]]; do
    if [[ "$1" == --model ]]; then model="$2"; break; fi
    shift
  done
  body=""
  for i in {1..8}; do body+="The supplied packet is internally consistent and the proposed boundary is testable. "; done
  body+=$'The implementation preserves the reviewed input boundary and creates an auditable artifact.\n\nVERDICT: ACCEPT'
  jq -n --arg response "$body" --arg model "${GEMINI_MOCK_RESOLVED:-$model}" '{response:$response, stats:{models:{($model):{}}}}'
  exit 0
fi
exit 42
EOF
chmod 755 "$test_root/bin/claude" "$test_root/bin/ollama" "$test_root/bin/gemini"
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
  PATH="$test_root/bin:$PATH" GEMINI_API_KEY=test CLAUDE_REVIEW_MODEL_POLICY="$test_root/claude-policy.json" \
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

# Gemini policy pins both tiers and rejects a resolved-model mismatch.
gemini_marker="$test_root/gemini-marker"
: > "$gemini_marker"
PATH="$test_root/bin:$PATH" GEMINI_API_KEY=test GEMINI_TEST_MODE=success \
  GEMINI_MOCK_MARKER="$gemini_marker" "$root/gemini-review.sh" pro \
  "$test_root/prompt.md" "$test_root/.collab/gemini-hard.json" \
  "$test_root/packet/source.md" >/dev/null
grep -F -- '--model gemini-3.8-flash' "$gemini_marker" >/dev/null
jq -e '.reviewer_metadata.requested_model == "pro" and .reviewer_metadata.preflight_selected_model == "gemini-3.8-flash"' \
  "$test_root/.collab/gemini-hard.json" >/dev/null
[[ -s "$test_root/.collab/gemini-hard.json.sha256" ]]

PATH="$test_root/bin:$PATH" GEMINI_TEST_MODE=success \
  GEMINI_MOCK_MARKER="$gemini_marker" "$root/gemini-review.sh" flash \
  "$test_root/prompt.md" "$test_root/.collab/gemini-routine.json" \
  "$test_root/packet/source.md" >/dev/null
grep -F -- '--model gemini-3.6-flash' "$gemini_marker" >/dev/null

set +e
PATH="$test_root/bin:$PATH" GEMINI_TEST_MODE=success GEMINI_MOCK_RESOLVED=gemini-3.7-flash \
  "$root/gemini-review.sh" pro "$test_root/prompt.md" \
  "$test_root/.collab/gemini-mismatch.json" "$test_root/packet/source.md" >/dev/null 2>&1
code=$?
set -e
[[ $code -eq 74 && -s "$test_root/.collab/gemini-mismatch.diagnostic.json" ]]
[[ ! -e "$test_root/.collab/gemini-mismatch.json" ]]

# A CLI that skipped the enforced settings ran without the login/no-overage
# guarantees; its otherwise valid review must not be captured.
set +e
PATH="$test_root/bin:$PATH" GEMINI_TEST_MODE=skipped-settings \
  "$root/gemini-review.sh" pro "$test_root/prompt.md" \
  "$test_root/.collab/gemini-skipped.json" "$test_root/packet/source.md" >/dev/null 2>&1
code=$?
set -e
[[ $code -eq 78 && -s "$test_root/.collab/gemini-skipped.diagnostic.json" ]]
[[ ! -e "$test_root/.collab/gemini-skipped.json" ]]

set +e
PATH="$test_root/bin:$PATH" GEMINI_TEST_MODE=success GEMINI_REVIEW_SYSTEM_SETTINGS="$test_root/gemini-settings-weak.json" \
  "$root/gemini-review.sh" pro "$test_root/prompt.md" \
  "$test_root/.collab/gemini-weak.json" "$test_root/packet/source.md" >/dev/null 2>&1
code=$?
set -e
[[ $code -eq 78 && -s "$test_root/.collab/gemini-weak.diagnostic.json" ]]

set +e
PATH="$test_root/bin:$PATH" GEMINI_TEST_MODE=hang GEMINI_MAX_TIME_SECONDS=1 \
  "$root/gemini-review.sh" pro "$test_root/prompt.md" \
  "$test_root/.collab/gemini-timeout.json" "$test_root/packet/source.md" >/dev/null 2>&1
code=$?
set -e
[[ $code -eq 70 ]]
jq -e '.reason == "Gemini invocation timed out"' "$test_root/.collab/gemini-timeout.diagnostic.json" >/dev/null

# No key in the environment or any credentials file fails before staging.
set +e
env -u GEMINI_API_KEY PATH="$test_root/bin:$PATH" GEMINI_TEST_MODE=success \
  "$root/gemini-review.sh" pro "$test_root/prompt.md" \
  "$test_root/.collab/gemini-nokey.json" "$test_root/packet/source.md" >/dev/null 2>&1
code=$?
set -e
[[ $code -eq 78 && -s "$test_root/.collab/gemini-nokey.diagnostic.json" ]]

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
