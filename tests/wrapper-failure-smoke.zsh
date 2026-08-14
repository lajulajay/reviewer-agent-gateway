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

cat > "$test_root/bin/claude" <<'EOF'
#!/bin/zsh
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
exit 42
EOF
chmod 755 "$test_root/bin/claude" "$test_root/bin/ollama" "$test_root/bin/gemini"

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
  PATH="$test_root/bin:$PATH" GEMINI_API_KEY=test \
    "$root/$wrapper" "$model" "$test_root/prompt.md" "$test_root/.collab/$output" "$test_root/packet/source.md" >/dev/null 2>&1
  local code=$?
  set -e
  [[ $code -ne 0 ]]
  [[ -s "$test_root/.collab/${output%.md}.diagnostic.json" || -s "$test_root/.collab/${output%.json}.diagnostic.json" ]]
}

run_failure kimi-review.sh kimi-k2.6:cloud kimi.md
: > "$test_root/.collab/claude.md.diagnostic.json"
run_failure claude-review.sh sonnet claude.md
run_failure gemini-review.sh gemini-3.1-pro-preview gemini.json

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
