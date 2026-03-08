"""Shared fixtures for credit module tests."""

import asyncio
from contextlib import ExitStack
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from modules.credit.config import Settings
from modules.credit.types import (
    AccountSummary,
    CreditProfile,
    ScoreBand,
)

_TEST_SETTINGS = Settings(
    jwt_secret="test-secret",
    api_key=None,
    database_url="sqlite+aiosqlite://",
)


def create_test_user(
    app,
    email: str,
    *,
    role: str = "viewer",
    org_id: str = "org-test",
    password: str = "Secret123!",
) -> None:
    """Create a test user directly in the DB."""
    from modules.credit.password import hash_password
    from modules.credit.repo_users import UserRepository

    factory = app.state.db_session_factory

    async def _create():
        async with factory() as session:
            repo = UserRepository(session)
            existing = await repo.get_by_email(email)
            if existing is not None:
                if existing.role != role:
                    await repo.set_role(email, role)
                return
            await repo.create(
                email=email,
                password_hash=hash_password(password),
                role=role,
                org_id=org_id,
            )

    asyncio.run(_create())


def register_and_login(
    client: TestClient, email: str, password: str = "Secret123!"
) -> str:
    """Register a user and return their JWT token."""
    client.post("/auth/register", json={"email": email, "password": password})
    resp = client.post("/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    return resp.json()["access_token"]


def patch_auth_settings(settings: Settings | None = None) -> ExitStack:
    """Patch settings across all auth-dependent modules. Returns ExitStack."""
    s = settings or _TEST_SETTINGS
    stack = ExitStack()
    for mod in ["router", "auth_routes", "assess_routes", "auth"]:
        stack.enter_context(patch(f"modules.credit.{mod}.settings", s))
    return stack


# Shared valid payload dict for endpoint tests (matches good_credit_profile).
VALID_ASSESS_PAYLOAD: dict = {
    "current_score": 740,
    "score_band": "good",
    "overall_utilization": 20.0,
    "account_summary": {"total_accounts": 8, "open_accounts": 6},
    "payment_history_pct": 98.0,
    "average_account_age_months": 72,
}


@pytest.fixture
def client() -> TestClient:
    """Shared TestClient for the FastAPI app with in-memory DB."""
    from modules.credit.rate_limit import limiter
    from modules.credit.router import app

    limiter.reset()
    limiter.enabled = False
    with patch_auth_settings(_TEST_SETTINGS):
        with TestClient(app) as c:
            yield c
    limiter.enabled = True
    # Clear stale factory so tests using bare TestClient(app) don't
    # hit a disposed engine from this fixture's in-memory DB.
    if hasattr(app.state, "db_session_factory"):
        del app.state.db_session_factory


@pytest.fixture
def admin_headers(client):
    """Create admin user in DB, patch JWT settings, and return auth headers."""
    from modules.credit.auth import create_access_token
    from modules.credit.router import app

    create_test_user(app, "admin@test.com", role="admin", org_id="org-admin")
    token = create_access_token(
        subject="admin@test.com",
        secret=_TEST_SETTINGS.jwt_secret,
        algorithm=_TEST_SETTINGS.jwt_algorithm,
        expire_minutes=30,
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def bypass_auth():
    """Override verify_auth to return a fixed test identity."""
    from modules.credit.assess_routes import verify_auth
    from modules.credit.router import app

    from modules.credit.auth import AuthIdentity

    app.dependency_overrides[verify_auth] = lambda: AuthIdentity(identity="test-user")
    yield
    app.dependency_overrides.pop(verify_auth, None)


@pytest.fixture
def good_credit_profile() -> CreditProfile:
    """Score=740, no negatives, 20% utilization."""
    return CreditProfile(
        current_score=740,
        score_band=ScoreBand.GOOD,
        overall_utilization=20.0,
        account_summary=AccountSummary(
            total_accounts=8,
            open_accounts=6,
            closed_accounts=2,
            negative_accounts=0,
            collection_accounts=0,
            total_balance=8000.0,
            total_credit_limit=40000.0,
            monthly_payments=350.0,
        ),
        payment_history_pct=98.0,
        average_account_age_months=72,
        negative_items=[],
    )


@pytest.fixture
def poor_credit_profile() -> CreditProfile:
    """Score=520, 3 collections, 85% utilization."""
    return CreditProfile(
        current_score=520,
        score_band=ScoreBand.VERY_POOR,
        overall_utilization=85.0,
        account_summary=AccountSummary(
            total_accounts=12,
            open_accounts=5,
            closed_accounts=7,
            negative_accounts=5,
            collection_accounts=3,
            total_balance=42500.0,
            total_credit_limit=50000.0,
            monthly_payments=1200.0,
        ),
        payment_history_pct=62.0,
        average_account_age_months=48,
        negative_items=[
            "collection_medical_2500",
            "collection_utility_800",
            "collection_credit_card_5000",
        ],
    )


@pytest.fixture
def fair_credit_profile() -> CreditProfile:
    """Score=650, 1 negative, 45% utilization."""
    return CreditProfile(
        current_score=650,
        score_band=ScoreBand.FAIR,
        overall_utilization=45.0,
        account_summary=AccountSummary(
            total_accounts=6,
            open_accounts=4,
            closed_accounts=2,
            negative_accounts=1,
            collection_accounts=0,
            total_balance=13500.0,
            total_credit_limit=30000.0,
            monthly_payments=450.0,
        ),
        payment_history_pct=88.0,
        average_account_age_months=36,
        negative_items=["late_payment_30day"],
    )


@pytest.fixture
def thin_file_profile() -> CreditProfile:
    """Score=620, 2 accounts, no negatives."""
    return CreditProfile(
        current_score=620,
        score_band=ScoreBand.POOR,
        overall_utilization=30.0,
        account_summary=AccountSummary(
            total_accounts=2,
            open_accounts=2,
            closed_accounts=0,
            negative_accounts=0,
            collection_accounts=0,
            total_balance=1500.0,
            total_credit_limit=5000.0,
            monthly_payments=75.0,
        ),
        payment_history_pct=100.0,
        average_account_age_months=8,
        negative_items=[],
    )
