#!/usr/bin/env python3
"""Agent registry and the vendor-independence rule.

  agents.py check REVIEWER [--owner O] [--author A]... [--author-model M]...

A reviewer may review work only if none of its model vendors is the vendor of
the owner, of an additional author, or of any model that wrote the work. Model
versions do not matter: any Gemini model is Google, any Claude model is
Anthropic. Channels whose vendor depends on the model (Copilot) require every
authoring model to be named; routers such as Copilot Fusion are refused
because their vendor cannot be known.

Exit 0 when eligible, 64 on a rule or usage violation, 78 when the registry
cannot be read.
"""

import json
import sys
from pathlib import Path

REGISTRY = Path(__file__).resolve().parent / "agents.json"


class IdentityError(ValueError):
    """The requested review violates the owner or vendor rules."""


def load(path=REGISTRY):
    data = json.loads(Path(path).read_text())
    channels = data["channels"]
    prefixes = data["vendor_prefixes"]
    if not isinstance(channels, dict) or not isinstance(prefixes, dict):
        raise ValueError("agents.json: channels and vendor_prefixes must be objects")
    for name, spec in channels.items():
        vendors = spec.get("vendors")
        if vendors != "by-model" and not (isinstance(vendors, list) and vendors and all(v in prefixes for v in vendors)):
            raise ValueError(f"agents.json: channel {name} has unknown vendors {vendors!r}")
    return data


def model_vendor(registry, model):
    """Return the vendor of a model ID; fail closed on routers and unknown IDs."""
    ident = model.strip().lower()
    if not ident or ident in registry.get("unresolvable_models", []):
        raise IdentityError(f"model {model!r} is a router or empty; pin a concrete model")
    for vendor, prefixes in registry["vendor_prefixes"].items():
        if any(ident.startswith(p) for p in prefixes):
            return vendor
    raise IdentityError(f"model {model!r} matches no known vendor; add its prefix to agents.json")


def owners(registry):
    return sorted(n for n, s in registry["channels"].items() if s.get("can_own"))


def channel_vendors(registry, channel):
    spec = registry["channels"].get(channel)
    if spec is None:
        raise IdentityError(f"unknown agent {channel!r}")
    return spec["vendors"]


def excluded_vendors(registry, owner=None, authors=(), author_models=()):
    """Vendors that may not review this work."""
    if owner is not None and owner not in owners(registry):
        raise IdentityError(f"--owner must be one of {', '.join(owners(registry))}")
    excluded, needs_models = set(), False
    for agent in ([owner] if owner else []) + list(authors):
        vendors = channel_vendors(registry, agent)
        if vendors == "by-model":
            needs_models = True
        else:
            excluded.update(vendors)
    if needs_models and not author_models:
        raise IdentityError("work owned or authored through a multi-vendor channel (copilot) needs --author-model for every model that wrote it")
    excluded.update(model_vendor(registry, m) for m in author_models)
    return excluded


def check(registry, reviewer, owner=None, authors=(), author_models=(), reviewer_model=None):
    """Raise IdentityError unless REVIEWER may review the described work."""
    spec = registry["channels"].get(reviewer)
    if spec is None or not spec.get("can_review"):
        raise IdentityError(f"{reviewer!r} is not a reviewer channel")
    vendors = spec["vendors"]
    if vendors == "by-model":
        if not reviewer_model:
            raise IdentityError(f"reviewer channel {reviewer} needs the reviewer model to establish its vendor")
        vendors = [model_vendor(registry, reviewer_model)]
    clash = set(vendors) & excluded_vendors(registry, owner, authors, author_models)
    if clash:
        raise IdentityError(
            f"{reviewer} ({', '.join(sorted(vendors))}) cannot review work owned or written by the same vendor "
            f"({', '.join(sorted(clash))}), whatever the model version")


def main(argv):
    if len(argv) < 3 or argv[1] != "check":
        print(__doc__.strip().splitlines()[2].strip(), file=sys.stderr)
        return 64
    reviewer, owner, authors, models, reviewer_model = argv[2], None, [], [], None
    args = argv[3:]
    while args:
        if len(args) < 2 or not args[1]:
            print(f"agents.py: {args[0]} needs a value", file=sys.stderr)
            return 64
        flag, value, args = args[0], args[1], args[2:]
        if flag == "--owner":
            owner = value
        elif flag == "--author":
            authors.append(value)
        elif flag == "--author-model":
            models.append(value)
        elif flag == "--reviewer-model":
            reviewer_model = value
        else:
            print(f"agents.py: unknown option {flag}", file=sys.stderr)
            return 64
    try:
        registry = load()
    except (OSError, KeyError, TypeError, ValueError) as exc:
        print(f"agents.py: cannot read the registry: {exc}", file=sys.stderr)
        return 78
    try:
        check(registry, reviewer, owner, authors, models, reviewer_model)
    except IdentityError as exc:
        print(str(exc), file=sys.stderr)
        return 64
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
