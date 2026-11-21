# <Title>

Workstream: <YYYY-MM-DD>-<slug>
Owner: <Claude|Copilot|Codex> (<date>, assigned by the user at <commit>)
Status: active
Branch: <branch>
Operational: <yes|no>
Links: <experiment, issue, or document links>

## Brief

<User goal, evidence, invariants, proposed design, open decisions, mutation gate.>

## Decisions

- <YYYY-MM-DD>, user, scope: <what this covers>.
  Quote: "<user's words>". Supersedes: <earlier decision or none>.

## Tasks

<!-- Copilot delegation only (delete otherwise). One row per sub-agent task; the
     coordinator keeps it. Author-models: every model that wrote code in the task,
     the coordinator's included; never auto or Copilot Fusion. State: planned |
     draft | ready | merged | dropped (Branch from draft on, PR for draft, ready,
     merged), or batch for a shared routine round (D6), whose Covers lists its
     members. An integration row I<n> (Branch main@<commit>) covers merged tasks
     and carries all their authors and models (D7). Reviews run with
     --task <Task> and must match its row. -->

| Task | Author | Author-models | Branch | PR | State | Covers |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |

## Reviews

| Round | Reviewer | Tier | Artifact | Verdict |
| :--- | :--- | :--- | :--- | :--- |

## Findings and conditions

<!-- One row per labeled item; generate with: docs-check.py dispositions <artifact> <round>.
     Blocker/condition: verified rNN   (review NN contains the line "<ID> is resolved.")
       | user-decided <date> "<quote naming this ID>"   (inside a Decisions entry of that date with a scope)
     Major/minor: either of the above, fixed <commit in pushed history>,
       or rejected: <the scoped decision or changed fact that makes it inapplicable> -->

| ID | Severity | Disposition | Status |
| :--- | :--- | :--- | :--- |

## Log

- <date>: <event>

<!-- Handoff block (append on transfer; run docs-check.py transfer first):

### Handoff <date> <from> -> <to>

Current state: <one paragraph>
Decisions: <links to Decisions entries in force>
Open obligations: <row IDs still open, with state>
Inventory: `git status --short --ignored`; <n> untracked, <n> ignored; needed by next owner: <committed paths, comma-separated> | none
Runtime observation: <YYYY-MM-DD HH:MM> `<command>` -> <result>   (within two hours) | n/a (not operational) if Operational: no
Restart sequence: <numbered steps>
-->
