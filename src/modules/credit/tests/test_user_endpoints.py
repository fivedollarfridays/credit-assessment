"""Tests for user registration, login, password reset, and security — T4.1/T9.2 TDD."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from modules.credit.config import Settings

_SETTINGS = Settings()


def _get_client():
    from modules.credit.router import app

    return TestClient(app)


def _mock_db_factory(mock_session):
    """Create a mock session factory that yields mock_session."""
    factory = MagicMock()
    factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    factory.return_value.__aexit__ = AsyncMock(return_value=None)
    return factory


class TestRegisterEndpoint:
    """Test POST /auth/register."""

    def test_register_returns_201(self):
        client = _get_client()
        resp = client.post(
            "/auth/register",
            json={"email": "new@example.com", "password": "Secret123!"},
        )
        assert resp.status_code == 201

    def test_register_returns_user_email(self):
        client = _get_client()
        resp = client.post(
            "/auth/register",
            json={"email": "new2@example.com", "password": "Secret123!"},
        )
        data = resp.json()
        assert data["email"] == "new2@example.com"

    def test_register_does_not_return_password(self):
        client = _get_client()
        resp = client.post(
            "/auth/register",
            json={"email": "new3@example.com", "password": "Secret123!"},
        )
        data = resp.json()
        assert "password" not in data
        assert "password_hash" not in data

    def test_register_duplicate_email_returns_409(self):
        client = _get_client()
        payload = {"email": "dupe@example.com", "password": "Secret123!"}
        client.post("/auth/register", json=payload)
        resp = client.post("/auth/register", json=payload)
        assert resp.status_code == 409


class TestLoginEndpoint:
    """Test POST /auth/login."""

    def test_login_returns_tokens(self):
        client = _get_client()
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

    def test_login_wrong_password_returns_401(self):
        client = _get_client()
        client.post(
            "/auth/register",
            json={"email": "login2@example.com", "password": "Secret123!"},
        )
        resp = client.post(
            "/auth/login",
            json={"email": "login2@example.com", "password": "WrongPass!"},
        )
        assert resp.status_code == 401

    def test_login_nonexistent_user_returns_401(self):
        client = _get_client()
        resp = client.post(
            "/auth/login",
            json={"email": "noone@example.com", "password": "Secret123!"},
        )
        assert resp.status_code == 401


class TestPasswordReset:
    """Test password reset flow."""

    def test_request_reset_returns_200(self):
        client = _get_client()
        client.post(
            "/auth/register",
            json={"email": "reset@example.com", "password": "Secret123!"},
        )
        resp = client.post(
            "/auth/reset-password",
            json={"email": "reset@example.com"},
        )
        assert resp.status_code == 200

    def test_request_reset_nonexistent_returns_200(self):
        """Returns 200 even for nonexistent email to prevent enumeration."""
        client = _get_client()
        resp = client.post(
            "/auth/reset-password",
            json={"email": "ghost@example.com"},
        )
        assert resp.status_code == 200

    def test_confirm_reset_invalid_token_returns_400(self):
        client = _get_client()
        resp = client.post(
            "/auth/confirm-reset",
            json={"token": "bogus-token", "new_password": "NewPass1!"},
        )
        assert resp.status_code == 400

    def test_confirm_reset_changes_password(self):
        from modules.credit.user_store import _reset_tokens

        client = _get_client()
        client.post(
            "/auth/register",
            json={"email": "reset2@example.com", "password": "OldPass123!"},
        )
        # Request reset — token no longer in HTTP response
        client.post(
            "/auth/reset-password",
            json={"email": "reset2@example.com"},
        )
        # Get token from internal store (simulating email delivery)
        token = next(
            t for t, email in _reset_tokens.items() if email == "reset2@example.com"
        )

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


class TestUserStorePublicAPIs:
    """Test public accessor functions for user store."""

    def test_get_all_users_empty(self):
        from modules.credit.user_store import _users, get_all_users

        saved = dict(_users)
        _users.clear()
        assert get_all_users() == {}
        _users.update(saved)

    def test_get_all_users_returns_copy(self):
        from modules.credit.user_store import _users, get_all_users

        _users["test@x.com"] = {"email": "test@x.com", "role": "viewer"}
        result = get_all_users()
        assert "test@x.com" in result
        # Verify the outer dict is a copy (adding/removing keys doesn't affect original)
        del result["test@x.com"]
        assert "test@x.com" in _users
        _users.pop("test@x.com", None)

    def test_get_user_found(self):
        from modules.credit.user_store import _users, get_user

        _users["found@x.com"] = {"email": "found@x.com", "role": "viewer"}
        assert get_user("found@x.com") is not None
        assert get_user("found@x.com")["email"] == "found@x.com"
        _users.pop("found@x.com", None)

    def test_get_user_not_found(self):
        from modules.credit.user_store import get_user

        assert get_user("nobody@x.com") is None

    def test_count_users(self):
        from modules.credit.user_store import _users, count_users

        saved = dict(_users)
        _users.clear()
        assert count_users() == 0
        _users["a@x.com"] = {"email": "a@x.com"}
        assert count_users() == 1
        _users.clear()
        _users.update(saved)


class TestResetTokenNotLeaked:
    """T9.2: Verify reset token is NOT returned in HTTP response."""

    def test_reset_response_has_no_token_field(self):
        """The reset endpoint must not include reset_token in response body."""
        client = _get_client()
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

    def test_reset_response_identical_for_existing_and_nonexistent(self):
        """Response body must be identical for existing and nonexistent emails."""
        client = _get_client()
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


class TestUpdateUserFieldAllowlist:
    """T9.2: Verify update_user only allows whitelisted fields."""

    def test_rejects_role_injection(self):
        """Passing role= to update_user must NOT change the user's role."""
        from modules.credit.user_store import _users, update_user

        _users["inject1@x.com"] = {
            "email": "inject1@x.com",
            "role": "viewer",
            "password_hash": "hashed",
            "is_active": True,
            "org_id": "org-1",
        }
        update_user("inject1@x.com", role="admin")
        assert _users["inject1@x.com"]["role"] == "viewer"
        _users.pop("inject1@x.com", None)

    def test_rejects_password_hash_injection(self):
        """Passing password_hash= to update_user must NOT change the hash."""
        from modules.credit.user_store import _users, update_user

        _users["inject2@x.com"] = {
            "email": "inject2@x.com",
            "role": "viewer",
            "password_hash": "original_hash",
            "is_active": True,
            "org_id": "org-1",
        }
        update_user("inject2@x.com", password_hash="evil_hash")
        assert _users["inject2@x.com"]["password_hash"] == "original_hash"
        _users.pop("inject2@x.com", None)

    def test_allows_is_active(self):
        """is_active is an allowed field and should be updated."""
        from modules.credit.user_store import _users, update_user

        _users["allow1@x.com"] = {
            "email": "allow1@x.com",
            "role": "viewer",
            "password_hash": "hashed",
            "is_active": True,
            "org_id": "org-1",
        }
        update_user("allow1@x.com", is_active=False)
        assert _users["allow1@x.com"]["is_active"] is False
        # Also cover not-found branch
        assert update_user("nonexistent@x.com", is_active=False) is None
        _users.pop("allow1@x.com", None)


class TestPasswordComplexity:
    """T9.2: Validate password complexity requirements."""

    def test_rejects_short_password(self):
        """Passwords under 8 characters must be rejected."""
        from modules.credit.user_store import validate_password

        with pytest.raises(ValueError, match="at least 8 characters"):
            validate_password("Ab1!xyz")

    def test_rejects_no_uppercase(self):
        """Passwords without uppercase letters must be rejected."""
        from modules.credit.user_store import validate_password

        with pytest.raises(ValueError, match="uppercase"):
            validate_password("abcdefg1!")

    def test_rejects_no_digit(self):
        """Passwords without digits must be rejected."""
        from modules.credit.user_store import validate_password

        with pytest.raises(ValueError, match="digit"):
            validate_password("Abcdefgh!")

    def test_rejects_no_special_char(self):
        """Passwords without special characters or lowercase must be rejected."""
        from modules.credit.user_store import validate_password

        with pytest.raises(ValueError, match="special character"):
            validate_password("Abcdefg1")
        with pytest.raises(ValueError, match="lowercase"):
            validate_password("ABCDEFG1!")

    def test_accepts_valid_password(self):
        """A password meeting all criteria should be accepted."""
        from modules.credit.user_store import validate_password

        result = validate_password("Secret123!")
        assert result == "Secret123!"

    def test_confirm_reset_rejects_weak_password(self):
        """The confirm-reset endpoint must reject weak passwords."""
        from modules.credit.user_store import _reset_tokens

        client = _get_client()
        client.post(
            "/auth/register",
            json={"email": "weakreset@example.com", "password": "Secret123!"},
        )
        client.post(
            "/auth/reset-password",
            json={"email": "weakreset@example.com"},
        )
        token = next(
            t for t, email in _reset_tokens.items() if email == "weakreset@example.com"
        )
        resp = client.post(
            "/auth/confirm-reset",
            json={"token": token, "new_password": "weak"},
        )
        assert resp.status_code == 422


class TestSetUserRole:
    """Test set_user_role privileged function."""

    def test_set_user_role_updates_role(self):
        from modules.credit.roles import Role
        from modules.credit.user_store import _users, set_user_role

        _users["role-test@x.com"] = {
            "email": "role-test@x.com",
            "role": "viewer",
            "password_hash": "h",
            "is_active": True,
            "org_id": "org-1",
        }
        result = set_user_role("role-test@x.com", Role.ADMIN)
        assert result is not None
        assert result["role"] == "admin"
        _users.pop("role-test@x.com", None)

    def test_set_user_role_returns_none_for_missing(self):
        from modules.credit.roles import Role
        from modules.credit.user_store import set_user_role

        assert set_user_role("nobody@x.com", Role.ADMIN) is None


class TestUserStoreMutations:
    """Test create_user, store/pop reset token, set_password_hash."""

    def test_create_user_stores_and_returns(self):
        from modules.credit.user_store import _users, create_user

        _users.pop("cu@x.com", None)
        user = create_user("cu@x.com", password_hash="h", role="viewer", org_id="org-1")
        assert user["email"] == "cu@x.com"
        assert user["is_active"] is True
        assert _users["cu@x.com"] is user
        _users.pop("cu@x.com", None)

    def test_create_user_duplicate_raises(self):
        from modules.credit.user_store import _users, create_user

        _users["dup@x.com"] = {"email": "dup@x.com"}
        with pytest.raises(ValueError, match="already registered"):
            create_user("dup@x.com", password_hash="h", role="viewer", org_id="org-1")
        _users.pop("dup@x.com", None)

    def test_store_reset_token(self):
        from modules.credit.user_store import _reset_tokens, store_reset_token

        store_reset_token("tok-1", "a@x.com")
        assert _reset_tokens["tok-1"] == "a@x.com"
        _reset_tokens.pop("tok-1", None)

    def test_store_reset_token_evicts_oldest(self):
        from modules.credit.user_store import (
            _MAX_RESET_TOKENS,
            _reset_tokens,
            store_reset_token,
        )

        saved = dict(_reset_tokens)
        _reset_tokens.clear()
        for i in range(_MAX_RESET_TOKENS):
            _reset_tokens[f"old-{i}"] = f"u{i}@x.com"
        store_reset_token("new-tok", "new@x.com")
        assert len(_reset_tokens) == _MAX_RESET_TOKENS
        assert "old-0" not in _reset_tokens
        assert "new-tok" in _reset_tokens
        _reset_tokens.clear()
        _reset_tokens.update(saved)

    def test_pop_reset_token_found(self):
        from modules.credit.user_store import _reset_tokens, pop_reset_token

        _reset_tokens["pop-tok"] = "pop@x.com"
        assert pop_reset_token("pop-tok") == "pop@x.com"
        assert "pop-tok" not in _reset_tokens

    def test_pop_reset_token_missing(self):
        from modules.credit.user_store import pop_reset_token

        assert pop_reset_token("nonexistent") is None

    def test_set_password_hash(self):
        from modules.credit.user_store import _users, set_password_hash

        _users["pw@x.com"] = {"email": "pw@x.com", "password_hash": "old"}
        set_password_hash("pw@x.com", "new-hash")
        assert _users["pw@x.com"]["password_hash"] == "new-hash"
        _users.pop("pw@x.com", None)
