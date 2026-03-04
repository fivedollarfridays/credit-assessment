"""Tests for database integration in router — T3.3 TDD."""

import asyncio

from fastapi.testclient import TestClient

_VALID_PAYLOAD = {
    "current_score": 740,
    "score_band": "good",
    "overall_utilization": 20.0,
    "account_summary": {"total_accounts": 8, "open_accounts": 6},
    "payment_history_pct": 98.0,
    "average_account_age_months": 72,
}


class TestAssessmentPersistence:
    """Test that assessments are persisted to the database."""

    def test_assess_persists_record(self):
        """After calling /assess, a record exists in the database."""
        from modules.credit.database import create_engine, get_session_factory
        from modules.credit.models_db import Base
        from modules.credit.repository import AssessmentRepository
        from modules.credit.router import app

        engine = create_engine("sqlite+aiosqlite://")
        factory = get_session_factory(engine)

        # Create tables
        async def _init():
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

        asyncio.run(_init())

        # Inject test database into app state
        app.state.db_session_factory = factory

        client = TestClient(app)
        response = client.post("/assess", json=_VALID_PAYLOAD)
        assert response.status_code == 200

        # Verify record was persisted
        async def _check():
            async with factory() as session:
                repo = AssessmentRepository(session)
                records = await repo.list_assessments()
                assert len(records) >= 1
                assert records[0].credit_score == 740

        asyncio.run(_check())

        # Clean up
        app.state.db_session_factory = None

    def test_assess_works_without_database(self):
        """When no database is configured, /assess still works."""
        from modules.credit.router import app

        app.state.db_session_factory = None
        client = TestClient(app)
        response = client.post("/assess", json=_VALID_PAYLOAD)
        assert response.status_code == 200
