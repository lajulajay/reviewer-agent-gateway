    start = time.time()
    try:
        with opener().open(req, timeout=min(timeout, READ_TIMEOUT)) as resp:
            if urllib.parse.urlsplit(resp.geturl()).hostname != cfg["host"]:
                raise Refusal(70, "response came from an unexpected host; reservation kept")
            data = read_reply(cfg, resp, start + timeout)
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
    if not isinstance(data, dict):
        data = {"status": "reply is not a JSON object"}
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
            # The validator prints one fixed-text reason; surface it so a refused
            # round can be fixed rather than guessed at. The ledger note below stays
            # fixed text; the reason goes only to stderr and the meta file.
            lines = [l.strip() for l in check.stderr.splitlines() if l.strip()]
            reason = "".join(c for c in redact(lines[-1]) if c.isprintable())[:200] if lines else ""
            problem = "substance validation failed" + (f": {reason}" if reason else "")
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
