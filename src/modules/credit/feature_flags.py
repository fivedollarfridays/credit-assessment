"""Feature flags — toggleable flags with targeting rules for gradual rollouts."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from enum import StrEnum


class RuleType(StrEnum):
    """Targeting rule types."""

    ORG = "org"
    USER = "user"
    PERCENTAGE = "percentage"


@dataclass
class TargetingRule:
    """A targeting rule for a feature flag."""

    type: RuleType
    values: list[str] = field(default_factory=list)


@dataclass
class FeatureFlag:
    """A feature flag with optional targeting rules."""

    key: str
    description: str = ""
    enabled: bool = False
    targeting: list[TargetingRule] = field(default_factory=list)


# --- In-memory store ---

_flags: dict[str, FeatureFlag] = {}


def reset_flags() -> None:
    """Clear all flags (testing)."""
    _flags.clear()


# --- CRUD ---


def create_flag(
    key: str,
    *,
    description: str = "",
    enabled: bool = False,
) -> FeatureFlag:
    """Create a new feature flag. Raises ValueError if key already exists."""
    if key in _flags:
        raise ValueError(f"Flag '{key}' already exists")
    flag = FeatureFlag(key=key, description=description, enabled=enabled)
    _flags[key] = flag
    return flag


def get_flag(key: str) -> FeatureFlag | None:
    """Get a flag by key."""
    return _flags.get(key)


def get_all_flags() -> list[FeatureFlag]:
    """List all flags."""
    return list(_flags.values())


def update_flag(
    key: str,
    *,
    enabled: bool | None = None,
    description: str | None = None,
    targeting: list[TargetingRule] | None = None,
) -> FeatureFlag | None:
    """Update a flag. Returns None if not found."""
    flag = _flags.get(key)
    if flag is None:
        return None
    if enabled is not None:
        flag.enabled = enabled
    if description is not None:
        flag.description = description
    if targeting is not None:
        flag.targeting = targeting
    return flag


def delete_flag(key: str) -> bool:
    """Delete a flag. Returns True if found and removed."""
    return _flags.pop(key, None) is not None


# --- Evaluation ---


def _hash_percentage(flag_key: str, user_id: str) -> int:
    """Deterministic 0-99 bucket for percentage targeting."""
    digest = hashlib.sha256(f"{flag_key}:{user_id}".encode()).hexdigest()
    return int(digest[:8], 16) % 100


def _matches_rule(
    rule: TargetingRule,
    flag_key: str,
    *,
    org_id: str | None,
    user_id: str | None,
) -> bool:
    """Check if a single targeting rule matches the given context."""
    if rule.type == RuleType.ORG:
        return org_id is not None and org_id in rule.values
    if rule.type == RuleType.USER:
        return user_id is not None and user_id in rule.values
    if rule.type == RuleType.PERCENTAGE:
        if user_id is None:
            return False
        try:
            pct = int(rule.values[0]) if rule.values else 0
        except (ValueError, IndexError):
            return False
        return _hash_percentage(flag_key, user_id) < pct
    return False


def evaluate_flag(
    key: str,
    *,
    org_id: str | None = None,
    user_id: str | None = None,
) -> bool:
    """Evaluate a feature flag for the given context."""
    flag = _flags.get(key)
    if flag is None or not flag.enabled:
        return False
    if not flag.targeting:
        return True
    return any(
        _matches_rule(r, key, org_id=org_id, user_id=user_id) for r in flag.targeting
    )
