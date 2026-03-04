"""Tests for dashboard — usage analytics, customer management, system health."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from modules.credit.dashboard import (
    get_customer_detail,
    get_customer_list,
    get_system_health,
    get_usage_overview,
    update_customer,
)
from modules.credit.roles import Role
from modules.credit.router import app


@pytest.fixture(autouse=True)
def _clean():
    from modules.credit.audit import reset_audit_trail
    from modules.credit.billing import _subscriptions
    from modules.credit.tenant import _org_assessments
    from modules.credit.user_routes import _users

    _users.clear()
    _subscriptions.clear()
    _org_assessments.clear()
    reset_audit_trail()
    yield
    _users.clear()
    _subscriptions.clear()
    _org_assessments.clear()
    reset_audit_trail()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def _seed_users():
    from modules.credit.user_routes import _users
    from modules.credit.password import hash_password

    _users["alice@acme.com"] = {
        "email": "alice@acme.com",
        "password_hash": hash_password("pw"),
        "is_active": True,
        "role": "admin",
        "org_id": "org-alice",
    }
    _users["bob@corp.com"] = {
        "email": "bob@corp.com",
        "password_hash": hash_password("pw"),
        "is_active": True,
        "role": "viewer",
        "org_id": "org-bob",
    }


def _seed_subscriptions():
    from modules.credit.billing import _subscriptions

    _subscriptions["alice@acme.com"] = {
        "subscription_id": "sub_1",
        "status": "active",
        "plan": "pro",
    }
    _subscriptions["bob@corp.com"] = {
        "subscription_id": "sub_2",
        "status": "active",
        "plan": "starter",
    }


def _seed_assessments():
    from modules.credit.tenant import store_org_assessment

    store_org_assessment(
        "org-alice", {"score": 85, "timestamp": "2026-03-01T00:00:00Z"}
    )
    store_org_assessment(
        "org-alice", {"score": 72, "timestamp": "2026-03-02T00:00:00Z"}
    )
    store_org_assessment("org-bob", {"score": 60, "timestamp": "2026-03-01T00:00:00Z"})


# --- Usage overview ---


class TestUsageOverview:
    def test_empty_state(self):
        result = get_usage_overview()
        assert result["total_users"] == 0
        assert result["total_assessments"] == 0
        assert result["active_subscriptions"] == 0

    def test_with_data(self):
        _seed_users()
        _seed_subscriptions()
        _seed_assessments()
        result = get_usage_overview()
        assert result["total_users"] == 2
        assert result["total_assessments"] == 3
        assert result["active_subscriptions"] == 2

    def test_counts_only_active_subscriptions(self):
        _seed_users()
        from modules.credit.billing import _subscriptions

        _subscriptions["alice@acme.com"] = {
            "subscription_id": "sub_1",
            "status": "canceled",
            "plan": "pro",
        }
        result = get_usage_overview()
        assert result["active_subscriptions"] == 0


# --- Customer list ---


class TestCustomerList:
    def test_empty(self):
        assert get_customer_list() == []

    def test_returns_customers(self):
        _seed_users()
        _seed_subscriptions()
        _seed_assessments()
        customers = get_customer_list()
        assert len(customers) == 2
        alice = next(c for c in customers if c["email"] == "alice@acme.com")
        assert alice["role"] == "admin"
        assert alice["plan"] == "pro"
        assert alice["assessment_count"] == 2

    def test_customer_without_subscription(self):
        _seed_users()
        customers = get_customer_list()
        alice = next(c for c in customers if c["email"] == "alice@acme.com")
        assert alice["plan"] is None


# --- Customer detail ---


class TestCustomerDetail:
    def test_found(self):
        _seed_users()
        _seed_subscriptions()
        _seed_assessments()
        detail = get_customer_detail("alice@acme.com")
        assert detail is not None
        assert detail["email"] == "alice@acme.com"
        assert detail["assessment_count"] == 2
        assert detail["plan"] == "pro"

    def test_not_found(self):
        assert get_customer_detail("nobody@test.com") is None


# --- Update customer ---


class TestUpdateCustomer:
    def test_update_role(self):
        _seed_users()
        result = update_customer("alice@acme.com", role=Role.ANALYST)
        assert result is not None
        assert result["role"] == "analyst"

    def test_deactivate(self):
        _seed_users()
        result = update_customer("alice@acme.com", is_active=False)
        assert result is not None
        assert result["is_active"] is False

    def test_not_found(self):
        assert update_customer("nobody@test.com", role=Role.ADMIN) is None

    def test_no_fields_returns_current_data(self):
        """When neither role nor is_active is provided, return current user info."""
        _seed_users()
        result = update_customer("alice@acme.com")
        assert result is not None
        assert result["email"] == "alice@acme.com"
        assert result["role"] == "admin"
        assert result["is_active"] is True
        # Not found case with no fields
        assert update_customer("nobody@test.com") is None

    def test_returns_post_mutation_data(self):
        """Returned dict must reflect state AFTER mutations, not before."""
        stale = {"email": "a@b.com", "role": "viewer", "is_active": True}
        fresh = {"email": "a@b.com", "role": "analyst", "is_active": True}
        call_count = {"n": 0}

        def mock_get_user(email):
            call_count["n"] += 1
            if call_count["n"] == 1:
                return stale
            return fresh

        with patch("modules.credit.dashboard.get_user", side_effect=mock_get_user):
            with patch("modules.credit.dashboard.set_user_role"):
                result = update_customer("a@b.com", role=Role.ANALYST)
        assert result is not None
        assert result["role"] == "analyst"
        assert call_count["n"] == 2


# --- System health ---


class TestSystemHealth:
    def test_returns_health_dict(self):
        health = get_system_health()
        assert "status" in health
        assert "users" in health
        assert "audit_entries" in health


# --- API Endpoints ---


class TestDashboardEndpoints:
    def test_overview_requires_auth(self, client):
        resp = client.get("/v1/dashboard/overview")
        assert resp.status_code in (401, 403)

    def test_overview_requires_admin(self, client):
        _seed_users()
        with patch("modules.credit.assess_routes.settings") as mock_settings:
            mock_settings.jwt_secret = "test-secret"
            mock_settings.jwt_algorithm = "HS256"
            mock_settings.api_key = None
            from modules.credit.auth import create_access_token

            token = create_access_token(
                subject="bob@corp.com",
                secret="test-secret",
                algorithm="HS256",
                expire_minutes=30,
            )
            resp = client.get(
                "/v1/dashboard/overview",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 403

    def test_overview_admin_success(self, client):
        _seed_users()
        _seed_subscriptions()
        _seed_assessments()
        with patch("modules.credit.assess_routes.settings") as mock_settings:
            mock_settings.jwt_secret = "test-secret"
            mock_settings.jwt_algorithm = "HS256"
            mock_settings.api_key = None
            from modules.credit.auth import create_access_token

            token = create_access_token(
                subject="alice@acme.com",
                secret="test-secret",
                algorithm="HS256",
                expire_minutes=30,
            )
            resp = client.get(
                "/v1/dashboard/overview",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["total_users"] == 2
            assert data["total_assessments"] == 3

    def test_customers_list_endpoint(self, client):
        _seed_users()
        with patch("modules.credit.assess_routes.settings") as mock_settings:
            mock_settings.jwt_secret = "test-secret"
            mock_settings.jwt_algorithm = "HS256"
            mock_settings.api_key = None
            from modules.credit.auth import create_access_token

            token = create_access_token(
                subject="alice@acme.com",
                secret="test-secret",
                algorithm="HS256",
                expire_minutes=30,
            )
            resp = client.get(
                "/v1/dashboard/customers",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 200
            assert len(resp.json()) == 2

    def test_customer_detail_endpoint(self, client):
        _seed_users()
        _seed_subscriptions()
        with patch("modules.credit.assess_routes.settings") as mock_settings:
            mock_settings.jwt_secret = "test-secret"
            mock_settings.jwt_algorithm = "HS256"
            mock_settings.api_key = None
            from modules.credit.auth import create_access_token

            token = create_access_token(
                subject="alice@acme.com",
                secret="test-secret",
                algorithm="HS256",
                expire_minutes=30,
            )
            resp = client.get(
                "/v1/dashboard/customers/alice@acme.com",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 200
            assert resp.json()["email"] == "alice@acme.com"

    def test_customer_detail_not_found(self, client):
        _seed_users()
        with patch("modules.credit.assess_routes.settings") as mock_settings:
            mock_settings.jwt_secret = "test-secret"
            mock_settings.jwt_algorithm = "HS256"
            mock_settings.api_key = None
            from modules.credit.auth import create_access_token

            token = create_access_token(
                subject="alice@acme.com",
                secret="test-secret",
                algorithm="HS256",
                expire_minutes=30,
            )
            resp = client.get(
                "/v1/dashboard/customers/nobody@test.com",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 404

    def test_update_customer_endpoint(self, client):
        _seed_users()
        with patch("modules.credit.assess_routes.settings") as mock_settings:
            mock_settings.jwt_secret = "test-secret"
            mock_settings.jwt_algorithm = "HS256"
            mock_settings.api_key = None
            from modules.credit.auth import create_access_token

            token = create_access_token(
                subject="alice@acme.com",
                secret="test-secret",
                algorithm="HS256",
                expire_minutes=30,
            )
            resp = client.put(
                "/v1/dashboard/customers/bob@corp.com",
                json={"role": "analyst"},
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 200
            assert resp.json()["role"] == "analyst"

    def test_delete_customer_endpoint(self, client):
        _seed_users()
        with patch("modules.credit.assess_routes.settings") as mock_settings:
            mock_settings.jwt_secret = "test-secret"
            mock_settings.jwt_algorithm = "HS256"
            mock_settings.api_key = None
            from modules.credit.auth import create_access_token

            token = create_access_token(
                subject="alice@acme.com",
                secret="test-secret",
                algorithm="HS256",
                expire_minutes=30,
            )
            resp = client.delete(
                "/v1/dashboard/customers/bob@corp.com",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 200
            from modules.credit.user_routes import _users

            assert _users["bob@corp.com"]["is_active"] is False

    def test_health_endpoint(self, client):
        _seed_users()
        with patch("modules.credit.assess_routes.settings") as mock_settings:
            mock_settings.jwt_secret = "test-secret"
            mock_settings.jwt_algorithm = "HS256"
            mock_settings.api_key = None
            from modules.credit.auth import create_access_token

            token = create_access_token(
                subject="alice@acme.com",
                secret="test-secret",
                algorithm="HS256",
                expire_minutes=30,
            )
            resp = client.get(
                "/v1/dashboard/health",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 200
            assert "status" in resp.json()

    def test_customer_update_rejects_invalid_role(self, client):
        _seed_users()
        with patch("modules.credit.assess_routes.settings") as mock_settings:
            mock_settings.jwt_secret = "test-secret"
            mock_settings.jwt_algorithm = "HS256"
            mock_settings.api_key = None
            from modules.credit.auth import create_access_token

            token = create_access_token(
                subject="alice@acme.com",
                secret="test-secret",
                algorithm="HS256",
                expire_minutes=30,
            )
            resp = client.put(
                "/v1/dashboard/customers/bob@corp.com",
                json={"role": "superadmin"},
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 422

    def test_put_and_delete_customer_not_found(self, client, admin_headers):
        """PUT and DELETE return 404 for unknown customer emails."""
        resp = client.put(
            "/v1/dashboard/customers/unknown@test.com",
            json={"role": "analyst"},
            headers=admin_headers,
        )
        assert resp.status_code == 404
        resp = client.delete(
            "/v1/dashboard/customers/unknown@test.com",
            headers=admin_headers,
        )
        assert resp.status_code == 404

    def test_serve_dashboard_page(self, client):
        """GET /dashboard serves the static HTML file."""
        resp = client.get("/dashboard")
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]
