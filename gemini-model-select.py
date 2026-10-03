#!/usr/bin/env python3
"""Select a pinned Antigravity (agy) Gemini reviewer model from a plan-quota policy."""

import json
import re
import sys
from datetime import date
from pathlib import Path

# agy model IDs carry a reasoning-effort suffix, e.g. gemini-3.8-flash-high.
MODEL_ID = re.compile(r"gemini-[0-9]+(?:\.[0-9]+)?-(?:pro|flash)-(?:low|medium|high)")

def select(policy_path: Path, requested: str) -> str:
    policy = json.loads(policy_path.read_text())
    models = policy["models_newest_first"]
    if not isinstance(models, list) or not models:
        raise ValueError("models_newest_first must be a non-empty list")
    scope = policy["routine_two_releases_down_scope"]
    if scope not in ("same_family", "all_models"):
        raise ValueError("routine scope must be same_family or all_models")
    ids = []
    approved = []
    dates = []
    for row in models:
        model_id = row["id"]
        if not isinstance(model_id, str) or not MODEL_ID.fullmatch(model_id):
            raise ValueError(f"invalid review model ID: {model_id!r}")
        if model_id in ids:
            raise ValueError(f"duplicate model ID: {model_id}")
        if type(row["included_no_credits"]) is not bool:
            raise ValueError(f"included_no_credits must be boolean: {model_id}")
        released_on = date.fromisoformat(row["released_on"])
        if dates and released_on >= dates[-1]:
            raise ValueError("models_newest_first must have strictly descending release dates")
        dates.append(released_on)
        ids.append(model_id)
        if row["included_no_credits"]:
            approved.append(model_id)
    explicit_only = policy.get("explicit_only_models", [])
    if not isinstance(explicit_only, list):
        raise ValueError("explicit_only_models must be a list")
    for model_id in explicit_only:
        if not isinstance(model_id, str) or not MODEL_ID.fullmatch(model_id):
            raise ValueError(f"invalid review model ID: {model_id!r}")
        if model_id in ids:
            raise ValueError(f"duplicate model ID: {model_id}")
        ids.append(model_id)
    if not approved:
        raise ValueError("no models approved for included usage")
    hard = policy["hard_model"]
    if hard not in approved:
        raise ValueError("hard_model is not approved for included usage")
    if requested in ("pro", "hard"):
        return hard
    if requested in ("flash", "routine"):
        family = hard.split("-")[2]
        older = approved[approved.index(hard) + 1 :]
        candidates = [m for m in older if scope == "all_models" or m.split("-")[2] == family]
        if len(candidates) < 2:
            raise ValueError("fewer than two older approved releases in routine selection scope")
        return candidates[1]
    # Explicit-only models have no release date in the catalog, so tiers never
    # select them; a caller must name one by its full ID.
    if requested in approved or requested in explicit_only:
        return requested
    raise ValueError(f"requested model is not approved for included usage: {requested}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: gemini-model-select.py POLICY_JSON MODEL_OR_TIER")
    try:
        print(select(Path(sys.argv[1]), sys.argv[2]))
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Gemini model policy error: {exc}")
