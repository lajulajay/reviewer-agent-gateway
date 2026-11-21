#!/usr/bin/env python3
"""Order eligible subscription reviewers without querying provider usage."""

import importlib.util
import json
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("review_budget", ROOT / "review-budget.py")
budget = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(budget)
_spec = importlib.util.spec_from_file_location("agents", ROOT / "agents.py")
agents = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(agents)

_spec = importlib.util.spec_from_file_location("copilot_model_select", ROOT / "copilot-model-select.py")
copilot_select = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(copilot_select)

SUBSCRIPTION_REVIEWERS = ("claude", "codex", "kimi", "copilot")
TIERS = ("hard", "routine")


def _string_list(value, label):
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise ValueError(f"{label} must be a list of reviewer names")
    if len(set(value)) != len(value):
        raise ValueError(f"{label} contains duplicate reviewers")
    return value


def load_roster(policy_path):
    policy = json.loads(policy_path.read_text())
    active = _string_list(policy["active_reviewers"], "active_reviewers")
    order = _string_list(policy["tie_break_order"], "tie_break_order")
    if set(order) != set(SUBSCRIPTION_REVIEWERS) or len(order) != len(SUBSCRIPTION_REVIEWERS):
        raise ValueError("tie_break_order must contain claude, codex, kimi, and copilot exactly once")
    if any(provider not in SUBSCRIPTION_REVIEWERS for provider in active):
        raise ValueError("active_reviewers may contain only claude, codex, kimi, and copilot; Gemini is fallback-only")
    return active, order


def _topic(output):
    if not output.name.startswith("auto-"):
        raise ValueError("automatic output name must start with auto-")
    parsed = budget.parse("kimi-" + output.name[len("auto-") :])
    if not parsed or not parsed[2]:
        raise ValueError("output name must be auto-YYYY-MM-DD-<topic>[-rNN].md")
    return parsed[1], date.fromisoformat(parsed[2])


def _round_number(path):
    match = re.search(r"-r(\d+)(?:\.md|\.json|\.diagnostic\.json)$", path.name)
    return int(match.group(1)) if match else None


def _daily_cap():
    policy = json.loads((ROOT / "review-budget.json").read_text())
    return int(policy["max_reviews_per_provider_per_day"])


def _latest_eligible(topic_rounds, available):
    if not topic_rounds:
        return None
    numbered = [(round_, _round_number(round_[2])) for round_ in topic_rounds]
    explicit = [(round_, number) for round_, number in numbered if number is not None]
    if explicit and len(explicit) != len(topic_rounds):
        # Mixed numbered/unnumbered history is ambiguous: unnumbered rounds may
        # belong to any topic round, so no single latest reviewer can be trusted.
        return None
    if explicit:
        latest_round = max(number for _, number in explicit)
        latest = [round_ for round_, number in explicit if number == latest_round]
        providers = {round_[0] for round_ in latest}
        provider = next(iter(providers)) if len(providers) == 1 else None
        return provider if provider in available else None
    providers = {round_[0] for round_ in topic_rounds}
    provider = next(iter(providers)) if len(providers) == 1 else None
    return provider if provider in available else None


def _independent(registry, provider, owner, authors, author_models, tier=None):
    """Whether PROVIDER may review this work; Copilot needs an eligible model for the tier."""
    try:
        if provider == "copilot":
            policy = json.loads((ROOT / "copilot-model-policy.json").read_text())
            for t in ([tier] if tier else TIERS):
                try:
                    copilot_select.select(policy, t, registry, None, owner, authors, author_models)
                    return True
                except (agents.IdentityError, copilot_select.agents.IdentityError):
                    continue
            return False
        agents.check(registry, provider, owner, authors, author_models)
        return True
    except agents.IdentityError:
        return False


def order(policy_path, owner, output, today=None, authors=(), author_models=(), registry=None, tier=None):
    """Return provider names in invocation order for an auto-* output path.

    A provider is eligible only if no vendor it runs is the vendor of the
    owner, an additional author, or any authoring model (agents.json); Copilot
    is eligible when its model policy has an eligible model for the tier.
    A channel that owns or wrote the work ranks after every other channel
    (same channel, different vendor: allowed but last), then the usual
    balancing by today's count and the tie-break order applies.
    """
    if tier is not None and tier not in TIERS:
        raise ValueError("tier must be hard or routine")
    registry = registry or agents.load()
    # Validates owner, authors, and author models; raises IdentityError (a ValueError).
    agents.excluded_vendors(registry, owner, authors, author_models)
    output = Path(output)
    active, tie_order = load_roster(Path(policy_path))
    eligible = [provider for provider in tie_order
                if provider in active and _independent(registry, provider, owner, authors, author_models, tier)]
    if not eligible:
        raise ValueError("no eligible active subscription reviewer; use gemini-review.sh")
    if not output.parent.is_dir():
        raise ValueError(f"output directory does not exist: {output.parent}")
    topic, output_day = _topic(output)
    history = list(budget.rounds(output.parent))
    today = today or date.today()
    if output_day != today:
        raise ValueError(f"automatic output date must be today ({today.isoformat()})")
    counts = {
        provider: sum(1 for round_ in history if round_[0] == provider and round_[3] == today)
        for provider in eligible
    }
    daily_cap = _daily_cap()
    available = [provider for provider in eligible if counts[provider] < daily_cap]
    if not available:
        raise ValueError("no eligible active subscription reviewer under today's review budget; use gemini-review.sh")
    tie_index = {provider: index for index, provider in enumerate(tie_order)}
    own_channels = {owner, *authors}
    balanced = sorted(available, key=lambda provider: (provider in own_channels, counts[provider], tie_index[provider]))
    topic_rounds = [round_ for round_ in history if round_[1] == topic]
    latest = _latest_eligible(topic_rounds, available)
    if latest and (latest not in own_channels or all(p in own_channels for p in available)):
        return [latest] + [provider for provider in balanced if provider != latest]
    return balanced


def main(argv):
    if len(argv) < 4:
        print("usage: reviewer-select.py ROSTER_JSON OWNER AUTO_OUTPUT_PATH [ADDITIONAL_AUTHOR...] [--author-model=MODEL...] [--tier=hard|routine]", file=sys.stderr)
        return 64
    extra = argv[4:]
    authors = [a for a in extra if not a.startswith("--")]
    models = [a.split("=", 1)[1] for a in extra if a.startswith("--author-model=")]
    tiers = [a.split("=", 1)[1] for a in extra if a.startswith("--tier=")]
    unknown = [a for a in extra if a.startswith("--") and not a.startswith(("--author-model=", "--tier="))]
    if unknown or len(tiers) > 1:
        print(f"reviewer selection error: unknown or repeated option {(unknown or ['--tier'])[0]}", file=sys.stderr)
        return 64
    try:
        for provider in order(Path(argv[1]), argv[2], Path(argv[3]), authors=authors, author_models=models,
                              tier=tiers[0] if tiers else None):
            print(provider)
        return 0
    except agents.IdentityError as exc:
        print(f"reviewer selection error: {exc}", file=sys.stderr)
        return 64
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        print(f"reviewer selection error: {exc}", file=sys.stderr)
        return 78


if __name__ == "__main__":
    sys.exit(main(sys.argv))
