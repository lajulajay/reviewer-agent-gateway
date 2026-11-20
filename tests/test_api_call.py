#!/usr/bin/env python3
import importlib.util
import io
import json
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("api_call", ROOT / "api-call.py")
api = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(api)


class Resp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def policy(style="openai-responses", cap=18.0):
    return {"api": {"style": style, "base_url": "https://api.example.test/v1", "keychain_service": "svc",
                    "ledger": "test", "spend_cap_usd": cap,
                    "tiers": {"hard": {"model": "gpt-6.1-sol", "reasoning_effort": "high", "max_output_tokens": 1000,
                                       "usd_per_1m_input": 2.0, "usd_per_1m_output": 10.0}}}}


class ApiCallTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        api.STATE = self.base / "state"
        (self.base / "prompt.txt").write_text("Review this.\n")
        self.sent = []

    def tearDown(self):
        self.tmp.cleanup()

    def run_call(self, pol, reply, tier="hard"):
        (self.base / "policy.json").write_text(json.dumps(pol))

        def fake_urlopen(req, timeout):
            self.sent.append((req.full_url, dict(req.header_items()), json.loads(req.data)))
            if isinstance(reply, Exception):
                raise reply
            return Resp(json.dumps(reply).encode())

        argv = ["api-call.py", str(self.base / "policy.json"), tier, str(self.base / "prompt.txt"),
                str(self.base / "out.md"), str(self.base / "meta.json")]
        with mock.patch.object(api, "key", return_value="sk-test-secret"), \
                mock.patch.object(api.urllib.request, "urlopen", fake_urlopen):
            try:
                return api.main(argv)
            except SystemExit as exc:
                return exc.code

    def ledger(self):
        path = api.STATE / "api-spend-test.jsonl"
        return [json.loads(l) for l in path.read_text().splitlines()] if path.exists() else []

    def test_openai_success_records_cost_and_sends_no_tools(self):
        reply = {"model": "gpt-6.1-sol-2026", "status": "completed",
                 "output": [{"type": "reasoning"}, {"type": "message", "content": [{"type": "output_text", "text": "VERDICT: ACCEPT"}]}],
                 "usage": {"input_tokens": 1000, "output_tokens": 500}}
        self.assertEqual(self.run_call(policy(), reply), 0)
        url, headers, body = self.sent[0]
        self.assertTrue(url.endswith("/responses"))
        self.assertEqual(body["tools"], [])
        self.assertFalse(body["store"])
        self.assertEqual(body["reasoning"], {"effort": "high"})
        self.assertEqual((self.base / "out.md").read_text(), "VERDICT: ACCEPT")
        meta = json.loads((self.base / "meta.json").read_text())
        self.assertAlmostEqual(meta["cost_usd"], 1000 * 2 / 1e6 + 500 * 10 / 1e6)
        self.assertNotIn("sk-test-secret", (self.base / "meta.json").read_text())
        self.assertNotIn("sk-test-secret", (api.STATE / "api-spend-test.jsonl").read_text())

    def test_chat_completions_and_tool_calls_rejected(self):
        reply = {"model": "kimi-k3.1-pro", "choices": [{"finish_reason": "tool_calls",
                 "message": {"content": "", "tool_calls": [{"id": "x"}]}}], "usage": {"prompt_tokens": 10, "completion_tokens": 5}}
        self.assertEqual(self.run_call(policy("chat-completions"), reply), 70)
        self.assertTrue(self.sent[0][0].endswith("/chat/completions"))
        self.assertEqual(len(self.ledger()), 1)

    def test_spend_cap_refuses_before_any_request(self):
        api.STATE.mkdir(parents=True)
        (api.STATE / "api-spend-test.jsonl").write_text(json.dumps({"cost_usd": 17.995}) + "\n")
        self.assertEqual(self.run_call(policy(), {}), 79)
        self.assertEqual(self.sent, [])

    def test_unknown_usage_is_charged_worst_case(self):
        reply = {"output": [{"type": "message", "content": [{"type": "output_text", "text": "ok"}]}]}
        self.assertEqual(self.run_call(policy(), reply), 0)
        self.assertTrue(self.ledger()[0]["estimated"])
        self.assertGreaterEqual(self.ledger()[0]["cost_usd"], 1000 * 10 / 1e6)

    def test_http_4xx_is_counted_failure_without_charge(self):
        err = urllib.error.HTTPError("u", 401, "no", {}, io.BytesIO(b'{"error":"bad key"}'))
        self.assertEqual(self.run_call(policy(), err), 70)
        self.assertEqual(self.ledger()[0]["cost_usd"], 0.0)

    def test_bad_policy_and_tier_refuse_before_request(self):
        self.assertEqual(self.run_call(policy(), {}, tier="routine"), 78)
        bad = policy(); bad["api"]["base_url"] = "http://insecure"
        self.assertEqual(self.run_call(bad, {}), 78)
        self.assertEqual(self.sent, [])


if __name__ == "__main__":
    unittest.main()
