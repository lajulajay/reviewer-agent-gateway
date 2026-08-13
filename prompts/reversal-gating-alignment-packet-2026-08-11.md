# Scope and evidence (read-only, 2026-08-11)

The agent is paper trading. No code changes are included in this packet.

## Current implementation

`decide_position_action` in `agent/src/econ_agent/edge.py` first exits when
current edge is below the negative exit cost. It then exits immediately when a
fresh LLM direction is opposite the entered side. The reversal branch does not
require the exit-cost condition. `exit_reason` is persisted. Paper exits record
realized P&L; early exits do not set `outcome` or feed the circuit breaker.
Source calibration scores the original recommendation against eventual
settlement, not the exit decision.

## Completed read-only exit audit

All 12 exited paper trades were checked against current Kalshi results.

Negative-edge exits (9):
- realized P&L: +$33.0075;
- six resolved cases had hold-to-settlement P&L of +$43.13 and all six entered
  sides ultimately won;
- three cases remain unresolved.

Signal-reversal exits (3):
- realized P&L: -$26.42;
- trade 54, KXUSFLYCAN, realized -$19.97; final result YES; holding would have
  produced +$13.29, making the exit $33.26 worse;
- trade 69, KXU3, realized -$5.69; unresolved;
- trade 60, KXAAAGASM, realized -$0.76; unresolved.

Across six resolved exits overall, realized exit P&L was +$30.09 versus
hold-to-settlement +$43.13. Six exits remain unresolved.

## Recent entry losses and concentration

- KXAMSAVO trade 53: -$26.28; YES at 58c; model 0.708 versus market 0.56;
  single stale USDA MARS value 1.10.
- KXAAAGASW trade 63: -$16.92; YES at 44c; model 0.659 versus market 0.42;
  single weekly GasBuddy proxy.
- KXAAAGASW trade 64: -$15.05; YES at 54c; model 0.702 versus market 0.525;
  same event and same proxy.
- KXAMSAVO trade 68: -$7.31; YES at 80c; same stale USDA source.

The two large weekly-gas losses were not independent. Stored risk was $16.92
and $15.05, with an additional $5.02 winning strike in that event; event risk
was about $37. Per-series exposure was below the nominal cap based on stored
rows, but event concentration was high.

## Calibration and accounting caveats

Avocado calibration is 1/4, GasBuddy weekly 1/1, FlightAware 3/3, and FRED
jobless claims 5/5. None has reached the configured 10-observation learned-
weight threshold, so these results are diagnostic only.

Recent stored entry costs generally match all-in cost implied by entry price
and contracts. Older July rows show historical cost mismatches. Paper P&L
ledger is -$114.31 while settled trade rows sum to -$110.40; partial
realization timing explains part of this, while July differences remain
unexplained by the row-level query.

## Constraints

- Do not change unrelated risk parameters.
- Preserve negative-edge exits, scale-downs, and all de-risking paths.
- If supporting a reversal gate, keep it narrow and paper-only/observable first.
- Treat the accounting discrepancy as an attribution caveat, not automatically
  as a blocker for a small paper-policy experiment.
- Recommend tests and telemetry required before implementation is considered
  complete.
