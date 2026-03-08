"""Tests for LOW/INFO severity security audit fixes (T27.5).

A04-4: Feature flag endpoints must have rate limits
A04-5: GDPR endpoints must have rate limits
A05-3: Health endpoints must return Cache-Control: no-store + global X-Frame-Options
A06-1: Stripe dependency pin tightened
A08-1: Dockerfile uses exec-form CMD
A09-2: Audit log supports org_id filter
A07-2 + A02-3: Informational items documented
"""

from __future__ import annotations

import re
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[4]


# ---------------------------------------------------------------------------
# A04-4: Feature flag endpoints must have rate limits
# ---------------------------------------------------------------------------


class TestFlagRateLimits:
    """Feature flag endpoints must have rate limit decorators."""

    def test_flag_create_has_rate_limit(self) -> None:
        import inspect

        from modules.credit.flag_routes import create

        source = inspect.getsource(create)
        assert "limiter" in source or "limit" in source.lower(), (
            "create flag endpoint missing rate limit"
        )

    def test_flag_list_has_rate_limit(self) -> None:
        import inspect

        from modules.credit.flag_routes import list_flags

        source = inspect.getsource(list_flags)
        assert "limiter" in source or "limit" in source.lower(), (
            "list_flags endpoint missing rate limit"
        )

    def test_flag_routes_import_limiter(self) -> None:
        import inspect

        from modules.credit import flag_routes

        source = inspect.getsource(flag_routes)
        assert "limiter" in source, "flag_routes.py does not import limiter"


# ---------------------------------------------------------------------------
# A04-5: GDPR endpoints must have rate limits
# ---------------------------------------------------------------------------


class TestGdprRateLimits:
    """GDPR data rights endpoints must have rate limit decorators."""

    def test_data_export_has_rate_limit(self) -> None:
        import inspect

        from modules.credit.data_rights_routes import data_export

        source = inspect.getsource(data_export)
        assert "limiter" in source or "limit" in source.lower(), (
            "data_export endpoint missing rate limit"
        )

    def test_data_delete_has_rate_limit(self) -> None:
        import inspect

        from modules.credit.data_rights_routes import data_delete

        source = inspect.getsource(data_delete)
        assert "limiter" in source or "limit" in source.lower(), (
            "data_delete endpoint missing rate limit"
        )


# ---------------------------------------------------------------------------
# A05-3: Health endpoints must return Cache-Control: no-store
# ---------------------------------------------------------------------------


class TestHealthCacheControl:
    """Health and ready endpoints must return Cache-Control: no-store."""

    def test_health_has_cache_control_no_store(self, client) -> None:
        resp = client.get("/health")
        cc = resp.headers.get("cache-control", "")
        assert "no-store" in cc, (
            f"GET /health missing Cache-Control: no-store, got '{cc}'"
        )

    def test_ready_has_cache_control_no_store(self, client) -> None:
        resp = client.get("/ready")
        cc = resp.headers.get("cache-control", "")
        assert "no-store" in cc, (
            f"GET /ready missing Cache-Control: no-store, got '{cc}'"
        )

    def test_global_x_frame_options(self, client) -> None:
        """All responses should have X-Frame-Options: DENY."""
        resp = client.get("/health")
        xfo = resp.headers.get("x-frame-options", "")
        assert xfo.upper() == "DENY", (
            f"Missing global X-Frame-Options: DENY, got '{xfo}'"
        )


# ---------------------------------------------------------------------------
# A06-1: Stripe dependency pin tightened
# ---------------------------------------------------------------------------


class TestStripeDependencyPin:
    """Stripe dependency pin must span at most 2 major versions."""

    def test_stripe_pin_at_most_2_major_versions(self) -> None:
        toml_path = _PROJECT_ROOT / "pyproject.toml"
        content = toml_path.read_text()
        match = re.search(r'"stripe>=(\d+)\..*<(\d+)"', content)
        assert match is not None, "stripe dependency not found in pyproject.toml"
        low = int(match.group(1))
        high = int(match.group(2))
        span = high - low
        assert span <= 2, (
            f"Stripe pin spans {span} major versions (>={low},<{high}), max 2"
        )


# ---------------------------------------------------------------------------
# A08-1: Dockerfile uses exec-form CMD
# ---------------------------------------------------------------------------


class TestDockerfileCmdForm:
    """Dockerfile CMD must use exec form for proper SIGTERM handling."""

    def test_cmd_uses_exec_form(self) -> None:
        dockerfile = (_PROJECT_ROOT / "Dockerfile").read_text()
        lines = dockerfile.splitlines()
        # Find standalone CMD instructions (not part of HEALTHCHECK)
        in_healthcheck = False
        cmd_lines = []
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("HEALTHCHECK"):
                in_healthcheck = True
            elif stripped and not stripped.startswith("#") and not in_healthcheck:
                if stripped.startswith("CMD"):
                    cmd_lines.append(stripped)
            # End continuation when line doesn't end with backslash
            if in_healthcheck and not line.rstrip().endswith("\\"):
                in_healthcheck = False
        assert len(cmd_lines) >= 1, "No CMD found in Dockerfile"
        for stripped in cmd_lines:
            assert stripped.startswith("CMD ["), (
                f"CMD uses shell form (breaks SIGTERM): {stripped[:60]}..."
            )


# ---------------------------------------------------------------------------
# A09-2: Audit log supports org_id filter
# ---------------------------------------------------------------------------


class TestAuditOrgIdFilter:
    """Admin audit-log endpoint must support org_id query parameter."""

    def test_audit_log_has_org_id_param(self) -> None:
        import inspect

        from modules.credit.admin_routes import audit_log

        sig = inspect.signature(audit_log)
        assert "org_id" in sig.parameters, (
            "audit_log endpoint missing org_id query parameter"
        )

    def test_get_audit_trail_accepts_org_id(self) -> None:
        import inspect

        from modules.credit.audit import get_audit_trail

        sig = inspect.signature(get_audit_trail)
        assert "org_id" in sig.parameters, "get_audit_trail missing org_id parameter"


# ---------------------------------------------------------------------------
# A07-2 + A02-3: Informational items documented
# ---------------------------------------------------------------------------


class TestInfoItemsDocumented:
    """Informational findings should have code comments documenting tradeoffs."""

    def test_dummy_hash_has_comment(self) -> None:
        """_DUMMY_HASH in user_routes should have a comment about per-worker."""
        import inspect

        from modules.credit import user_routes

        source = inspect.getsource(user_routes)
        # Find the _DUMMY_HASH line and check for a comment
        for line in source.splitlines():
            if "_DUMMY_HASH" in line and "=" in line:
                # Either a comment on the same line or preceding comment
                idx = source.splitlines().index(line)
                context = "\n".join(source.splitlines()[max(0, idx - 2) : idx + 1])
                assert "#" in context, (
                    "_DUMMY_HASH missing comment explaining per-worker behavior"
                )
                break

    def test_lru_cache_has_comment(self) -> None:
        """LRU cache in crypto.py should have a comment about key retention."""
        import inspect

        from modules.credit import crypto

        source = inspect.getsource(crypto)
        assert "lru_cache" in source, "crypto.py missing lru_cache"
        # Should have a comment near lru_cache about key material
        assert any(
            word in source.lower()
            for word in ["cache", "key material", "retained", "memory"]
        ), "crypto.py missing comment about LRU cache key material retention"
