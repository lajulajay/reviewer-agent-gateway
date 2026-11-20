#!/usr/bin/env python3
"""One tool-free review call through a provider's HTTP API, with a spend cap.

  api-call.py POLICY_JSON TIER PROMPT_FILE OUT_TEXT OUT_META

POLICY_JSON's "api" object names the endpoint style ("openai-responses" or
"chat-completions"), base URL, Keychain service holding the key, spend cap
and ledger name, and per-tier model, effort, max output tokens and prices
(USD per 1M tokens). The key is read from the macOS Keychain inside this
process and sent only in the Authorization header; it is never written to
disk, argv, logs or artifacts. No tools are offered to the model.

Before the call, the worst case (all input + max output tokens at list price)
plus the ledger's recorded spend must stay within the cap. After the call the
actual cost from reported usage is appended to the ledger
(~/.local/state/reviewer-gateway/api-spend-<ledger>.jsonl, outside any repo).

Exit: 0 ok; 64 usage; 78 not configured / key missing (before any request);
79 spend cap refusal (before any request); 70 request sent but failed.
"""

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

STATE = Path(os.environ.get("REVIEWER_API_STATE_DIR", Path.home() / ".local/state/reviewer-gateway"))


def die(code, msg):
    print(msg, file=sys.stderr)
    sys.exit(code)


def load(policy_path, tier):
    try:
        api = json.loads(Path(policy_path).read_text())["api"]
        t = api["tiers"][tier]
        cfg = {
            "style": api["style"], "base_url": api["base_url"].rstrip("/"),
            "keychain_service": api["keychain_service"], "ledger": api["ledger"],
            "spend_cap_usd": float(api["spend_cap_usd"]), "model": t["model"],
            "effort": t.get("reasoning_effort"), "max_output_tokens": int(t["max_output_tokens"]),
            "usd_in": float(t["usd_per_1m_input"]), "usd_out": float(t["usd_per_1m_output"]),
        }
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        die(78, f"API review policy is incomplete for tier {tier!r}: {exc}")
    if cfg["style"] not in ("openai-responses", "chat-completions"):
        die(78, f"unknown API style {cfg['style']!r}")
    if not cfg["base_url"].startswith("https://"):
        die(78, "API base_url must be https")
    return cfg


def ledger_path(cfg):
    return STATE / f"api-spend-{cfg['ledger']}.jsonl"


def spent(cfg):
    path = ledger_path(cfg)
    if not path.exists():
        return 0.0
    total = 0.0
    for line in path.read_text().splitlines():
        if line.strip():
            total += float(json.loads(line)["cost_usd"])
    return total


def key(cfg):
    if sys.platform != "darwin":
        die(78, "API reviews read keys from the macOS Keychain")
    r = subprocess.run(["security", "find-generic-password", "-a", os.environ.get("USER", ""),
                        "-s", cfg["keychain_service"], "-w"], capture_output=True, text=True)
    k = r.stdout.strip()
    if r.returncode != 0 or not k:
        die(78, f"no Keychain item {cfg['keychain_service']!r}; store the key with security add-generic-password")
    return k


def request(cfg, text):
    if cfg["style"] == "openai-responses":
        body = {"model": cfg["model"], "input": text, "max_output_tokens": cfg["max_output_tokens"],
                "store": False, "tools": []}
        if cfg["effort"]:
            body["reasoning"] = {"effort": cfg["effort"]}
        return cfg["base_url"] + "/responses", body
    body = {"model": cfg["model"], "messages": [{"role": "user", "content": text}],
            "max_tokens": cfg["max_output_tokens"]}
    return cfg["base_url"] + "/chat/completions", body


def parse(cfg, data):
    if cfg["style"] == "openai-responses":
        parts = [c.get("text", "") for item in data.get("output", []) if item.get("type") == "message"
                 for c in item.get("content", []) if c.get("type") == "output_text"]
        tools = [item.get("type") for item in data.get("output", [])
                 if item.get("type") not in ("message", "reasoning")]
        u = data.get("usage") or {}
        return "".join(parts), tools, u.get("input_tokens"), u.get("output_tokens"), data.get("model"), data.get("status")
    choice = (data.get("choices") or [{}])[0]
    msg = choice.get("message") or {}
    tools = ["tool_calls"] if msg.get("tool_calls") else []
    u = data.get("usage") or {}
    return msg.get("content") or "", tools, u.get("prompt_tokens"), u.get("completion_tokens"), data.get("model"), choice.get("finish_reason")


def main(argv):
    if len(argv) != 6:
        die(64, __doc__.strip().splitlines()[2].strip())
    policy, tier, prompt_file, out_text, out_meta = argv[1:]
    cfg = load(policy, tier)
    text = Path(prompt_file).read_text()
    # Conservative token bound: ~3 characters per token for code-heavy packets.
    est_in = len(text) // 3 + 1
    worst = est_in * cfg["usd_in"] / 1e6 + cfg["max_output_tokens"] * cfg["usd_out"] / 1e6
    already = spent(cfg)
    if already + worst > cfg["spend_cap_usd"]:
        die(79, f"API spend cap: ${already:.2f} spent + ${worst:.2f} worst case exceeds the "
                f"${cfg['spend_cap_usd']:.2f} cap for {cfg['ledger']}; only the user may raise it")
    url, body = request(cfg, text)
    req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST", headers={
        "Content-Type": "application/json", "Authorization": f"Bearer {key(cfg)}"})
    timeout = int(os.environ.get("REVIEWER_API_TIMEOUT_SECONDS", "900"))
    start = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        detail = exc.read()[:500].decode(errors="replace")
        record(cfg, tier, 0, 0, worst_case=True, note=f"HTTP {exc.code}")
        die(70, f"API request failed: HTTP {exc.code}: {detail}")
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        record(cfg, tier, 0, 0, worst_case=True, note=f"transport error: {exc}")
        die(70, f"API request failed: {exc}")
    reply, tools, tin, tout, served, status = parse(cfg, data)
    cost = record(cfg, tier, tin, tout, worst_case=tin is None or tout is None)
    meta = {"route": "api", "endpoint": url, "selected_model": cfg["model"], "served_model": served,
            "reasoning_effort": cfg["effort"], "status": status, "input_tokens": tin, "output_tokens": tout,
            "cost_usd": round(cost, 6), "ledger_spent_usd": round(already + cost, 6),
            "spend_cap_usd": cfg["spend_cap_usd"], "tool_items": tools, "elapsed_seconds": round(time.time() - start, 1)}
    Path(out_meta).write_text(json.dumps(meta))
    if tools:
        die(70, f"API response contained tool items {tools}; reviews must be tool-free")
    if not reply.strip():
        die(70, f"API returned no text (status {status})")
    Path(out_text).write_text(reply)
    return 0


def record(cfg, tier, tin, tout, worst_case=False, note=None):
    """Append the call's cost to the ledger; unknown usage is charged at the worst case."""
    if worst_case:
        cost = cfg["max_output_tokens"] * cfg["usd_out"] / 1e6 + (tin or 0) * cfg["usd_in"] / 1e6
        if note and note.startswith("HTTP 4"):
            cost = 0.0  # rejected before generation (auth, validation, quota)
    else:
        cost = tin * cfg["usd_in"] / 1e6 + tout * cfg["usd_out"] / 1e6
    STATE.mkdir(parents=True, exist_ok=True)
    entry = {"at": datetime.now(timezone.utc).isoformat(), "tier": tier, "model": cfg["model"],
             "input_tokens": tin, "output_tokens": tout, "cost_usd": round(cost, 6), "estimated": worst_case}
    if note:
        entry["note"] = note
    with ledger_path(cfg).open("a") as fh:
        fh.write(json.dumps(entry) + "\n")
    return cost


if __name__ == "__main__":
    sys.exit(main(sys.argv))
