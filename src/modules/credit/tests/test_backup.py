"""Tests for database backup configuration and retention policies."""

from __future__ import annotations

import re
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Cycle 1: RetentionPolicy dataclass defaults
# ---------------------------------------------------------------------------


class TestRetentionPolicy:
    """Tests for RetentionPolicy defaults."""

    def test_default_daily_count(self) -> None:
        from src.modules.credit.backup import RetentionPolicy

        policy = RetentionPolicy()
        assert policy.daily_count == 7

    def test_default_weekly_count(self) -> None:
        from src.modules.credit.backup import RetentionPolicy

        policy = RetentionPolicy()
        assert policy.weekly_count == 4

    def test_default_monthly_count(self) -> None:
        from src.modules.credit.backup import RetentionPolicy

        policy = RetentionPolicy()
        assert policy.monthly_count == 12


# ---------------------------------------------------------------------------
# Cycle 2: BackupConfig dataclass fields and validation
# ---------------------------------------------------------------------------


class TestBackupConfig:
    """Tests for BackupConfig construction and validation."""

    def test_creates_with_valid_database_url(self) -> None:
        from src.modules.credit.backup import BackupConfig

        cfg = BackupConfig(database_url="postgresql://localhost/credit")
        assert cfg.database_url == "postgresql://localhost/credit"

    def test_default_backup_dir(self) -> None:
        from src.modules.credit.backup import BackupConfig

        cfg = BackupConfig(database_url="postgresql://localhost/credit")
        assert cfg.backup_dir == "/var/backups/credit-assessment"

    def test_default_retention_policy(self) -> None:
        from src.modules.credit.backup import BackupConfig

        cfg = BackupConfig(database_url="postgresql://localhost/credit")
        assert cfg.retention.daily_count == 7
        assert cfg.retention.weekly_count == 4
        assert cfg.retention.monthly_count == 12

    def test_raises_on_empty_database_url(self) -> None:
        from src.modules.credit.backup import BackupConfig

        with pytest.raises(ValueError, match="database_url is required"):
            BackupConfig(database_url="")

    def test_raises_on_none_database_url(self) -> None:
        from src.modules.credit.backup import BackupConfig

        with pytest.raises(ValueError, match="database_url is required"):
            BackupConfig(database_url=None)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Cycle 3: get_backup_filename() format
# ---------------------------------------------------------------------------


class TestGetBackupFilename:
    """Tests for timestamped backup filename generation."""

    def test_default_prefix(self) -> None:
        from src.modules.credit.backup import get_backup_filename

        name = get_backup_filename()
        assert name.startswith("credit_assessment_")
        assert name.endswith(".sql.gz")

    def test_custom_prefix(self) -> None:
        from src.modules.credit.backup import get_backup_filename

        name = get_backup_filename(prefix="mydb")
        assert name.startswith("mydb_")
        assert name.endswith(".sql.gz")

    def test_timestamp_format(self) -> None:
        from src.modules.credit.backup import get_backup_filename

        name = get_backup_filename()
        # Extract the timestamp portion between prefix and extension
        # Format: credit_assessment_YYYYMMDD_HHMMSS.sql.gz
        pattern = r"^credit_assessment_\d{8}_\d{6}\.sql\.gz$"
        assert re.match(pattern, name), (
            f"Filename {name!r} does not match expected pattern"
        )


# ---------------------------------------------------------------------------
# Cycle 4: should_retain() retention logic
# ---------------------------------------------------------------------------


class TestShouldRetain:
    """Tests for backup retention decision logic."""

    def test_retains_recent_daily_backup(self) -> None:
        from src.modules.credit.backup import RetentionPolicy, should_retain

        policy = RetentionPolicy()
        assert should_retain(backup_age_days=3, policy=policy) is True

    def test_retains_backup_at_daily_boundary(self) -> None:
        from src.modules.credit.backup import RetentionPolicy, should_retain

        policy = RetentionPolicy()
        assert should_retain(backup_age_days=7, policy=policy) is True

    def test_retains_weekly_backup(self) -> None:
        from src.modules.credit.backup import RetentionPolicy, should_retain

        policy = RetentionPolicy()
        # Day 14 is exactly 2 weeks old and 14 % 7 == 0
        assert should_retain(backup_age_days=14, policy=policy) is True

    def test_discards_non_weekly_outside_daily_window(self) -> None:
        from src.modules.credit.backup import RetentionPolicy, should_retain

        policy = RetentionPolicy()
        # Day 10 is outside daily (>7) and not a weekly boundary (10 % 7 != 0)
        assert should_retain(backup_age_days=10, policy=policy) is False

    def test_retains_monthly_backup(self) -> None:
        from src.modules.credit.backup import RetentionPolicy, should_retain

        policy = RetentionPolicy()
        # Day 60 is outside weekly window (>28), but 60 % 30 == 0
        assert should_retain(backup_age_days=60, policy=policy) is True

    def test_discards_old_non_monthly_backup(self) -> None:
        from src.modules.credit.backup import RetentionPolicy, should_retain

        policy = RetentionPolicy()
        # Day 45 is outside weekly (>28) and 45 % 30 != 0
        assert should_retain(backup_age_days=45, policy=policy) is False

    def test_discards_backup_beyond_all_windows(self) -> None:
        from src.modules.credit.backup import RetentionPolicy, should_retain

        policy = RetentionPolicy()
        # Day 400 is beyond monthly window (12 * 30 = 360)
        assert should_retain(backup_age_days=400, policy=policy) is False


# ---------------------------------------------------------------------------
# Cycle 5: Shell scripts exist and are executable
# ---------------------------------------------------------------------------

# Project root is resolved relative to this test file:
# tests/test_backup.py -> src/modules/credit/tests/ -> project root
_PROJECT_ROOT = Path(__file__).resolve().parents[4]


class TestShellScripts:
    """Tests for backup/restore shell scripts."""

    def test_backup_script_exists(self) -> None:
        script = _PROJECT_ROOT / "scripts" / "backup.sh"
        assert script.is_file(), f"Expected {script} to exist"

    def test_restore_script_exists(self) -> None:
        script = _PROJECT_ROOT / "scripts" / "restore.sh"
        assert script.is_file(), f"Expected {script} to exist"

    def test_backup_script_is_executable(self) -> None:
        import os
        import stat

        script = _PROJECT_ROOT / "scripts" / "backup.sh"
        mode = os.stat(script).st_mode
        assert mode & stat.S_IXUSR, "backup.sh should be executable"

    def test_restore_script_is_executable(self) -> None:
        import os
        import stat

        script = _PROJECT_ROOT / "scripts" / "restore.sh"
        mode = os.stat(script).st_mode
        assert mode & stat.S_IXUSR, "restore.sh should be executable"
