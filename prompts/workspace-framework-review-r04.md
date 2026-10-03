Round 4 of an adversarial review. Packet: (1) proposal v4, (2) the workstream
record with dispositions of all round-1 to round-3 findings and the user's
decisions, (3) your raw round-3 review. You have no tools; review only the
text.

Constraints set by the user: sprawl is a central problem, so mechanisms must
reduce or bound text and not add a file per event; prefer a policy the single
user can own over new machinery. v4 scopes its guarantees to a single-session
pilot in one clean, paused repository.

1. For each round-3 finding F1..F11 and condition C1..C6, state whether v4
   satisfies it within the pilot scope; challenge any overclaim.
2. Find defects v4 introduces.
3. Is v4 ready for that pilot? If not, name the smallest set of changes.

Format every finding as `F<n> [blocker|major|minor]: <text>` with a concrete
failure scenario and recommended change, and every condition of acceptance as
`C<n>: <text>`. End your findings with the line
`ATTESTATION: all actionable findings and conditions are labeled.`
