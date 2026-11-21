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
