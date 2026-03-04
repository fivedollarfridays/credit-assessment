"""Tests for SQLAlchemy ORM models — T3.3 TDD."""

import asyncio
import datetime


def _setup_db():
    """Create in-memory engine, session factory, and tables."""
    from modules.credit.database import create_engine, get_session_factory
    from modules.credit.models_db import Base

    engine = create_engine("sqlite+aiosqlite://")
    factory = get_session_factory(engine)

    async def _init():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        return engine, factory

    return asyncio.run(_init())


class TestAssessmentRecordModel:
    """Test AssessmentRecord ORM model."""

    def test_table_exists(self):
        from modules.credit.models_db import AssessmentRecord

        assert AssessmentRecord.__tablename__ == "assessment_records"

    def test_insert_and_retrieve(self):
        engine, factory = _setup_db()
        from modules.credit.models_db import AssessmentRecord

        async def _run():
            async with factory() as session:
                record = AssessmentRecord(
                    credit_score=740,
                    score_band="good",
                    barrier_severity="low",
                    readiness_score=82,
                    request_payload={"current_score": 740},
                    response_payload={"barrier_severity": "low"},
                )
                session.add(record)
                await session.commit()
                await session.refresh(record)
                assert record.id is not None
                assert record.credit_score == 740
                assert record.created_at is not None

        asyncio.run(_run())

    def test_created_at_defaults_to_now(self):
        engine, factory = _setup_db()
        from modules.credit.models_db import AssessmentRecord

        async def _run():
            async with factory() as session:
                record = AssessmentRecord(
                    credit_score=650,
                    score_band="fair",
                    barrier_severity="medium",
                    readiness_score=55,
                    request_payload={},
                    response_payload={},
                )
                session.add(record)
                await session.commit()
                await session.refresh(record)
                assert isinstance(record.created_at, datetime.datetime)

        asyncio.run(_run())


class TestAuditLogModel:
    """Test AuditLog ORM model."""

    def test_table_exists(self):
        from modules.credit.models_db import AuditLog

        assert AuditLog.__tablename__ == "audit_logs"

    def test_insert_and_retrieve(self):
        engine, factory = _setup_db()
        from modules.credit.models_db import AuditLog

        async def _run():
            async with factory() as session:
                log = AuditLog(
                    action="assess",
                    resource="credit_profile",
                    detail={"score": 740},
                )
                session.add(log)
                await session.commit()
                await session.refresh(log)
                assert log.id is not None
                assert log.action == "assess"
                assert log.created_at is not None

        asyncio.run(_run())
