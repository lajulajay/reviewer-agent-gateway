# Reviewer invocation failure report

Date: 2026-08-11
Invoked from: `prediction-markets/kalshi-econ-agent`
Canonical wrapper repository: `~/Developer/reviewers`
Review topic: LLM signal-reversal exit gating and a pre-implementation plan

## Packet

Prompt:

`kalshi-econ-agent/reviewers/prompts/reversal-gating-alignment-2026-08-11.md`

Packet:

`kalshi-econ-agent/reviewers/prompts/reversal-gating-alignment-packet-2026-08-11.md`

Additional explicit files:

- `agent/src/econ_agent/edge.py`
- `agent/src/econ_agent/settlement.py`
- `agent/src/econ_agent/config.py`
- `agent/src/econ_agent/models.py`

The packet was sanitized and contained paper-trading results only. No
credentials, private keys, raw exports, or unsealed outcomes were supplied.

## Kimi invocation

Command shape from the consumer repository:

```text
KIMI_MAX_TIME_SECONDS=900 perl -e 'alarm 960; exec @ARGV' \
  reviewers/kimi-review.sh kimi-k3 \
  reviewers/prompts/reversal-gating-alignment-2026-08-11.md \
  .collab/kimi-round-2026-08-11-reversal-gating-alignment.md \
  reviewers/prompts/reversal-gating-alignment-packet-2026-08-11.md \
  agent/src/econ_agent/edge.py agent/src/econ_agent/settlement.py \
  agent/src/econ_agent/config.py agent/src/econ_agent/models.py
```

Delegation path:

```text
kalshi-econ-agent/reviewers/kimi-review.sh
  -> ~/Developer/reviewers/kimi-review.sh
```

Observed failure:

```text
/Users/lajulajay/Developer/reviewers/kimi-review.sh:11:
read-only variable: status
```

The failure occurred before packet/provider invocation. The canonical zsh
wrapper declares `status="$tmp/status"`; in zsh, `status` is a read-only
special variable. No Moonshot request was made by this attempt.

Artifacts:

- No requested Kimi review artifact was created.
- No Kimi checksum or diagnostic artifact was created.
- No repository, database, or production mutation occurred.

Comparison artifact:

`kalshi-econ-agent/.collab/DIAG-kimi-probe-2.md` and its checksum contain a
prior substantive `kimi-k3` probe from the wrapper root-cause investigation.
That artifact is useful review evidence, but it is not the output of this
latest invocation.

## Claude invocation

Command shape from the consumer repository:

```text
CLAUDE_MAX_TIME_SECONDS=600 perl -e 'alarm 660; exec @ARGV' \
  reviewers/claude-review.sh sonnet \
  reviewers/prompts/reversal-gating-alignment-2026-08-11.md \
  .collab/claude-round-2026-08-11-reversal-gating-alignment.md \
  reviewers/prompts/reversal-gating-alignment-packet-2026-08-11.md \
  agent/src/econ_agent/edge.py agent/src/econ_agent/settlement.py \
  agent/src/econ_agent/config.py agent/src/econ_agent/models.py
```

Delegation path:

```text
kalshi-econ-agent/reviewers/claude-review.sh
  -> ~/Developer/reviewers/claude-review.sh
```

Observed failure:

```text
jq: Bad JSON in --rawfile stdout \
/var/folders/.../reviewers-claude.*/stdout.json:
Could not open .../stdout.json: No such file or directory
```

The wrapper failed while constructing its required failure diagnostic. Its
`fail()` function uses `jq --rawfile stdout "$stdout"` even when the Claude
process has not created the stdout file. This masks the underlying provider or
process failure and prevents a valid diagnostic from being written.

Artifacts:

- The requested Claude review artifact was not created.
- A zero-byte file was left at:
  `kalshi-econ-agent/.collab/claude-round-2026-08-11-reversal-gating-alignment.diagnostic.json`
- No Claude checksum was created.
- No repository, database, or production mutation occurred.

## Outcome and protocol assessment

The updated invocation protocol is still not operational for this review:

1. Kimi fails deterministically in the wrapper before reaching the provider.
2. Claude reaches failure handling but its diagnostic path fails too, masking
   the original error.
3. Neither invocation produced a substantive, immutable, checksum-backed
   review artifact.

The owner therefore did not treat this session as a successful two-reviewer
alignment. No implementation or risk-policy change was made.

## Recommended fixes

- Rename the Kimi wrapper variable `status` to a non-special name such as
  `http_status_file`.
- Ensure all diagnostic `--rawfile` inputs exist before calling `jq`, or create
  empty stdout/stderr files immediately after the temporary directory is made.
- Preserve the original exit code, elapsed time, stdout, stderr, provider
  status, and failure reason in the diagnostic artifact.
- Add a wrapper smoke test that forces a local pre-provider failure and asserts
  a non-empty diagnostic JSON is created.
- Add an end-to-end dry invocation test that asserts successful review,
  machine-detectable verdict, immutable output, and SHA-256 sidecar.
- Do not consider a provider call successful unless the expected artifact and
  checksum both exist.
