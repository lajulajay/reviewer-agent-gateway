# Scope and evidence (read-only, 2026-08-11)

The agent is paper trading. No code changes are included in this packet.

## Current implementation

`decide_position_action` first exits if current edge is below negative exit cost. It then exits immediately if the fresh LLM direction is opposite the entered side. The reversal branch does not require the exit-cost condition. `exit_reason` is persisted. Paper exits record realized P&L; early exits do not set `outcome` or feed the circuit breaker. Source calibration scores the original recommendation against eventual Kalshi settlement, not the exit decision.

## Exit audit: all 12 exited paper trades

Negative-edge exits (9): realized P&L +$33.0075; hold-to-settlement P&L for the 6 resolved exits +$43.13; all six resolved entered sides won; three rows remain unresolved.

Signal-reversal exits (3): realized P&L -$26.42. Trade 54 (KXUSFLYCAN) realized -$19.97, final result YES, and holding would have produced +$13.29: a $33.26 worse outcome from exiting. Trade 69 (KXU3) realized -$5.69 and trade 60 (KXAAAGASM) realized -$0.76; both were unresolved at audit time.

Across six resolved exits overall: realized exit P&L +$30.09 versus hold-to-settlement +$43.13. Six exits remain unresolved.

## Recent entry losses

- KXAMSAVO trade 53: -$26.28; YES at 58c; model 0.708 vs market 0.56; single stale USDA MARS value 1.10.
- KXAAAGASW trade 63: -$16.92; YES at 44c; model 0.659 vs market 0.42; single weekly GasBuddy proxy.
- KXAAAGASW trade 64: -$15.05; YES at 54c; model 0.702 vs market 0.525; same event and proxy.
- KXAMSAVO trade 68: -$7.31; YES at 80c; same stale USDA source.

## Calibration state

USDA avocado: 1/4 (6 more needed for the configured 10-sample threshold); GasBuddy weekly: 1/1 (9 more); FlightAware: 3/3 (7 more); FRED jobless claims: 5/5 (5 more). No cited source has reached the threshold, so current weights have not changed.

## Exposure, execution, and accounting checks

The two large KXAAAGASW losses were one event and one weekly proxy. Stored risk was $16.92 and $15.05, with an additional $5.02 winning strike in that event; total event risk $37.0. Per-series exposure was below the nominal cap at entry based on stored rows, but event concentration was high.

Recent stored `dollar_risked` generally matches all-in cost implied by stored entry price and contracts. Older July trades show historical mismatches (trade 41: $36.54 stored vs $37.62 modeled; trade 40: $26.10 vs $27.60). The paper P&L ledger is -$114.31 while settled trade rows sum to -$110.40; daily differences occur on 2026-07-20, 07-30, 08-07, and 08-08. Trade 72 has $0.3175 prior realized P&L from a partial action, proving settlement-date rows do not fully represent cash-flow dates; the July differences remain unexplained by the row-level query.

## Decision constraints

Do not change unrelated risk parameters. If recommending a gate, define it narrowly and preserve de-risking. Treat the accounting discrepancy as a caveat for attribution, not automatically as a reason to block a small paper-only policy experiment. State what telemetry/tests must accompany any implementation.
