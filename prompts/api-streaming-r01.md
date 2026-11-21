# Review: streamed replies on the gateway API route (based on ab1ba95)

Owner: Claude. Reviewer: Kimi via the Moonshot API. Read-only; review only
the attached material. No tools.

Problem: a non-streamed Kimi hard-tier review (kimi-k3.1-pro) was closed by
Moonshot after 601 s with no reply (RemoteDisconnected); long reasoning on a
large packet exceeds the provider's limit for a silent connection.

Change (attached diff and full api-call.py): both request styles set
`stream: true`. `read_reply()` reads server-sent events line by line and
rebuilds the same object the non-streamed path returned, which then passes
the unchanged `parse()` checks (completion status / single choice with
finish_reason stop / no tool items or calls), redaction, substance
validation, and reserve-then-settle accounting. OpenAI Responses: the final
`response.completed|incomplete|failed` event's `response` is used; no final
event is a rejected reply. Chat completions: deltas are concatenated per
choice index; tool_calls / function_call deltas, finish_reason, and usage
(top-level or, as Moonshot sends it, inside the choice) are kept; an `error`
event becomes a rejected choice. A server that ignores `stream` and sends
plain JSON is accepted. Limits: 32 MiB reply, 300 s socket read timeout,
overall deadline REVIEWER_API_TIMEOUT_SECONDS (default now 1800 s).
Malformed streams raise inside the request block, so the full reservation is
kept (exit 70). 11 new tests; all 100 unit tests and the wrapper smoke test
pass.

Check: correctness of the stream reassembly for both APIs as documented by
OpenAI and Moonshot; that no path lets an incomplete, tool-using, multi-choice
or truncated reply be accepted; that the key cannot leak through new paths;
that spend accounting is unchanged (rejected replies keep the full bound);
and that the deadline and size limits hold. Label findings
`F1 [blocker|major|minor]: ...` and conditions `C1: ...`.
Include `ATTESTATION: all actionable findings and conditions are labeled.`
The last non-empty line must be exactly one of `VERDICT: ACCEPT`,
`VERDICT: ACCEPT WITH CONDITIONS` or `VERDICT: REJECT`.
