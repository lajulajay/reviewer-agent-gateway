#!/bin/zsh
# Review through the GitHub Copilot CLI on the user's Copilot plan, with a
# model chosen by tier and vendor (copilot-model-policy.json). The reviewer
# vendor is the model's vendor, so the vendor rule applies per model. The CLI
# runs in an empty directory with every tool hidden and denied, MCP servers
# disabled and custom instructions off; any tool event fails the review.
set -euo pipefail
umask 077

packet_root=""; owner=""; task=""; vendor=""; authors=(); author_models=()
while [[ "${1:-}" == --* ]]; do
  case "$1" in
    --packet-root) [[ $# -ge 2 ]] || exit 64; packet_root="$2"; shift 2 ;;
    --owner) [[ $# -ge 2 && -n "$2" ]] || exit 64; owner="$2"; shift 2 ;;
    --author) [[ $# -ge 2 && -n "$2" ]] || exit 64; authors+=("$2"); shift 2 ;;
    --author-model) [[ $# -ge 2 && -n "$2" ]] || exit 64; author_models+=("$2"); shift 2 ;;
    --task) [[ $# -ge 2 && "$2" =~ '^[A-Za-z0-9._-]+$' ]] || { print -u2 -- "--task must be a short identifier"; exit 64; }; task="$2"; shift 2 ;;
    --vendor) [[ $# -ge 2 && "$2" =~ '^[a-z]+$' ]] || { print -u2 -- "--vendor must be a vendor name from agents.json"; exit 64; }; vendor="$2"; shift 2 ;;
    *) print -u2 "unknown option: $1"; exit 64 ;;
  esac
done
[[ $# -ge 4 ]] || { print -u2 "usage: $0 [--packet-root DIR] --owner AGENT [--author AGENT]... [--author-model MODEL]... [--task ID] [--vendor VENDOR] <hard|routine> <prompt-file> <.collab/copilot-YYYY-MM-DD-topic.md> <packet-file>..."; exit 64; }
[[ -n "$owner" ]] || { print -u2 -- "--owner is required for Copilot reviews"; exit 64; }
identity=(--owner "$owner"); for a in "${authors[@]}"; do identity+=(--author "$a"); done; for m in "${author_models[@]}"; do identity+=(--author-model "$m"); done
requested_model="$1"; prompt="$2"; output="$3"; shift 3
policy="${COPILOT_REVIEW_MODEL_POLICY:-${0:A:h}/copilot-model-policy.json}"
# Model choice and the vendor rule: the reviewer's vendor is the selected model's vendor.
vendor_arg=(); [[ -z "$vendor" ]] || vendor_arg=(--vendor "$vendor")
selection="$(python3 "${0:A:h}/copilot-model-select.py" "$policy" "$requested_model" "${vendor_arg[@]}" "${identity[@]}")" || exit $?
model="${selection%% *}"; rest="${selection#* }"; model_vendor="${rest%% *}"; max_credits="${rest##* }"
python3 "${0:A:h}/agents.py" check copilot "${identity[@]}" --reviewer-model "$model" || exit $?
outdir="$(cd "$(dirname "$output")" && pwd -P)"; base="$(basename "$output")"; root="$(cd "$outdir/.." && pwd -P)"
[[ "$outdir" == "$root/.collab" && "$base" == copilot-*.md && ! -e "$output" && ! -e "$outdir/${base%.md}.diagnostic.json" ]] || { print -u2 "invalid, existing, or previously attempted output (must be .collab/copilot-*.md)"; exit 65; }
# Copilot sub-agent rounds run only on a coordinator ticket (review-ticket.py); any ticket for this output is enforced.
ticket_args=("${identity[@]}" --vendor "$model_vendor"); [[ -z "$task" ]] || ticket_args+=(--task "$task")
python3 "${0:A:h}/review-ticket.py" check copilot "$requested_model" "$output" "${ticket_args[@]}" -- "$@" || exit $?
tmp="$(mktemp -d "${TMPDIR:-/tmp}/reviewers-copilot.XXXXXX")"
stdout="$tmp/stream.jsonl"; stderr="$tmp/stderr"; combined="$tmp/prompt.txt"; last="$tmp/last.md"; usage="$tmp/usage.json"; diagnostic="$outdir/${base%.md}.diagnostic.json"; start=$SECONDS
model_invocation_started=0; sum_linked=0; stage=""; stage_sum=""
: > "$stdout"; : > "$stderr"
fail() { local code="$1" reason="$2"; local began=false; [[ "$model_invocation_started" == 1 ]] && began=true; if [[ ! -s "$diagnostic" ]]; then jq -n --arg owner "$owner" --arg requested "$requested_model" --arg selected "${model:-}" --arg vendor "${model_vendor:-}" --arg reason "$reason" --arg code "$code" --argjson invoked "$began" --arg elapsed "$((SECONDS-start))" --rawfile stdout "$stdout" --rawfile stderr "$stderr" '{provider:"copilot",cli:"copilot",owner:$owner,requested_model:$requested,selected_model:$selected,reviewer_vendor:$vendor,reason:$reason,exit_code:($code|tonumber),model_invocation_began:$invoked,elapsed_seconds:($elapsed|tonumber),stdout:$stdout,stderr:$stderr}' > "$tmp/diagnostic.json" && chmod 444 "$tmp/diagnostic.json" && mv -f "$tmp/diagnostic.json" "$diagnostic"; fi; print -u2 "$reason; diagnostics captured at $diagnostic"; exit "$code"; }
# Backstop: an exit after the call began that left neither artifact nor diagnostic still records a spent attempt.
cleanup() { local rc=$?; [[ -n "${stage:-}" ]] && rm -f "$stage"; [[ -n "${stage_sum:-}" ]] && rm -f "$stage_sum"; [[ "$sum_linked" == 1 && ! -e "$output" ]] && rm -f "$output.sha256"; if [[ "$model_invocation_started" == 1 && ! ( -e "$output" && -s "$output.sha256" ) && ! -s "$diagnostic" ]]; then ( fail 70 "Copilot wrapper stopped after model invocation began without recording an outcome (exit $rc)" ) 2>/dev/null; fi; rm -rf "$tmp"; }
interrupted() { local signal="$1"; trap - "$signal"; if [[ "$model_invocation_started" == 1 ]]; then fail 70 "Copilot invocation did not complete after model invocation began (interrupted by SIG$signal)"; else fail 78 "Copilot invocation interrupted before model invocation began (SIG$signal)"; fi; }
trap cleanup EXIT
trap 'interrupted HUP' HUP
trap 'interrupted INT' INT
trap 'interrupted TERM' TERM
safe() { local f="$1" label="$2"; [[ -f "$f" && ! -L "$f" ]] || fail 66 "$label is not a regular file"; f="$(cd "$(dirname "$f")" && pwd -P)/$(basename "$f")"; if [[ -n "$packet_root" ]]; then local pr="$(cd "$packet_root" 2>/dev/null && pwd -P)" || fail 77 "invalid packet root"; case "$f" in "$root"/*|"$pr"/*) ;; *) fail 77 "$label is outside allowed roots";; esac; else case "$f" in "$root"/*) ;; *) fail 77 "$label must be inside repo or use --packet-root";; esac; fi; case "$f" in */.env|*/.env.*|*/.reviewers.env|*/data/*|*/exports/*|*/artifacts/private/*|*.pem|*.key) fail 77 "refusing private $label";; esac; REPLY="$f"; }
# Provenance: record the gateway commit; refuse uncommitted wrapper changes.
wrapper_rev="unversioned"
if git -C "$(dirname "$0")" rev-parse --git-dir >/dev/null 2>&1; then
  wrapper_rev="$(git -C "$(dirname "$0")" rev-parse HEAD 2>/dev/null)" || fail 78 "cannot read the gateway revision"
  wrapper_dirty="$(git -C "$(dirname "$0")" status --porcelain -- '*.sh' '*.py' '*.json' output-contract.txt ':(exclude).collab' 2>/dev/null)" || fail 78 "cannot read gateway status"
  [[ -z "$wrapper_dirty" ]] || fail 78 "gateway wrapper files have uncommitted changes"
fi
command -v copilot >/dev/null || fail 69 "GitHub Copilot CLI not found"; command -v jq >/dev/null || fail 69 "jq is required"
# A provider override would move the call off the Copilot plan.
[[ -z "${COPILOT_PROVIDER_BASE_URL:-}${COPILOT_PROVIDER_API_KEY:-}${COPILOT_PROVIDER_TYPE:-}${COPILOT_MODEL:-}" ]] || fail 78 "Copilot provider or model environment overrides are not allowed for reviews"
copilot_version="$(copilot --version 2>> "$stderr" | head -1)" || fail 69 "Copilot CLI version check failed"
safe "$prompt" prompt; prompt="$REPLY"
{ cat "$prompt"; for f in "$@"; do safe "$f" packet; printf '\n\n===== %s =====\n' "$(basename "$REPLY")"; cat "$REPLY"; done
  print -r -- "

TOOLS: None are available. Review only the text above. Your final message must be the complete review and nothing else.
"; cat "$(dirname "$0")/output-contract.txt"; } > "$combined"
max_prompt_bytes="$(jq -er '.max_prompt_bytes | select(type == "number" and . >= 1)' "$policy" 2>> "$stderr")" || fail 78 "copilot-model-policy.json has no max_prompt_bytes"
prompt_bytes="$(wc -c < "$combined" | tr -d ' ')"
[[ "$prompt_bytes" -le "$max_prompt_bytes" ]] || fail 65 "prompt and packet exceed $max_prompt_bytes bytes"
timeout_seconds="${COPILOT_MAX_TIME_SECONDS:-1800}"
[[ "$timeout_seconds" == <-> && "$timeout_seconds" -ge 1 ]] || fail 64 "COPILOT_MAX_TIME_SECONDS must be a positive integer"
# When the escalation reviewer may not review this work (vendor rule), Copilot may
# substitute for it with a vendor not yet involved in the topic (review-budget.py).
escalation="$(jq -er '.escalation_provider | select(type == "string")' "$(dirname "$0")/review-budget.json" 2>> "$stderr")" || fail 78 "review-budget.json has no escalation_provider"
esc_sub=(); set +e; python3 "$(dirname "$0")/agents.py" check "$escalation" "${identity[@]}" 2>/dev/null; escalation_rc=$?; set -e
[[ $escalation_rc -eq 0 || $escalation_rc -eq 64 ]] || fail 78 "cannot check the escalation reviewer's eligibility"
[[ $escalation_rc -ne 64 ]] || esc_sub=(--escalation-substitute "$model_vendor")
budget="$(python3 "$(dirname "$0")/review-budget.py" copilot "$requested_model" "$outdir/$base" "${esc_sub[@]}" 2> "$tmp/budget.err")" || fail 79 "$(<"$tmp/budget.err")"
# An empty workspace and an empty Copilot home per call: no user MCP configuration, plugins,
# custom agents or saved state can load. Sign-in comes from the system credential store.
workspace="$tmp/workspace"; copilot_home="$tmp/home"; mkdir -m 700 "$workspace" "$copilot_home"
model_invocation_started=1
set +e
(cd "$workspace" && env -u COPILOT_ALLOW_ALL -u COPILOT_ASSISTED_APPROVAL -u COPILOT_CUSTOM_INSTRUCTIONS_DIRS COPILOT_HOME="$copilot_home" \
  COPILOT_PLUGIN_DIR_ONLY=true COPILOT_AUTO_UPDATE=false COPILOT_MAX_TIME_SECONDS="$timeout_seconds" \
  perl -e 'alarm($ENV{COPILOT_MAX_TIME_SECONDS}); exec @ARGV' copilot --model "$model" \
    --available-tools=gateway_no_tools --deny-tool=shell --deny-tool=write --deny-tool=read --deny-tool=memory --deny-tool=url \
    --disable-builtin-mcps --disable-mcp-server=computer-use --disable-mcp-server=browser-use --disable-mcp-server=github-copilot-browser --disable-mcp-server=WorkIQ \
    --no-custom-instructions --disallow-temp-dir --no-ask-user --sync-session=off --no-auto-update \
    --max-ai-credits "$max_credits" --output-format json --usage-output-file "$usage" < "$combined") > "$stdout" 2>> "$stderr"
code=$?
set -e
[[ $code -ne 142 ]] || fail 70 "Copilot invocation timed out"
[[ $code -eq 0 ]] || fail 70 "Copilot invocation returned nonzero after model invocation began (exit $code)"
[[ -s "$stdout" ]] || fail 70 "Copilot returned no stream output"
jq -e . "$stdout" >/dev/null 2>&1 || fail 70 "Copilot returned invalid stream JSON"
# Isolation: no tool event of any kind, no tool request, and every MCP server disabled.
# serverTools on a message names the API provider ({"provider": ...}); any other content counts as tool use.
tool_events="$(jq -sc '[.[] | select((.type? // "" | test("^tool\\.|tool_call|subagent")) or ((.data.toolRequests? // []) | length > 0) or ((.data.serverTools? // []) | if type == "object" then (del(.provider) | length > 0) else length > 0 end))] | length' "$stdout" 2>/dev/null)" || fail 70 "Copilot tool-event validation failed"
[[ "$tool_events" -eq 0 ]] || fail 70 "Copilot response failed isolation validation: tool events were emitted"
live_servers="$(jq -sc '[.[] | select(.type? == "session.mcp_servers_loaded") | .data.servers[]? | select(.status != "disabled") | .name] | length' "$stdout" 2>/dev/null)" || fail 70 "Copilot MCP status validation failed"
[[ "$live_servers" -eq 0 ]] || fail 70 "Copilot response failed isolation validation: an MCP server was enabled"
# Exactly one result, as the final event, reporting success.
jq -se '([.[] | select(.type? == "result")] | length) == 1 and (last | .type? == "result" and .exitCode? == 0)' "$stdout" >/dev/null 2>&1 || fail 70 "Copilot run did not end with one successful result"
# Every assistant message must name its model, and all must be the selected one.
unlabeled="$(jq -s '[.[] | select(.type? == "assistant.message" and ((.data.model? | type) != "string" or .data.model == ""))] | length' "$stdout")" || fail 70 "Copilot model extraction failed"
[[ "$unlabeled" -eq 0 ]] || fail 74 "Copilot reply did not name its model in $unlabeled message(s)"
resolved="$(jq -sr '[.[] | select(.type? == "assistant.message") | .data.model] | unique | join(", ")' "$stdout")" || fail 70 "Copilot model extraction failed"
[[ "$resolved" == "$model" ]] || fail 74 "Copilot resolved outside the selected model ($resolved)"
# The review is the final reply: the trailing run of assistant messages that
# share one reply key (originatingMessageId, else messageId, plus apiCallId).
# The key must be present and must not occur earlier in the stream, message
# IDs must be unique, every chunk must be present with one consistent
# chunkCount, and an unchunked reply is a single message. An empty or
# incomplete final reply fails; earlier replies are never used instead.
jq -sr 'def key: [(.data.originatingMessageId // .data.messageId), (.data.apiCallId // null)];
  [.[] | select(.type? == "assistant.message")] as $all
  | if ($all | length) == 0 then error("no assistant reply") else
      ($all | last | key) as $k
      | if ($k[0] | type) != "string" or $k[0] == "" then error("final reply has no message id") else . end
      | ([$all | to_entries[] | select(.value | key != $k) | .key] | max // -1) as $before
      | $all[($before + 1):] as $g
      | if any($all[:($before + 1)][]; key == $k) then error("reply key occurs outside the final reply") else . end
      | if ($g | map(.data.messageId) | unique | length) != ($g | length) then error("duplicate message ids") else . end
      | ($g | sort_by(.data.chunkIndex // 0)) as $s
      | ($s | map(.data.chunkCount) | unique) as $c
      | if ($c == [null] and ($s | length) == 1)
           or (($c | length) == 1 and ($c[0] | type) == "number" and $c[0] == ($s | length) and ($s | map(.data.chunkIndex)) == [range($s | length)])
        then $s | map(.data.content // "") | join("") else error("incomplete or inconsistent reply chunks") end
    end' "$stdout" > "$last" || fail 70 "Copilot response extraction failed"
[[ -s "$last" ]] || fail 70 "Copilot returned no assistant review"
python3 "$(dirname "$0")/reviewer-validate.py" < "$last" || fail 70 "Copilot response failed substance validation"
checks="$(python3 "$(dirname "$0")/reviewer-claims.py" < "$last")" || fail 70 "Copilot mechanical claim check failed"
credits="$(jq -r 'if .totalNanoAiu? then (.totalNanoAiu / 1e9 * 1000 | round / 1000 | tostring) + " AI credits" else "not reported" end' "$usage" 2>/dev/null || print 'not reported')"
tokens="$(jq -c '.tokenDetails? // {}' "$usage" 2>/dev/null || print '{}')"
{ print '# Copilot review'; print ''; [[ -n "$owner" ]] && print "Owner: $owner"; [[ $#authors -eq 0 ]] || print "Authors: ${(j:, :)authors}"; [[ $#author_models -eq 0 ]] || print "Author models: ${(j:, :)author_models}"; [[ -z "$task" ]] || print "Task: $task"; print "Wrapper revision: $wrapper_rev"; print "Requested model: $requested_model"; print "Selected model: $model"; print "Reviewer vendor: $model_vendor"; print "Resolved model(s): $resolved"; print "CLI version: $copilot_version"; print "Tool events: $tool_events"; print "Usage: $tokens"; print "AI credits: $credits (cap $max_credits)"; [[ -z "${REVIEW_BUDGET_OVERRIDE:-}" ]] || print "Budget override: $REVIEW_BUDGET_OVERRIDE"; while IFS= read -r note; do [[ -z "$note" ]] || print "Mechanical check: $note"; done <<< "$checks"; print ''; cat "$last"; } > "$tmp/final.md" || fail 70 "Copilot artifact assembly failed"
# Publish: stage both files beside the output under unique names (same
# filesystem), then hard-link the checksum and finally the artifact into place.
# ln never replaces an existing file, so a concurrent call for the same output
# fails instead of overwriting; a checksum this call linked is removed on any
# exit (including a signal) that leaves no artifact.
stage="$(mktemp "$outdir/.${base}.XXXXXX")" && stage_sum="$(mktemp "$outdir/.${base}.sha256.XXXXXX")" || fail 70 "Copilot artifact staging failed"
{ cat "$tmp/final.md" > "$stage" && digest="$(shasum -a 256 < "$stage")" && print -r -- "${digest%% *}  $output" > "$stage_sum" \
  && chmod 444 "$stage" "$stage_sum" && ln "$stage_sum" "$output.sha256" && sum_linked=1 && ln "$stage" "$output"; } \
  || fail 70 "Copilot artifact or checksum was not written"
rm -f "$stage" "$stage_sum"
[[ -s "$output" && -s "$output.sha256" ]] || fail 70 "Copilot artifact or checksum was not created"; print "captured $output"
