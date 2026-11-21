def artifact_text(path):
    raw = path.read_text(errors="replace")
    if path.suffix == ".json":
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return raw
        return data.get("response") or data.get("result") or raw
    return raw
