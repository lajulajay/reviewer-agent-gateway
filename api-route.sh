# Sourced by codex-review.sh and kimi-review.sh when their model policy sets
# "route": "api". Expects the caller's fail, safe, and variables (provider,
# policy, requested_model, prompt, outdir, base, output, tmp, stderr, combined,
# last, owner, authors, author_models, task, wrapper_rev). The call itself is
# api-call.py: tool-free, key from the Keychain, spend-capped. Never returns.
api_route() {
  local title="$1"; shift
  command -v jq >/dev/null || fail 69 "jq is required"
  safe "$prompt" prompt; prompt="$REPLY"
  model="$(jq -er --arg tier "$requested_model" '.api.tiers[$tier].model | select(type == "string" and length > 0)' "$policy" 2>> "$stderr")" || fail 78 "$title API review tier must be one of: $(jq -r '.api.tiers | keys | join(", ")' "$policy" 2>/dev/null)"
  effort="$(jq -r --arg tier "$requested_model" '.api.tiers[$tier].reasoning_effort // "not set"' "$policy")"
  local budget_tier="$requested_model"
  [[ "$requested_model" == hard ]] || budget_tier=routine
  budget="$(python3 "${0:A:h}/review-budget.py" "$provider" "$budget_tier" "$outdir/$base" 2> "$tmp/budget.err")" || fail 79 "$(<"$tmp/budget.err")"
  { cat "$prompt"; for f in "$@"; do safe "$f" packet; printf '\n\n===== %s =====\n' "$(basename "$REPLY")"; cat "$REPLY"; done
    print -r -- "

TOOLS: None are available. Review only the text above.
"; cat "${0:A:h}/output-contract.txt"; } > "$combined"
  model_invocation_started=1
  local code
  set +e
  python3 "${0:A:h}/api-call.py" "$policy" "$requested_model" "$combined" "$last" "$tmp/api.json" 2>> "$stderr"
  code=$?
  set -e
  # 78/79/64 are refusals before any request; anything else after it was sent.
  if [[ $code -eq 78 || $code -eq 79 || $code -eq 64 ]]; then model_invocation_started=0; fail $code "$(tail -1 "$stderr")"; fi
  [[ $code -eq 0 ]] || fail 70 "$title API call failed: $(tail -1 "$stderr")"
  python3 "${0:A:h}/reviewer-validate.py" < "$last" || fail 70 "$title response failed substance validation"
  local checks; checks="$(python3 "${0:A:h}/reviewer-claims.py" < "$last")"
  { print "# $title review"; print ''; [[ -n "$owner" ]] && print "Owner: $owner"; [[ $#authors -eq 0 ]] || print "Authors: ${(j:, :)authors}"; [[ $#author_models -eq 0 ]] || print "Author models: ${(j:, :)author_models}"; [[ -z "$task" ]] || print "Task: $task"
    print "Wrapper revision: $wrapper_rev"; print "Route: api"; print "Requested model: $requested_model"; print "Selected model: $model"; print "Reasoning effort: $effort"
    print "Resolved model(s): $(jq -r '.served_model // "not reported"' "$tmp/api.json")"
    print "Usage: $(jq -c '{input_tokens, output_tokens}' "$tmp/api.json")"
    print "API cost: $(jq -r '"$\(.cost_usd) (ledger $\(.ledger_spent_usd) of $\(.spend_cap_usd) cap)"' "$tmp/api.json")"
    [[ -z "${REVIEW_BUDGET_OVERRIDE:-}" ]] || print "Budget override: $REVIEW_BUDGET_OVERRIDE"
    while IFS= read -r note; do [[ -z "$note" ]] || print "Mechanical check: $note"; done <<< "$checks"; print ''; cat "$last"; } > "$tmp/final.md"
  chmod 444 "$tmp/final.md"; mv "$tmp/final.md" "$output"; shasum -a 256 "$output" > "$output.sha256"; chmod 444 "$output.sha256"
  [[ -s "$output" && -s "$output.sha256" ]] || fail 70 "$title artifact or checksum was not created"
  print "captured $output"
  exit 0
}
