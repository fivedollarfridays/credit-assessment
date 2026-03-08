"""Tests for critical security audit findings: rate limiting, key hashing."""

from __future__ import annotations

import asyncio
import hashlib
from datetime import datetime, timedelta, timezone

import pytest

from modules.credit.database import create_engine, get_session_factory
from modules.credit.models_db import Base


@pytest.fixture
def db_factory():
    """Create in-memory database with tables for each test."""
    engine = create_engine("sqlite+aiosqlite://")
    factory = get_session_factory(engine)

    async def _init():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(_init())
    return factory


# ---------------------------------------------------------------------------
# Finding #1: Rate limiting on /auth/token endpoint
# ---------------------------------------------------------------------------


class TestAuthTokenRateLimit:
    """The /auth/token endpoint must have a @limiter.limit decorator."""

    def test_issue_token_has_rate_limit_decorator(self) -> None:
        from modules.credit.auth_routes import issue_token

        assert hasattr(issue_token, "_rate_limits") or hasattr(
            issue_token, "__wrapped__"
        ), "issue_token should be rate-limited"


# ---------------------------------------------------------------------------
# Finding #2: API keys stored as hashed values
# ---------------------------------------------------------------------------


class TestApiKeyHashing:
    """API keys must be stored as SHA-256 hashes, not plaintext."""

    def test_hash_key_helper_exists(self) -> None:
        from modules.credit.repo_api_keys import _hash_key

        result = _hash_key("test-key")
        assert isinstance(result, str)
        assert len(result) == 64  # SHA-256 hex digest

    def test_hash_key_returns_sha256(self) -> None:
        from modules.credit.repo_api_keys import _hash_key

        expected = hashlib.sha256("my-secret-key".encode()).hexdigest()
        assert _hash_key("my-secret-key") == expected

    def test_stored_key_is_hashed_not_plaintext(self, db_factory) -> None:
        """After create(), the DB row should contain the hash, not the raw key."""
        from modules.credit.repo_api_keys import ApiKeyRepository, _hash_key

        async def _run():
            async with db_factory() as session:
                repo = ApiKeyRepository(session)
                await repo.create(key="raw-api-key-123", org_id="org-1", role="viewer")

                # Direct DB query to check what was stored
                from sqlalchemy import text

                result = await session.execute(
                    text("SELECT key_hash, key_prefix FROM api_keys LIMIT 1")
                )
                row = result.first()
                assert row is not None
                # Should store hash, not plaintext
                assert row.key_hash == _hash_key("raw-api-key-123")
                assert row.key_prefix == "raw-api-k"[:8]

        asyncio.run(_run())

    def test_lookup_by_raw_key_works(self, db_factory) -> None:
        """lookup() should accept the raw key and find the hashed entry."""
        from modules.credit.repo_api_keys import ApiKeyRepository

        async def _run():
            async with db_factory() as session:
                repo = ApiKeyRepository(session)
                await repo.create(key="lookup-test-key", org_id="org-2", role="analyst")
                result = await repo.lookup("lookup-test-key")
                assert result is not None
                assert result.org_id == "org-2"

        asyncio.run(_run())

    def test_lookup_wrong_key_returns_none(self, db_factory) -> None:
        """lookup() with wrong raw key returns None."""
        from modules.credit.repo_api_keys import ApiKeyRepository

        async def _run():
            async with db_factory() as session:
                repo = ApiKeyRepository(session)
                await repo.create(key="correct-key", org_id="org-1", role="viewer")
                result = await repo.lookup("wrong-key")
                assert result is None

        asyncio.run(_run())

    def test_revoke_by_raw_key_works(self, db_factory) -> None:
        """revoke() should accept the raw key and revoke the hashed entry."""
        from modules.credit.repo_api_keys import ApiKeyRepository

        async def _run():
            async with db_factory() as session:
                repo = ApiKeyRepository(session)
                await repo.create(key="revoke-me", org_id="org-1", role="viewer")
                revoked = await repo.revoke("revoke-me")
                assert revoked is True
                # Should now be None on lookup
                result = await repo.lookup("revoke-me")
                assert result is None

        asyncio.run(_run())

    def test_revoke_nonexistent_key_returns_false(self, db_factory) -> None:
        """revoke() with a nonexistent raw key returns False."""
        from modules.credit.repo_api_keys import ApiKeyRepository

        async def _run():
            async with db_factory() as session:
                repo = ApiKeyRepository(session)
                revoked = await repo.revoke("does-not-exist")
                assert revoked is False

        asyncio.run(_run())

    def test_expired_hashed_key_returns_none(self, db_factory) -> None:
        """Expired keys should still return None even with hashed storage."""
        from modules.credit.repo_api_keys import ApiKeyRepository

        async def _run():
            async with db_factory() as session:
                repo = ApiKeyRepository(session)
                past = datetime.now(timezone.utc) - timedelta(hours=1)
                await repo.create(
                    key="expired-hashed", org_id="org-1", role="viewer", expires_at=past
                )
                assert await repo.lookup("expired-hashed") is None

        asyncio.run(_run())

    def test_key_prefix_stored_for_identification(self, db_factory) -> None:
        """The first 8 chars of the raw key should be stored as key_prefix."""
        from modules.credit.repo_api_keys import ApiKeyRepository

        async def _run():
            async with db_factory() as session:
                repo = ApiKeyRepository(session)
                await repo.create(key="abcdefghijklmnop", org_id="org-1", role="viewer")
                from sqlalchemy import text

                result = await session.execute(
                    text("SELECT key_prefix FROM api_keys LIMIT 1")
                )
                row = result.first()
                assert row is not None
                assert row.key_prefix == "abcdefgh"

        asyncio.run(_run())


class TestApiKeyModelColumns:
    """The ApiKeyDB model must use key_hash and key_prefix columns."""

    def test_model_has_key_hash_column(self) -> None:
        from modules.credit.models_db import ApiKeyDB

        assert hasattr(ApiKeyDB, "key_hash")

    def test_model_has_key_prefix_column(self) -> None:
        from modules.credit.models_db import ApiKeyDB

        assert hasattr(ApiKeyDB, "key_prefix")

    def test_model_key_hash_is_primary_key(self) -> None:
        from modules.credit.models_db import ApiKeyDB

        mapper = ApiKeyDB.__mapper__
        pk_cols = [c.name for c in mapper.primary_key]
        assert "key_hash" in pk_cols
