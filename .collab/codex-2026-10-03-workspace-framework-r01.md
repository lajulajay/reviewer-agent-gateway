# Codex review

Owner: claude
Requested model: hard
Selected model: gpt-6-sol
Reasoning effort: high
Resolved model(s): not reported by codex exec
CLI version: codex-cli 0.159.3
Blocked tool attempts: 0

## Blockers

1. **D1 does not preserve the anti-softening guarantee.** A reviewer can write three conditions in prose; the owner can enter two mild rows, omit the third, and still pass `docs-check`. The checksum proves only that a selected file matches its sidecar. Both can be replaced together, and nothing checks that every condition was captured or that its wording survived. **Change:** keep the raw review in git, record its commit and digest, and quote each verdict and condition exactly beside its disposition. Require an explicit completeness check before closing a workstream.

2. **The ownership protocol cannot prevent concurrent edits.** Two worktrees do not share an untracked `.agent-session` lock. Two sessions can read the same `Owner:` line, both proceed, and later overwrite or merge conflicting `STATUS.md` rows and workstream handoffs. A PID is meaningful only on its host and can be reused. Restricting process docs to `main` adds another race: an active branch may continue using an older protocol after `main` changes. **Change:** treat the lock as a warning, require separate worktrees, and make ownership changes explicit assignments against a known repository revision. Serialize work on the same workstream; avoid a shared, hand-edited status row for concurrent workstreams.

3. **The migration can erase the only copy of current work or disrupt live operations.** Archiving `COLLAB.md` and replacing `CLAUDE.md` while thousands of lines are uncommitted can omit a handoff, mix unfinished notes into a supposedly frozen record, or change instructions an active owner relies on. Moving gateway paths or generating user-level stubs can also change what running sessions and reviewer wrappers load. “Paper mode” does not make cutover instructions harmless. **Change:** leave active dirty repos untouched until their owner inventories and preserves the exact working tree, confirms current runtime state, and hands off. Migrate from that preserved revision; verify loader and wrapper behavior before changing entry points.

## Major

4. **“Committed or declared” still leaves invisible state.** If a session lists dirty documentation in a dirty `STATUS.md` and closes, a second worktree sees neither. If it commits only `STATUS.md`, the listed content still exists solely in the first working tree. This makes the §1 uncommitted-documentation problem worse by giving it an apparent disposition. **Change:** a handoff must commit the needed content or place it in a shared, durable artifact. A pending-work entry should identify its location and base revision, and must not count as a completed handoff.

5. **The proposed source precedence can turn stale text into operational authority.** `STATUS.md` ranks above experiment records and operations knowledge, yet it is an overwritten summary that may be seven days old. An owner could follow its “next safe actions” after a live cutover or a rejected review. Code and production data also cannot establish user approval or resolve review conditions. **Change:** distinguish observed runtime facts, approved decisions, review obligations, and summaries. Require a current runtime check for operational actions and a cited decision or review record for authorization.

6. **`docs-check` misses the important invariant and several rules are easy to game.** A fresh timestamp can conceal stale content; a changed status can avoid the active-workstream check; a forbidden phrase can be paraphrased; a checksum and archive manifest can be updated with the files they purport to protect. A generated experiment index can faithfully reproduce a stale manifest, as econ’s H1 evidence already suggests. Line limits and a weekly report risk producing noise while unresolved conditions pass. **Change:** make the key closure check trace every review verdict and condition to an exact disposition and, where relevant, a fixing commit or user decision. Use machine checks for objective properties; require runtime reconciliation for experiment status. Do not describe self-maintained hashes as immutability.

7. **Centralization can create a new drift point.** Shared platform facts such as cron budgets, fees, secret locations, and venue behavior can differ by repo and change independently. An unversioned gateway standard may change while another repo’s branch still relies on the old wording. Cross-repo links also mean the repository alone no longer contains everything needed to resume, contrary to the stated goal. **Change:** keep volatile operational facts in their owning repo, link to a versioned shared standard, and state how an active branch adopts a standards change.

8. **The review evidence calls for triage before restructuring.** Roughly 289 artifacts have conditional acceptance, 32 are rejections, and 82 have no verdict. Moving them into files and tables will not determine which conditions remain open. The fact that only two artifacts have an `Owner:` line also gives the proposed owner-versus-reviewer check little evidentiary basis; it may reject a legitimate later ownership change while missing an omitted condition. **Change:** identify open obligations and missing verdicts in active work first. Check ownership at the review round, rather than comparing one current owner with every historical reviewer.

9. **Initializing git in `trading-strategies` is a separate risk decision.** Its 3,594-line untracked `COLLAB.md` and unknown generated files or secrets could be added to a first commit or remote by mistake. **Change:** audit the directory and ignore rules before choosing what the initial repository records; do not make git initialization a prerequisite for the documentation pilot.

## Minor

10. **The framework is too large for the evidence of what is failing.** Five repos and two interchangeable owners do not yet justify generated user stubs, a platform knowledge layer, multiple document classes, frozen archive moves, global memory rewrites, a weekly routine, and a blocking hook. Each adds a place where instructions can diverge or fail to load. **Change:** start with a short neutral repo entry point, one current handoff per active workstream, tracked raw reviews with exact condition quotations and dispositions, and a small check for broken links and missing artifacts. Defer the other layers until a pilot shows a specific need.

11. **The evidence points to a workflow failure the file layout cannot fix.** Large `COLLAB.md` changes with only 10–14 commits, stale memory restored after a concurrent-session wipe, and a stale experiment registry show that recording and reconciliation are not happening reliably. Splitting those files may make omissions less visible. **Change:** define a clear handoff event that verifies the working tree, open review obligations, and current operational state, and require that event before another owner resumes.

VERDICT: REJECT