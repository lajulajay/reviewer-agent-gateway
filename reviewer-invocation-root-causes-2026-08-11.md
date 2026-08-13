# Adversarial reviewer invocation — root cause analysis

Date: 2026-08-11
Scope: cross-repo. Affects `kalshi-temperature-bot`, `kalshi-finance-agent`,
`kalshi-econ-agent`, `polymarket-temperature-bot`, and the shared wrapper host
`~/Developer/trading-strategies`.

Placed at the `prediction-markets` level because six of the seven causes are
properties of the shared wrapper set or the cross-repo protocol, not of any one
repository.

## Inputs

- `kalshi-temperature-bot/.collab/invocation-failure-2026-08-11.txt`
- `kalshi-finance-agent/.collab/invocation-failure-2026-08-11.txt`
- `kalshi-econ-agent/.collab/invocation-failure-2026-08-11.txt`
- All wrapper scripts in `*/reviewers/` across the five repos.

Findings 1–3 were reproduced empirically rather than inferred from the logs.
Reproduction cost three real provider calls (two Moonshot, one Anthropic).

---

## 1. Kimi — the wrapper timeout is 2–3x shorter than real review latency

Deterministic, not intermittent. This is the largest single cause.

`trading-strategies/reviewers/kimi-review.sh` caps the request at
`KIMI_MAX_TIME_SECONDS:-180`. Measured `kimi-k3` latency on the actual packets
from these logs:

| Payload | Wall time | Result |
|---|---|---|
| finance approval-policy prompt + packet (5 KB) | 374 s | HTTP 200, 16.2 KB review, 8,539 reasoning tokens |
| econ reversal-gating prompt + packet + 4 source files (the exact logged command) | 485 s | HTTP 200, usable review captured |

Both exceed the 180 s ceiling, so every `kimi-k3` review fails by construction.
The wrapper path is otherwise healthy: rerunning the exact econ command with
`KIMI_MAX_TIME_SECONDS=600` produced a complete review in 8:05 with exit 0.

The 900 s ceiling described in the 08-09 temperature-bot log was lowered to
180 s at some point before 08-11 02:14. That change converted "slow" into
"always fails."

`kimi-k3` is a heavy-reasoning model — roughly 70% of its output tokens are
reasoning tokens — and the request is not streamed, so no bytes arrive until
generation completes. A fixed non-streaming `max-time` is the wrong control for
this model.

Secondary defect: the Kimi wrapper writes **no diagnostic artifact** on failure,
unlike the Claude wrapper's `.diagnostic.json`. It prints to stderr and exits
70. Reproduced with a short timeout:
`curl: (28) Operation timed out ... HTTP status: 000`, `EXIT=70`, no file
created. This is why the econ log records "returned without a captured review,
error text, or artifact" — the signal existed but was not durable.

**Fix:** raise `KIMI_MAX_TIME_SECONDS` to 900; use `kimi-k2.6` for routine
scans and reserve `kimi-k3` for architecture/experiment review; move to a
streaming request so slow is distinguishable from dead; always write a
structured failure artifact.

## 2. Claude — `--permission-mode plan` combined with `--tools=` is unstable

The finance log's "false-success capture" and the temperature-bot's placeholder
artifacts are the same defect.

Plan mode instructs the model to record its work in a plan file and terminate
via `ExitPlanMode`. `--tools=` removes the ability to do either. The model then
sometimes emits only the narration of that intent. That is exactly the content
of `kalshi-finance-agent/.collab/claude-round-2026-08-11-implementation.md`
("I'll write the review into the plan file and then present it via
ExitPlanMode") and `kalshi-temperature-bot/.collab/claude-2026-08-11-diagnostic-review.md`.

It is intermittent, not deterministic. Rerunning the identical finance prompt
and packet through the identical flags produced a complete 16,477-character
adversarial review. The same invocation yields either outcome.

The wrapper cannot tell the two apart and does not try. `claude-review.sh`
validates only `.is_error == false and (.result | type == "string")`. A
one-line procedural narration satisfies that check, is written to `.collab/`,
is `chmod 444`'d, and is then indistinguishable from a signed-off review.

The three 15-byte `Execution error` files (08-02 and 08-09) predate the wrapper
and came from raw `claude -p ... > file` with stderr discarded.

Asymmetry: the Claude wrapper writes no `.sha256` sidecar, while Kimi and
Gemini both do. Claude artifacts are not integrity-checkable.

**Fix:** drop `--permission-mode plan` — `--tools=` already provides the
required isolation, and plan mode only adds a workflow the model cannot
complete. Add the missing SHA-256 sidecar.

## 3. Gemini — fail-closed exact-model check fights provider alias remapping

`gemini-review.sh` requires the response's `.stats.models` keys to contain the
requested model string exactly (`grep -Fxq`), otherwise exit 74. The check runs
*after* the call has been made and paid for, and the response is discarded.

Against observed provider behavior:

- `gemini-2.5-flash` is remapped by the CLI to `gemini-3.5-flash` (recorded in
  the 08-09 temperature-bot log) — exit 74 every time.
- `gemini-2.5-pro` and `gemini-2.5-flash-lite` return `ModelNotFoundError` from
  the CLI even though both are listed as available for this API key (verified
  by querying the models endpoint directly). This is a CLI entitlement issue,
  not a credential issue.
- `gemini-2.0-flash` "completed the wait but produced no artifact" in the econ
  log. That is exit 74, silently.

There is no pre-flight model validation, and no use of the `-latest` aliases
(`gemini-flash-latest`, `gemini-pro-latest`) that exist for this key.

**Fix:** pre-flight the model list before invoking; record the requested and
resolved model pair as metadata; fail only on a family mismatch rather than on
exact-string inequality.

## 4. The shared wrapper directory is untracked and unversioned

`~/Developer/trading-strategies` **is not a git repository**. It hosts the
canonical `claude-review.sh`, `kimi-review.sh`, and `moonshot-review.py` that
all four prediction-markets repos exec through 155-byte shims
(`../../../trading-strategies/reviewers/...`).

The component that broke therefore has no history, no diff, and no revert, and
it breaks all four repos simultaneously and invisibly. The 900 s to 180 s
regression in finding 1 is unattributable for exactly this reason.

`gemini-review.sh` was not centralized the same way: it exists as four
independently drifted forks (3397 / 3403 / 3429 / 3570 bytes) with three
different credential paths (`.reviewers.env`, `.env`, `agent/.env`).

The wrappers are also untracked inside the repos that depend on them:
`?? reviewers/` in econ-agent, `?? reviewers/claude-review.sh` in finance-agent
and polymarket.

**Fix:** `git init` trading-strategies, or move the wrappers into a tracked
repo and vendor them. Then centralize `gemini-review.sh` and delete the forks.

## 5. Prompts and packets must live inside the repo, so they fork

Every wrapper derives `workspace_root` from the *output* path and rejects any
prompt or packet outside it (exit 77).

The shared `~/Developer/reviewers/prompts/` directory (created 08-11 21:55) is
structurally unusable for this reason. The econ log's "invalid prompt file
because the prompt had been staged outside the repository path" is this
constraint firing.

The workaround is copying prompts into each repo, and they diverged
immediately: `reversal-gating-packet-2026-08-11.md` is 3,144 bytes in the
shared directory and 2,788 bytes in `kalshi-econ-agent/reviewers/prompts/`.

**Fix:** allow an explicit `--packet-root` outside the workspace, retaining the
symlink and secret-path guards.

## 6. The protocol contradicts itself across repos

- `kalshi-temperature-bot/reviewers/README.md`: "Claude remains the primary
  reviewer. Gemini may be invoked only under the escalation rule."
- `kalshi-finance-agent/reviewers/README.md`: "Kimi is the primary reviewer and
  Claude is the first backup. Gemini... last-resort."
- `kalshi-temperature-bot/AGENTS.md`: "Codex and Kimi form the primary loop.
  Claude is the first backup reviewer and Gemini is the last-resort reviewer."

The temperature-bot's own README and AGENTS.md disagree with each other. There
is no single definition of the escalation chain, so "which reviewer failed and
what runs next" is decided ad hoc per session.

Related: `kalshi-finance-agent/reviewers/prompts/approval-policy-implementation-review-2026-08-11.md`
opens "You are Kimi, the primary adversarial reviewer" and was sent verbatim to
Claude on fallback. Fallbacks reuse the primary's role prompt. Claude also
receives no output-format contract at all, while Gemini is given JSON and Kimi
a system role.

**Fix:** one canonical escalation section, referenced rather than copied; make
the reviewer role prompt a per-reviewer template instead of one file addressed
to Kimi.

## 7. No caller-side timeout budget matched to real latency

Every log records the caller killing a process that appeared hung. The
arithmetic never worked:

- real `kimi-k3` review: 374–485 s (measured);
- Kimi wrapper ceiling: 180 s;
- Claude wrapper `perl alarm` ceiling: 180 s;
- a typical agent shell-tool default: 120 s — the first measurement attempt
  here was killed at exactly 120 s.

The chain fails at whichever ceiling is lowest, and each failure presents as a
different bug.

**Fix:** set one timeout budget per reviewer derived from measured p95 latency,
and make the caller's timeout strictly longer than the wrapper's so the
wrapper's own diagnostics always win the race.

---

## Fix list in dependency order

1. Raise `KIMI_MAX_TIME_SECONDS` to 900; route routine scans to `kimi-k2.6`.
   This alone restores the primary reviewer. Streaming is the durable fix.
2. Add a substance gate to all three wrappers before `chmod 444`: minimum
   length, a required verdict token (`ACCEPT` / `ACCEPT WITH CONDITIONS` /
   `REJECT` / `VERDICT`), and rejection of first-person procedural narration.
   A zero exit status is not a review.
3. Drop `--permission-mode plan` from the Claude wrapper; add its `.sha256`
   sidecar.
4. Pre-flight Gemini model availability; relax the exact-match check to
   requested/resolved recording with family-level validation.
5. Write a structured failure artifact on every path: command, model, elapsed
   time, exit code, stdout, stderr, HTTP or provider status.
6. Put trading-strategies under version control; centralize `gemini-review.sh`
   and delete the four forks.
7. Allow a packet root outside the workspace so prompts stop forking.
8. Publish one canonical escalation rule; template the reviewer role prompt.

## Reproduction notes

- `kalshi-econ-agent/.collab/DIAG-kimi-probe-2.md` (+ `.sha256`) is a real
  `kimi-k3` review of the reversal-gating packet, produced by the finding-1
  reproduction run at `KIMI_MAX_TIME_SECONDS=600`. It is a byproduct, not part
  of this analysis; keep, rename into the normal scheme, or delete.
- No repository, database, or production mutation occurred during this
  investigation. No credentials are recorded here.
