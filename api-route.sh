# Sourced by codex-review.sh and kimi-review.sh when their model policy sets
# "route": "api". Expects the caller's fail, safe, and variables (provider,
# policy, requested_model, prompt, outdir, base, output, tmp, stderr, combined,
# last, owner, authors, author_models, task, wrapper_rev, gateway_dir). The call itself is
# api-call.py: tool-free, key from the Keychain, spend-capped. Never returns.
api_route() {
  local title="$1"; shift
  command -v jq >/dev/null || fail 69 "jq is required"
  safe "$prompt" prompt; prompt="$REPLY"
  model="$(jq -er --arg tier "$requested_model" '.api.tiers[$tier].model | select(type == "string" and length > 0)' "$policy" 2>> "$stderr")" || fail 78 "$title API review tier must be one of: $(jq -r '.api.tiers | keys | join(", ")' "$policy" 2>/dev/null)"
  effort="$(jq -r --arg tier "$requested_model" '.api.tiers[$tier].reasoning_effort // "not set"' "$policy")" || fail 78 "cannot read the API policy"
  local budget_tier="$requested_model"
  [[ "$requested_model" == hard ]] || budget_tier=routine
  budget="$(python3 "$gateway_dir/review-budget.py" "$provider" "$budget_tier" "$outdir/$base" 2> "$tmp/budget.err")" || fail 79 "$(<"$tmp/budget.err")"
  # Each assembly step is checked: an incomplete packet must never be sent.
  cat "$prompt" > "$combined" || fail 78 "cannot assemble the review prompt"
  for f in "$@"; do
    safe "$f" packet
    printf '\n\n===== %s =====\n' "$(basename "$REPLY")" >> "$combined" || fail 78 "cannot assemble the review prompt"
    cat "$REPLY" >> "$combined" || fail 78 "cannot read packet $REPLY"
  done
  print -r -- "

TOOLS: None are available. Review only the text above.
" >> "$combined" || fail 78 "cannot assemble the review prompt"
  cat "$gateway_dir/output-contract.txt" >> "$combined" || fail 78 "cannot read the output contract"
  # api-call.py creates the marker immediately before sending; only then may
  # the model have been reached (Kimi diagnostics report this truthfully).
  local marker="$tmp/api.sent" code
  set +e
  python3 "$gateway_dir/api-call.py" "$policy" "$requested_model" "$combined" "$last" "$tmp/api.json" "$marker" 2>> "$stderr"
  code=$?
  set -e
  if [[ -e "$marker" ]]; then model_invocation_started=1; fi
  if [[ ! -e "$marker" ]]; then
    case $code in 64|78|79) fail $code "$(tail -1 "$stderr")" ;; 0) fail 78 "API call exited 0 without sending" ;; *) fail 78 "$title API preflight failed (exit $code): $(tail -1 "$stderr")" ;; esac
  fi
  [[ $code -eq 0 ]] || fail 70 "$title API call failed: $(tail -1 "$stderr")"
  python3 "$gateway_dir/reviewer-validate.py" < "$last" || fail 70 "$title response failed substance validation"
  local checks
  checks="$(python3 "$gateway_dir/reviewer-claims.py" < "$last")" || fail 70 "$title mechanical checks failed"
  # Every value is computed and checked before the artifact is written.
  local served usage cost
  served="$(jq -r '.served_model // "not reported"' "$tmp/api.json")" || fail 70 "cannot read API metadata"
  usage="$(jq -c '{input_tokens, output_tokens}' "$tmp/api.json")" || fail 70 "cannot read API metadata"
  cost="$(jq -r '"$\(.cost_usd) (ledger committed $\(.ledger_committed_usd) of $\(.spend_cap_usd) cap)"' "$tmp/api.json")" || fail 70 "cannot read API metadata"
  { print "# $title review"; print ''; [[ -n "$owner" ]] && print "Owner: $owner"; [[ $#authors -eq 0 ]] || print "Authors: ${(j:, :)authors}"; [[ $#author_models -eq 0 ]] || print "Author models: ${(j:, :)author_models}"; [[ -z "$task" ]] || print "Task: $task"
    print "Wrapper revision: $wrapper_rev"; print "Route: api"; print "Requested model: $requested_model"; print "Selected model: $model"; print "Reasoning effort: $effort"
    print "Resolved model(s): $served"; print "Usage: $usage"; print "API cost: $cost"
    [[ -z "${REVIEW_BUDGET_OVERRIDE:-}" ]] || print "Budget override: $REVIEW_BUDGET_OVERRIDE"
    while IFS= read -r note; do [[ -z "$note" ]] || print "Mechanical check: $note"; done <<< "$checks"; print ''; } > "$tmp/final.md" || fail 70 "cannot write the $title artifact"
  cat "$last" >> "$tmp/final.md" || fail 70 "cannot write the $title artifact"
  { chmod 444 "$tmp/final.md" && mv "$tmp/final.md" "$output" && shasum -a 256 "$output" > "$output.sha256" && chmod 444 "$output.sha256"; } || fail 70 "cannot store the $title artifact or checksum"
  [[ -s "$output" && -s "$output.sha256" ]] || fail 70 "$title artifact or checksum was not created"
  print "captured $output"
  exit 0
}
