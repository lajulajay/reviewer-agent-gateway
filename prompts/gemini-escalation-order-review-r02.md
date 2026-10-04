Verify your r01 items for the Gemini escalation-order change. They were:
R01-F1 [major]: the trading-strategies edit removes the note about the gateway's older COLLAB.md owner-location sentence, and the gateway diff does not correct that sentence.
R01-F2 [major]: the workstream says kalshi-finance-agent's pin moves only at its next review, so if the pin selects the governing protocol, finance stays on the older rule.
R01-C1: restore the clarification or correct the gateway sentence.
R01-C2: state that kalshi-finance-agent remains on its pinned protocol until its next review.

Packets: `efc1333-owner-location-fix.diff`, an earlier gateway commit (before
this change) that corrected the owner-location sentence; and the updated
workstream file, whose brief now explains what the pin does and does not
govern. You have no tools; review only the text.

Write exactly one line per ID, using the full ID: either `<ID> is resolved.`
or `<ID> remains open: <reason>`. Then label any new defect, following the
output contract.
