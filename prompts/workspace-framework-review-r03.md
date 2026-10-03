Round 3 of an adversarial review. Packet: (1) proposal v3, (2) the workstream
record with dispositions of all round-1 and round-2 findings, (3) your raw
round-2 review. You have no tools; review only the text.

The user has set a design constraint for v3: sprawl is a central problem, so
every mechanism must reduce or bound text rather than add files, and where a
single user can own a policy, prefer the policy over new machinery. Judge v3
against that constraint as well as correctness. Do not recommend new
machinery unless a concrete failure scenario shows a policy cannot work.

1. For each round-2 condition C1..C6 and blocker (F1, F2, F6, F15), state
   whether v3 satisfies it, and challenge any disposition that claims more
   than v3 delivers.
2. Find defects v3 introduces, especially in: the tier budgets and eviction
   rule, STATUS.md as RAM, the compaction pass, the three checks, and the
   agent-cache tier.
3. Is v3 ready for a pilot in one clean, paused repository? If not, what is
   the smallest set of changes that would make it ready?

Format every finding as `F<n> [blocker|major|minor]: <text>` with a concrete
failure scenario and recommended change, and every condition of acceptance as
`C<n>: <text>`. End your findings with the line
`ATTESTATION: all actionable findings and conditions are labeled.`
