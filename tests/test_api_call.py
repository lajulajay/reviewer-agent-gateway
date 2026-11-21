#!/usr/bin/env python3
import importlib.util
import ast
import io
import json
import math
import subprocess
import sys
import re
import tempfile
import threading
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("api_call", ROOT / "api-call.py")
api = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(api)
SECRET = "sk-test-SECRET-value-123"


class Resp(io.BytesIO):
    def __init__(self, body, url="https://api.example.test/v1/responses"):
        super().__init__(body)
        self._url = url

    def geturl(self):
        return self._url

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def policy(style="openai-responses", cap=18.0, **tier):
    t = {"model": "gpt-6.1-sol", "reasoning_effort": "high", "max_output_tokens": 1000,
         "usd_per_1m_input": 2.0, "usd_per_1m_output": 10.0}
    t.update(tier)
    return {"api": {"style": style, "base_url": "https://api.example.test/v1", "keychain_service": "svc",
                    "ledger": "test", "spend_cap_usd": cap, "tiers": {"hard": t}}}


GOOD = ("The packet is internally consistent and the proposed boundary is testable. " * 8 + "\n\nATTESTATION: all actionable findings and conditions are labeled.\n\nVERDICT: ACCEPT")


def openai_reply(text=GOOD, status="completed", usage=(1000, 500), extra=()):
    out = [{"type": "reasoning"}, {"type": "message", "content": [{"type": "output_text", "text": text}]}, *extra]
    r = {"model": "gpt-6.1-sol", "status": status, "output": out}
    if usage:
        r["usage"] = {"input_tokens": usage[0], "output_tokens": usage[1]}
    return r


def sse(*events, done=True):
    body = "".join(f"event: x\ndata: {json.dumps(e)}\n\n" for e in events)
    return (": keep-alive\n\n" + body + ("data: [DONE]\n\n" if done else "")).encode()


def chat_chunks(text=GOOD, finish="stop", usage_in_choice=True, extra_delta=None):
    parts = [text[i:i + 50] for i in range(0, len(text), 50)]
    evs = [{"model": "kimi-k2.6", "choices": [{"index": 0, "delta": {"role": "assistant"}}]}]
    evs += [{"model": "kimi-k2.6", "choices": [{"index": 0, "delta": {"content": p}}]} for p in parts]
    last = {"index": 0, "delta": dict(extra_delta or {}), "finish_reason": finish}
    usage = {"prompt_tokens": 10, "completion_tokens": 5}
    if usage_in_choice:
        last["usage"] = usage
    evs.append({"model": "kimi-k2.6", "choices": [last], **({} if usage_in_choice else {"usage": usage})})
    return evs


class ApiCallTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        api.STATE = self.base / "state"
        api._SECRET.clear()
        (self.base / "prompt.txt").write_text("Review this.\n")
        self.sent = []

    def tearDown(self):
        self.tmp.cleanup()

    def call(self, pol, reply, tier="hard", secret=SECRET):
        (self.base / "policy.json").write_text(json.dumps(pol))
        self.marker = self.base / "sent"
        self.marker.unlink(missing_ok=True)
        (self.base / "out.md").unlink(missing_ok=True)

        class FakeOpener:
            def open(inner, req, timeout):
                self.sent.append((req.full_url, dict(req.header_items()), json.loads(req.data)))
                if isinstance(reply, BaseException):
                    raise reply
                if isinstance(reply, Resp):
                    return reply
                return Resp(json.dumps(reply).encode())

        def fake_key(cfg):
            api._SECRET.append(secret)
            if not all(33 <= ord(c) < 127 for c in secret):
                raise api.Refusal(78, "malformed key")
            return secret

        argv = ["api-call.py", str(self.base / "policy.json"), tier, str(self.base / "prompt.txt"),
                str(self.base / "out.md"), str(self.base / "meta.json"), str(self.marker)]
        err = io.StringIO()
        with mock.patch.object(api, "key", fake_key), mock.patch.object(api, "opener", lambda: FakeOpener()), \
                mock.patch("sys.stderr", err):
            code = api.main(argv)
        self.err = err.getvalue()
        return code

    def entries(self):
        p = api.STATE / "api-spend-test.jsonl"
        return [json.loads(l) for l in p.read_text().splitlines()] if p.exists() else []

    def committed(self):
        p = api.STATE / "api-spend-test.jsonl"
        return api.committed(p.read_text().splitlines()) if p.exists() else 0

    def bound(self):
        payload = json.dumps(self.sent[0][2]).encode()
        return math.ceil((len(payload) + api.FRAMING_TOKENS) * 2.0 + 1000 * 10.0)

    # --- success and request shape
    def test_success_settles_actual_usage_and_sends_no_tools(self):
        self.assertEqual(self.call(policy(), openai_reply()), 0)
        url, headers, body = self.sent[0]
        self.assertTrue(url.endswith("/responses"))
        self.assertEqual((body["tools"], body["store"], body["reasoning"]), ([], False, {"effort": "high"}))
        self.assertEqual(self.committed(), math.ceil(1000 * 2.0 + 500 * 10.0))
        self.assertEqual([e["kind"] for e in self.entries()], ["reserve", "settle"])
        self.assertTrue(self.marker.exists())

    # --- streaming
    def test_requests_ask_for_streaming(self):
        self.call(policy(), openai_reply())
        self.assertIs(self.sent[0][2]["stream"], True)
        self.call(policy("chat-completions"), Resp(sse(*chat_chunks())))
        self.assertIs(self.sent[1][2]["stream"], True)

    def test_streamed_responses_reply_uses_the_final_event(self):
        stream = sse({"type": "response.created", "response": {"status": "in_progress"}},
                     {"type": "response.output_text.delta", "delta": "partial"},
                     {"type": "response.completed", "response": openai_reply()}, done=False)
        self.assertEqual(self.call(policy(), Resp(stream)), 0)
        self.assertEqual((self.base / "out.md").read_text(), GOOD)
        self.assertEqual(self.committed(), math.ceil(1000 * 2.0 + 500 * 10.0))

    def test_streamed_responses_without_final_event_keeps_the_bound(self):
        stream = sse({"type": "response.output_text.delta", "delta": GOOD}, done=False)
        self.assertEqual(self.call(policy(), Resp(stream)), 70)
        self.assertEqual(self.committed(), self.bound())
        self.assertFalse((self.base / "out.md").exists())

    def test_streamed_incomplete_response_is_rejected(self):
        stream = sse({"type": "response.incomplete", "response": openai_reply(status="incomplete")})
        self.assertEqual(self.call(policy(), Resp(stream)), 70)
        self.assertEqual(self.committed(), self.bound())

    def test_streamed_chat_reply_is_assembled_with_usage_from_the_choice(self):
        self.assertEqual(self.call(policy("chat-completions"), Resp(sse(*chat_chunks()))), 0)
        self.assertEqual((self.base / "out.md").read_text(), GOOD)
        self.assertEqual(self.committed(), math.ceil(10 * 2.0 + 5 * 10.0))

    def test_streamed_chat_usage_at_top_level(self):
        self.assertEqual(self.call(policy("chat-completions"), Resp(sse(*chat_chunks(usage_in_choice=False)))), 0)
        self.assertEqual(self.committed(), math.ceil(10 * 2.0 + 5 * 10.0))

    def test_streamed_chat_length_and_tool_calls_are_rejected(self):
        self.assertEqual(self.call(policy("chat-completions"), Resp(sse(*chat_chunks(finish="length")))), 70)
        self.assertIn("finish_reason", self.err)
        self.assertEqual(self.call(policy("chat-completions"),
                                   Resp(sse(*chat_chunks(extra_delta={"tool_calls": [{"id": "t"}]})))), 70)
        self.assertIn("tool call", self.err)

    def test_streamed_chat_two_choices_and_error_event_are_rejected(self):
        evs = chat_chunks() + [{"choices": [{"index": 1, "delta": {"content": "x"}, "finish_reason": "stop"}]}]
        self.assertEqual(self.call(policy("chat-completions"), Resp(sse(*evs))), 70)
        self.assertIn("choices", self.err)
        evs = chat_chunks() + [{"error": {"message": SECRET}}]
        self.assertEqual(self.call(policy("chat-completions"), Resp(sse(*evs))), 70)
        self.assertNotIn(SECRET, self.err)

    def test_streamed_secret_is_redacted_and_malformed_stream_keeps_the_bound(self):
        text = GOOD.replace("testable.", f"testable {SECRET}.", 1)
        self.assertEqual(self.call(policy("chat-completions"), Resp(sse(*chat_chunks(text=text)))), 0)
        self.assertNotIn(SECRET, (self.base / "out.md").read_text())
        before = self.committed()
        self.assertEqual(self.call(policy("chat-completions"), Resp(b"data: {not json\n\n")), 70)
        self.assertGreater(self.committed(), before)
        self.assertIn("full reservation kept", self.err)

    def test_plain_json_fallback_and_its_size_bound(self):
        # A server that ignores "stream" answers with plain JSON (leading blank lines allowed).
        self.assertEqual(self.call(policy(), Resp(b"\n\n" + json.dumps(openai_reply()).encode())), 0)
        self.assertEqual((self.base / "out.md").read_text(), GOOD)
        with mock.patch.object(api, "MAX_REPLY_BYTES", 100):
            self.assertEqual(self.call(policy(), openai_reply()), 70)
            self.assertIn("full reservation kept", self.err)
            self.assertEqual(self.call(policy("chat-completions"), Resp(sse(*chat_chunks()))), 70)
            self.assertIn("full reservation kept", self.err)

    def test_non_object_json_reply_is_rejected(self):
        self.assertEqual(self.call(policy(), Resp(b"[1, 2]")), 70)
        self.assertEqual(self.committed(), self.bound())

    def test_overall_deadline_applies_to_streams(self):
        with mock.patch.dict("os.environ", {"REVIEWER_API_TIMEOUT_SECONDS": "5"}), \
                mock.patch.object(api.time, "time", side_effect=[0, 0] + [100] * 50):
            self.assertEqual(self.call(policy("chat-completions"), Resp(sse(*chat_chunks()))), 70)
        self.assertIn("TimeoutError", self.err)

    def test_chat_request_asks_for_one_choice(self):
        reply = {"model": "k", "choices": [{"finish_reason": "stop", "message": {"content": GOOD}}],
                 "usage": {"prompt_tokens": 10, "completion_tokens": 5}}
        self.assertEqual(self.call(policy("chat-completions"), reply), 0)
        self.assertTrue(self.sent[0][0].endswith("/chat/completions"))
        self.assertEqual(self.sent[0][2]["n"], 1)

    # --- F1 redirects / host
    def test_redirect_handler_refuses(self):
        handler = api._NoRedirect()
        req = mock.Mock(full_url="https://api.example.test/v1/responses")
        with self.assertRaises(urllib.error.HTTPError):
            handler.redirect_request(req, None, 302, "Found", {}, "http://evil.test/")

    def test_response_from_other_host_fails_and_keeps_reservation(self):
        resp = Resp(json.dumps(openai_reply()).encode(), url="https://evil.test/x")
        self.assertEqual(self.call(policy(), resp), 70)
        self.assertEqual(self.committed(), self.bound())

    # --- F3 secrets never echoed
    def test_error_text_is_redacted(self):
        body = io.BytesIO(f'{{"error": "bad key {SECRET}"}}'.encode())
        err = urllib.error.HTTPError("u", 401, "no", {}, body)
        self.assertEqual(self.call(policy(), err), 70)
        self.assertNotIn(SECRET, self.err)
        self.assertNotIn("bad key", self.err)  # untrusted error bodies are never echoed

    def test_json_escaped_secret_is_redacted(self):
        api._SECRET[:] = ['sk-a"b']
        self.assertEqual(api.redact('{"k": "sk-a\\"b"}'), '{"k": "[REDACTED]"}')

    def test_malformed_key_refused_before_send_without_echo(self):
        bad = "sk-bad\nkey"
        self.assertEqual(self.call(policy(), openai_reply(), secret=bad), 78)
        self.assertEqual(self.sent, [])
        self.assertNotIn(bad, self.err)
        self.assertFalse(self.marker.exists())

    def test_unexpected_exception_after_send_is_70_and_redacted(self):
        self.assertEqual(self.call(policy(), RuntimeError(f"boom {SECRET}")), 70)
        self.assertNotIn(SECRET, self.err)

    # --- F4/F5/F6 spend bound, reservation, failures
    def test_bound_counts_every_body_byte(self):
        (self.base / "prompt.txt").write_text("é" * 5000)  # 2 bytes each, JSON-escaped further
        self.call(policy(), openai_reply(usage=None))
        self.assertGreaterEqual(self.committed(), math.ceil(10000 * 2.0 + 1000 * 10.0))

    def test_cap_refuses_before_any_request_and_counts_open_reservations(self):
        api.STATE.mkdir(parents=True)
        (api.STATE / "api-spend-test.jsonl").write_text(
            json.dumps({"kind": "reserve", "id": "a", "micro_usd": 17_990_000}) + "\n")
        self.assertEqual(self.call(policy(), openai_reply()), 79)
        self.assertEqual(self.sent, [])
        self.assertFalse(self.marker.exists())

    def test_concurrent_reservations_cannot_both_pass(self):
        (self.base / "policy.json").write_text(json.dumps(policy(cap=0.02)))
        cfg = api.load(self.base / "policy.json", "hard")
        results = []

        def go():
            try:
                api.reserve(cfg, "hard", 15_000)
                results.append("ok")
            except api.Refusal as exc:
                results.append(exc.code)

        threads = [threading.Thread(target=go) for _ in range(4)]
        [t.start() for t in threads]
        [t.join() for t in threads]
        self.assertEqual(sorted(map(str, results)), ["79", "79", "79", "ok"])

    def test_missing_usage_charges_full_bound(self):
        self.assertEqual(self.call(policy(), openai_reply(usage=None)), 0)
        self.assertEqual(self.committed(), self.bound())

    def test_transport_failure_keeps_full_reservation(self):
        self.assertEqual(self.call(policy(), urllib.error.URLError("down")), 70)
        self.assertEqual(self.committed(), self.bound())

    def test_unbilled_4xx_releases_but_429_and_5xx_keep(self):
        for code, expect_zero in ((401, True), (422, True), (429, False), (500, False)):
            with self.subTest(code=code):
                (api.STATE / "api-spend-test.jsonl").unlink(missing_ok=True)
                self.sent.clear()
                err = urllib.error.HTTPError("u", code, "x", {}, io.BytesIO(b"{}"))
                self.assertEqual(self.call(policy(), err), 70)
                self.assertEqual(self.committed(), 0 if expect_zero else self.bound())

    def test_malformed_ledger_and_bad_numbers_refuse(self):
        api.STATE.mkdir(parents=True)
        (api.STATE / "api-spend-test.jsonl").write_text('{"kind": "settle", "id": "a", "micro_usd": -5}\n')
        self.assertEqual(self.call(policy(), openai_reply()), 78)
        (api.STATE / "api-spend-test.jsonl").unlink()
        for bad in (policy(cap=float("nan")), policy(usd_per_1m_output=-1.0), policy(cap=float("inf"))):
            self.assertEqual(self.call(bad, openai_reply()), 78)
        bad = policy(); bad["api"]["base_url"] = "http://insecure.test/v1"
        self.assertEqual(self.call(bad, openai_reply()), 78)
        self.assertEqual(self.sent, [])

    # --- F9 completion and tools
    def test_incomplete_or_tool_replies_fail(self):
        cases = [
            ("openai-responses", openai_reply(status="incomplete")),
            ("openai-responses", openai_reply(extra=[{"type": "function_call"}])),
            ("chat-completions", {"choices": [{"finish_reason": "length", "message": {"content": "VERDICT: ACCEPT"}}],
                                  "usage": {"prompt_tokens": 1, "completion_tokens": 1}}),
            ("chat-completions", {"choices": [{"finish_reason": "stop", "message": {"content": "x", "function_call": {}}}],
                                  "usage": {"prompt_tokens": 1, "completion_tokens": 1}}),
            ("chat-completions", {"choices": [{"finish_reason": "stop", "message": {"content": "x", "function_call": None}}],
                                  "usage": {"prompt_tokens": 1, "completion_tokens": 1}}),
            ("chat-completions", {"choices": [{"finish_reason": "stop", "message": {"content": "x", "tool_calls": [], "function_call": {}}}],
                                  "usage": {"prompt_tokens": 1, "completion_tokens": 1}}),
            ("chat-completions", {"choices": [{"finish_reason": "stop", "message": {"content": "a"}},
                                              {"finish_reason": "stop", "message": {"content": "b"}}],
                                  "usage": {"prompt_tokens": 1, "completion_tokens": 1}}),
        ]
        for style, reply in cases:
            with self.subTest(style=style, reply=str(reply)[:60]):
                self.assertEqual(self.call(policy(style), reply), 70)
                self.assertFalse((self.base / "out.md").exists())

    def test_substance_rejected_reply_keeps_full_bound(self):
        self.assertEqual(self.call(policy(), openai_reply(text="VERDICT: ACCEPT")), 70)
        self.assertEqual(self.committed(), self.bound())

    def test_substance_rejection_surfaces_the_validator_reason(self):
        text = GOOD.replace("VERDICT: ACCEPT", "VERDICT: ACCEPT WITH CONDITIONS")
        self.assertEqual(self.call(policy(), openai_reply(text=text)), 70)
        self.assertIn("API reply rejected: substance validation failed: an ACCEPT WITH CONDITIONS "
                      "verdict needs at least one labeled C<n> condition", self.err)
        self.assertIn("needs at least one labeled C<n> condition", json.loads((self.base / "meta.json").read_text())["problem"])
        self.assertEqual([e["note"] for e in self.entries() if e["kind"] == "settle"], ["reply rejected: full bound kept"])
        self.assertEqual(self.committed(), self.bound())

    def test_reply_derived_validator_text_is_never_echoed(self):
        # The severity message interpolates reply text; a carriage return would
        # split it, and a NUL-separated key would survive redaction. Neither is echoed.
        split_key = "\x00".join(SECRET)
        text = f"F1 [weird\r{split_key}]\n" + GOOD
        self.assertEqual(self.call(policy(), openai_reply(text=text)), 70)
        meta = (self.base / "meta.json").read_text()
        for out in (self.err, meta):
            self.assertIn("substance validation failed: a finding has a severity other than blocker, major or minor", out)
            self.assertNotIn("weird", out)
            self.assertNotIn("\\u0000", out)
            self.assertNotIn("\x00", out)
        self.assertEqual(self.err.count("\n"), 1)  # one line: the wrapper's diagnostic quotes the last line
        self.assertEqual(self.committed(), self.bound())

    def test_unrecognized_validator_output_is_not_echoed(self):
        cases = [(1, f"Traceback (most recent call last):\nValueError: {SECRET} leaked text\n"),
                 (1, "review has multiple approved verdict lines\nextra\n"),
                 (2, "review is shorter than 4000000 characters\n"),
                 (-9, "")]
        for code, stderr in cases:
            with self.subTest(stderr=stderr[:30]):
                fake = mock.Mock(returncode=code, stderr=stderr)
                with mock.patch.object(api.subprocess, "run", return_value=fake):
                    self.assertEqual(self.call(policy(), openai_reply()), 70)
                self.assertIn(f"substance validation failed: unrecognized validator output (exit {code})", self.err)
                self.assertNotIn("leaked", self.err)
                self.assertNotIn("extra", self.err)
                self.assertNotIn(SECRET, self.err)

    @staticmethod
    def stderr_messages(source):
        """Every print(..., file=sys.stderr) in source: fixed strings, and a count of formatted ones."""
        fixed, formatted = [], 0
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, ast.Call) and getattr(node.func, "id", None) == "print" and \
                    any(k.arg == "file" and ast.unparse(k.value) == "sys.stderr" for k in node.keywords):
                arg = node.args[0]
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    fixed.append(arg.value)
                else:
                    formatted += 1
        return fixed, formatted

    def test_every_fixed_validator_message_is_recognized(self):
        fixed, formatted = self.stderr_messages((ROOT / "reviewer-validate.py").read_text())
        self.assertEqual(sorted(fixed), sorted(api.VALIDATOR_REASONS))
        self.assertEqual(formatted, 2)  # "shorter than" and the severity message, both handled by pattern
        self.assertEqual(api.validator_reason(1, "review is shorter than 400 characters\n"),
                         "review is shorter than 400 characters")

    @staticmethod
    def formatted_reasons(validator):
        """Run validator on replies that trigger its two formatted messages; map each output."""
        severity = "F1 [critical]: x\n" + GOOD
        out = []
        for text in ("short", severity):
            r = subprocess.run([sys.executable, str(validator)], input=text, capture_output=True, text=True)
            out.append(api.validator_reason(r.returncode, r.stderr))
        return out

    def test_formatted_validator_messages_are_recognized(self):
        self.assertEqual(self.formatted_reasons(ROOT / "reviewer-validate.py"),
                         ["review is shorter than 400 characters",
                          "a finding has a severity other than blocker, major or minor"])
        source = (ROOT / "reviewer-validate.py").read_text()
        edits = [('f"review is shorter than {minimum} characters"', 'f"review shorter than {minimum} chars"'),
                 ('f"finding F{m.group(1)} has severity', 'f"F{m.group(1)} has severity')]
        for i, (before, after) in enumerate(edits):
            with self.subTest(edit=after):
                self.assertIn(before, source)
                changed = self.base / "reviewer-validate.py"
                changed.write_text(source.replace(before, after))
                self.assertIn("unrecognized validator output (exit 1)", self.formatted_reasons(changed)[i])

    def test_sync_check_sees_every_quote_style(self):
        source = ("import sys\nprint('single quoted', file=sys.stderr)\nprint(\"a\" \"b\", file=sys.stderr)\n"
                  "print(\"\"\"triple\"\"\", file=sys.stderr)\nprint(f'{1}', file=sys.stderr)\nprint('stdout')\n")
        self.assertEqual(self.stderr_messages(source), (["single quoted", "ab", "triple"], 1))

    def test_error_bodies_are_never_printed(self):
        body = io.BytesIO(json.dumps({"error": {"type": "invalid_request_error", "code": "Review this. leaked prompt"}}).encode())
        self.assertEqual(self.call(policy(), urllib.error.HTTPError("u", 400, "x", {}, body)), 70)
        self.assertIn("HTTP 400", self.err)
        self.assertNotIn("invalid_request_error", self.err)  # no server-supplied field is printed
        self.assertNotIn("leaked prompt", self.err)

    def test_server_values_never_reach_the_ledger(self):
        self.assertEqual(self.call(policy(), openai_reply(status=f"weird {SECRET}")), 70)
        ledger = (api.STATE / "api-spend-test.jsonl").read_text()
        self.assertNotIn(SECRET, ledger)
        self.assertNotIn("weird", ledger)
        self.assertNotIn(SECRET, self.err)

    def test_every_ancestor_directory_is_synced(self):
        synced = []
        with mock.patch.object(api, "_fsync_dir", synced.append):
            self.assertEqual(self.call(policy(), openai_reply()), 0)
        self.assertIn(api.STATE, synced)
        self.assertIn(Path("/"), synced)
        self.assertTrue(all(p in synced for p in api.STATE.parents))

    def test_validation_runs_on_the_redacted_text(self):
        reply = openai_reply(text=SECRET + " " + GOOD)
        self.assertEqual(self.call(policy(), reply), 0)
        self.assertNotIn(SECRET, (self.base / "out.md").read_text())

    def test_rejected_reply_keeps_full_bound_even_with_zero_usage(self):
        self.assertEqual(self.call(policy(), openai_reply(text="", usage=(0, 0))), 70)
        self.assertEqual(self.committed(), self.bound())

    def test_fractional_ledger_amount_refuses(self):
        api.STATE.mkdir(parents=True)
        for amount in (-0.5, 1.5, True, "3"):
            (api.STATE / "api-spend-test.jsonl").write_text(json.dumps({"kind": "settle", "id": "a", "micro_usd": amount}) + "\n")
            self.assertEqual(self.call(policy(), openai_reply()), 78)
        self.assertEqual(self.sent, [])

    def test_unknown_tier_refuses_before_send(self):
        self.assertEqual(self.call(policy(), openai_reply(), tier="routine"), 78)
        self.assertFalse(self.marker.exists())


if __name__ == "__main__":
    unittest.main()
