"""Tests for INFO-severity security audit fixes (T26.5).

D-2:   Production compose does not mount dev source volume
CI-1:  All GitHub Actions pinned to commit SHAs
A06-2: Cryptography version pin widened
RC-1:  Shutdown flag uses threading.Event for thread safety
A08-2: Duplicate of CI-1
"""

from __future__ import annotations

import signal
import threading
from pathlib import Path

import pytest
import yaml

_PROJECT_ROOT = Path(__file__).resolve().parents[4]


# ---------------------------------------------------------------------------
# D-2: Production compose does not mount dev source volume
# ---------------------------------------------------------------------------


class TestProdVolumeOverride:
    """Deploy overlay should not mount dev source volumes."""

    def test_deploy_services_have_no_src_volume(self) -> None:
        """api-blue and api-green must not mount ./src."""
        path = _PROJECT_ROOT / "docker-compose.deploy.yml"
        data = yaml.safe_load(path.read_text())
        for svc_name in ("api-blue", "api-green"):
            svc = data["services"][svc_name]
            volumes = svc.get("volumes", [])
            for v in volumes:
                assert "./src" not in str(v), (
                    f"{svc_name} mounts dev source volume: {v}"
                )

    def test_deploy_services_override_volumes_to_empty(self) -> None:
        """api-blue and api-green should explicitly set volumes: []."""
        path = _PROJECT_ROOT / "docker-compose.deploy.yml"
        data = yaml.safe_load(path.read_text())
        for svc_name in ("api-blue", "api-green"):
            svc = data["services"][svc_name]
            # volumes key should be present and empty
            assert "volumes" in svc, f"{svc_name} missing volumes override"
            assert svc["volumes"] == [] or svc["volumes"] is None, (
                f"{svc_name} volumes should be empty, got {svc['volumes']}"
            )


# ---------------------------------------------------------------------------
# CI-1 / A08-2: GitHub Actions pinned to commit SHAs
# ---------------------------------------------------------------------------


class TestActionsSHAPinning:
    """All workflow files should pin actions to full commit SHAs."""

    _WORKFLOW_DIR = _PROJECT_ROOT / ".github" / "workflows"

    @staticmethod
    def _extract_uses(content: str) -> list[tuple[int, str]]:
        """Extract (line_number, uses_value) pairs from workflow content."""
        results = []
        for i, line in enumerate(content.splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith("- uses:") or stripped.startswith("uses:"):
                value = stripped.split("uses:", 1)[1].strip()
                results.append((i, value))
        return results

    def test_ci_yml_actions_pinned_to_sha(self) -> None:
        content = (self._WORKFLOW_DIR / "ci.yml").read_text()
        for line_no, uses in self._extract_uses(content):
            assert "@" in uses, f"ci.yml:{line_no}: {uses} missing version pin"
            ref = uses.split("@")[1].split()[0]
            assert len(ref) == 40 and all(c in "0123456789abcdef" for c in ref), (
                f"ci.yml:{line_no}: {uses} not pinned to full SHA"
            )

    def test_docker_publish_yml_actions_pinned_to_sha(self) -> None:
        content = (self._WORKFLOW_DIR / "docker-publish.yml").read_text()
        for line_no, uses in self._extract_uses(content):
            ref = uses.split("@")[1].split()[0]
            assert len(ref) == 40 and all(c in "0123456789abcdef" for c in ref), (
                f"docker-publish.yml:{line_no}: {uses} not pinned to full SHA"
            )

    def test_sdk_ci_yml_actions_pinned_to_sha(self) -> None:
        content = (self._WORKFLOW_DIR / "sdk-ci.yml").read_text()
        for line_no, uses in self._extract_uses(content):
            ref = uses.split("@")[1].split()[0]
            assert len(ref) == 40 and all(c in "0123456789abcdef" for c in ref), (
                f"sdk-ci.yml:{line_no}: {uses} not pinned to full SHA"
            )

    def test_all_workflows_have_version_comments(self) -> None:
        """Each pinned action should have a # vX.Y comment for readability."""
        for yml_file in self._WORKFLOW_DIR.glob("*.yml"):
            content = yml_file.read_text()
            for line_no, uses in self._extract_uses(content):
                assert "#" in uses, (
                    f"{yml_file.name}:{line_no}: {uses} missing version comment"
                )


# ---------------------------------------------------------------------------
# A06-2: Cryptography version pin widened
# ---------------------------------------------------------------------------


class TestCryptographyPin:
    """Cryptography dependency should allow minor version upgrades."""

    def test_cryptography_allows_version_48(self) -> None:
        content = (_PROJECT_ROOT / "pyproject.toml").read_text()
        for line in content.splitlines():
            if "cryptography" in line and "dependencies" not in line:
                assert "<48" in line or "<49" in line, (
                    f"cryptography pin too tight: {line.strip()}"
                )
                break
        else:
            pytest.fail("cryptography not found in dependencies")


# ---------------------------------------------------------------------------
# RC-1: Thread-safe shutdown flag
# ---------------------------------------------------------------------------


class TestThreadSafeShutdown:
    """Shutdown flag should use threading.Event for formal thread safety."""

    def test_shutdown_uses_threading_event(self) -> None:
        """The deploy module should use threading.Event, not a bare bool."""
        from modules.credit import deploy

        assert hasattr(deploy, "_shutdown_event"), (
            "deploy module should have _shutdown_event"
        )
        assert isinstance(deploy._shutdown_event, threading.Event)

    def test_is_shutting_down_reads_event(self) -> None:
        from modules.credit.deploy import is_shutting_down, reset_shutdown_state

        reset_shutdown_state()
        assert is_shutting_down() is False

    def test_sigterm_sets_event(self) -> None:
        from modules.credit.deploy import (
            is_shutting_down,
            reset_shutdown_state,
            setup_graceful_shutdown,
        )

        old_handler = signal.getsignal(signal.SIGTERM)
        try:
            reset_shutdown_state()
            setup_graceful_shutdown()
            handler = signal.getsignal(signal.SIGTERM)
            handler(signal.SIGTERM, None)
            assert is_shutting_down() is True
        finally:
            reset_shutdown_state()
            signal.signal(signal.SIGTERM, old_handler)

    def test_reset_clears_event(self) -> None:
        from modules.credit.deploy import (
            is_shutting_down,
            reset_shutdown_state,
            setup_graceful_shutdown,
        )

        old_handler = signal.getsignal(signal.SIGTERM)
        try:
            setup_graceful_shutdown()
            handler = signal.getsignal(signal.SIGTERM)
            handler(signal.SIGTERM, None)
            assert is_shutting_down() is True
            reset_shutdown_state()
            assert is_shutting_down() is False
        finally:
            signal.signal(signal.SIGTERM, old_handler)
