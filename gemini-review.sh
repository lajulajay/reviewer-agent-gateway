#!/bin/zsh
set -euo pipefail
umask 077
packet_root=""
if [[ "${1:-}" == "--packet-root" ]]; then [[ $# -ge 2 ]] || exit 64; packet_root="$2"; shift 2; fi
[[ $# -ge 4 ]] || { print -u2 "usage: $0 [--packet-root DIR] <model> <prompt-file> <new-output.json> <packet-file>..."; exit 64; }
requested_model="$1"; model="$requested_model"; prompt="$2"; output="$3"; shift 3
outdir="$(cd "$(dirname "$output")" && pwd -P)"; base="$(basename "$output")"; root="$(cd "$outdir/.." && pwd -P)"
[[ "$outdir" == "$root/.collab" && "$base" == *.json && ! -e "$output" ]] || { print -u2 "invalid or existing output"; exit 65; }
tmp="$(mktemp -d "${TMPDIR:-/tmp}/reviewers-gemini.XXXXXX")"; trap 'unset GEMINI_API_KEY; rm -rf "$tmp"' EXIT INT TERM
response="$tmp/response.json"; stderr="$tmp/stderr"; stdout="$tmp/stdout"; diagnostic="$outdir/${base%.json}.diagnostic.json"; start=$SECONDS
: > "$response"; : > "$stderr"; : > "$stdout"
fail() { local code="$1" reason="$2"; if [[ ! -s "$diagnostic" ]]; then jq -n --arg requested "$requested_model" --arg selected "${selected_model:-}" --arg reason "$reason" --arg code "$code" --arg elapsed "$((SECONDS-start))" --rawfile stdout "$stdout" --rawfile stderr "$stderr" '{provider:"gemini",requested_model:$requested,preflight_selected_model:$selected,reason:$reason,exit_code:($code|tonumber),elapsed_seconds:($elapsed|tonumber),stdout:$stdout,stderr:$stderr}' > "$tmp/diagnostic.json" && chmod 444 "$tmp/diagnostic.json" && mv -f "$tmp/diagnostic.json" "$diagnostic"; fi; print -u2 "$reason; diagnostics captured at $diagnostic"; exit "$code"; }
safe() { local f="$1" label="$2"; [[ -f "$f" && ! -L "$f" ]] || fail 66 "$label is not a regular file"; f="$(cd "$(dirname "$f")" && pwd -P)/$(basename "$f")"; if [[ -n "$packet_root" ]]; then local pr="$(cd "$packet_root" 2>/dev/null && pwd -P)"; case "$f" in "$root"/*|"$pr"/*) ;; *) fail 77 "$label is outside allowed roots";; esac; else case "$f" in "$root"/*) ;; *) fail 77 "$label must be inside repo or use --packet-root";; esac; fi; case "$f" in */.env|*/.env.*|*/.reviewers.env|*/data/*|*/exports/*|*/artifacts/private/*|*.pem|*.key) fail 77 "refusing private $label";; esac; REPLY="$f"; }
command -v gemini >/dev/null || fail 69 "gemini CLI not found"; command -v jq >/dev/null || fail 69 "jq is required"; safe "$prompt" prompt; prompt="$REPLY"
# Google retired Gemini CLI personal-account OAuth ("Code Assist for
# individuals") on 2026-10-02, so reviews authenticate with an API key again.
# Spend is bounded only by the key's Google Cloud project budget cap.
if [[ -n "${GEMINI_API_KEY:-}" ]]; then :; elif [[ -n "${REVIEWER_CREDENTIALS_FILE:-}" && -f "$REVIEWER_CREDENTIALS_FILE" ]]; then credentials="$REVIEWER_CREDENTIALS_FILE"; elif [[ -f "$root/.reviewers.env" ]]; then credentials="$root/.reviewers.env"; elif [[ -f "$root/.env" ]]; then credentials="$root/.env"; elif [[ -f "$root/agent/.env" ]]; then credentials="$root/agent/.env"; else fail 78 "Gemini credentials file not found"; fi
if [[ -z "${GEMINI_API_KEY:-}" ]]; then [[ "$(stat -f '%Lp' "$credentials")" == 600 ]] || fail 77 "credentials file must have mode 600"; GEMINI_API_KEY="$(awk -F= '/^GEMINI_API_KEY=/{sub(/^[^=]*=/,""); print; exit}' "$credentials")"; fi
[[ -n "${GEMINI_API_KEY:-}" ]] || fail 78 "GEMINI_API_KEY is not set"
policy="${GEMINI_REVIEW_MODEL_POLICY:-$(dirname "$0")/gemini-model-policy.json}"
selected_model="$(python3 "$(dirname "$0")/gemini-model-select.py" "$policy" "$requested_model" 2> "$stderr")" || fail 78 "Gemini model selection failed"
model="$selected_model"
# System overrides outrank user and project settings. Force API-key auth so
# the CLI cannot drift to another credential or billing path. Gemini
# CLI silently skips a system settings file unless it and its parent directory
# are root-owned, so the enforced file is provisioned once with sudo; a
# per-invocation temp file would be ignored.
system_settings="${GEMINI_REVIEW_SYSTEM_SETTINGS:-/etc/reviewer-gateway/gemini-settings.json}"
[[ -f "$system_settings" && ! -L "$system_settings" ]] || fail 78 "enforced Gemini system settings file is missing: $system_settings"
if [[ -z "${GEMINI_REVIEW_SYSTEM_SETTINGS:-}" ]]; then
  [[ "$(stat -f '%u' "$system_settings")" == 0 && "$(stat -f '%u' "$(dirname "$system_settings")")" == 0 ]] || fail 78 "enforced Gemini system settings file and directory must be root-owned"
  (( (8#$(stat -f '%Lp' "$system_settings") & 8#022) == 0 )) || fail 78 "enforced Gemini system settings file must not be group/other writable"
fi
jq -e '.security.auth.selectedType == "gemini-api-key" and .security.auth.enforcedType == "gemini-api-key"' "$system_settings" >/dev/null 2>&1 || fail 78 "enforced Gemini system settings do not require API-key auth"
packet="$tmp/packet"; mkdir -m 700 "$packet"; i=0
for f in "$@"; do safe "$f" packet; i=$((i+1)); cp -p "$REPLY" "$packet/$(printf '%02d' "$i")-$(basename "$REPLY")"; done
prompt_text="$(<"$prompt")

OUTPUT CONTRACT: Return a substantive review, not procedural narration. Your
final non-empty line must be exactly one of: VERDICT: ACCEPT; VERDICT: ACCEPT
WITH CONDITIONS; VERDICT: REJECT. Do not use any other verdict label or mention
another verdict line."
set +e
(cd "$packet" && env -u GOOGLE_API_KEY -u GOOGLE_GENAI_USE_VERTEXAI -u GOOGLE_GENAI_USE_GCA GEMINI_API_KEY="$GEMINI_API_KEY" GEMINI_CLI_SYSTEM_SETTINGS_PATH="$system_settings" SEATBELT_PROFILE=strict-open perl -e 'alarm($ENV{GEMINI_MAX_TIME_SECONDS} || 600); exec @ARGV' gemini --sandbox --skip-trust --approval-mode plan --extensions none --model "$model" --output-format json --prompt "$prompt_text") > "$response" 2> "$stderr"
code=$?; set -e
# Defense in depth: if the CLI reports skipping the enforced settings, the
# auth guarantee did not apply to this call.
grep -Eiq 'Skipping system settings|Security Warning' "$stderr" && fail 78 "Gemini CLI ignored the enforced system settings"
[[ $code -ne 142 ]] || fail 70 "Gemini invocation timed out"
[[ $code -eq 0 && -s "$response" ]] || fail 70 "Gemini invocation failed or returned empty output"
resolved="$(jq -r '.stats.models // {} | keys[]?' "$response" 2>/dev/null | paste -sd, -)"; [[ -n "$resolved" ]] || fail 74 "Gemini returned no resolved model metadata"
jq -e --arg model "$model" '(.stats.models // {} | keys) == [$model]' "$response" >/dev/null 2>&1 || fail 74 "Gemini resolved outside selected model"
text="$(jq -r '.response // .result // .text // empty' "$response")"; print -r -- "$text" | python3 "$(dirname "$0")/reviewer-validate.py" || fail 70 "Gemini response failed substance validation"
jq --arg requested "$requested_model" --arg selected "$selected_model" --arg resolved "$resolved" '. + {reviewer_metadata:{requested_model:$requested,preflight_selected_model:$selected,resolved_models:($resolved|split(","))}}' "$response" > "$tmp/final.json" || fail 70 "Gemini response was not valid JSON"
chmod 444 "$tmp/final.json"; mv "$tmp/final.json" "$output"; shasum -a 256 "$output" > "$output.sha256"; chmod 444 "$output" "$output.sha256"; [[ -s "$output" && -s "$output.sha256" ]] || fail 70 "Gemini artifact or checksum was not created"; print "captured $output"
