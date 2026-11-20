#!/usr/bin/env python3
import importlib.util
import io
import json
import math
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


def openai_reply(text="VERDICT: ACCEPT", status="completed", usage=(1000, 500), extra=()):
    out = [{"type": "reasoning"}, {"type": "message", "content": [{"type": "output_text", "text": text}]}, *extra]
    r = {"model": "gpt-6.1-sol", "status": status, "output": out}
    if usage:
        r["usage"] = {"input_tokens": usage[0], "output_tokens": usage[1]}
    return r


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

    def test_chat_request_asks_for_one_choice(self):
        reply = {"model": "k", "choices": [{"finish_reason": "stop", "message": {"content": "VERDICT: ACCEPT"}}],
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
        self.assertIn("[REDACTED]", self.err)

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

    def test_unknown_tier_refuses_before_send(self):
        self.assertEqual(self.call(policy(), openai_reply(), tier="routine"), 78)
        self.assertFalse(self.marker.exists())


if __name__ == "__main__":
    unittest.main()
