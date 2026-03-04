"""Database backup configuration and retention policies."""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field


@dataclass
class RetentionPolicy:
    """Backup retention windows."""

    daily_count: int = 7
    weekly_count: int = 4
    monthly_count: int = 12


@dataclass
class BackupConfig:
    """Database backup configuration."""

    database_url: str
    backup_dir: str = "/var/backups/credit-assessment"
    retention: RetentionPolicy = field(default_factory=RetentionPolicy)

    def __post_init__(self) -> None:
        if not self.database_url:
            raise ValueError("database_url is required for backups")


def get_backup_filename(prefix: str = "credit_assessment") -> str:
    """Generate a timestamped backup filename."""
    ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{ts}.sql.gz"


def should_retain(
    backup_age_days: int,
    policy: RetentionPolicy,
) -> bool:
    """Determine if a backup should be retained based on policy."""
    # Keep all daily backups within retention window
    if backup_age_days <= policy.daily_count:
        return True
    # Keep weekly backups (every 7 days) within weekly window
    if backup_age_days <= policy.weekly_count * 7 and backup_age_days % 7 == 0:
        return True
    # Keep monthly backups (every 30 days) within monthly window
    if backup_age_days <= policy.monthly_count * 30 and backup_age_days % 30 == 0:
        return True
    return False
