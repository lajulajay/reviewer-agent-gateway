Round 5 of an adversarial review. Packet: (1) proposal v5, (2) the workstream
record with dispositions of all round-1 to round-4 findings and the user's
decisions, (3) your raw round-4 review. You have no tools; review only the
text.

Constraints set by the user: sprawl is a central problem, so mechanisms must
reduce or bound text and not add a file per event; prefer a policy the single
user can own over new machinery. v5 scopes its guarantees to a single-session
pilot in one clean, paused repository.

1. For each round-4 finding F1..F12 and condition C1..C6, state whether v4
   satisfies it within the pilot scope (v5 marks each change R04-F<n>); challenge any overclaim.
2. Find defects v5 introduces.
3. Is v5 ready for that pilot? If not, name the smallest set of changes.

Format every finding as `F<n> [blocker|major|minor]: <text>` with a concrete
failure scenario and recommended change, and every condition of acceptance as
`C<n>: <text>`. End your findings with the line
`ATTESTATION: all actionable findings and conditions are labeled.`
