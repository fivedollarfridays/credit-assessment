"""Feature flags — toggleable flags with targeting rules for gradual rollouts."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from enum import StrEnum

from sqlalchemy.ext.asyncio import AsyncSession

from .repo_flags import FeatureFlagRepository


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


def _db_to_flag(db_flag) -> FeatureFlag:
    """Convert DB model to FeatureFlag dataclass."""
    targeting = []
    if db_flag.targeting:
        for rule_data in db_flag.targeting:
            targeting.append(
                TargetingRule(
                    type=RuleType(rule_data["type"]),
                    values=rule_data.get("values", []),
                )
            )
    return FeatureFlag(
        key=db_flag.key,
        description=db_flag.description,
        enabled=db_flag.enabled,
        targeting=targeting,
    )


async def create_flag(
    session: AsyncSession,
    key: str,
    *,
    description: str = "",
    enabled: bool = False,
) -> FeatureFlag:
    """Create a new feature flag. Raises ValueError if key already exists."""
    repo = FeatureFlagRepository(session)
    existing = await repo.get(key)
    if existing is not None:
        raise ValueError(f"Flag '{key}' already exists")
    db_flag = await repo.create(key=key, description=description, enabled=enabled)
    return _db_to_flag(db_flag)


async def get_flag(session: AsyncSession, key: str) -> FeatureFlag | None:
    """Get a flag by key."""
    repo = FeatureFlagRepository(session)
    db_flag = await repo.get(key)
    if db_flag is None:
        return None
    return _db_to_flag(db_flag)


async def get_all_flags(session: AsyncSession) -> list[FeatureFlag]:
    """List all flags."""
    repo = FeatureFlagRepository(session)
    db_flags = await repo.list_all()
    return [_db_to_flag(f) for f in db_flags]


async def update_flag(
    session: AsyncSession,
    key: str,
    *,
    enabled: bool | None = None,
    description: str | None = None,
    targeting: list[TargetingRule] | None = None,
) -> FeatureFlag | None:
    """Update a flag. Returns None if not found."""
    repo = FeatureFlagRepository(session)
    db_flag = await repo.get(key)
    if db_flag is None:
        return None
    if enabled is not None:
        db_flag.enabled = enabled
    if description is not None:
        db_flag.description = description
    if targeting is not None:
        db_flag.targeting = [
            {"type": r.type.value, "values": r.values} for r in targeting
        ]
    await session.commit()
    await session.refresh(db_flag)
    return _db_to_flag(db_flag)


async def delete_flag(session: AsyncSession, key: str) -> bool:
    """Delete a flag. Returns True if found and removed."""
    repo = FeatureFlagRepository(session)
    return await repo.delete(key)


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


async def evaluate_flag(
    session: AsyncSession,
    key: str,
    *,
    org_id: str | None = None,
    user_id: str | None = None,
) -> bool:
    """Evaluate a feature flag for the given context."""
    flag = await get_flag(session, key)
    if flag is None or not flag.enabled:
        return False
    if not flag.targeting:
        return True
    return any(
        _matches_rule(r, key, org_id=org_id, user_id=user_id) for r in flag.targeting
    )
