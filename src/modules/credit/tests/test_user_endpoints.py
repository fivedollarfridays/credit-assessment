"""Tests for user registration, login, password reset, and security — T4.1/T9.2 TDD.

Migrated from in-memory user_store to DB-backed repositories.
Repository unit tests live in test_repositories_new.py.
This file exercises behavior through the API (register, login, reset endpoints).
"""

import asyncio

import pytest

from modules.credit.user_store import validate_password


def _get_reset_token_from_db(app, email: str) -> str | None:
    """Retrieve a reset token for the given email directly from DB."""

    factory = app.state.db_session_factory

    async def _fetch():
        from sqlalchemy import select

        from modules.credit.models_db import ResetToken

        async with factory() as session:
            result = await session.execute(
                select(ResetToken).where(ResetToken.email == email)
            )
            entry = result.scalar_one_or_none()
            return entry.token if entry else None

    return asyncio.run(_fetch())


class TestRegisterEndpoint:
    """Test POST /auth/register."""

    def test_register_returns_201(self, client):
        resp = client.post(
            "/auth/register",
            json={"email": "new@example.com", "password": "Secret123!"},
        )
        assert resp.status_code == 201

    def test_register_returns_user_email(self, client):
        resp = client.post(
            "/auth/register",
            json={"email": "new2@example.com", "password": "Secret123!"},
        )
        data = resp.json()
        assert data["email"] == "new2@example.com"

    def test_register_does_not_return_password(self, client):
        resp = client.post(
            "/auth/register",
            json={"email": "new3@example.com", "password": "Secret123!"},
        )
        data = resp.json()
        assert "password" not in data
        assert "password_hash" not in data

    def test_register_duplicate_email_returns_409(self, client):
        payload = {"email": "dupe@example.com", "password": "Secret123!"}
        client.post("/auth/register", json=payload)
        resp = client.post("/auth/register", json=payload)
        assert resp.status_code == 409


class TestLoginEndpoint:
    """Test POST /auth/login."""

    def test_login_returns_tokens(self, client):
        client.post(
            "/auth/register",
            json={"email": "login@example.com", "password": "Secret123!"},
        )
        resp = client.post(
            "/auth/login",
            json={"email": "login@example.com", "password": "Secret123!"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password_returns_401(self, client):
        client.post(
            "/auth/register",
            json={"email": "login2@example.com", "password": "Secret123!"},
        )
        resp = client.post(
            "/auth/login",
            json={"email": "login2@example.com", "password": "WrongPass!"},
        )
        assert resp.status_code == 401

    def test_login_nonexistent_user_returns_401(self, client):
        resp = client.post(
            "/auth/login",
            json={"email": "noone@example.com", "password": "Secret123!"},
        )
        assert resp.status_code == 401


class TestPasswordReset:
    """Test password reset flow."""

    def test_request_reset_returns_200(self, client):
        client.post(
            "/auth/register",
            json={"email": "reset@example.com", "password": "Secret123!"},
        )
        resp = client.post(
            "/auth/reset-password",
            json={"email": "reset@example.com"},
        )
        assert resp.status_code == 200

    def test_request_reset_nonexistent_returns_200(self, client):
        """Returns 200 even for nonexistent email to prevent enumeration."""
        resp = client.post(
            "/auth/reset-password",
            json={"email": "ghost@example.com"},
        )
        assert resp.status_code == 200

    def test_confirm_reset_invalid_token_returns_400(self, client):
        resp = client.post(
            "/auth/confirm-reset",
            json={"token": "bogus-token", "new_password": "NewPass1!"},
        )
        assert resp.status_code == 400

    def test_confirm_reset_changes_password(self, client):
        from modules.credit.router import app

        client.post(
            "/auth/register",
            json={"email": "reset2@example.com", "password": "OldPass123!"},
        )
        # Request reset -- token stored in DB (simulating email delivery)
        client.post(
            "/auth/reset-password",
            json={"email": "reset2@example.com"},
        )
        # Retrieve token from DB
        token = _get_reset_token_from_db(app, "reset2@example.com")
        assert token is not None, "Reset token should have been stored in DB"

        # Confirm reset with new password
        resp = client.post(
            "/auth/confirm-reset",
            json={"token": token, "new_password": "NewPass456!"},
        )
        assert resp.status_code == 200

        # Login with new password
        resp = client.post(
            "/auth/login",
            json={"email": "reset2@example.com", "password": "NewPass456!"},
        )
        assert resp.status_code == 200


class TestUserLookupViaAPI:
    """Test user data access through the API (replaces in-memory store tests)."""

    def test_register_creates_user_accessible_via_login(self, client):
        """Registering a user makes them accessible via login."""
        client.post(
            "/auth/register",
            json={"email": "lookup@example.com", "password": "Secret123!"},
        )
        resp = client.post(
            "/auth/login",
            json={"email": "lookup@example.com", "password": "Secret123!"},
        )
        assert resp.status_code == 200

    def test_nonexistent_user_cannot_login(self, client):
        """A user that was never created cannot log in."""
        resp = client.post(
            "/auth/login",
            json={"email": "nobody@example.com", "password": "Secret123!"},
        )
        assert resp.status_code == 401

    def test_admin_can_list_users(self, client, admin_headers):
        """Admin endpoint returns registered users."""
        client.post(
            "/auth/register",
            json={"email": "listed@example.com", "password": "Secret123!"},
        )
        resp = client.get("/admin/users", headers=admin_headers)
        assert resp.status_code == 200
        emails = [u["email"] for u in resp.json()]
        assert "listed@example.com" in emails


class TestResetTokenNotLeaked:
    """T9.2: Verify reset token is NOT returned in HTTP response."""

    def test_reset_response_has_no_token_field(self, client):
        """The reset endpoint must not include reset_token in response body."""
        client.post(
            "/auth/register",
            json={"email": "leak1@example.com", "password": "Secret123!"},
        )
        resp = client.post(
            "/auth/reset-password",
            json={"email": "leak1@example.com"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "reset_token" not in data

    def test_reset_response_identical_for_existing_and_nonexistent(self, client):
        """Response body must be identical for existing and nonexistent emails."""
        client.post(
            "/auth/register",
            json={"email": "leak2@example.com", "password": "Secret123!"},
        )
        resp_existing = client.post(
            "/auth/reset-password",
            json={"email": "leak2@example.com"},
        )
        resp_ghost = client.post(
            "/auth/reset-password",
            json={"email": "nobody-leak2@example.com"},
        )
        assert resp_existing.json() == resp_ghost.json()


class TestFieldIsolationViaAPI:
    """T9.2: Verify the repository/API only allows safe field mutations.

    The old update_user allowlist is replaced by separate repository methods
    (set_role, set_password_hash) that are only callable from admin/internal code.
    The register endpoint must not accept role or password_hash fields.
    """

    def test_register_ignores_extra_role_field(self, client, admin_headers):
        """Passing role in register payload must not change the default role."""
        resp = client.post(
            "/auth/register",
            json={
                "email": "inject1@example.com",
                "password": "Secret123!",
                "role": "admin",
            },
        )
        assert resp.status_code == 201
        # Verify via admin endpoint that the user is NOT admin
        resp = client.get("/admin/users", headers=admin_headers)
        user = next(
            (u for u in resp.json() if u["email"] == "inject1@example.com"), None
        )
        assert user is not None
        assert user["role"] == "viewer"

    def test_register_ignores_extra_password_hash_field(self, client):
        """Passing password_hash in register payload must not bypass hashing."""
        resp = client.post(
            "/auth/register",
            json={
                "email": "inject2@example.com",
                "password": "Secret123!",
                "password_hash": "evil_hash",
            },
        )
        assert resp.status_code == 201
        # Can log in with the actual password (not the injected hash)
        resp = client.post(
            "/auth/login",
            json={"email": "inject2@example.com", "password": "Secret123!"},
        )
        assert resp.status_code == 200


class TestPasswordComplexity:
    """T9.2: Validate password complexity requirements."""

    def test_rejects_short_password(self):
        """Passwords under 8 characters must be rejected."""
        with pytest.raises(ValueError, match="at least 8 characters"):
            validate_password("Ab1!xyz")

    def test_rejects_no_uppercase(self):
        """Passwords without uppercase letters must be rejected."""
        with pytest.raises(ValueError, match="uppercase"):
            validate_password("abcdefg1!")

    def test_rejects_no_digit(self):
        """Passwords without digits must be rejected."""
        with pytest.raises(ValueError, match="digit"):
            validate_password("Abcdefgh!")

    def test_rejects_no_special_char(self):
        """Passwords without special characters or lowercase must be rejected."""
        with pytest.raises(ValueError, match="special character"):
            validate_password("Abcdefg1")
        with pytest.raises(ValueError, match="lowercase"):
            validate_password("ABCDEFG1!")

    def test_accepts_valid_password(self):
        """A password meeting all criteria should be accepted."""
        result = validate_password("Secret123!")
        assert result == "Secret123!"

    def test_confirm_reset_rejects_weak_password(self, client):
        """The confirm-reset endpoint must reject weak passwords."""
        from modules.credit.router import app

        client.post(
            "/auth/register",
            json={"email": "weakreset@example.com", "password": "Secret123!"},
        )
        client.post(
            "/auth/reset-password",
            json={"email": "weakreset@example.com"},
        )
        token = _get_reset_token_from_db(app, "weakreset@example.com")
        assert token is not None
        resp = client.post(
            "/auth/confirm-reset",
            json={"token": token, "new_password": "weak"},
        )
        assert resp.status_code == 422


class TestSetRoleViaRepository:
    """Test role changes through the repository (replaces in-memory set_user_role)."""

    def test_set_role_updates_role(self, client, admin_headers):
        """Creating a user via register gives viewer role; verify via admin API."""
        from modules.credit.tests.conftest import create_test_user
        from modules.credit.router import app

        create_test_user(app, "role-test@example.com", role="viewer")
        # Verify initial role
        resp = client.get("/admin/users", headers=admin_headers)
        user = next(
            (u for u in resp.json() if u["email"] == "role-test@example.com"),
            None,
        )
        assert user is not None
        assert user["role"] == "viewer"

        # Change role via repository
        from modules.credit.repo_users import UserRepository

        factory = app.state.db_session_factory

        async def _set():
            async with factory() as session:
                repo = UserRepository(session)
                return await repo.set_role("role-test@example.com", "admin")

        result = asyncio.run(_set())
        assert result is True

        # Verify updated role via admin API
        resp = client.get("/admin/users", headers=admin_headers)
        user = next(
            (u for u in resp.json() if u["email"] == "role-test@example.com"),
            None,
        )
        assert user["role"] == "admin"

    def test_set_role_returns_false_for_missing(self):
        """Setting role on a nonexistent user returns False."""
        from modules.credit.database import create_engine, get_session_factory
        from modules.credit.models_db import Base
        from modules.credit.repo_users import UserRepository

        engine = create_engine("sqlite+aiosqlite://")

        async def _run():
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            factory = get_session_factory(engine)
            async with factory() as session:
                repo = UserRepository(session)
                result = await repo.set_role("nobody@x.com", "admin")
                assert result is False

        asyncio.run(_run())


class TestAccountLockout:
    """T18.4: Account lockout after repeated failed logins."""

    def test_five_failures_locks_account(self, client):
        """After 5 bad passwords, account returns 429."""
        client.post(
            "/auth/register",
            json={"email": "lockout@example.com", "password": "Secret123!"},
        )
        for _ in range(5):
            resp = client.post(
                "/auth/login",
                json={"email": "lockout@example.com", "password": "WrongPass!"},
            )
            assert resp.status_code == 401

        # 6th attempt should be locked
        resp = client.post(
            "/auth/login",
            json={"email": "lockout@example.com", "password": "WrongPass!"},
        )
        assert resp.status_code == 429
        assert "Retry-After" in resp.headers
        assert resp.json()["detail"] == "Account temporarily locked"

    def test_correct_password_while_locked_returns_429(self, client):
        """Even correct password returns 429 when locked."""
        client.post(
            "/auth/register",
            json={"email": "lockright@example.com", "password": "Secret123!"},
        )
        for _ in range(5):
            client.post(
                "/auth/login",
                json={"email": "lockright@example.com", "password": "Bad1!"},
            )
        resp = client.post(
            "/auth/login",
            json={"email": "lockright@example.com", "password": "Secret123!"},
        )
        assert resp.status_code == 429

    def test_successful_login_resets_counter(self, client):
        """A successful login resets the failure counter."""
        client.post(
            "/auth/register",
            json={"email": "resetcnt@example.com", "password": "Secret123!"},
        )
        # 3 failures (below threshold)
        for _ in range(3):
            client.post(
                "/auth/login",
                json={"email": "resetcnt@example.com", "password": "WrongP1!"},
            )
        # Successful login
        resp = client.post(
            "/auth/login",
            json={"email": "resetcnt@example.com", "password": "Secret123!"},
        )
        assert resp.status_code == 200
        # 4 more failures should not lock (counter was reset)
        for _ in range(4):
            client.post(
                "/auth/login",
                json={"email": "resetcnt@example.com", "password": "Wrong1!"},
            )
        resp = client.post(
            "/auth/login",
            json={"email": "resetcnt@example.com", "password": "Secret123!"},
        )
        assert resp.status_code == 200

    def test_lockout_expires_after_duration(self, client):
        """Account unlocks after lockout duration expires."""
        from datetime import datetime, timedelta, timezone
        from unittest.mock import patch

        client.post(
            "/auth/register",
            json={"email": "expire@example.com", "password": "Secret123!"},
        )
        for _ in range(5):
            client.post(
                "/auth/login",
                json={"email": "expire@example.com", "password": "WrongPass!"},
            )
        # Verify locked
        resp = client.post(
            "/auth/login",
            json={"email": "expire@example.com", "password": "Secret123!"},
        )
        assert resp.status_code == 429

        # Time travel past lockout
        future = datetime.now(timezone.utc) + timedelta(minutes=16)
        with patch("modules.credit.user_routes.datetime") as mock_dt:
            mock_dt.now.return_value = future
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            resp = client.post(
                "/auth/login",
                json={"email": "expire@example.com", "password": "Secret123!"},
            )
            assert resp.status_code == 200

    def test_lockout_creates_audit_entry(self, client):
        """Lockout event is logged to audit trail."""
        from modules.credit.audit import get_audit_trail, reset_audit_trail

        reset_audit_trail()
        client.post(
            "/auth/register",
            json={"email": "auditlock@example.com", "password": "Secret123!"},
        )
        for _ in range(5):
            client.post(
                "/auth/login",
                json={"email": "auditlock@example.com", "password": "WrongP1!"},
            )
        entries = get_audit_trail(action="account_locked")
        assert len(entries) == 1
        assert entries[0]["request_summary"]["email"] == "auditlock@example.com"

    def test_deactivated_user_cannot_login(self, client):
        """Deactivated user returns 401 even with correct password."""
        from modules.credit.repo_users import UserRepository
        from modules.credit.router import app

        client.post(
            "/auth/register",
            json={"email": "deact@example.com", "password": "Secret123!"},
        )
        # Deactivate via DB
        factory = app.state.db_session_factory

        async def _deactivate():
            async with factory() as session:
                repo = UserRepository(session)
                user = await repo.get_by_email("deact@example.com")
                user.is_active = False
                await session.commit()

        asyncio.run(_deactivate())

        resp = client.post(
            "/auth/login",
            json={"email": "deact@example.com", "password": "Secret123!"},
        )
        assert resp.status_code == 401

    def test_nonexistent_user_returns_401_not_429(self, client):
        """Login for nonexistent user returns 401, not lockout."""
        for _ in range(10):
            resp = client.post(
                "/auth/login",
                json={"email": "ghost@example.com", "password": "WrongP1!"},
            )
            assert resp.status_code == 401
