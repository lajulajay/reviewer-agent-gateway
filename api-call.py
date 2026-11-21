#!/usr/bin/env python3
"""One tool-free review call through a provider's HTTP API, with a spend cap.

  api-call.py POLICY_JSON TIER PROMPT_FILE OUT_TEXT OUT_META SENT_MARKER

POLICY_JSON's "api" object names the endpoint style ("openai-responses" or
"chat-completions"), https base URL, Keychain service holding the key, spend
cap and ledger name, and per-tier model, effort, max output tokens and list
prices (USD per 1M tokens). No tools are offered to the model.

Key handling: read from the macOS Keychain inside this process, validated
without being echoed, sent only in the Authorization header of one request to
the configured host. Redirects are refused, and every message this script
emits is redacted.

Spend cap: under an exclusive lock on the ledger, the full bound for this call
(every UTF-8 byte of the request body as one input token, plus max output
tokens, at list price) is reserved before sending, and only if all recorded
spend and open reservations plus that bound fit the cap. After the reply the
reservation is settled at the reported usage. It is released to zero only for
HTTP 400/401/403/404/422, where the provider rejected the request before any
generation; every other failure, crash or missing usage keeps the full
reservation. The ledger lives in ~/.local/state/reviewer-gateway, outside
every repository.

SENT_MARKER is created immediately before the request is sent, so the caller
knows whether the model may have been reached.

Exit: 0 ok; 64 usage; 78 refused before sending (policy, key, ledger, local
error); 79 spend cap refusal; 70 the request may have been sent and the review
failed.
"""

import fcntl
import json
import math
import os
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path

STATE = Path.home() / ".local/state/reviewer-gateway"
MICRO = 1_000_000  # ledger amounts are integer micro-dollars, rounded up
FRAMING_TOKENS = 1024  # request/message framing allowance on top of the body
UNBILLED_HTTP = (400, 401, 403, 404, 422)
_SECRET = []


class Refusal(Exception):
    def __init__(self, code, msg):
        super().__init__(msg)
        self.code = code


def redact(text):
    text = str(text)
    for s in _SECRET:
        if s:
            for form in (s, json.dumps(s)[1:-1]):
                text = text.replace(form, "[REDACTED]")
    return text


def _positive(value, label, allow_zero=False):
    v = float(value)
    if not math.isfinite(v) or v < 0 or (v == 0 and not allow_zero):
        raise ValueError(f"{label} must be a finite {'non-negative' if allow_zero else 'positive'} number")
    return v


def load(policy_path, tier):
    try:
        api = json.loads(Path(policy_path).read_text())["api"]
        t = api["tiers"][tier]
        cfg = {
            "style": api["style"], "base_url": api["base_url"].rstrip("/"),
            "keychain_service": api["keychain_service"], "ledger": api["ledger"],
            "cap_micro": math.floor(_positive(api["spend_cap_usd"], "spend_cap_usd") * MICRO),
            "model": t["model"], "effort": t.get("reasoning_effort"),
            "max_output_tokens": int(_positive(t["max_output_tokens"], "max_output_tokens")),
            "usd_in": _positive(t["usd_per_1m_input"], "usd_per_1m_input"),
            "usd_out": _positive(t["usd_per_1m_output"], "usd_per_1m_output"),
        }
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise Refusal(78, f"API review policy is incomplete for tier {tier!r}: {exc}")
    if cfg["style"] not in ("openai-responses", "chat-completions"):
        raise Refusal(78, f"unknown API style {cfg['style']!r}")
    url = urllib.parse.urlsplit(cfg["base_url"])
    if url.scheme != "https" or not url.hostname:
        raise Refusal(78, "API base_url must be an https URL with a host")
    if not cfg["ledger"].replace("-", "").isalnum():
        raise Refusal(78, "ledger name must be alphanumeric")
    cfg["host"] = url.hostname
    return cfg


def micro(tokens_in, tokens_out, cfg):
    """Cost in micro-dollars, rounded up."""
    return math.ceil(tokens_in * cfg["usd_in"] + tokens_out * cfg["usd_out"])


def ledger_path(cfg):
    return STATE / f"api-spend-{cfg['ledger']}.jsonl"


def committed(lines):
    """Micro-dollars spent or reserved: settled amounts, else open reservations."""
    reserved, settled = {}, {}
    for n, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            e = json.loads(line)
            amount = e["micro_usd"]
            if type(amount) is not int or amount < 0 or e["kind"] not in ("reserve", "settle"):
                raise ValueError
            (reserved if e["kind"] == "reserve" else settled)[e["id"]] = amount
        except (ValueError, KeyError, TypeError, json.JSONDecodeError):
            raise Refusal(78, f"ledger line {n} is malformed; refusing to guess spend")
    return sum(settled.get(i, amount) for i, amount in reserved.items()) + \
        sum(a for i, a in settled.items() if i not in reserved)


def append(fh, entry):
    fh.write(json.dumps(entry) + "\n")
    fh.flush()
    os.fsync(fh.fileno())


def _fsync_dir(path):
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _durable_chain():
    """STATE and every ancestor up to the filesystem root: any of them may have
    just been created by mkdir(parents=True), so all their entries are synced."""
    return [STATE, *STATE.parents]


def reserve(cfg, tier, bound):
    STATE.mkdir(parents=True, exist_ok=True, mode=0o700)
    call_id = uuid.uuid4().hex
    with ledger_path(cfg).open("a+") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        # Under the lock, before any reservation is trusted or sent: make the
        # directory entries durable every time, so a crash or restart between
        # creation and use can never drop the ledger's pathname.
        for directory in _durable_chain():
            _fsync_dir(directory)
        fh.seek(0)
        already = committed(fh.read().splitlines())
        if already + bound > cfg["cap_micro"]:
            raise Refusal(79, f"API spend cap: ${already / MICRO:.4f} spent or reserved + ${bound / MICRO:.4f} bound "
                              f"exceeds the ${cfg['cap_micro'] / MICRO:.2f} cap for {cfg['ledger']}; only the user may raise it")
        append(fh, {"kind": "reserve", "id": call_id, "micro_usd": bound, "tier": tier, "model": cfg["model"],
                    "at": datetime.now(timezone.utc).isoformat()})
    return call_id, already


def settle(cfg, call_id, amount, note):
    with ledger_path(cfg).open("a") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        append(fh, {"kind": "settle", "id": call_id, "micro_usd": amount, "note": redact(note)[:120],
                    "at": datetime.now(timezone.utc).isoformat()})


def key(cfg):
    if sys.platform != "darwin":
        raise Refusal(78, "API reviews read keys from the macOS Keychain")
    r = subprocess.run(["security", "find-generic-password", "-a", os.environ.get("USER", ""),
                        "-s", cfg["keychain_service"], "-w"], capture_output=True, text=True)
    k = r.stdout.strip()
    if r.returncode != 0 or not k:
        raise Refusal(78, f"no Keychain item {cfg['keychain_service']!r}; store the key with keychain-store.py")
    _SECRET.append(k)
    if not all(33 <= ord(c) < 127 for c in k):
        raise Refusal(78, f"Keychain item {cfg['keychain_service']!r} holds a malformed key (non-printable or non-ASCII characters)")
    return k


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise urllib.error.HTTPError(req.full_url, code, "redirect refused: the key is never forwarded", headers, fp)


def opener():
    return urllib.request.build_opener(_NoRedirect)


def build(cfg, text):
    if cfg["style"] == "openai-responses":
        body = {"model": cfg["model"], "input": text, "max_output_tokens": cfg["max_output_tokens"],
                "store": False, "tools": []}
        if cfg["effort"]:
            body["reasoning"] = {"effort": cfg["effort"]}
        return cfg["base_url"] + "/responses", body
    body = {"model": cfg["model"], "messages": [{"role": "user", "content": text}],
            "max_tokens": cfg["max_output_tokens"], "n": 1}
    return cfg["base_url"] + "/chat/completions", body


def parse(cfg, data):
    """Return (text, problem, tokens_in, tokens_out, served_model); problem is None on success."""
    u = data.get("usage") or {}
    if cfg["style"] == "openai-responses":
        items = data.get("output") or []
        tools = sorted({i.get("type") for i in items if i.get("type") not in ("message", "reasoning")})
        text = "".join(c.get("text", "") for i in items if i.get("type") == "message"
                       for c in i.get("content") or [] if c.get("type") == "output_text")
        problem = (f"tool items {tools}" if tools else
                   None if data.get("status") == "completed" else f"response status {data.get('status')!r}")
        return text, problem, u.get("input_tokens"), u.get("output_tokens"), data.get("model")
    choices = data.get("choices") or []
    problem = None
    if len(choices) != 1:
        problem = f"{len(choices)} choices returned; exactly one is required"
    for ch in choices:
        msg = ch.get("message") or {}
        has_tool = bool(msg.get("tool_calls")) or "function_call" in msg \
            or ch.get("finish_reason") in ("tool_calls", "function_call")
        if has_tool:
            problem = "tool call in reply"
        elif ch.get("finish_reason") != "stop" and problem is None:
            problem = f"finish_reason {ch.get('finish_reason')!r}"
    text = ((choices[0].get("message") or {}).get("content") or "") if choices else ""
    return text, problem, u.get("prompt_tokens"), u.get("completion_tokens"), data.get("model")


def run(argv):
    if len(argv) != 7:
        raise Refusal(64, "usage: api-call.py POLICY_JSON TIER PROMPT_FILE OUT_TEXT OUT_META SENT_MARKER")
    policy, tier, prompt_file, out_text, out_meta, marker = argv[1:]
    cfg = load(policy, tier)
    try:
        text = Path(prompt_file).read_text()
        timeout = int(os.environ.get("REVIEWER_API_TIMEOUT_SECONDS", "900"))
        if timeout < 1:
            raise ValueError("timeout must be positive")
    except (OSError, ValueError) as exc:
        raise Refusal(78, f"cannot prepare the request: {exc}")
    url, body = build(cfg, text)
    payload = json.dumps(body).encode()
    # Byte-level tokenizers emit at most one token per byte; framing is added on top.
    bound = micro(len(payload) + FRAMING_TOKENS, cfg["max_output_tokens"], cfg)
    secret = key(cfg)
    req = urllib.request.Request(url, data=payload, method="POST", headers={
        "Content-Type": "application/json", "Authorization": f"Bearer {secret}"})
    call_id, already = reserve(cfg, tier, bound)
    Path(marker).touch()
    start = time.time()
    try:
        with opener().open(req, timeout=timeout) as resp:
            if urllib.parse.urlsplit(resp.geturl()).hostname != cfg["host"]:
                raise Refusal(70, "response came from an unexpected host; reservation kept")
            data = json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        released = exc.code in UNBILLED_HTTP
        settle(cfg, call_id, 0 if released else bound, f"HTTP {exc.code}")
        # Nothing from the error body is printed: every field is server-controlled
        # and may quote the request. The status code alone is reported.
        detail = ""
        raise Refusal(70, f"API request failed: HTTP {exc.code}{detail}"
                          + ("" if released else "; full reservation kept"))
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        raise Refusal(70, f"API request failed ({type(exc).__name__}); full reservation kept")
    reply, problem, tin, tout, served = parse(cfg, data)
    if not problem and not reply.strip():
        problem = "no text in reply"
    reply = redact(reply)  # the stored, validated and settled text are the same text
    if not problem:
        # The gateway's substance check runs on that exact text before settling,
        # so a reply it rejects keeps the full bound like any other rejected reply.
        check = subprocess.run([sys.executable, str(Path(__file__).resolve().parent / "reviewer-validate.py")],
                               input=reply, capture_output=True, text=True)
        if check.returncode != 0:
            problem = "substance validation failed"
    usage_ok = all(type(v) is int and v >= 0 for v in (tin, tout))
    if problem:
        cost, note = bound, "reply rejected: full bound kept"  # fixed text: problem may carry server values
    elif usage_ok:
        cost, note = micro(tin, tout, cfg), "usage"
    else:
        cost, note = bound, "usage missing: charged the full bound"
    settle(cfg, call_id, cost, note)
    meta = {"route": "api", "endpoint": url, "selected_model": cfg["model"], "served_model": served,
            "reasoning_effort": cfg["effort"], "input_tokens": tin, "output_tokens": tout,
            "cost_usd": cost / MICRO, "ledger_committed_usd": (already + cost) / MICRO,
            "spend_cap_usd": cfg["cap_micro"] / MICRO, "problem": problem,
            "elapsed_seconds": round(time.time() - start, 1)}
    Path(out_meta).write_text(redact(json.dumps(meta)))
    if problem:
        raise Refusal(70, f"API reply rejected: {problem}")
    Path(out_text).write_text(reply)
    return 0


def main(argv):
    marker = Path(argv[6]) if len(argv) == 7 else None
    try:
        return run(argv)
    except Refusal as exc:
        print(redact(exc), file=sys.stderr)
        return exc.code
    except Exception as exc:  # never leak a traceback that might carry the key
        sent = marker is not None and marker.exists()
        print(redact(f"API review error ({type(exc).__name__}): {exc}"), file=sys.stderr)
        return 70 if sent else 78


if __name__ == "__main__":
    sys.exit(main(sys.argv))
