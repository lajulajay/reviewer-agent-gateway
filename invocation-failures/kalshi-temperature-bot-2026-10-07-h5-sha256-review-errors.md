# Reviewer invocation quality failure report

Date: 2026-10-07 (America/New_York)
Invoked from: `prediction-markets/kalshi-temperature-bot`
Canonical wrapper repository: `~/Developer/reviewer-agent-gateway`
Review topic: H5 final analysis, city table extensions, and city-day dropoff explanation
Owner: Codex; primary reviewer: Claude

## Failure classification

The Claude wrapper calls completed and wrote immutable `.collab` responses with
SHA-256 sidecars. The failure was in the **review content**: Claude repeatedly
declared valid 64-character SHA-256 digests malformed after counting them by
eye. One false finding was labeled a blocker and alleged that a reported
successful script execution could not have happened. These were not wrapper,
provider, or checksum-generation failures.

The requests used the repository shim with `--owner codex`, an explicit prompt
and sanitized packet, for example:

```text
reviewers/claude-review.sh --owner codex sonnet \
  reviewers/prompts/h5-final-analysis-r22-2026-10-07.md \
  .collab/claude-2026-10-07-h5-final-analysis-r22.md \
  reviewers/packets/h5-final-analysis-r22-2026-10-07.md
```

The affected Sonnet responses resolved to `claude-sonnet-5`. The final
consolidated r24 review requested Opus and resolved to `claude-opus-5-5`.
No credentials, private H5 rows, raw exports, orders, or production mutations
were supplied or performed through these review calls.

## Three false digest-length findings

| Round | Artifact being checked | Reviewer claim | Verified result | Correction |
| :--- | :--- | :--- | :--- | :--- |
| r07 | `experiments/h5/FINAL_BY_LOCATION.csv` digest in the r07 packet | 65 hex characters; `F2 [major]` and conditions | `ca71fc6a71fca61d604705e0105298c4a7c52c8c2cdf22a9e25294cdddd483b1` is 64 characters and matched the file bytes when checked | r08 counted eight groups of eight and explicitly identified the r07 finding as a counting error |
| r14 | Raw r12 review artifact digest in the r14 packet | 63 hex characters; `F1 [blocker]` and conditions | `8ec46ce936f2ecfd3725814f190723ede72539444449dc5d5cc9b56428305923` is 64 characters and matched both the r12 artifact bytes and its `.sha256` sidecar | r15 verified the 64-character grouped value; r24 closed the remaining exact-line audit obligations |
| r22 | Expected sidecar-excerpt digest in the r22 check | 63 hex characters; `F1 [blocker]` and `F2 [major]` alleged the script could not print PASS | `418da641d69a6fa8c04df705d5a16800466bdc4b072435b2f384c0bf47cdac7a` is 64 characters. The actual script exited 0 and its directly captured stdout printed PASS and `SIDE_SHA256_LENGTH 64` | r23 independently recounted eight groups of eight and withdrew the r22 findings; r24 confirmed the check's static consistency |

Source artifacts are preserved in the consumer repository as
`.collab/claude-2026-10-07-h5-final-analysis-rNN.md` and matching `.sha256`
files. The relevant explicit packets are
`reviewers/packets/h5-final-analysis-r07-2026-10-07.md`, `r14`, and `r22`;
`reviewers/packets/h5-final-analysis-r23-check-2026-10-07.py` and
`h5-final-analysis-r23-output-2026-10-07.txt` preserve the executable check
and redirected output. The r24 packet includes the original disputed review
text and supporting packet files.

## Verification and impact

The owner extracted the digest literals from the actual packets and checked
their lengths with Python. For r07 and r14, `hashlib.sha256` over the referenced
file bytes equaled the packet literal; the r14 sidecar also matched. For r22,
the owner ran the supplied script from a file. It exited 0 and produced:

```text
PASS index and sidecar SHA256 equal the expected r18 values present in preserved r18 packet
SIDE_SHA256_LENGTH 64
SIDE_SHA256_GROUPS 418da641 d69a6fa8 c04df705 d5a16800 466bdc4b 072435b2 f384c0bf 47cdac7a
```

No digest value or H5 result had to be corrected. The false findings instead
triggered additional rounds to restate hashes in groups, provide literal
sidecar and index excerpts, attach the prior review artifact, and preserve
script/output evidence. Several subsequent conditions concerned hypothetical
future audit packets or the reviewer's lack of file tools rather than a
defect in the H5 analysis. The r24 Opus response returned `VERDICT: ACCEPT`
and supplied standalone closure lines for the remaining audit obligations.
The repository's final documentation check then reported only unrelated
shared-memory budget overages; no H5 review finding remained open.

## Recommended safeguards

- Before treating a digest-length concern as a finding, validate it with
  `re.fullmatch(r"[0-9a-f]{64}", digest)` or eight explicit 8-character groups.
  A manual count alone did not support the major and blocker severities here.
- Separate a reviewer's lack of file access from a claim that an owner-provided
  digest or execution result is impossible. State the access limit without
  asserting a contradiction that a simple length check can disprove.
- Keep the original artifact, sidecar, exact disputed text, and executable
  check/output together for a factual dispute. Make current conditions
  specific; avoid adding prospective conditions for hypothetical packets.
- Classify these cases as reviewer reasoning failures. All cited wrapper
  invocations produced their requested response and checksum artifacts.

No review artifact was edited or deleted, and no commit, push, deployment,
database mutation, or trading action was performed for this report.
