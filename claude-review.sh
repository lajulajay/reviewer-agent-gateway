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
[[ $# -ge 4 ]] || { print -u2 "usage: $0 [--packet-root DIR] [--owner codex|claude] <model> <prompt-file> <new-output.md> <packet-file>..."; exit 64; }
[[ "$owner" != claude ]] || { print -u2 "Claude cannot review work it owns; use codex-review.sh"; exit 64; }
requested_model="$1"; prompt="$2"; output="$3"; shift 3
outdir="$(cd "$(dirname "$output")" && pwd -P)"; base="$(basename "$output")"; root="$(cd "$outdir/.." && pwd -P)"
[[ "$outdir" == "$root/.collab" && "$base" == *.md && ! -e "$output" ]] || { print -u2 "invalid or existing output"; exit 65; }
tmp="$(mktemp -d "${TMPDIR:-/tmp}/reviewers-claude.XXXXXX")"; trap 'rm -rf "$tmp"' EXIT INT TERM
stdout="$tmp/stdout.json"; stderr="$tmp/stderr"; combined="$tmp/prompt.txt"; debug="$tmp/debug.log"; diagnostic="$outdir/${base%.md}.diagnostic.json"; start=$SECONDS
: > "$stdout"; : > "$stderr"; : > "$debug"
fail() { local code="$1" reason="$2"; if [[ ! -s "$diagnostic" ]]; then jq -n --arg owner "$owner" --arg requested "$requested_model" --arg selected "${model:-}" --arg reason "$reason" --arg code "$code" --arg elapsed "$((SECONDS-start))" --rawfile stdout "$stdout" --rawfile stderr "$stderr" '{provider:"claude",owner:$owner,requested_model:$requested,selected_model:$selected,reason:$reason,exit_code:($code|tonumber),elapsed_seconds:($elapsed|tonumber),stdout:$stdout,stderr:$stderr}' > "$tmp/diagnostic.json" && chmod 444 "$tmp/diagnostic.json" && mv -f "$tmp/diagnostic.json" "$diagnostic"; fi; print -u2 "$reason; diagnostics captured at $diagnostic"; exit "$code"; }
safe() { local f="$1" label="$2"; [[ -f "$f" && ! -L "$f" ]] || fail 66 "$label is not a regular file"; f="$(cd "$(dirname "$f")" && pwd -P)/$(basename "$f")"; if [[ -n "$packet_root" ]]; then local pr="$(cd "$packet_root" 2>/dev/null && pwd -P)" || fail 77 "invalid packet root"; case "$f" in "$root"/*|"$pr"/*) ;; *) fail 77 "$label is outside allowed roots";; esac; else case "$f" in "$root"/*) ;; *) fail 77 "$label must be inside repo or use --packet-root";; esac; fi; case "$f" in */.env|*/.env.*|*/.reviewers.env|*/data/*|*/exports/*|*/artifacts/private/*|*.pem|*.key) fail 77 "refusing private $label";; esac; REPLY="$f"; }
# Provenance (workspace framework v6 §7): record the gateway commit this wrapper
# ran from; refuse to run with uncommitted wrapper changes or a Git error. A
# copy outside any repository (consumer-shim fixtures) records "unversioned",
# which docs-check rejects for reviews captured after adoption.
wrapper_rev="unversioned"
if git -C "$(dirname "$0")" rev-parse --git-dir >/dev/null 2>&1; then
  wrapper_rev="$(git -C "$(dirname "$0")" rev-parse HEAD 2>/dev/null)" || fail 78 "cannot read the gateway revision"
  wrapper_dirty="$(git -C "$(dirname "$0")" status --porcelain -- '*.sh' '*.py' '*.json' output-contract.txt 2>/dev/null)" || fail 78 "cannot read gateway status"
  [[ -z "$wrapper_dirty" ]] || fail 78 "gateway wrapper files have uncommitted changes"
fi
command -v claude >/dev/null || fail 69 "claude CLI not found"; command -v jq >/dev/null || fail 69 "jq is required"; safe "$prompt" prompt; prompt="$REPLY"
policy="${CLAUDE_REVIEW_MODEL_POLICY:-$(dirname "$0")/claude-model-policy.json}"
policy_active=false
if [[ -f "$policy" || -n "${CLAUDE_REVIEW_MODEL_POLICY:-}" ]]; then
  policy_active=true
  [[ -z "${ANTHROPIC_API_KEY:-}" ]] || fail 78 "ANTHROPIC_API_KEY would bypass included Claude Code usage"
  claude auth status --json > "$tmp/auth.json" 2>> "$stderr" || fail 78 "Claude Code authentication status is unavailable"
  jq -e '.loggedIn == true and .authMethod == "claude.ai"' "$tmp/auth.json" >/dev/null 2>&1 || fail 78 "Claude Code is not using claude.ai subscription authentication"
  model="$(python3 "$(dirname "$0")/claude-model-select.py" "$policy" "$requested_model" 2> "$stderr")" || fail 78 "Claude model selection failed"
else
  model="$requested_model"
fi
{ cat "$prompt"; for f in "$@"; do safe "$f" packet; print -r -- "\n\n===== $(basename "$REPLY") ====="; cat "$REPLY"; done; } > "$combined"
# Review budget (review-budget.json): round caps per topic, one hard-tier
# round per topic, a daily cap per repository, and a lower effort for
# follow-up rounds, which only check the owner's responses.
tier=routine
[[ "$requested_model" == opus || ( "$policy_active" == true && "$model" == "$(jq -r '.hard_model // empty' "$policy")" ) ]] && tier=hard
prior_rounds="$(python3 "$(dirname "$0")/review-budget.py" claude "$tier" "$outdir/$base" 2> "$tmp/budget.err")" || fail 79 "$(<"$tmp/budget.err")"
effort_round=first_round; [[ "$prior_rounds" -eq 0 ]] || effort_round=follow_up
effort="$(jq -er --arg r "$effort_round" '.claude_effort[$r]' "$(dirname "$0")/review-budget.json")" || fail 78 "review-budget.json has no claude_effort.$effort_round"
set +e
perl -e 'alarm($ENV{CLAUDE_MAX_TIME_SECONDS} || 600); exec @ARGV' claude -p --safe-mode --model "$model" --effort "$effort" --tools= --system-prompt "You are an isolated external adversarial reviewer. Use only the supplied packet. Do not use tools or edit state. $(<"$(dirname "$0")/output-contract.txt")" --no-session-persistence --output-format json --debug-file "$debug" < "$combined" > "$stdout" 2> "$stderr"
code=$?; set -e
[[ $code -ne 142 ]] || fail 70 "Claude invocation timed out"
[[ $code -eq 0 ]] || fail 70 "Claude invocation failed"
jq -e '.is_error == false and (.result | type == "string")' "$stdout" >/dev/null 2>&1 || fail 70 "Claude returned invalid JSON"
jq -r '.result' "$stdout" | python3 "$(dirname "$0")/reviewer-validate.py" || fail 70 "Claude response failed substance validation"
resolved="$(jq -r '[(.modelUsage // {} | keys[]?), .model?] | map(select(. != null and . != "")) | unique | join(", ")' "$stdout")"
if [[ "$policy_active" == true ]]; then
  jq -e --arg model "$model" '(.modelUsage // {} | has($model)) or .model == $model' "$stdout" >/dev/null 2>&1 || fail 74 "Claude resolved outside selected model"
fi
usage="$(jq -c '{usage: (.usage // null | if . then {input_tokens, output_tokens, cache_read_input_tokens, cache_creation_input_tokens} else null end), total_cost_usd, duration_ms, num_turns}' "$stdout")"
checks="$(jq -r '.result' "$stdout" | python3 "$(dirname "$0")/reviewer-claims.py")"
{ print '# Claude review'; print ''; [[ -n "$owner" ]] && print "Owner: $owner"; print "Wrapper revision: $wrapper_rev"; print "Requested model: $requested_model"; [[ "$policy_active" == true ]] && print "Selected model: $model"; print "Resolved model(s): $resolved"; print "Effort: $effort"; print "Usage: $usage"; [[ -z "${REVIEW_BUDGET_OVERRIDE:-}" ]] || print "Budget override: $REVIEW_BUDGET_OVERRIDE"; while IFS= read -r note; do [[ -z "$note" ]] || print "Mechanical check: $note"; done <<< "$checks"; print ''; jq -r '.result' "$stdout"; } > "$output"
chmod 444 "$output"; shasum -a 256 "$output" > "$output.sha256"; chmod 444 "$output.sha256"; [[ -s "$output" && -s "$output.sha256" ]] || fail 70 "Claude artifact or checksum was not created"; print "captured $output"
