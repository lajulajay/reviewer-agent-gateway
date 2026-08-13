# Implementation review: paper-only LLM reversal gate

Review the supplied implementation packet adversarially. Do not edit files or
use tools beyond the explicit packet. Confirm or reject these invariants:

1. A standalone opposite-side LLM direction is suppressed only in paper mode
   and only when the feature flag is enabled.
2. A negative edge below `-exit_cost_edge` still exits before any reversal gate.
3. Real positions retain prior unconditional reversal behavior.
4. Every suppressed paper reversal writes durable, queryable AgentAudit context
   without a schema migration.
5. Scaling and unrelated risk parameters are untouched.
6. Tests materially prove the changed behavior and the real-mode guard.

Call out concrete defects, missing tests, telemetry gaps, or deployment risks.
End with exactly one line: VERDICT: ACCEPT, VERDICT: ACCEPT WITH CONDITIONS,
or VERDICT: REJECT.
