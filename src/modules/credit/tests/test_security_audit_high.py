"""Tests for HIGH severity security audit fixes (T27.1).

A05-1: CORS allow_methods must include PATCH
A02-1: Sentry init must set send_default_pii=False
A07-1: Login must run bcrypt even for inactive users (timing oracle)
"""

from __future__ import annotations

from unittest.mock import patch


# ---------------------------------------------------------------------------
# A05-1: CORS allow_methods must include PATCH
# ---------------------------------------------------------------------------


class TestCorsPatchMethod:
    """CORS middleware must allow PATCH for dispute status updates."""

    def test_cors_allows_patch_method(self) -> None:
        """CORSMiddleware config should include PATCH in allow_methods."""
        from modules.credit.router import app

        # Find CORSMiddleware in the middleware stack
        cors_found = False
        for mw in app.user_middleware:
            if mw.cls.__name__ == "CORSMiddleware":
                cors_found = True
                methods = mw.kwargs.get(
                    "allow_methods", mw.args[1] if len(mw.args) > 1 else []
                )
                assert "PATCH" in methods, f"PATCH not in CORS allow_methods: {methods}"
                break
        assert cors_found, "CORSMiddleware not found in app middleware"

    def test_cors_includes_all_needed_methods(self) -> None:
        """Verify all HTTP methods used by the API are allowed."""
        from modules.credit.router import app

        for mw in app.user_middleware:
            if mw.cls.__name__ == "CORSMiddleware":
                methods = mw.kwargs.get("allow_methods", [])
                for method in ("GET", "POST", "PUT", "DELETE", "PATCH"):
                    assert method in methods, (
                        f"{method} missing from CORS allow_methods"
                    )
                break


# ---------------------------------------------------------------------------
# A02-1: Sentry init must set send_default_pii=False
# ---------------------------------------------------------------------------


class TestSentryPiiProtection:
    """Sentry must not collect PII by default."""

    def test_sentry_init_disables_default_pii(self) -> None:
        """setup_sentry must pass send_default_pii=False to sentry_sdk.init."""
        from modules.credit.sentry import setup_sentry

        with patch("modules.credit.sentry.sentry_sdk") as mock_sdk:
            setup_sentry(dsn="https://key@sentry.io/123", environment="production")
            call_kwargs = mock_sdk.init.call_args[1]
            assert call_kwargs.get("send_default_pii") is False, (
                "Sentry init missing send_default_pii=False"
            )

    def test_sentry_noop_still_works_without_dsn(self) -> None:
        """When DSN is None, init should not be called at all."""
        from modules.credit.sentry import setup_sentry

        with patch("modules.credit.sentry.sentry_sdk") as mock_sdk:
            setup_sentry(dsn=None, environment="development")
            mock_sdk.init.assert_not_called()


# ---------------------------------------------------------------------------
# A07-1: Timing oracle — inactive user must still run bcrypt
# ---------------------------------------------------------------------------


class TestTimingOracleFix:
    """Login must run bcrypt for inactive users to prevent timing enumeration."""

    def test_is_active_check_not_before_verify_password(self) -> None:
        """The is_active check must not short-circuit before verify_password.

        The login function must call verify_password() before checking
        is_active, so an attacker cannot distinguish inactive from
        nonexistent accounts via response time.
        """
        import ast
        import inspect

        from modules.credit import user_routes

        source = inspect.getsource(user_routes.login)
        # Remove the decorator lines to get just the function body
        tree = ast.parse(source)

        # Find the verify_password call and any is_active check
        verify_line = None
        is_active_reject_line = None

        for node in ast.walk(tree):
            # Find verify_password call
            if isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Name) and func.id == "verify_password":
                    verify_line = node.lineno
                elif isinstance(func, ast.Attribute) and func.attr == "verify_password":
                    verify_line = node.lineno

        # There must be no standalone `if not user.is_active: raise` before
        # verify_password. The is_active check should be combined with the
        # verify_password condition (same line/branch) or come after it.
        for node in ast.walk(tree):
            if isinstance(node, ast.If):
                # Check for `if not user.is_active:` as a standalone guard
                test = node.test
                if isinstance(test, ast.UnaryOp) and isinstance(test.op, ast.Not):
                    operand = test.operand
                    if (
                        isinstance(operand, ast.Attribute)
                        and operand.attr == "is_active"
                    ):
                        # This is a standalone `if not user.is_active:` check
                        # that would raise before verify_password
                        if any(isinstance(n, ast.Raise) for n in ast.walk(node)):
                            is_active_reject_line = node.lineno

        assert verify_line is not None, "verify_password call not found in login()"
        assert is_active_reject_line is None, (
            f"Standalone 'if not user.is_active: raise' found at line {is_active_reject_line} "
            f"(verify_password at line {verify_line}). "
            "is_active must be checked AFTER or combined WITH verify_password "
            "to prevent timing oracle."
        )

    def test_inactive_user_gets_401_via_api(self, client) -> None:
        """Deactivated user returns 401 even with correct password."""
        import asyncio

        from modules.credit.repo_users import UserRepository
        from modules.credit.router import app

        # Register a user
        client.post(
            "/auth/register",
            json={"email": "timing-oracle@example.com", "password": "Secret123!"},
        )

        # Deactivate via DB
        factory = app.state.db_session_factory

        async def _deactivate():
            async with factory() as session:
                repo = UserRepository(session)
                user = await repo.get_by_email("timing-oracle@example.com")
                user.is_active = False
                await session.commit()

        asyncio.run(_deactivate())

        # Login should fail with 401
        resp = client.post(
            "/auth/login",
            json={"email": "timing-oracle@example.com", "password": "Secret123!"},
        )
        assert resp.status_code == 401
        assert resp.json()["detail"] == "Invalid credentials"

    def test_inactive_user_same_error_as_wrong_password(self, client) -> None:
        """Inactive user must get identical error message as wrong password."""
        import asyncio

        from modules.credit.repo_users import UserRepository
        from modules.credit.router import app

        client.post(
            "/auth/register",
            json={"email": "timing2@example.com", "password": "Secret123!"},
        )

        # Get wrong-password response first
        wrong_pw_resp = client.post(
            "/auth/login",
            json={"email": "timing2@example.com", "password": "WrongP1!"},
        )

        # Deactivate
        factory = app.state.db_session_factory

        async def _deactivate():
            async with factory() as session:
                repo = UserRepository(session)
                user = await repo.get_by_email("timing2@example.com")
                user.is_active = False
                await session.commit()

        asyncio.run(_deactivate())

        inactive_resp = client.post(
            "/auth/login",
            json={"email": "timing2@example.com", "password": "Secret123!"},
        )

        # Same status code and message
        assert inactive_resp.status_code == wrong_pw_resp.status_code
        assert inactive_resp.json()["detail"] == wrong_pw_resp.json()["detail"]
