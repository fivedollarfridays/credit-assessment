"""Tests for MEDIUM security audit findings #9-#14 — Sprint 25 TDD."""

from __future__ import annotations

import asyncio
from unittest.mock import patch

import pytest

from modules.credit.config import Settings


# ---------------------------------------------------------------------------
# Finding #10: JWT algorithm not validated
# ---------------------------------------------------------------------------


class TestJwtAlgorithmValidation:
    """Settings must reject unsafe JWT algorithms."""

    def test_rejects_none_algorithm(self):
        """Algorithm 'none' must be rejected to prevent unsigned tokens."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError, match="jwt_algorithm"):
            Settings(jwt_algorithm="none")

    def test_rejects_rs256_algorithm(self):
        """RS256 must be rejected (asymmetric algos not supported)."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError, match="jwt_algorithm"):
            Settings(jwt_algorithm="RS256")

    def test_accepts_hs256_algorithm(self):
        """HS256 is the default and must be accepted."""
        s = Settings(jwt_algorithm="HS256")
        assert s.jwt_algorithm == "HS256"

    def test_accepts_hs384_algorithm(self):
        """HS384 must be accepted."""
        s = Settings(jwt_algorithm="HS384")
        assert s.jwt_algorithm == "HS384"

    def test_accepts_hs512_algorithm(self):
        """HS512 must be accepted."""
        s = Settings(jwt_algorithm="HS512")
        assert s.jwt_algorithm == "HS512"


# ---------------------------------------------------------------------------
# Finding #11: Reset tokens not invalidated after use
# ---------------------------------------------------------------------------


class TestResetTokenInvalidation:
    """After password reset, all remaining tokens for that email must be deleted."""

    def test_second_token_invalid_after_first_used(self, client):
        """Request two reset tokens; use one; the other must be invalid."""
        from modules.credit.router import app

        # Register a user
        client.post(
            "/auth/register",
            json={"email": "twotoken@example.com", "password": "Secret123!"},
        )
        # Request two reset tokens
        client.post("/auth/reset-password", json={"email": "twotoken@example.com"})
        client.post("/auth/reset-password", json={"email": "twotoken@example.com"})

        # Retrieve both tokens from DB
        factory = app.state.db_session_factory

        async def _fetch_tokens():
            from sqlalchemy import select

            from modules.credit.models_db import ResetToken

            async with factory() as session:
                result = await session.execute(
                    select(ResetToken).where(ResetToken.email == "twotoken@example.com")
                )
                return [row.token for row in result.scalars().all()]

        tokens = asyncio.run(_fetch_tokens())
        assert len(tokens) == 2, f"Expected 2 tokens, got {len(tokens)}"

        token_a, token_b = tokens[0], tokens[1]

        # Use the first token to reset password
        resp = client.post(
            "/auth/confirm-reset",
            json={"token": token_a, "new_password": "NewPass789!"},
        )
        assert resp.status_code == 200

        # Second token must now be invalid
        resp = client.post(
            "/auth/confirm-reset",
            json={"token": token_b, "new_password": "AnotherPass1!"},
        )
        assert resp.status_code == 400, (
            "Second reset token should have been invalidated"
        )


# ---------------------------------------------------------------------------
# Finding #12: Template injection via braces in consumer_name
# ---------------------------------------------------------------------------


class TestTemplateInjectionPrevention:
    """User-supplied template values must not contain braces."""

    def test_consumer_name_rejects_braces(self):
        """consumer_name with {__class__} must be rejected."""
        from modules.credit.letter_generator import LetterRequest
        from modules.credit.letter_types import Bureau, LetterType
        from modules.credit.types import NegativeItem, NegativeItemType

        item = NegativeItem(
            type=NegativeItemType.COLLECTION,
            description="Test item",
        )
        with pytest.raises(ValueError, match="[Bb]races"):
            LetterRequest(
                negative_item=item,
                letter_type=LetterType.VALIDATION,
                bureau=Bureau.EQUIFAX,
                consumer_name="{__class__}",
            )

    def test_consumer_name_rejects_closing_brace(self):
        """consumer_name containing } must be rejected."""
        from modules.credit.letter_generator import LetterRequest
        from modules.credit.letter_types import Bureau, LetterType
        from modules.credit.types import NegativeItem, NegativeItemType

        item = NegativeItem(
            type=NegativeItemType.COLLECTION,
            description="Test item",
        )
        with pytest.raises(ValueError, match="[Bb]races"):
            LetterRequest(
                negative_item=item,
                letter_type=LetterType.VALIDATION,
                bureau=Bureau.EQUIFAX,
                consumer_name="name}",
            )

    def test_consumer_name_accepts_normal_name(self):
        """Normal names without braces must be accepted."""
        from modules.credit.letter_generator import LetterRequest
        from modules.credit.letter_types import Bureau, LetterType
        from modules.credit.types import NegativeItem, NegativeItemType

        item = NegativeItem(
            type=NegativeItemType.COLLECTION,
            description="Test item",
        )
        req = LetterRequest(
            negative_item=item,
            letter_type=LetterType.VALIDATION,
            bureau=Bureau.EQUIFAX,
            consumer_name="Jane Doe",
        )
        assert req.consumer_name == "Jane Doe"


# ---------------------------------------------------------------------------
# Finding #13: Stripe webhook secret not validated as non-None
# ---------------------------------------------------------------------------


class TestWebhookSecretValidation:
    """handle_webhook must reject None or empty webhook_secret early."""

    def test_none_webhook_secret_returns_error(self):
        """webhook_secret=None must return error without calling Stripe."""
        from modules.credit.billing import handle_webhook
        from modules.credit.database import create_engine, get_session_factory
        from modules.credit.models_db import Base

        engine = create_engine("sqlite+aiosqlite://")

        async def _run():
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            factory = get_session_factory(engine)
            async with factory() as session:
                with patch("modules.credit.billing.stripe") as mock_stripe:
                    result = await handle_webhook(
                        session=session,
                        payload=b"{}",
                        sig_header="sig",
                        webhook_secret=None,
                    )
                    assert result["status"] == "error"
                    assert "not configured" in result["detail"].lower()
                    mock_stripe.Webhook.construct_event.assert_not_called()

        asyncio.run(_run())

    def test_empty_webhook_secret_returns_error(self):
        """webhook_secret='' must return error without calling Stripe."""
        from modules.credit.billing import handle_webhook
        from modules.credit.database import create_engine, get_session_factory
        from modules.credit.models_db import Base

        engine = create_engine("sqlite+aiosqlite://")

        async def _run():
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            factory = get_session_factory(engine)
            async with factory() as session:
                with patch("modules.credit.billing.stripe") as mock_stripe:
                    result = await handle_webhook(
                        session=session,
                        payload=b"{}",
                        sig_header="sig",
                        webhook_secret="",
                    )
                    assert result["status"] == "error"
                    assert "not configured" in result["detail"].lower()
                    mock_stripe.Webhook.construct_event.assert_not_called()

        asyncio.run(_run())


# ---------------------------------------------------------------------------
# Finding #14: Dispute negative_item_data values unbounded
# ---------------------------------------------------------------------------


class TestDisputeItemDataSizeLimit:
    """negative_item_data must be rejected when total size exceeds 10KB."""

    def test_rejects_oversized_payload(self):
        """20 keys each with 1000-char values should exceed 10KB and be rejected."""
        from modules.credit.dispute_routes import CreateDisputeRequest

        big_data = {f"key_{i}": "x" * 1000 for i in range(20)}
        with pytest.raises(ValueError, match="10KB"):
            CreateDisputeRequest(
                bureau="equifax",
                negative_item_data=big_data,
            )

    def test_accepts_normal_sized_payload(self):
        """A normal-sized payload should pass validation."""
        from modules.credit.dispute_routes import CreateDisputeRequest

        normal_data = {"type": "collection", "description": "Medical debt"}
        req = CreateDisputeRequest(
            bureau="equifax",
            negative_item_data=normal_data,
        )
        assert req.negative_item_data == normal_data


# ---------------------------------------------------------------------------
# A04-1: user_id max_length on GDPR query parameters (T27.2)
# ---------------------------------------------------------------------------


class TestUserIdMaxLength:
    """GDPR endpoint user_id query params must have max_length=255."""

    @staticmethod
    def _get_max_length(endpoint_fn, param_name: str) -> int | None:
        """Extract max_length from a FastAPI Query parameter's metadata."""
        import inspect

        sig = inspect.signature(endpoint_fn)
        param = sig.parameters[param_name]
        query = param.default
        for m in getattr(query, "metadata", []):
            if hasattr(m, "max_length"):
                return m.max_length
        return None

    def test_data_export_user_id_has_max_length(self) -> None:
        """data_export endpoint must have max_length on user_id parameter."""
        from modules.credit.data_rights_routes import data_export

        ml = self._get_max_length(data_export, "user_id")
        assert ml is not None, "user_id Query missing max_length"
        assert ml <= 255, f"user_id max_length should be <=255, got {ml}"

    def test_data_delete_user_id_has_max_length(self) -> None:
        """data_delete endpoint must have max_length on user_id parameter."""
        from modules.credit.data_rights_routes import data_delete

        ml = self._get_max_length(data_delete, "user_id")
        assert ml is not None, "user_id Query missing max_length"
        assert ml <= 255, f"user_id max_length should be <=255, got {ml}"


# ---------------------------------------------------------------------------
# A04-3: SQLite database_url rejected in production (T27.2)
# ---------------------------------------------------------------------------


class TestSqliteProductionGuard:
    """SQLite must be rejected when environment=production."""

    def test_sqlite_rejected_in_production(self) -> None:
        """Settings should raise ValueError for sqlite in production."""
        with pytest.raises(
            ValueError, match="(?i)sqlite.*production|production.*sqlite"
        ):
            Settings(
                environment="production",
                database_url="sqlite+aiosqlite:///./credit.db",
                jwt_secret="secure-production-secret-that-is-long-enough",
                pii_pepper="secure-production-pepper-that-is-long-enough",
            )

    def test_sqlite_allowed_in_development(self) -> None:
        """SQLite should work fine in development."""
        with patch.dict("os.environ", {}, clear=True):
            s = Settings(
                environment="development",
                database_url="sqlite+aiosqlite:///./credit.db",
            )
            assert "sqlite" in s.database_url

    def test_postgres_allowed_in_production(self) -> None:
        """PostgreSQL URLs should be accepted in production."""
        s = Settings(
            environment="production",
            database_url="postgresql+asyncpg://user:pass@localhost/db",
            jwt_secret="secure-production-secret-that-is-long-enough",
            pii_pepper="secure-production-pepper-that-is-long-enough",
        )
        assert "postgresql" in s.database_url


# ---------------------------------------------------------------------------
# A04-2: Billing checkout URL validation (T27.2)
# ---------------------------------------------------------------------------


class TestBillingUrlValidation:
    """Checkout URLs must be validated against allowed origins."""

    def test_rejects_non_https_success_url(self) -> None:
        """success_url with http:// scheme should be rejected."""
        from modules.credit.billing import create_checkout_session

        with pytest.raises(ValueError, match="(?i)url|https|allowed"):
            create_checkout_session(
                customer_email="test@example.com",
                price_id="price_123",
                success_url="http://evil.com/success",
                cancel_url="https://myapp.com/cancel",
            )

    def test_rejects_javascript_url(self) -> None:
        """javascript: URLs must be rejected."""
        from modules.credit.billing import create_checkout_session

        with pytest.raises(ValueError, match="(?i)url|https|allowed"):
            create_checkout_session(
                customer_email="test@example.com",
                price_id="price_123",
                success_url="javascript:alert(1)",
                cancel_url="https://myapp.com/cancel",
            )

    def test_rejects_data_url(self) -> None:
        """data: URLs must be rejected."""
        from modules.credit.billing import create_checkout_session

        with pytest.raises(ValueError, match="(?i)url|https|allowed"):
            create_checkout_session(
                customer_email="test@example.com",
                price_id="price_123",
                success_url="https://myapp.com/success",
                cancel_url="data:text/html,<script>alert(1)</script>",
            )

    def test_accepts_valid_https_urls(self) -> None:
        """Valid https:// URLs should be accepted (Stripe call mocked)."""
        from modules.credit.billing import create_checkout_session

        with patch(
            "modules.credit.billing.stripe.checkout.Session.create"
        ) as mock_create:
            mock_create.return_value = {"id": "cs_test_123"}
            create_checkout_session(
                customer_email="test@example.com",
                price_id="price_123",
                success_url="https://myapp.com/success",
                cancel_url="https://myapp.com/cancel",
            )
            mock_create.assert_called_once()
