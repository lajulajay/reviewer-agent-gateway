            current[1] += " " + line.strip()
        elif not line.strip():
            current = None
    return entries


def disposition_errors(ws, rid):
    """Errors for one row's final disposition (v6 §3.4, tightened by r06/r07)."""
    row = ws.rows[rid]
    rnd = int(ROW_ID.match(rid).group(1))
    sev, disp = row["severity"], row["disposition"]
    strict = sev in ("blocker", "condition")
    m = re.match(r"^verified r(\d+)$", disp)
    if m:
        # The later review must contain the exact status line "<ID> is resolved."
        # at the start of a line: affirmative, specific, and in the reviewer's words.
        # Trailing spaces or tabs are ignored (Codex r03 of 2026-11-21-api-validator-reason
        # ended the line with two spaces); any other trailing text still fails.
        later = int(m.group(1))
        if later <= rnd or later not in ws.reviews:
            return [f"{rid}: verified cites r{later:02d}, which is not a later indexed round"]
        text = artifact_text(ws.repo / ws.reviews[later])
        if not re.search(rf"(?m)^{re.escape(rid)} is resolved\.[ \t]*$", text):
            return [f"{rid}: r{later:02d} has no line '{rid} is resolved.'"]
        if re.search(rf"(?m)^\W*{re.escape(rid)} remains open", text):
            return [f"{rid}: r{later:02d} also says {rid} remains open"]
        return []
    m = re.match(r'^user-decided (\d{4}-\d{2}-\d{2}) "(.+)"$', disp)
    if m:
        # The quote must sit in a Decisions entry of the same date with a stated
        # scope, and name this item. Authenticity of the transcription is policy.
