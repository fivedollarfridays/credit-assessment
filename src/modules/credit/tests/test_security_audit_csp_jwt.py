"""Tests for MEDIUM severity security audit fixes (T27.4).

A05-2: CSP style-src must not use 'unsafe-inline'
A01-1: JWT role freshness documented in _resolve_user_id
"""

from __future__ import annotations


# ---------------------------------------------------------------------------
# A05-2: CSP style-src must not use 'unsafe-inline'
# ---------------------------------------------------------------------------


class TestCspStyleSrcNoUnsafeInline:
    """CSP style-src must use hash-based directives, not 'unsafe-inline'."""

    def test_csp_style_src_no_unsafe_inline(self) -> None:
        """The _DASHBOARD_CSP must not contain 'unsafe-inline' in style-src."""
        from modules.credit.dashboard_routes import _DASHBOARD_CSP

        # Parse out the style-src directive
        for directive in _DASHBOARD_CSP.split(";"):
            directive = directive.strip()
            if directive.startswith("style-src"):
                assert "'unsafe-inline'" not in directive, (
                    f"CSP style-src still contains 'unsafe-inline': {directive}"
                )
                break

    def test_csp_style_src_has_hash(self) -> None:
        """The style-src directive must contain at least one sha256 hash."""
        from modules.credit.dashboard_routes import _DASHBOARD_CSP

        for directive in _DASHBOARD_CSP.split(";"):
            directive = directive.strip()
            if directive.startswith("style-src"):
                assert "'sha256-" in directive, (
                    f"CSP style-src missing sha256 hash: {directive}"
                )
                break

    def test_csp_header_set_on_dashboard(self, client) -> None:
        """GET /dashboard must return CSP header without 'unsafe-inline' in style-src."""
        resp = client.get("/dashboard")
        csp = resp.headers.get("content-security-policy", "")
        assert csp, "CSP header not set on /dashboard"
        for directive in csp.split(";"):
            directive = directive.strip()
            if directive.startswith("style-src"):
                assert "'unsafe-inline'" not in directive

    def test_no_inline_style_attributes_in_html(self) -> None:
        """dashboard.html must not use inline style= attributes."""
        from pathlib import Path

        html_path = Path(__file__).resolve().parents[1] / "static" / "dashboard.html"
        content = html_path.read_text()
        import re

        # Find style="..." attributes (but not <style> tags)
        matches = re.findall(r'\bstyle\s*=\s*["\']', content)
        assert len(matches) == 0, (
            f"Found {len(matches)} inline style= attribute(s) in dashboard.html. "
            "Move them to <style> block CSS classes for CSP compliance."
        )


# ---------------------------------------------------------------------------
# A01-1: JWT role freshness documented
# ---------------------------------------------------------------------------


class TestJwtRoleFreshnessDocumented:
    """_resolve_user_id must document why it checks DB role, not JWT claim."""

    def test_resolve_user_id_has_db_role_check(self) -> None:
        """_resolve_user_id must verify role from DB, not JWT claims."""
        import inspect

        from modules.credit.data_rights_routes import _resolve_user_id

        source = inspect.getsource(_resolve_user_id)
        # Must access user.role from DB, not auth.role from JWT
        assert "user.role" in source or "repo" in source.lower(), (
            "_resolve_user_id does not check DB role"
        )

    def test_resolve_user_id_documents_role_freshness(self) -> None:
        """_resolve_user_id docstring must mention role verification rationale."""
        import inspect

        from modules.credit.data_rights_routes import _resolve_user_id

        docstring = inspect.getdoc(_resolve_user_id) or ""
        source = inspect.getsource(_resolve_user_id)
        # Either docstring or inline comments must explain the DB role check
        combined = docstring + source
        assert any(
            phrase in combined.lower()
            for phrase in ["jwt", "stale", "fresh", "db", "database", "not just"]
        ), (
            "_resolve_user_id missing documentation about JWT role freshness. "
            "Add a comment explaining why DB role is checked instead of JWT claim."
        )
