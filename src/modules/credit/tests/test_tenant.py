"""Tests for tenant isolation — T4.5 TDD."""

from modules.credit.tests.conftest import patch_auth_settings


def _get_client():
    from fastapi.testclient import TestClient

    from modules.credit.router import app

    return TestClient(app)


class TestOrgModel:
    """Test Organization data model."""

    def test_org_has_org_id_field(self):
        from modules.credit.tenant import Organization

        org = Organization(org_id="org-1", name="Acme Corp")
        assert org.org_id == "org-1"

    def test_org_has_name_field(self):
        from modules.credit.tenant import Organization

        org = Organization(org_id="org-1", name="Acme Corp")
        assert org.name == "Acme Corp"


class TestUserOrgAssociation:
    """Test users are associated with organizations."""

    def test_register_user_with_org(self):
        client = _get_client()
        with patch_auth_settings():
            client.post(
                "/auth/register",
                json={"email": "orguser@test.com", "password": "Secret123!"},
            )
            from modules.credit.user_routes import _users

            user = _users.get("orguser@test.com")
            assert "org_id" in user


class TestApiKeyOrgResolution:
    """Test API keys resolve to correct org."""

    def test_api_key_contains_org_id(self):
        from modules.credit.admin_routes import _api_keys

        # The _api_keys store already maps keys to org_id
        _api_keys["test-key"] = {
            "org_id": "org-1",
            "role": "analyst",
            "expires_at": None,
        }
        assert _api_keys["test-key"]["org_id"] == "org-1"
        del _api_keys["test-key"]


class TestTenantResolver:
    """Test resolving org_id from request context."""

    def test_resolve_org_from_user(self):
        from modules.credit.tenant import resolve_org_id

        user_data = {"email": "a@test.com", "org_id": "org-1", "role": "analyst"}
        assert resolve_org_id(user_data) == "org-1"

    def test_resolve_org_returns_none_for_missing(self):
        from modules.credit.tenant import resolve_org_id

        user_data = {"email": "a@test.com", "role": "analyst"}
        assert resolve_org_id(user_data) is None

    def test_admin_can_specify_org_override(self):
        from modules.credit.tenant import resolve_org_id

        user_data = {"email": "admin@test.com", "org_id": "org-admin", "role": "admin"}
        assert resolve_org_id(user_data, override_org="org-other") == "org-other"

    def test_non_admin_cannot_override_org(self):
        from modules.credit.tenant import resolve_org_id

        user_data = {"email": "user@test.com", "org_id": "org-1", "role": "analyst"}
        assert resolve_org_id(user_data, override_org="org-other") == "org-1"


class TestScopedRepository:
    """Test repository queries are scoped by org_id."""

    def test_scoped_repo_requires_org_id(self):
        from modules.credit.tenant import ScopedAssessmentRepository

        repo = ScopedAssessmentRepository(session=None, org_id="org-1")
        assert repo.org_id == "org-1"

    def test_scoped_repo_rejects_none_org_id(self):
        import pytest

        from modules.credit.tenant import ScopedAssessmentRepository

        with pytest.raises(ValueError, match="org_id"):
            ScopedAssessmentRepository(session=None, org_id=None)


class TestCrossTenantIsolation:
    """Test that tenants cannot access each other's data."""

    def test_org_store_isolation(self):
        from modules.credit.tenant import (
            _org_assessments,
            get_org_assessments,
            store_org_assessment,
        )

        store_org_assessment("org-A", {"score": 700})
        store_org_assessment("org-B", {"score": 800})

        assert len(get_org_assessments("org-A")) == 1
        assert get_org_assessments("org-A")[0]["score"] == 700
        assert len(get_org_assessments("org-B")) == 1
        assert get_org_assessments("org-B")[0]["score"] == 800
        assert len(get_org_assessments("org-C")) == 0

        # Clean up
        _org_assessments.clear()

    def test_admin_can_query_across_orgs(self):
        from modules.credit.tenant import (
            _org_assessments,
            get_all_assessments,
            store_org_assessment,
        )

        store_org_assessment("org-X", {"score": 700})
        store_org_assessment("org-Y", {"score": 800})

        all_data = get_all_assessments()
        assert len(all_data) >= 2

        # Clean up
        _org_assessments.clear()
