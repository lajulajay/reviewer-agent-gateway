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
[[ $# -ge 4 ]] || { print -u2 "usage: $0 [--packet-root DIR] --owner AGENT [--author AGENT]... [--author-model MODEL]... [--task ID] <hard|routine> <prompt-file> <auto-output.md> <packet-file>..."; exit 64; }
tier="$1"; prompt="$2"; output="$3"; shift 3
[[ "$tier" == hard || "$tier" == routine ]] || { print -u2 "automatic review tier must be hard or routine"; exit 64; }
[[ -n "$owner" ]] || { print -u2 "--owner is required for automatic reviewer selection"; exit 64; }
outdir="$(cd "$(dirname "$output")" && pwd -P)"; base="$(basename "$output")"; root="$(cd "$outdir/.." && pwd -P)"
[[ "$outdir" == "$root/.collab" && "$base" == auto-*.md && ! -e "$output" && ! -e "$outdir/${base%.md}.diagnostic.json" ]] || { print -u2 "invalid, existing, or previously attempted automatic output"; exit 65; }
# Reserve the auto- template across every provider prefix before selection, so a
# counted failure on one candidate can never free the template for a new auto- run.
for provider in claude codex kimi copilot; do
  reserved="$outdir/${provider}-${base#auto-}"
  [[ ! -e "$reserved" && ! -e "${reserved%.md}.diagnostic.json" ]] || { print -u2 "invalid, existing, or previously attempted automatic output (reserved by $reserved)"; exit 65; }
done
gateway="$(cd "$(dirname "$0")" && pwd -P)"
if git -C "$gateway" rev-parse --git-dir >/dev/null 2>&1; then
  git -C "$gateway" rev-parse HEAD >/dev/null 2>&1 || { print -u2 "cannot read the gateway revision"; exit 78; }
  wrapper_dirty="$(git -C "$gateway" status --porcelain -- '*.sh' '*.py' '*.json' output-contract.txt ':(exclude).collab' 2>/dev/null)" || { print -u2 "cannot read gateway status"; exit 78; }
  [[ -z "$wrapper_dirty" ]] || { print -u2 "gateway wrapper files have uncommitted changes"; exit 78; }
fi
set +e
identity=(--owner "$owner"); for a in "${authors[@]}"; do identity+=(--author "$a"); done; for m in "${author_models[@]}"; do identity+=(--author-model "$m"); done
[[ -z "$task" ]] || identity+=(--task "$task")
selection="$(python3 "$gateway/reviewer-select.py" "$gateway/reviewer-roster.json" "$owner" "$output" "${authors[@]}" "${(@)${(@)author_models/#/--author-model=}}" "--tier=$tier" 2>&1)"
code=$?
set -e
[[ $code -eq 0 ]] || { print -u2 "$selection"; exit "$code"; }
candidates=(${(f)selection})
[[ $#candidates -gt 0 ]] || { print -u2 "no eligible active subscription reviewer; use gemini-review.sh"; exit 78; }
forward=("${identity[@]}")
[[ -z "$packet_root" ]] || forward+=(--packet-root "$packet_root")
last_code=78
for provider in "${candidates[@]}"; do
  candidate_output="$outdir/${provider}-${base#auto-}"
  candidate_diagnostic="${candidate_output%.md}.diagnostic.json"
  [[ ! -e "$candidate_output" && ! -e "$candidate_diagnostic" ]] || { print -u2 "candidate output already has an artifact or diagnostic: $candidate_output"; exit 65; }
  provider_tier="$tier"
  if [[ "$provider" == claude ]]; then
    if [[ "$tier" == hard ]]; then provider_tier=opus; else provider_tier=sonnet; fi
  fi
  set +e
  "$gateway/$provider-review.sh" "${forward[@]}" "$provider_tier" "$prompt" "$candidate_output" "$@"
  code=$?
  set -e
  [[ $code -ne 0 ]] || exit 0
  [[ $code -eq 69 || $code -eq 78 ]] || exit "$code"
  print -u2 "$provider is unavailable before model invocation (exit $code); trying the next eligible reviewer"
  last_code=$code
done
print -u2 "all eligible subscription reviewers failed preflight; use gemini-review.sh as the fallback reviewer"
exit "$last_code"
