Round 8: verification of the round-7 fixes. Packet: (1) proposal v6,
(2) the diff fixing your round-7 findings, (3) your raw reviews r01-r07.
You have no tools; review only the text.

Part A — for EVERY item ID below, write exactly one line at the start of a
line in one of these forms, judged against v6 plus the implementation as now
fixed (use the item's original text in its raw review, and your r07 reason):

  <ID> is resolved.
  <ID> remains open: <one-sentence reason>.
  <ID> remains open: inherent — <one-sentence reason>.

Use the "inherent" form only when no reasonable machine check can close the
gap (for example, whether a quote the owner transcribed truly came from the
user); those go to the user for an explicit decision. IDs: R01-F4 R01-F5 R01-F6 R01-F8 R01-F11 R02-F4 R02-F5 R02-F6 R02-F8 R02-F11 R02-F14 R02-C1 R02-C2 R02-C3 R02-C5 R03-F3 R03-F4 R03-F5 R03-F9 R03-F10 R03-C1 R03-C2 R03-C3 R03-C5 R04-F3 R04-F5 R04-F9 R04-F10 R04-C1 R04-C2 R04-C3 R04-C5 R05-F3 R05-F5 R05-F9 R05-F10 R05-F13 R05-C1 R05-C2 R05-C3 R05-C5 R06-F2 R06-F3 R06-F4 R06-F5 R06-F6 R06-F7 R06-F8 R07-F1 R07-F2 R07-F3 R07-F4 R07-F5 R07-F6 R07-F7 R07-C1 R07-C2 R07-C3 

Part B — new findings in the diff, labeled F<n> [blocker|major|minor]: and
conditions C<n>: per the output contract.

Part C — is the tooling ready for the single-session pilot, apart from items
the user accepts as inherent?
