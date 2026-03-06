"""Tests for dashboard — usage analytics, customer management, system health."""

from __future__ import annotations

import asyncio

from .conftest import create_test_user


def _seed_subscriptions_db(app):
    """Seed subscriptions in the database."""
    from modules.credit.billing import update_subscription

    factory = app.state.db_session_factory

    async def _insert():
        async with factory() as session:
            await update_subscription(
                session, "alice@acme.com", "sub_1", "active", "pro"
            )
            await update_subscription(
                session, "bob@corp.com", "sub_2", "active", "starter"
            )

    asyncio.run(_insert())


def _seed_canceled_subscription(app, email):
    """Seed a canceled subscription in the database."""
    from modules.credit.billing import update_subscription

    factory = app.state.db_session_factory

    async def _insert():
        async with factory() as session:
            await update_subscription(session, email, "sub_1", "canceled", "pro")

    asyncio.run(_insert())


def _seed_assessments(app):
    from modules.credit.repo_assessments import AssessmentRepository

    factory = app.state.db_session_factory

    async def _insert():
        async with factory() as session:
            repo = AssessmentRepository(session)
            await repo.save_assessment(
                credit_score=85,
                score_band="good",
                barrier_severity="low",
                readiness_score=80,
                request_payload={},
                response_payload={},
                org_id="org-alice",
            )
            await repo.save_assessment(
                credit_score=72,
                score_band="good",
                barrier_severity="low",
                readiness_score=70,
                request_payload={},
                response_payload={},
                org_id="org-alice",
            )
            await repo.save_assessment(
                credit_score=60,
                score_band="fair",
                barrier_severity="medium",
                readiness_score=55,
                request_payload={},
                response_payload={},
                org_id="org-bob",
            )

    asyncio.run(_insert())


def _seed_users(app):
    """Create alice and bob test users in the DB."""
    create_test_user(app, "alice@acme.com", role="admin", org_id="org-alice")
    create_test_user(app, "bob@corp.com", role="viewer", org_id="org-bob")


# --- Usage overview (via API) ---


class TestUsageOverview:
    def test_empty_state(self, client, admin_headers):
        resp = client.get("/v1/dashboard/overview", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        # Only the admin@test.com user from admin_headers fixture exists
        assert data["total_users"] == 1
        assert data["total_assessments"] == 0
        assert data["active_subscriptions"] == 0

    def test_with_data(self, client, admin_headers):
        from modules.credit.router import app

        _seed_users(app)
        _seed_subscriptions_db(app)
        _seed_assessments(app)
        resp = client.get("/v1/dashboard/overview", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        # admin@test.com + alice + bob = 3
        assert data["total_users"] == 3
        assert data["total_assessments"] == 3
        assert data["active_subscriptions"] == 2

    def test_counts_only_active_subscriptions(self, client, admin_headers):
        from modules.credit.router import app

        _seed_users(app)
        _seed_canceled_subscription(app, "alice@acme.com")
        resp = client.get("/v1/dashboard/overview", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json()["active_subscriptions"] == 0


# --- Customer list (via API) ---


class TestCustomerList:
    def test_empty_returns_only_admin(self, client, admin_headers):
        resp = client.get("/v1/dashboard/customers", headers=admin_headers)
        assert resp.status_code == 200
        customers = resp.json()
        # Only the admin fixture user
        assert len(customers) == 1
        assert customers[0]["email"] == "admin@test.com"

    def test_returns_customers(self, client, admin_headers):
        from modules.credit.router import app

        _seed_users(app)
        _seed_subscriptions_db(app)
        _seed_assessments(app)
        resp = client.get("/v1/dashboard/customers", headers=admin_headers)
        assert resp.status_code == 200
        customers = resp.json()
        # admin@test.com + alice + bob = 3
        assert len(customers) == 3
        alice = next(c for c in customers if c["email"] == "alice@acme.com")
        assert alice["role"] == "admin"
        assert alice["plan"] == "pro"
        assert alice["assessment_count"] == 2

    def test_customer_without_subscription(self, client, admin_headers):
        from modules.credit.router import app

        _seed_users(app)
        resp = client.get("/v1/dashboard/customers", headers=admin_headers)
        assert resp.status_code == 200
        customers = resp.json()
        alice = next(c for c in customers if c["email"] == "alice@acme.com")
        assert alice["plan"] is None


# --- Customer detail (via API) ---


class TestCustomerDetail:
    def test_found(self, client, admin_headers):
        from modules.credit.router import app

        _seed_users(app)
        _seed_subscriptions_db(app)
        _seed_assessments(app)
        resp = client.get(
            "/v1/dashboard/customers/alice@acme.com", headers=admin_headers
        )
        assert resp.status_code == 200
        detail = resp.json()
        assert detail["email"] == "alice@acme.com"
        assert detail["assessment_count"] == 2
        assert detail["plan"] == "pro"

    def test_not_found(self, client, admin_headers):
        resp = client.get(
            "/v1/dashboard/customers/nobody@test.com", headers=admin_headers
        )
        assert resp.status_code == 404


# --- Update customer (via API) ---


class TestUpdateCustomer:
    def test_update_role(self, client, admin_headers):
        from modules.credit.router import app

        _seed_users(app)
        resp = client.put(
            "/v1/dashboard/customers/alice@acme.com",
            json={"role": "analyst"},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["role"] == "analyst"

    def test_deactivate(self, client, admin_headers):
        from modules.credit.router import app

        _seed_users(app)
        resp = client.put(
            "/v1/dashboard/customers/alice@acme.com",
            json={"is_active": False},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["is_active"] is False

    def test_not_found(self, client, admin_headers):
        resp = client.put(
            "/v1/dashboard/customers/nobody@test.com",
            json={"role": "admin"},
            headers=admin_headers,
        )
        assert resp.status_code == 404

    def test_no_fields_returns_current_data(self, client, admin_headers):
        """When neither role nor is_active is provided, return current user info."""
        from modules.credit.router import app

        _seed_users(app)
        resp = client.put(
            "/v1/dashboard/customers/alice@acme.com",
            json={},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == "alice@acme.com"
        assert data["role"] == "admin"
        assert data["is_active"] is True

    def test_update_reflects_post_mutation_state(self, client, admin_headers):
        """Returned dict reflects state AFTER mutations, not before."""
        from modules.credit.router import app

        create_test_user(app, "a@b.com", role="viewer", org_id="org-test")
        resp = client.put(
            "/v1/dashboard/customers/a@b.com",
            json={"role": "analyst"},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["role"] == "analyst"

    def test_rejects_invalid_role(self, client, admin_headers):
        from modules.credit.router import app

        _seed_users(app)
        resp = client.put(
            "/v1/dashboard/customers/bob@corp.com",
            json={"role": "superadmin"},
            headers=admin_headers,
        )
        assert resp.status_code == 422


# --- System health (via API) ---


class TestSystemHealth:
    def test_returns_health_dict(self, client, admin_headers):
        resp = client.get("/v1/dashboard/health", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data
        assert "users" in data
        assert "audit_entries" in data


# --- Auth and access control ---


class TestDashboardAuth:
    def test_overview_requires_auth(self, client):
        resp = client.get("/v1/dashboard/overview")
        assert resp.status_code in (401, 403)

    def test_overview_requires_admin(self, client, admin_headers):
        from modules.credit.auth import create_access_token
        from modules.credit.router import app

        create_test_user(app, "bob@corp.com", role="viewer", org_id="org-bob")
        bob_token = create_access_token(
            subject="bob@corp.com",
            secret="test-secret",
            algorithm="HS256",
            expire_minutes=30,
        )
        resp = client.get(
            "/v1/dashboard/overview",
            headers={"Authorization": f"Bearer {bob_token}"},
        )
        assert resp.status_code == 403


# --- Delete (deactivate) customer ---


class TestDeleteCustomer:
    def test_deactivate_customer_endpoint(self, client, admin_headers):
        from modules.credit.router import app

        _seed_users(app)
        resp = client.delete(
            "/v1/dashboard/customers/bob@corp.com", headers=admin_headers
        )
        assert resp.status_code == 200
        assert resp.json()["is_active"] is False
        # Verify via detail endpoint that user is deactivated
        detail = client.get(
            "/v1/dashboard/customers/bob@corp.com", headers=admin_headers
        )
        assert detail.status_code == 200
        assert detail.json()["is_active"] is False

    def test_put_and_delete_not_found(self, client, admin_headers):
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


# --- Static dashboard page ---


class TestDashboardPage:
    def test_serve_dashboard_page(self, client):
        """GET /dashboard serves the static HTML file."""
        resp = client.get("/dashboard")
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]
