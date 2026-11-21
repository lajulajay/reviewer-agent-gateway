#!/usr/bin/env python3
"""Pick the Copilot reviewer model for a tier under the vendor rule.

  copilot-model-select.py POLICY TIER [--vendor V] [--owner O] [--author A]... [--author-model M]...

Prints "<model> <vendor> <max_ai_credits>". With --vendor, uses that vendor's
model for the tier or refuses (exit 64) if the vendor rule forbids it. Without
it, takes the first vendor in the tier's vendor_order that the rule allows.
Every model is checked against agents.json, so a mapping entry whose model
belongs to another vendor is refused (exit 78).
"""

import importlib.util
import json
import sys
from pathlib import Path

MIN_AI_CREDITS = 30  # copilot --max-ai-credits refuses lower values (CLI 1.0.114)

_spec = importlib.util.spec_from_file_location("agents", Path(__file__).resolve().parent / "agents.py")
agents = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(agents)


def select(policy, tier, registry, vendor=None, owner=None, authors=(), author_models=()):
    spec = policy["tiers"].get(tier)
    if not isinstance(spec, dict):
        raise ValueError(f"tier must be one of: {', '.join(sorted(policy['tiers']))}")
    credits = spec["max_ai_credits"]
    if type(credits) is not int or credits < MIN_AI_CREDITS:
        raise ValueError(f"max_ai_credits must be an integer of at least {MIN_AI_CREDITS} (the Copilot CLI minimum)")
    order = [vendor] if vendor else spec["vendor_order"]
    refusals = []
    for v in order:
        model = spec["models"].get(v)
        if not model:
            if vendor:
                raise agents.IdentityError(f"no {tier} Copilot model is mapped for vendor {v}")
            continue
        if agents.model_vendor(registry, model) != v:
            raise ValueError(f"policy maps {v} to {model}, which agents.json assigns to another vendor")
        try:
            agents.check(registry, "copilot", owner, authors, author_models, reviewer_model=model)
            return model, v, credits
        except agents.IdentityError as exc:
            refusals.append(str(exc))
            if vendor:
                raise
    raise agents.IdentityError("no Copilot reviewer model is eligible under the vendor rule: " + "; ".join(refusals))


def main(argv):
    if len(argv) < 3:
        print(__doc__.strip().splitlines()[2].strip(), file=sys.stderr)
        return 64
    policy_path, tier, args = argv[1], argv[2], argv[3:]
    vendor, owner, authors, models = None, None, [], []
    while args:
        if len(args) < 2 or not args[1]:
            print(f"copilot-model-select: {args[0]} needs a value", file=sys.stderr)
            return 64
        flag, value, args = args[0], args[1], args[2:]
        if flag == "--vendor":
            vendor = value
        elif flag == "--owner":
            owner = value
        elif flag == "--author":
            authors.append(value)
        elif flag == "--author-model":
            models.append(value)
        else:
            print(f"copilot-model-select: unknown option {flag}", file=sys.stderr)
            return 64
    try:
        policy = json.loads(Path(policy_path).read_text())
        registry = agents.load()
        model, v, credits = select(policy, tier, registry, vendor, owner, authors, models)
    except agents.IdentityError as exc:
        print(f"copilot-model-select: {exc}", file=sys.stderr)
        return 64
    except (OSError, KeyError, TypeError, ValueError) as exc:
        print(f"copilot-model-select: {exc}", file=sys.stderr)
        return 78
    print(model, v, credits)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
