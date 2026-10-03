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
[[ $# -ge 4 ]] || { print -u2 "usage: $0 [--packet-root DIR] [--owner codex|claude] <hard|routine> <prompt-file> <new-output.md> <packet-file>..."; exit 64; }
[[ "$owner" != codex ]] || { print -u2 "Codex cannot review work it owns; use claude-review.sh"; exit 64; }
requested_model="$1"; prompt="$2"; output="$3"; shift 3
outdir="$(cd "$(dirname "$output")" && pwd -P)"; base="$(basename "$output")"; root="$(cd "$outdir/.." && pwd -P)"
[[ "$outdir" == "$root/.collab" && "$base" == *.md && ! -e "$output" ]] || { print -u2 "invalid or existing output"; exit 65; }
tmp="$(mktemp -d "${TMPDIR:-/tmp}/reviewers-codex.XXXXXX")"; trap 'rm -rf "$tmp"' EXIT INT TERM
stdout="$tmp/events.jsonl"; stderr="$tmp/stderr"; combined="$tmp/prompt.txt"; last="$tmp/last.md"; diagnostic="$outdir/${base%.md}.diagnostic.json"; start=$SECONDS
: > "$stdout"; : > "$stderr"
fail() { local code="$1" reason="$2"; if [[ ! -s "$diagnostic" ]]; then jq -n --arg owner "$owner" --arg requested "$requested_model" --arg selected "${model:-}" --arg reason "$reason" --arg code "$code" --arg elapsed "$((SECONDS-start))" --rawfile stdout "$stdout" --rawfile stderr "$stderr" '{provider:"codex",owner:$owner,requested_model:$requested,selected_model:$selected,reason:$reason,exit_code:($code|tonumber),elapsed_seconds:($elapsed|tonumber),stdout:$stdout,stderr:$stderr}' > "$tmp/diagnostic.json" && chmod 444 "$tmp/diagnostic.json" && mv -f "$tmp/diagnostic.json" "$diagnostic"; fi; print -u2 "$reason; diagnostics captured at $diagnostic"; exit "$code"; }
safe() { local f="$1" label="$2"; [[ -f "$f" && ! -L "$f" ]] || fail 66 "$label is not a regular file"; f="$(cd "$(dirname "$f")" && pwd -P)/$(basename "$f")"; if [[ -n "$packet_root" ]]; then local pr="$(cd "$packet_root" 2>/dev/null && pwd -P)" || fail 77 "invalid packet root"; case "$f" in "$root"/*|"$pr"/*) ;; *) fail 77 "$label is outside allowed roots";; esac; else case "$f" in "$root"/*) ;; *) fail 77 "$label must be inside repo or use --packet-root";; esac; fi; case "$f" in */.env|*/.env.*|*/.reviewers.env|*/data/*|*/exports/*|*/artifacts/private/*|*.pem|*.key) fail 77 "refusing private $label";; esac; REPLY="$f"; }
# Provenance (workspace framework v6 §7): record the gateway commit this wrapper
# ran from and refuse uncommitted wrapper changes. REVIEWER_ALLOW_DIRTY_WRAPPER
# is for the provider-free tests only; it is recorded as "(dirty)".
wrapper_rev="$(git -C "$(dirname "$0")" rev-parse HEAD 2>/dev/null || print unversioned)"
if [[ "$wrapper_rev" != unversioned && -n "$(git -C "$(dirname "$0")" status --porcelain -- '*.sh' '*.py' '*.json' output-contract.txt 2>/dev/null)" ]]; then [[ -n "${REVIEWER_ALLOW_DIRTY_WRAPPER:-}" ]] || fail 78 "gateway wrapper files have uncommitted changes"; wrapper_rev+=" (dirty)"; fi
command -v codex >/dev/null || fail 69 "codex CLI not found"; command -v jq >/dev/null || fail 69 "jq is required"; safe "$prompt" prompt; prompt="$REPLY"
# Reviews run on the ChatGPT plan. An API key would switch Codex to billed
# API usage, so its presence is refused and the login method is checked.
[[ -z "${OPENAI_API_KEY:-}" && -z "${CODEX_API_KEY:-}" ]] || fail 78 "OPENAI_API_KEY/CODEX_API_KEY would bypass ChatGPT plan usage"
codex login status > "$tmp/login.txt" 2>&1 || fail 78 "Codex login status is unavailable"
grep -q 'Logged in using ChatGPT' "$tmp/login.txt" || fail 78 "Codex is not using ChatGPT plan authentication"
policy="${CODEX_REVIEW_MODEL_POLICY:-$(dirname "$0")/codex-model-policy.json}"
model="$(jq -er --arg tier "$requested_model" '.tiers[$tier].model | select(type == "string" and length > 0)' "$policy" 2>> "$stderr")" || fail 78 "Codex review tier must be one of: $(jq -r '.tiers | keys | join(", ")' "$policy" 2>/dev/null)"
effort="$(jq -er --arg tier "$requested_model" '.tiers[$tier].reasoning_effort | select(type == "string" and length > 0)' "$policy" 2>> "$stderr")" || fail 78 "Codex review tier has no reasoning_effort"
codex_version="$(codex --version 2>> "$stderr" | head -1)"
{ cat "$prompt"; for f in "$@"; do safe "$f" packet; print -r -- "\n\n===== $(basename "$REPLY") ====="; cat "$REPLY"; done
  print -r -- "

TOOLS: None are available. Review only the text above.
"; cat "$(dirname "$0")/output-contract.txt"; } > "$combined"
# Isolation: user config (danger-full-access sandbox, plugins, MCP) and
# execpolicy rules are not loaded, nothing is persisted, the sandbox is
# read-only, and the features that expose tools are disabled. Verified with
# codex-cli 0.159.3 on 2026-10-02: shell, file reads, apply_patch (listed, but
# it runs through the disabled code-mode host), apps/connectors, web, and image
# tools fail. Subagent spawn also fails, but only because --ephemeral leaves no
# rollout to fork.
disabled=(apps plugins remote_plugin plugin_sharing multi_agent multi_agent_v2 collaboration_modes code_mode_host shell_tool unified_exec shell_snapshot image_generation browser_use browser_use_external computer_use in_app_browser goals skill_search skill_mcp_dependency_install tool_suggest view_image sleep_tool workspace_dependencies hooks)
disable_flags=(); for f in $disabled; do disable_flags+=(--disable "$f"); done
workspace="$tmp/workspace"; mkdir -m 700 "$workspace"
set +e
env -u OPENAI_API_KEY -u CODEX_API_KEY perl -e 'alarm($ENV{CODEX_MAX_TIME_SECONDS} || 600); exec @ARGV' codex exec --ephemeral --ignore-user-config --ignore-rules --skip-git-repo-check -s read-only -C "$workspace" -m "$model" -c "model_reasoning_effort=\"$effort\"" -c 'web_search="disabled"' "${disable_flags[@]}" --json -o "$last" - < "$combined" > "$stdout" 2>> "$stderr"
code=$?; set -e
[[ $code -ne 142 ]] || fail 70 "Codex invocation timed out"
[[ $code -eq 0 ]] || fail 70 "Codex invocation failed (exit $code)"
jq -e 'select(.type == "turn.completed")' "$stdout" >/dev/null 2>&1 || fail 70 "Codex did not complete its turn"
[[ -s "$last" ]] || fail 70 "Codex returned no final message"
python3 "$(dirname "$0")/reviewer-validate.py" < "$last" || fail 70 "Codex response failed substance validation"
# Startup notices (e.g. "code-mode host is disabled") are also error items;
# only errors after the turn starts are tool attempts.
blocked="$(jq -s '[foreach .[] as $e (false; . or ($e.type == "turn.started"); if . and $e.type == "item.completed" and $e.item.type == "error" then 1 else empty end)] | length' "$stdout" 2>/dev/null || print 0)"
# codex exec does not report the serving model; the artifact records the
# pinned request.
{ print '# Codex review'; print ''; [[ -n "$owner" ]] && print "Owner: $owner"; print "Wrapper revision: $wrapper_rev"; print "Requested model: $requested_model"; print "Selected model: $model"; print "Reasoning effort: $effort"; print "Resolved model(s): not reported by codex exec"; print "CLI version: $codex_version"; print "Blocked tool attempts: $blocked"; print ''; cat "$last"; } > "$tmp/final.md"
chmod 444 "$tmp/final.md"; mv "$tmp/final.md" "$output"; shasum -a 256 "$output" > "$output.sha256"; chmod 444 "$output.sha256"; [[ -s "$output" && -s "$output.sha256" ]] || fail 70 "Codex artifact or checksum was not created"; print "captured $output"
