#!/bin/zsh
set -euo pipefail
umask 077
packet_root=""; owner=""
while [[ "${1:-}" == --* ]]; do
  case "$1" in
    --packet-root) [[ $# -ge 2 ]] || exit 64; packet_root="$2"; shift 2 ;;
    --owner) [[ $# -ge 2 && ( "$2" == codex || "$2" == claude ) ]] || { print -u2 -- "--owner must be codex or claude"; exit 64; }; owner="$2"; shift 2 ;;
    *) print -u2 "unknown option: $1"; exit 64 ;;
  esac
done
[[ $# -ge 4 ]] || { print -u2 "usage: $0 [--packet-root DIR] [--owner codex|claude] <model> <prompt-file> <new-output.json> <packet-file>..."; exit 64; }
requested_model="$1"; model="$requested_model"; prompt="$2"; output="$3"; shift 3
outdir="$(cd "$(dirname "$output")" && pwd -P)"; base="$(basename "$output")"; root="$(cd "$outdir/.." && pwd -P)"
[[ "$outdir" == "$root/.collab" && "$base" == *.json && ! -e "$output" ]] || { print -u2 "invalid or existing output"; exit 65; }
tmp="$(mktemp -d "${TMPDIR:-/tmp}/reviewers-gemini.XXXXXX")"; trap 'rm -rf "$tmp"' EXIT INT TERM
response="$tmp/stream.jsonl"; stderr="$tmp/stderr"; hook_log="$tmp/hook.log"; diagnostic="$outdir/${base%.json}.diagnostic.json"; start=$SECONDS
: > "$response"; : > "$stderr"; : > "$hook_log"
fail() { local code="$1" reason="$2"; if [[ ! -s "$diagnostic" ]]; then jq -n --arg owner "$owner" --arg requested "$requested_model" --arg selected "${selected_model:-}" --arg reason "$reason" --arg code "$code" --arg elapsed "$((SECONDS-start))" --rawfile stdout "$response" --rawfile stderr "$stderr" '{provider:"gemini",cli:"agy",owner:$owner,requested_model:$requested,preflight_selected_model:$selected,reason:$reason,exit_code:($code|tonumber),elapsed_seconds:($elapsed|tonumber),stdout:$stdout,stderr:$stderr}' > "$tmp/diagnostic.json" && chmod 444 "$tmp/diagnostic.json" && mv -f "$tmp/diagnostic.json" "$diagnostic"; fi; print -u2 "$reason; diagnostics captured at $diagnostic"; exit "$code"; }
safe() { local f="$1" label="$2"; [[ -f "$f" && ! -L "$f" ]] || fail 66 "$label is not a regular file"; f="$(cd "$(dirname "$f")" && pwd -P)/$(basename "$f")"; if [[ -n "$packet_root" ]]; then local pr="$(cd "$packet_root" 2>/dev/null && pwd -P)"; case "$f" in "$root"/*|"$pr"/*) ;; *) fail 77 "$label is outside allowed roots";; esac; else case "$f" in "$root"/*) ;; *) fail 77 "$label must be inside repo or use --packet-root";; esac; fi; case "$f" in */.env|*/.env.*|*/.reviewers.env|*/data/*|*/exports/*|*/artifacts/private/*|*.pem|*.key) fail 77 "refusing private $label";; esac; REPLY="$f"; }
# Provenance (workspace framework v6 §7): record the gateway commit this wrapper
# ran from; refuse to run with uncommitted wrapper changes or a Git error. A
# copy outside any repository (consumer-shim fixtures) records "unversioned",
# which docs-check rejects for reviews captured after adoption.
wrapper_rev="unversioned"
if git -C "$(dirname "$0")" rev-parse --git-dir >/dev/null 2>&1; then
  wrapper_rev="$(git -C "$(dirname "$0")" rev-parse HEAD 2>/dev/null)" || fail 78 "cannot read the gateway revision"
  wrapper_dirty="$(git -C "$(dirname "$0")" status --porcelain -- '*.sh' '*.py' '*.json' output-contract.txt ':(exclude).collab' 2>/dev/null)" || fail 78 "cannot read gateway status"
  [[ -z "$wrapper_dirty" ]] || fail 78 "gateway wrapper files have uncommitted changes"
fi
command -v agy >/dev/null || fail 69 "agy (Antigravity CLI) not found"; command -v jq >/dev/null || fail 69 "jq is required"; safe "$prompt" prompt; prompt="$REPLY"
# Reviews run on the signed-in Google account's plan quota. An API key would
# switch agy to billed Gemini API calls, so its presence is refused.
[[ -z "${GEMINI_API_KEY:-}" && -z "${GOOGLE_API_KEY:-}" ]] || fail 78 "GEMINI_API_KEY/GOOGLE_API_KEY would bypass the Antigravity plan quota"
policy="${GEMINI_REVIEW_MODEL_POLICY:-$(dirname "$0")/gemini-model-policy.json}"
selected_model="$(python3 "$(dirname "$0")/gemini-model-select.py" "$policy" "$requested_model" 2> "$stderr")" || fail 78 "Gemini model selection failed"
model="$selected_model"
export AGY_CLI_DISABLE_AUTO_UPDATE=1
agy_version="$(agy --version 2>> "$stderr" | head -1)" || fail 69 "agy version check failed"
# The workspace holds only the deny-all hook. agy runs PreToolUse hooks before
# its permission rules (a user-level allow does not bypass them) and blocks
# the call if the hook itself fails, so the reviewer can use no tools: no
# file reads, shell, web, browser, scheduling, or subagents. The packet is
# inlined into the prompt instead; agy -p ignores stdin.
workspace="$tmp/workspace"; mkdir -p -m 700 "$workspace/.agents"
cat > "$workspace/.agents/deny-tools.sh" <<'EOF'
#!/bin/sh
{ cat; printf '\n'; } >> ../../hook.log
printf '{"decision":"deny","reason":"reviewer isolation: tools are disabled"}'
EOF
chmod 700 "$workspace/.agents/deny-tools.sh"
print -r -- '{"reviewer-isolation":{"PreToolUse":[{"matcher":"*","hooks":[{"type":"command","command":"./deny-tools.sh","timeout":5}]}]}}' > "$workspace/.agents/hooks.json"
prompt_text="$(<"$prompt")"
for f in "$@"; do safe "$f" packet; prompt_text+="

===== $(basename "$REPLY") =====
$(<"$REPLY")"; done
prompt_text+="

TOOLS: None are available; every tool call is denied. Review only the text above.

$(<"$(dirname "$0")/output-contract.txt")"
max_prompt_bytes="${GEMINI_MAX_PROMPT_BYTES:-800000}"
prompt_bytes="$(print -rn -- "$prompt_text" | wc -c | tr -d ' ')"
[[ "$prompt_bytes" -le "$max_prompt_bytes" ]] || fail 65 "prompt and packet exceed $max_prompt_bytes bytes (agy takes the prompt as an argument)"
# The hard-tier model spends its output tokens on hidden reasoning over large
# packets and hits its output-token limit (215-245 KB failed, 40 KB succeeded on
# 2026-10-08). Refuse before the budget check so no round is used.
hard_max_bytes="${GEMINI_HARD_MAX_PROMPT_BYTES:-150000}"
[[ "$model" != "$(jq -r '.hard_model // empty' "$policy")" || "$prompt_bytes" -le "$hard_max_bytes" ]] \
  || fail 65 "hard-tier prompt and packet are $prompt_bytes bytes, over $hard_max_bytes: split the packet or send a delta"
run_agy() { (cd "$workspace" && env -u GEMINI_API_KEY -u GOOGLE_API_KEY -u GOOGLE_APPLICATION_CREDENTIALS -u GOOGLE_GENAI_USE_VERTEXAI -u GOOGLE_GENAI_USE_GCA -u GOOGLE_CLOUD_PROJECT "$@"); }
# Gemini tiers are not capped per topic: Gemini is the escalation reviewer.
budget="$(python3 "$(dirname "$0")/review-budget.py" gemini routine "$outdir/$base" 2> "$tmp/budget.err")" || fail 79 "$(<"$tmp/budget.err")"
# Quota preflight: the Gemini group shares one weekly limit across Flash and
# Pro. Stop with headroom left rather than spending AI credits after it.
min_quota="${GEMINI_REVIEW_MIN_QUOTA:-0.15}"
set +e
run_agy perl -e 'alarm(60); exec @ARGV' agy -p /usage --output-format json > "$tmp/usage.json" 2>> "$stderr"
code=$?; set -e
[[ $code -eq 0 ]] || fail 78 "Antigravity quota check failed (signed out?)"
quota="$(jq -r '[.command.data.groups[]? | select(.name == "Gemini Models") | .buckets[]?.remaining_fraction] | if length == 0 then empty else min end' "$tmp/usage.json" 2>/dev/null)"
[[ -n "$quota" ]] || fail 78 "Antigravity quota check returned no Gemini bucket"
jq -en --argjson q "$quota" --argjson min "$min_quota" '$q >= $min' >/dev/null || fail 78 "Gemini weekly quota remaining ($quota) is below the $min_quota floor"
timeout_seconds="${GEMINI_MAX_TIME_SECONDS:-600}"
[[ "$timeout_seconds" == <-> && "$timeout_seconds" -ge 1 ]] || fail 64 "GEMINI_MAX_TIME_SECONDS must be a positive integer"
grace_seconds="${GEMINI_TIMEOUT_GRACE_SECONDS:-30}"
[[ "$grace_seconds" == <-> && "$grace_seconds" -ge 1 ]] || fail 64 "GEMINI_TIMEOUT_GRACE_SECONDS must be a positive integer"
# --print-timeout is agy's own limit; the alarm is a backstop if agy hangs.
set +e
run_agy perl -e 'alarm($ARGV[0]); shift; exec @ARGV' "$((timeout_seconds + grace_seconds))" agy -p "$prompt_text" --model "$model" --sandbox --disable-slash-commands --output-format stream-json --print-timeout "${timeout_seconds}s" > "$response" 2>> "$stderr"
code=$?; set -e
[[ $code -ne 142 ]] || fail 70 "Gemini invocation timed out"
[[ -s "$response" ]] || fail 70 "Gemini invocation failed or returned empty output"
result="$(jq -c 'select(.event == "result") | .result' "$response" 2>/dev/null | tail -1)" || fail 70 "Gemini returned invalid stream JSON"
# Model or agent errors exit 3 with an AGY_ERROR line on stderr.
agy_error="$(grep -m1 AGY_ERROR "$stderr" || true)"
[[ $code -eq 0 && -n "$result" ]] || fail 70 "Gemini invocation failed (exit $code)${agy_error:+: $agy_error}"
# A run that hits the output-token limit ends as ERROR even when the review it
# returned is complete (hidden reasoning used the tokens; 2026-10-08). Keep it
# only if it passes validation, and record the warning.
truncation=""
if ! jq -e '.status == "SUCCESS" and (.response | type == "string")' <<< "$result" >/dev/null 2>&1; then
  jq -e '.status == "ERROR" and ((.error // "") | test("^Your previous response was cut off because it exceeded the output token limit")) and (.response | type == "string")' <<< "$result" >/dev/null 2>&1 \
    || fail 70 "Gemini invocation did not succeed"
  jq -r '.response' <<< "$result" | python3 "$(dirname "$0")/reviewer-validate.py" 2>> "$stderr" \
    || fail 70 "Gemini hit the output-token limit before finishing the review; split the packet or send a delta"
  truncation="agy reported the output-token limit; the returned review passed validation and was kept"
fi
# agy reports the session model only in the stream's init event.
resolved="$(jq -r 'select(.event == "init") | .init.model // empty' "$response" | sort -u | paste -sd, -)"; [[ -n "$resolved" ]] || fail 74 "Gemini returned no resolved model metadata"
[[ "$resolved" == "$model" ]] || fail 74 "Gemini resolved outside selected model"
jq -r '.response' <<< "$result" | python3 "$(dirname "$0")/reviewer-validate.py" || fail 70 "Gemini response failed substance validation"
checks="$(jq -r '.response' <<< "$result" | python3 "$(dirname "$0")/reviewer-claims.py" | jq -Rsc 'split("\n") | map(select(length > 0))')"
denied="$(jq -sc '[.[] | .toolCall.name? // empty]' "$hook_log" 2>/dev/null)" || denied='["<unparseable hook log>"]'
jq --arg owner "$owner" --arg wrev "$wrapper_rev" --arg requested "$requested_model" --arg selected "$selected_model" --arg resolved "$resolved" --arg version "$agy_version" --argjson quota "$quota" --argjson denied "$denied" --argjson checks "$checks" --arg override "${REVIEW_BUDGET_OVERRIDE:-}" --arg truncation "$truncation" \
  '. + {reviewer_metadata:({owner:$owner,wrapper_revision:$wrev,cli:"agy",cli_version:$version,requested_model:$requested,preflight_selected_model:$selected,resolved_models:($resolved|split(",")),conversation_id:.conversation_id,quota_remaining_before:$quota,denied_tool_calls:$denied,mechanical_checks:$checks} + (if $override == "" then {} else {budget_override:$override} end) + (if $truncation == "" then {} else {truncation_warning:$truncation} end))}' <<< "$result" > "$tmp/final.json" || fail 70 "Gemini response was not valid JSON"
chmod 444 "$tmp/final.json"; mv "$tmp/final.json" "$output"; shasum -a 256 "$output" > "$output.sha256"; chmod 444 "$output" "$output.sha256"; [[ -s "$output" && -s "$output.sha256" ]] || fail 70 "Gemini artifact or checksum was not created"; print "captured $output"
