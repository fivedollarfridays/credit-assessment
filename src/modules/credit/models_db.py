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
    user_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    org_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )


class User(Base):
    """Registered user account."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(
        String(20), insert_default="viewer", nullable=False
    )
    org_id: Mapped[str] = mapped_column(String(100), insert_default="", nullable=False)
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
    detail: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    user_id_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    org_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )


class Subscription(Base):
    """Stripe subscription record."""

    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    subscription_id: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    plan: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )


class ConsentRecord(Base):
    """GDPR consent tracking."""

    __tablename__ = "consent_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    consent_version: Mapped[str] = mapped_column(String(20), nullable=False)
    consented_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )


class UserAssessment(Base):
    """Per-user assessment record for GDPR data rights."""

    __tablename__ = "user_assessments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    assessment_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    recorded_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )


class ResetToken(Base):
    """Password reset token with expiry."""

    __tablename__ = "reset_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    token: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )


class WebhookRegistrationDB(Base):
    """Persisted webhook endpoint registration."""

    __tablename__ = "webhook_registrations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    events: Mapped[list] = mapped_column(JSON, nullable=False)
    secret: Mapped[str] = mapped_column(String(255), nullable=False)
    owner_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, insert_default=True, server_default="1", nullable=False
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )


class WebhookDeliveryDB(Base):
    """Webhook delivery attempt log."""

    __tablename__ = "webhook_deliveries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    webhook_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(10), nullable=False)
    status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )


class ApiKeyDB(Base):
    """Scoped API key for org-level access."""

    __tablename__ = "api_keys"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    org_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    expires_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime, nullable=True
    )
    revoked_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime, nullable=True
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )


class FeatureFlagDB(Base):
    """Feature flag with targeting rules."""

    __tablename__ = "feature_flags"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    description: Mapped[str] = mapped_column(
        String(500), insert_default="", nullable=False
    )
    enabled: Mapped[bool] = mapped_column(
        Boolean, insert_default=False, server_default="0", nullable=False
    )
    targeting: Mapped[list | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )
