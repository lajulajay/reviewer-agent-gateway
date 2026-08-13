#!/bin/zsh
set -euo pipefail
umask 077
packet_root=""
if [[ "${1:-}" == "--packet-root" ]]; then [[ $# -ge 2 ]] || exit 64; packet_root="$2"; shift 2; fi
[[ $# -ge 4 ]] || { print -u2 "usage: $0 [--packet-root DIR] <model> <prompt-file> <new-output.json> <packet-file>..."; exit 64; }
model="$1"; prompt="$2"; output="$3"; shift 3
outdir="$(cd "$(dirname "$output")" && pwd -P)"; base="$(basename "$output")"; root="$(cd "$outdir/.." && pwd -P)"
[[ "$outdir" == "$root/.collab" && "$base" == *.json && ! -e "$output" ]] || { print -u2 "invalid or existing output"; exit 65; }
tmp="$(mktemp -d "${TMPDIR:-/tmp}/reviewers-gemini.XXXXXX")"; trap 'unset GEMINI_API_KEY; rm -rf "$tmp"' EXIT INT TERM
response="$tmp/response.json"; stderr="$tmp/stderr"; stdout="$tmp/stdout"; diagnostic="$outdir/${base%.json}.diagnostic.json"; start=$SECONDS
: > "$response"; : > "$stderr"; : > "$stdout"
fail() { local code="$1" reason="$2"; if [[ ! -s "$diagnostic" ]]; then jq -n --arg model "$model" --arg reason "$reason" --arg code "$code" --arg elapsed "$((SECONDS-start))" --rawfile stdout "$stdout" --rawfile stderr "$stderr" '{provider:"gemini",requested_model:$model,reason:$reason,exit_code:($code|tonumber),elapsed_seconds:($elapsed|tonumber),stdout:$stdout,stderr:$stderr}' > "$tmp/diagnostic.json" && chmod 444 "$tmp/diagnostic.json" && mv -f "$tmp/diagnostic.json" "$diagnostic"; fi; print -u2 "$reason; diagnostics captured at $diagnostic"; exit "$code"; }
safe() { local f="$1" label="$2"; [[ -f "$f" && ! -L "$f" ]] || fail 66 "$label is not a regular file"; f="$(cd "$(dirname "$f")" && pwd -P)/$(basename "$f")"; if [[ -n "$packet_root" ]]; then local pr="$(cd "$packet_root" 2>/dev/null && pwd -P)"; case "$f" in "$root"/*|"$pr"/*) ;; *) fail 77 "$label is outside allowed roots";; esac; else case "$f" in "$root"/*) ;; *) fail 77 "$label must be inside repo or use --packet-root";; esac; fi; case "$f" in */.env|*/.env.*|*/.reviewers.env|*/data/*|*/exports/*|*/artifacts/private/*|*.pem|*.key) fail 77 "refusing private $label";; esac; REPLY="$f"; }
command -v gemini >/dev/null || fail 69 "gemini CLI not found"; command -v jq >/dev/null || fail 69 "jq is required"; safe "$prompt" prompt; prompt="$REPLY"
if [[ -n "${GEMINI_MODEL_LIST:-}" ]]; then print -r -- "$GEMINI_MODEL_LIST" | tr ',' '\n' | grep -Fxq -- "$model" || fail 74 "requested Gemini model is not in preflight model list"; fi
if [[ -n "${GEMINI_API_KEY:-}" ]]; then :; elif [[ -n "${REVIEWER_CREDENTIALS_FILE:-}" && -f "$REVIEWER_CREDENTIALS_FILE" ]]; then credentials="$REVIEWER_CREDENTIALS_FILE"; elif [[ -f "$root/.reviewers.env" ]]; then credentials="$root/.reviewers.env"; elif [[ -f "$root/.env" ]]; then credentials="$root/.env"; elif [[ -f "$root/agent/.env" ]]; then credentials="$root/agent/.env"; else fail 78 "Gemini credentials file not found"; fi
if [[ -z "${GEMINI_API_KEY:-}" ]]; then [[ "$(stat -f '%Lp' "$credentials")" == 600 ]] || fail 77 "credentials file must have mode 600"; GEMINI_API_KEY="$(awk -F= '/^GEMINI_API_KEY=/{sub(/^[^=]*=/,""); print; exit}' "$credentials")"; fi
[[ -n "${GEMINI_API_KEY:-}" ]] || fail 78 "GEMINI_API_KEY is not set"
packet="$tmp/packet"; mkdir -m 700 "$packet"; i=0
for f in "$@"; do safe "$f" packet; i=$((i+1)); cp -p "$REPLY" "$packet/$(printf '%02d' "$i")-$(basename "$REPLY")"; done
prompt_text="$(<"$prompt")

OUTPUT CONTRACT: Return a substantive review, not procedural narration. Your
final non-empty line must be exactly one of: VERDICT: ACCEPT; VERDICT: ACCEPT
WITH CONDITIONS; VERDICT: REJECT. Do not use any other verdict label or mention
another verdict line."
set +e
(cd "$packet" && GEMINI_API_KEY="$GEMINI_API_KEY" SEATBELT_PROFILE=strict-open gemini --sandbox --skip-trust --approval-mode plan --extensions none --model "$model" --output-format json --prompt "$prompt_text") > "$response" 2> "$stderr"
code=$?; set -e
[[ $code -eq 0 && -s "$response" ]] || fail 70 "Gemini invocation failed or returned empty output"
resolved="$(jq -r '.stats.models // {} | keys[]?' "$response" 2>/dev/null | paste -sd, -)"; [[ -n "$resolved" ]] || fail 74 "Gemini returned no resolved model metadata"
case "$model" in *flash*|*Flash*) print -r -- "$resolved" | grep -Eiq 'flash' || fail 74 "Gemini resolved outside Flash family";; *pro*|*Pro*) print -r -- "$resolved" | grep -Eiq 'pro' || fail 74 "Gemini resolved outside Pro family";; esac
text="$(jq -r '.response // .result // .text // empty' "$response")"; print -r -- "$text" | python3 "$(dirname "$0")/reviewer-validate.py" || fail 70 "Gemini response failed substance validation"
jq --arg requested "$model" --arg resolved "$resolved" '. + {reviewer_metadata:{requested_model:$requested,resolved_models:($resolved|split(","))}}' "$response" > "$tmp/final.json" || fail 70 "Gemini response was not valid JSON"
chmod 444 "$tmp/final.json"; mv "$tmp/final.json" "$output"; shasum -a 256 "$output" > "$output.sha256"; chmod 444 "$output" "$output.sha256"; [[ -s "$output" && -s "$output.sha256" ]] || fail 70 "Gemini artifact or checksum was not created"; print "captured $output"
