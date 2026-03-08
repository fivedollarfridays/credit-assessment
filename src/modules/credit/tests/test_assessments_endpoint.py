"""Tests for GET /v1/assessments endpoint — auth, pagination, scoping."""

import asyncio


def _seed_assessments(app, user_id, org_id, count=3):
    from modules.credit.repo_assessments import AssessmentRepository

    factory = app.state.db_session_factory

    async def _insert():
        async with factory() as session:
            repo = AssessmentRepository(session)
            for i in range(count):
                await repo.save_assessment(
                    credit_score=700 + i,
                    score_band="good",
                    barrier_severity="low",
                    readiness_score=80 + i,
                    request_payload={"i": i},
                    response_payload={"score": 700 + i},
                    user_id=user_id,
                    org_id=org_id,
                )

    asyncio.run(_insert())


class TestAssessmentsAuth:
    def test_requires_auth(self, client):
        resp = client.get("/v1/assessments")
        assert resp.status_code in (401, 403)

    def test_returns_200_with_auth(self, client, admin_headers):
        resp = client.get("/v1/assessments", headers=admin_headers)
        assert resp.status_code == 200


class TestAssessmentsPagination:
    def test_default_pagination(self, client, admin_headers):
        resp = client.get("/v1/assessments", headers=admin_headers)
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert "limit" in data
        assert "offset" in data
        assert data["limit"] == 20
        assert data["offset"] == 0

    def test_custom_limit_offset(self, client, admin_headers):
        resp = client.get("/v1/assessments?limit=5&offset=2", headers=admin_headers)
        data = resp.json()
        assert data["limit"] == 5
        assert data["offset"] == 2

    def test_invalid_limit_rejected(self, client, admin_headers):
        resp = client.get("/v1/assessments?limit=0", headers=admin_headers)
        assert resp.status_code == 422

    def test_limit_over_100_rejected(self, client, admin_headers):
        resp = client.get("/v1/assessments?limit=101", headers=admin_headers)
        assert resp.status_code == 422


class TestAssessmentsOrgScoping:
    def test_returns_org_assessments(self, client, admin_headers):
        from modules.credit.router import app

        _seed_assessments(app, "admin@test.com", "org-admin", count=3)
        resp = client.get("/v1/assessments", headers=admin_headers)
        data = resp.json()
        assert data["total"] == 3
        assert len(data["items"]) == 3

    def test_org_isolation(self, client, admin_headers):
        from modules.credit.router import app

        _seed_assessments(app, "other@test.com", "org-other", count=2)
        resp = client.get("/v1/assessments", headers=admin_headers)
        data = resp.json()
        # admin is in org-admin, should not see org-other data
        for item in data["items"]:
            assert item["org_id"] != "org-other"

    def test_items_contain_expected_fields(self, client, admin_headers):
        from modules.credit.router import app

        _seed_assessments(app, "admin@test.com", "org-admin", count=1)
        resp = client.get("/v1/assessments", headers=admin_headers)
        items = resp.json()["items"]
        if items:
            item = items[0]
            for key in [
                "id",
                "credit_score",
                "score_band",
                "barrier_severity",
                "readiness_score",
                "user_id",
                "org_id",
                "created_at",
            ]:
                assert key in item


class TestAssessmentsOrgIdBranch:
    """Cover the org_id branch (lines 264-265) when JWT includes org_id."""

    def test_org_id_in_jwt_queries_by_org(self, client):
        from modules.credit.assess_routes import verify_auth
        from modules.credit.auth import AuthIdentity
        from modules.credit.router import app

        _seed_assessments(app, "org-user@test.com", "org-jwt", count=2)
        app.dependency_overrides[verify_auth] = lambda: AuthIdentity(
            identity="org-user@test.com", org_id="org-jwt"
        )
        try:
            resp = client.get("/v1/assessments")
            data = resp.json()
            assert resp.status_code == 200
            assert data["total"] == 2
        finally:
            app.dependency_overrides.pop(verify_auth, None)


class TestAssessmentsStaticApiKey:
    def test_static_api_key_returns_empty(self, client):
        from modules.credit.config import Settings
        from unittest.mock import patch

        settings = Settings(
            jwt_secret="test-secret",
            api_key="static-test-key",
            database_url="sqlite+aiosqlite://",
        )
        with patch("modules.credit.assess_routes.settings", settings):
            resp = client.get(
                "/v1/assessments",
                headers={"X-API-Key": "static-test-key"},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0
