#!/bin/zsh
set -euo pipefail
umask 077

packet_root=""; owner=""; task=""; authors=(); author_models=()
while [[ "${1:-}" == --* ]]; do
  case "$1" in
    --packet-root) [[ $# -ge 2 ]] || exit 64; packet_root="$2"; shift 2 ;;
    --owner) [[ $# -ge 2 && -n "$2" ]] || exit 64; owner="$2"; shift 2 ;;
    --author) [[ $# -ge 2 && -n "$2" ]] || exit 64; authors+=("$2"); shift 2 ;;
    --author-model) [[ $# -ge 2 && -n "$2" ]] || exit 64; author_models+=("$2"); shift 2 ;;
    --task) [[ $# -ge 2 && "$2" =~ '^[A-Za-z0-9._-]+$' ]] || { print -u2 -- "--task must be a short identifier"; exit 64; }; task="$2"; shift 2 ;;
    *) print -u2 "unknown option: $1"; exit 64 ;;
  esac
done
[[ $# -ge 4 ]] || { print -u2 "usage: $0 [--packet-root DIR] [--owner AGENT] [--author AGENT]... [--author-model MODEL]... [--task ID] <hard|routine> <prompt-file> <new-output.md> <packet-file>..."; exit 64; }
# Identity and vendor independence (agents.json): no vendor reviews work it owns or wrote, whatever the model version.
identity=(); [[ -z "$owner" ]] || identity+=(--owner "$owner"); for a in "${authors[@]}"; do identity+=(--author "$a"); done; for m in "${author_models[@]}"; do identity+=(--author-model "$m"); done
python3 "${0:A:h}/agents.py" check kimi "${identity[@]}" || exit $?
requested_model="$1"; prompt="$2"; output="$3"; shift 3
outdir="$(cd "$(dirname "$output")" && pwd -P)"; base="$(basename "$output")"; root="$(cd "$outdir/.." && pwd -P)"
[[ "$outdir" == "$root/.collab" && "$base" == *.md && ! -e "$output" && ! -e "$outdir/${base%.md}.diagnostic.json" ]] || { print -u2 "invalid, existing, or previously attempted output"; exit 65; }
# Copilot sub-agent rounds run only on a coordinator ticket (review-ticket.py); any ticket for this output is enforced.
ticket_args=("${identity[@]}"); [[ -z "$task" ]] || ticket_args+=(--task "$task")
python3 "${0:A:h}/review-ticket.py" check kimi "$requested_model" "$output" "${ticket_args[@]}" -- "$@" || exit $?
tmp="$(mktemp -d "${TMPDIR:-/tmp}/reviewers-kimi.XXXXXX")"
stdout="$tmp/stream.jsonl"; stderr="$tmp/stderr"; combined="$tmp/prompt.txt"; last="$tmp/last.md"; diagnostic="$outdir/${base%.md}.diagnostic.json"; start=$SECONDS
model_invocation_started=0
: > "$stdout"; : > "$stderr"
fail() { local code="$1" reason="$2"; local began=false; [[ "$model_invocation_started" == 1 ]] && began=true; if [[ ! -s "$diagnostic" ]]; then jq -n --arg owner "$owner" --arg requested "$requested_model" --arg selected "${model:-}" --arg effort "${effort:-}" --arg reason "$reason" --arg code "$code" --argjson invoked "$began" --arg elapsed "$((SECONDS-start))" --rawfile stdout "$stdout" --rawfile stderr "$stderr" '{provider:"kimi",cli:"kimi",owner:$owner,requested_model:$requested,selected_model:$selected,reasoning_effort:$effort,reason:$reason,exit_code:($code|tonumber),model_invocation_began:$invoked,elapsed_seconds:($elapsed|tonumber),stdout:$stdout,stderr:$stderr}' > "$tmp/diagnostic.json" && chmod 444 "$tmp/diagnostic.json" && mv -f "$tmp/diagnostic.json" "$diagnostic"; fi; print -u2 "$reason; diagnostics captured at $diagnostic"; exit "$code"; }
cleanup() { rm -rf "$tmp"; }
interrupted() { local signal="$1"; trap - "$signal"; if [[ "$model_invocation_started" == 1 ]]; then fail 70 "Kimi invocation did not complete after model invocation began (interrupted by SIG$signal)"; else fail 78 "Kimi invocation interrupted before model invocation began (SIG$signal)"; fi; }
trap cleanup EXIT
trap 'interrupted HUP' HUP
trap 'interrupted INT' INT
trap 'interrupted TERM' TERM
safe() { local f="$1" label="$2"; [[ -f "$f" && ! -L "$f" ]] || fail 66 "$label is not a regular file"; f="$(cd "$(dirname "$f")" && pwd -P)/$(basename "$f")"; if [[ -n "$packet_root" ]]; then local pr="$(cd "$packet_root" 2>/dev/null && pwd -P)" || fail 77 "invalid packet root"; case "$f" in "$root"/*|"$pr"/*) ;; *) fail 77 "$label is outside allowed roots";; esac; else case "$f" in "$root"/*) ;; *) fail 77 "$label must be inside repo or use --packet-root";; esac; fi; case "$f" in */.env|*/.env.*|*/.reviewers.env|*/data/*|*/exports/*|*/artifacts/private/*|*.pem|*.key) fail 77 "refusing private $label";; esac; REPLY="$f"; }
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
# Route (model policy "route"): "api" calls the provider HTTP API with a Keychain key
# and a spend cap (api-route.sh, api-call.py); "subscription" (default) uses the CLI plan.
provider=kimi; policy="${KIMI_REVIEW_MODEL_POLICY:-$(dirname "$0")/kimi-model-policy.json}"
route="$(jq -r '.route // "subscription"' "$policy" 2>/dev/null)" || fail 78 "cannot read kimi-model-policy.json"
if [[ "$route" == api ]]; then gateway_dir="${0:A:h}"; source "$gateway_dir/api-route.sh"; api_route Kimi "$@"; fi
[[ "$route" == subscription ]] || fail 78 "unknown review route: $route"
command -v kimi >/dev/null || fail 69 "Kimi Code CLI not found"; command -v jq >/dev/null || fail 69 "jq is required"; safe "$prompt" prompt; prompt="$REPLY"
policy="${KIMI_REVIEW_MODEL_POLICY:-$(dirname "$0")/kimi-model-policy.json}"
model="$(jq -er --arg tier "$requested_model" '.tiers[$tier].model | select(type == "string" and length > 0)' "$policy" 2>> "$stderr")" || fail 78 "Kimi review tier must be one of: $(jq -r '.tiers | keys | join(", ")' "$policy" 2>/dev/null)"
effort="$(jq -er --arg tier "$requested_model" '.tiers[$tier].reasoning_effort | select(type == "string" and length > 0)' "$policy" 2>> "$stderr")" || fail 78 "Kimi review tier has no reasoning_effort"
# The managed OAuth provider uses the Kimi membership plan. API credentials and
# environment model/endpoint overrides are refused so they cannot bypass it.
[[ -z "${KIMI_API_KEY:-}" && -z "${MOONSHOT_API_KEY:-}" && -z "${KIMI_MODEL_API_KEY:-}" ]] || fail 78 "Kimi API credentials would bypass Kimi Code subscription usage"
[[ -z "${KIMI_MODEL_NAME:-}" && -z "${KIMI_MODEL_PROVIDER_TYPE:-}" && -z "${KIMI_MODEL_BASE_URL:-}" && -z "${KIMI_BASE_URL:-}" && -z "${KIMI_CODE_BASE_URL:-}" && -z "${KIMI_CODE_OAUTH_HOST:-}" && -z "${KIMI_OAUTH_HOST:-}" ]] || fail 78 "Kimi model or endpoint environment overrides are not allowed for subscription reviews"
set +e
kimi provider list --json 2>> "$stderr" | jq -c --arg alias "$model" '
  . as $all | ($all.models[$alias] // null) as $m |
  if $m == null then {found:false} else
    ($all.providers[$m.provider] // {}) as $p |
    {found:true,provider:$m.provider,provider_type:($p.type // null),oauth_configured:((($p.oauth // {}) | type == "object") and (([$p.oauth[]? | strings | select(length > 0)] | length) > 0)),api_key:((($p.api_key // "") | length) > 0),api_key_env:($p | has("api_key_env"))}
  end' > "$tmp/auth.json"
code=$?
set -e
[[ $code -eq 0 ]] || fail 78 "Kimi Code provider status is unavailable"
jq -e '.found and .provider == "managed:kimi-code" and .provider_type == "kimi" and .oauth_configured and (.api_key | not) and (.api_key_env | not)' "$tmp/auth.json" >/dev/null 2>&1 || fail 78 "Kimi selected model is not provisioned by managed Kimi Code OAuth"
kimi_version="$(kimi --version 2>> "$stderr" | head -1)" || fail 69 "Kimi Code version check failed"
{ cat "$prompt"; for f in "$@"; do safe "$f" packet; printf '\n\n===== %s =====\n' "$(basename "$REPLY")"; cat "$REPLY"; done
  print -r -- "

TOOLS: None are available. Review only the text above.
"; cat "$(dirname "$0")/output-contract.txt"; } > "$combined"
max_prompt_bytes="${KIMI_MAX_PROMPT_BYTES:-100000}"
[[ "$max_prompt_bytes" == <-> && "$max_prompt_bytes" -ge 1 ]] || fail 64 "KIMI_MAX_PROMPT_BYTES must be a positive integer"
prompt_bytes="$(wc -c < "$combined" | tr -d ' ')"
[[ "$prompt_bytes" -le "$max_prompt_bytes" ]] || fail 65 "prompt and packet exceed $max_prompt_bytes bytes (kimi takes the prompt as an argument)"
timeout_seconds="${KIMI_MAX_TIME_SECONDS:-900}"
[[ "$timeout_seconds" == <-> && "$timeout_seconds" -ge 1 ]] || fail 64 "KIMI_MAX_TIME_SECONDS must be a positive integer"
budget_tier="$requested_model"
if [[ "$model" == kimi-code/k3* || "$effort" == high ]]; then budget_tier=hard; fi
budget="$(python3 "$(dirname "$0")/review-budget.py" kimi "$budget_tier" "$outdir/$base" 2> "$tmp/budget.err")" || fail 79 "$(<"$tmp/budget.err")"
workspace="$tmp/workspace"; empty_skills="$tmp/empty-skills"; mkdir -m 700 "$workspace" "$empty_skills"
agent="$tmp/reviewer-agent.md"
cat > "$agent" <<'EOF'
---
name: gateway-reviewer
description: Isolated read-only adversarial reviewer with no tools or subagents
tools: []
subagents: []
---
You are an isolated external adversarial reviewer. Use only the supplied prompt and packet. Do not use tools, access files, contact services, or edit state. Your final message must be the complete review and nothing else.
EOF
model_invocation_started=1
set +e
(cd "$workspace" && env -u KIMI_API_KEY -u MOONSHOT_API_KEY -u KIMI_MODEL_API_KEY -u KIMI_MODEL_NAME -u KIMI_MODEL_PROVIDER_TYPE -u KIMI_MODEL_BASE_URL -u KIMI_BASE_URL -u KIMI_CODE_BASE_URL -u KIMI_CODE_OAUTH_HOST -u KIMI_OAUTH_HOST \
  KIMI_MODEL_THINKING_EFFORT="$effort" KIMI_CODE_NO_AUTO_UPDATE=1 KIMI_DISABLE_CRON=1 KIMI_CODE_BACKGROUND_PRINT_BACKGROUND_MODE=exit KIMI_CODE_BACKGROUND_KEEP_ALIVE_ON_EXIT=0 KIMI_LOOP_MAX_STEPS_PER_TURN=1 KIMI_CODE_BUILTIN_PRODUCT_SKILLS=0 KIMI_CODE_WATCH=0 \
  perl -e 'alarm($ENV{KIMI_MAX_TIME_SECONDS} || 900); exec @ARGV' kimi --model "$model" --agent-file "$agent" --skills-dir "$empty_skills" --prompt "$(<"$combined")" --output-format stream-json) > "$stdout" 2>> "$stderr"
code=$?
set -e
[[ $code -ne 142 ]] || fail 70 "Kimi invocation timed out"
[[ $code -eq 0 ]] || fail 70 "Kimi invocation returned nonzero after model invocation began (exit $code)"
[[ -s "$stdout" ]] || fail 70 "Kimi returned no stream output"
jq -e . "$stdout" >/dev/null 2>&1 || fail 70 "Kimi returned invalid stream JSON"
jq -sr '[.[] | select(.role? == "assistant" and (.content? | type == "string") and (.content | length > 0)) | .content] | last // empty' "$stdout" > "$last" || fail 70 "Kimi assistant response extraction failed"
[[ -s "$last" ]] || fail 70 "Kimi returned no assistant review"
tool_events="$(jq -sc '[.[] | select(.role? == "tool" or ((.tool_calls? // []) | length > 0) or .type? == "tool_call" or .type? == "tool_result" or .type? == "tool" or has("tool_call_id") or has("tool_call") or has("function_call") or has("tool_result"))] | length' "$stdout" 2>/dev/null)" || fail 70 "Kimi tool-event validation failed"
[[ "$tool_events" -eq 0 ]] || fail 70 "Kimi response failed isolation validation: tool events were emitted"
python3 "$(dirname "$0")/reviewer-validate.py" < "$last" || fail 70 "Kimi response failed substance validation"
checks="$(python3 "$(dirname "$0")/reviewer-claims.py" < "$last")"
{ print '# Kimi review'; print ''; [[ -n "$owner" ]] && print "Owner: $owner"; [[ $#authors -eq 0 ]] || print "Authors: ${(j:, :)authors}"; [[ $#author_models -eq 0 ]] || print "Author models: ${(j:, :)author_models}"; [[ -z "$task" ]] || print "Task: $task"; print "Wrapper revision: $wrapper_rev"; print "Requested model: $requested_model"; print "Selected model: $model"; print "Reasoning effort: $effort"; print "Resolved model(s): not reported by Kimi Code stream-json"; print "CLI version: $kimi_version"; print "Tool events: $tool_events"; print "Usage: not reported by Kimi Code stream-json"; [[ -z "${REVIEW_BUDGET_OVERRIDE:-}" ]] || print "Budget override: $REVIEW_BUDGET_OVERRIDE"; while IFS= read -r note; do [[ -z "$note" ]] || print "Mechanical check: $note"; done <<< "$checks"; print ''; cat "$last"; } > "$tmp/final.md"
chmod 444 "$tmp/final.md"; mv "$tmp/final.md" "$output"; shasum -a 256 "$output" > "$output.sha256"; chmod 444 "$output" "$output.sha256"; [[ -s "$output" && -s "$output.sha256" ]] || fail 70 "Kimi artifact or checksum was not created"; print "captured $output"
