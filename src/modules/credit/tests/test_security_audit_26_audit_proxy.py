"""Tests for Sprint 26 security audit fixes: assessment audit trail + proxy trust.

A09-2: Assessment compliance audit trail
RL-1: Rate limit proxy trust configuration
"""

from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# A09-2: Assessment compliance audit trail
# ---------------------------------------------------------------------------


class TestAssessmentAuditTrail:
    """POST /assess and /assess/simple must create compliance audit entries."""

    @pytest.mark.asyncio
    async def test_persist_assessment_creates_audit_entry(self) -> None:
        """_persist_assessment should call create_audit_entry after saving."""
        from contextlib import asynccontextmanager
        from unittest.mock import AsyncMock, MagicMock, patch

        from modules.credit.assess_tasks import (
            persist_assessment as _persist_assessment,
        )

        mock_session = AsyncMock()

        @asynccontextmanager
        async def _mock_factory():
            yield mock_session

        mock_profile = MagicMock()
        mock_profile.current_score = 520
        mock_profile.score_band.value = "very_poor"
        mock_profile.model_dump.return_value = {}

        mock_result = MagicMock()
        mock_result.barrier_severity.value = "high"
        mock_result.readiness.score_band.value = "very_poor"
        mock_result.readiness.score = 20
        mock_result.model_dump.return_value = {}

        with patch("modules.credit.assess_tasks.create_audit_entry") as mock_audit:
            mock_audit.return_value = {}
            await _persist_assessment(
                _mock_factory, mock_profile, mock_result, "user@test.com", "org-1"
            )
            mock_audit.assert_called_once()

    @pytest.mark.asyncio
    async def test_audit_entry_contains_no_pii(self) -> None:
        """The audit entry summary should contain score_band and severity, not PII."""
        from contextlib import asynccontextmanager
        from unittest.mock import AsyncMock, MagicMock, patch

        from modules.credit.assess_tasks import (
            persist_assessment as _persist_assessment,
        )

        mock_session = AsyncMock()

        @asynccontextmanager
        async def _mock_factory():
            yield mock_session

        mock_profile = MagicMock()
        mock_profile.current_score = 520
        mock_profile.score_band.value = "very_poor"
        mock_profile.model_dump.return_value = {}

        mock_result = MagicMock()
        mock_result.barrier_severity.value = "high"
        mock_result.readiness.score_band.value = "very_poor"
        mock_result.readiness.score = 20
        mock_result.model_dump.return_value = {}

        with patch("modules.credit.assess_tasks.create_audit_entry") as mock_audit:
            mock_audit.return_value = {}
            await _persist_assessment(
                _mock_factory, mock_profile, mock_result, "user@test.com", "org-1"
            )
            call_kwargs = mock_audit.call_args
            result_summary = call_kwargs.kwargs.get(
                "result_summary", call_kwargs[1].get("result_summary", {})
            )
            assert "score_band" in result_summary
            assert "barrier_severity" in result_summary
            # Should NOT contain raw email
            assert "user@test.com" not in str(result_summary)


# ---------------------------------------------------------------------------
# RL-1: Rate limit proxy trust configuration
# ---------------------------------------------------------------------------


class TestProxyTrustConfig:
    """Config should have trusted_proxy_ips setting."""

    def test_trusted_proxy_ips_defaults_to_none(self) -> None:
        from modules.credit.config import Settings

        s = Settings()
        assert s.trusted_proxy_ips is None

    def test_trusted_proxy_ips_accepts_value(self) -> None:
        from modules.credit.config import Settings

        s = Settings(trusted_proxy_ips="172.18.0.1")
        assert s.trusted_proxy_ips == "172.18.0.1"
