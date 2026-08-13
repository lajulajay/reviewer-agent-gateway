# Change summary

`kalshi-econ-agent` is currently paper trading. The owner approved a narrow
paper-only reversal-exit experiment after Gemini's design review.

Implemented delta:

- `Settings.gated_reversal_exits` defaults true.
- The runner passes `gate_reversal_exits = paper_trading_mode AND
  gated_reversal_exits` to `decide_position_action`.
- With the gate enabled, an opposite-side LLM direction inside the existing
  escape-cost band returns hold with reason
  `reversal_gated_edge_within_cost_bounds`.
- The negative-edge exit check remains first and unchanged.
- The runner writes an `AgentAudit` event with category `position_management`,
  reason `reversal_suppressed`, and JSON detail containing entered side, LLM
  direction, current edge, exit cost, model/market probabilities, and quote.
- No migration or risk-parameter change was made.
- Tests cover in-band hold, negative-edge precedence, no scaling on a gated
  reversal, telemetry payload, manager-level audit persistence, and the guard
  that real mode retains unconditional reversal behavior.

Verification already run:

`python -m pytest tests/ -q` → 255 passed.
