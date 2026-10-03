#!/bin/zsh
set -euo pipefail
umask 077

packet_root=""
if [[ "${1:-}" == "--packet-root" ]]; then [[ $# -ge 2 ]] || exit 64; packet_root="$2"; shift 2; fi
[[ $# -ge 4 ]] || { print -u2 "usage: $0 [--packet-root DIR] <model> <prompt-file> <new-output.md> <packet-file>..."; exit 64; }
requested_model="$1"; prompt="$2"; output="$3"; shift 3
outdir="$(cd "$(dirname "$output")" && pwd -P)"; base="$(basename "$output")"; root="$(cd "$outdir/.." && pwd -P)"
[[ "$outdir" == "$root/.collab" && "$base" == *.md && ! -e "$output" ]] || { print -u2 "invalid or existing output"; exit 65; }
tmp="$(mktemp -d "${TMPDIR:-/tmp}/reviewers-claude.XXXXXX")"; trap 'rm -rf "$tmp"' EXIT INT TERM
stdout="$tmp/stdout.json"; stderr="$tmp/stderr"; combined="$tmp/prompt.txt"; debug="$tmp/debug.log"; diagnostic="$outdir/${base%.md}.diagnostic.json"; start=$SECONDS
: > "$stdout"; : > "$stderr"; : > "$debug"
fail() { local code="$1" reason="$2"; if [[ ! -s "$diagnostic" ]]; then jq -n --arg requested "$requested_model" --arg selected "${model:-}" --arg reason "$reason" --arg code "$code" --arg elapsed "$((SECONDS-start))" --rawfile stdout "$stdout" --rawfile stderr "$stderr" '{provider:"claude",requested_model:$requested,selected_model:$selected,reason:$reason,exit_code:($code|tonumber),elapsed_seconds:($elapsed|tonumber),stdout:$stdout,stderr:$stderr}' > "$tmp/diagnostic.json" && chmod 444 "$tmp/diagnostic.json" && mv -f "$tmp/diagnostic.json" "$diagnostic"; fi; print -u2 "$reason; diagnostics captured at $diagnostic"; exit "$code"; }
safe() { local f="$1" label="$2"; [[ -f "$f" && ! -L "$f" ]] || fail 66 "$label is not a regular file"; f="$(cd "$(dirname "$f")" && pwd -P)/$(basename "$f")"; if [[ -n "$packet_root" ]]; then local pr="$(cd "$packet_root" 2>/dev/null && pwd -P)" || fail 77 "invalid packet root"; case "$f" in "$root"/*|"$pr"/*) ;; *) fail 77 "$label is outside allowed roots";; esac; else case "$f" in "$root"/*) ;; *) fail 77 "$label must be inside repo or use --packet-root";; esac; fi; case "$f" in */.env|*/.env.*|*/.reviewers.env|*/data/*|*/exports/*|*/artifacts/private/*|*.pem|*.key) fail 77 "refusing private $label";; esac; REPLY="$f"; }
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
set +e
perl -e 'alarm($ENV{CLAUDE_MAX_TIME_SECONDS} || 600); exec @ARGV' claude -p --safe-mode --model "$model" --tools= --system-prompt 'You are an isolated external adversarial reviewer. Use only the supplied packet. Do not use tools or edit state. Return substantive review text. Its final non-empty line must be exactly one of: VERDICT: ACCEPT; VERDICT: ACCEPT WITH CONDITIONS; VERDICT: REJECT. Do not use any other verdict label or mention another verdict line.' --no-session-persistence --output-format json --debug-file "$debug" < "$combined" > "$stdout" 2> "$stderr"
code=$?; set -e
[[ $code -eq 0 ]] || fail 70 "Claude invocation failed"
jq -e '.is_error == false and (.result | type == "string")' "$stdout" >/dev/null 2>&1 || fail 70 "Claude returned invalid JSON"
jq -r '.result' "$stdout" | python3 "$(dirname "$0")/reviewer-validate.py" || fail 70 "Claude response failed substance validation"
resolved="$(jq -r '[(.modelUsage // {} | keys[]?), .model?] | map(select(. != null and . != "")) | unique | join(", ")' "$stdout")"
if [[ "$policy_active" == true ]]; then
  jq -e --arg model "$model" '(.modelUsage // {} | has($model)) or .model == $model' "$stdout" >/dev/null 2>&1 || fail 74 "Claude resolved outside selected model"
fi
{ print '# Claude review'; print ''; print "Requested model: $requested_model"; [[ "$policy_active" == true ]] && print "Selected model: $model"; print "Resolved model(s): $resolved"; print ''; jq -r '.result' "$stdout"; } > "$output"
chmod 444 "$output"; shasum -a 256 "$output" > "$output.sha256"; chmod 444 "$output.sha256"; [[ -s "$output" && -s "$output.sha256" ]] || fail 70 "Claude artifact or checksum was not created"; print "captured $output"
