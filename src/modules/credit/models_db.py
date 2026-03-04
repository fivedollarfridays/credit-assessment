"""SQLAlchemy ORM models for persisting assessments and audit logs."""

from __future__ import annotations

import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all ORM models."""


class AssessmentRecord(Base):
    """Persisted credit assessment request/response."""

    __tablename__ = "assessment_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    credit_score: Mapped[int] = mapped_column(Integer, nullable=False)
    score_band: Mapped[str] = mapped_column(String(20), nullable=False)
    barrier_severity: Mapped[str] = mapped_column(String(10), nullable=False)
    readiness_score: Mapped[int] = mapped_column(Integer, nullable=False)
    request_payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    response_payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )


class User(Base):
    """Registered user account."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, insert_default=True, server_default="1", nullable=False
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )


class AuditLog(Base):
    """Audit trail entry for compliance tracking."""

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    resource: Mapped[str] = mapped_column(String(100), nullable=False)
    detail: Mapped[dict] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
