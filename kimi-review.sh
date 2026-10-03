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
[[ $# -ge 4 ]] || { print -u2 "usage: $0 [--packet-root DIR] [--owner codex|claude] <ollama-model> <prompt-file> <new-output.md> <packet-file>..."; exit 64; }
model="$1"; prompt="$2"; output="$3"; shift 3
case "$model" in
  kimi-k2.6:cloud|kimi-k3:cloud) ;;
  *) print -u2 "unsupported Kimi Ollama model: $model"; exit 64 ;;
esac

outdir="$(cd "$(dirname "$output")" && pwd -P)"; base="$(basename "$output")"; root="$(cd "$outdir/.." && pwd -P)"
[[ "$outdir" == "$root/.collab" && "$base" == *.md && ! -e "$output" ]] || { print -u2 "invalid or existing output"; exit 65; }
tmp="$(mktemp -d "${TMPDIR:-/tmp}/reviewers-kimi.XXXXXX")"
stdout="$tmp/stdout"; stderr="$tmp/stderr"; combined="$tmp/prompt.txt"; available="$tmp/available-models"; diagnostic="$outdir/${base%.md}.diagnostic.json"; start=$SECONDS
: > "$stdout"; : > "$stderr"; : > "$available"

cleanup() { rm -rf "$tmp"; }
publish_diagnostic() {
  [[ -s "$diagnostic" ]] && return
  jq -n --arg model "$model" --arg reason "$1" --arg code "$2" --arg elapsed "$((SECONDS-start))" \
    --rawfile stdout "$stdout" --rawfile stderr "$stderr" --rawfile available_models "$available" \
    '{provider:"ollama",requested_model:$model,reason:$reason,exit_code:($code|tonumber),elapsed_seconds:($elapsed|tonumber),stdout:$stdout,stderr:$stderr,available_models:$available_models}' \
    > "$tmp/diagnostic.json" && chmod 444 "$tmp/diagnostic.json" && mv -f "$tmp/diagnostic.json" "$diagnostic"
}
fail() { local code="$1" reason="$2"; publish_diagnostic "$reason" "$code"; print -u2 "$reason; diagnostics captured at $diagnostic"; exit "$code"; }
interrupted() { local signal="$1"; trap - "$signal"; fail 70 "Ollama invocation interrupted by SIG$signal"; }
trap cleanup EXIT
trap 'interrupted HUP' HUP
trap 'interrupted INT' INT
trap 'interrupted TERM' TERM

safe() {
  local f="$1" label="$2" root_allowed=""
  [[ -f "$f" && ! -L "$f" ]] || fail 66 "$label is not a regular file"
  f="$(cd "$(dirname "$f")" && pwd -P)/$(basename "$f")"
  if [[ -n "$packet_root" ]]; then
    root_allowed="$(cd "$packet_root" 2>/dev/null && pwd -P)" || fail 77 "invalid packet root"
    case "$f" in "$root"/*|"$root_allowed"/*) ;; *) fail 77 "$label is outside allowed roots";; esac
  else
    case "$f" in "$root"/*) ;; *) fail 77 "$label must be inside repo or use --packet-root";; esac
  fi
  case "$f" in */.env|*/.env.*|*/.reviewers.env|*/data/*|*/exports/*|*/artifacts/private/*|*.pem|*.key) fail 77 "refusing private $label";; esac
  REPLY="$f"
}
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

command -v ollama >/dev/null || fail 69 "Ollama CLI not found"
command -v jq >/dev/null || fail 69 "jq is required"
set +e
ollama list > "$available" 2> "$stderr"
list_code=$?
set -e
[[ $list_code -eq 0 ]] || fail 69 "Ollama model preflight failed"
awk 'NR > 1 {print $1}' "$available" | grep -Fxq -- "$model" || fail 74 "Ollama model is not available to this account: $model"

safe "$prompt" prompt; prompt="$REPLY"
packet="$tmp/packet"; mkdir -m 700 "$packet"; i=0
for f in "$@"; do
  safe "$f" packet
  i=$((i+1)); cp -p "$REPLY" "$packet/$(printf '%02d' "$i")-$(basename "$REPLY")"
done
{
  print -r -- 'You are an isolated, adversarial, read-only code reviewer.'
  print -r -- 'Use only the supplied prompt and packet. Do not propose or perform state mutation.'
  cat "$(dirname "$0")/output-contract.txt"
  print -r -- "\n===== REVIEW PROMPT =====\n"
  cat "$prompt"
  for f in "$packet"/*; do print -r -- "\n\n===== $(basename "$f") =====\n"; cat "$f"; done
} > "$combined"

set +e
perl -e 'alarm($ENV{OLLAMA_MAX_TIME_SECONDS} || 900); exec @ARGV' ollama run "$model" < "$combined" > "$stdout" 2> "$stderr"
code=$?
set -e
if [[ $code -ne 0 ]]; then
  if grep -Eiq '403 Forbidden: this model requires a subscription|upgrade for access' "$stderr"; then
    fail 78 "Ollama access denied: this Kimi model requires a subscription"
  fi
  fail 70 "Ollama invocation failed or timed out"
fi
python3 "$(dirname "$0")/reviewer-validate.py" < "$stdout" || fail 70 "Ollama response failed substance validation"
{
  print '# Kimi review'
  print ''
  [[ -z "$owner" ]] || print "Owner: $owner"
  print "Wrapper revision: $wrapper_rev"
  print "Provider: Ollama"
  print "Requested model: $model"
  print "Resolved model: $model"
  print ''
  cat "$stdout"
} > "$output"
chmod 444 "$output"; shasum -a 256 "$output" > "$output.sha256"; chmod 444 "$output.sha256"
[[ -s "$output" && -s "$output.sha256" ]] || fail 70 "Kimi artifact or checksum was not created"
print "captured $output"
