"""Tests for user and reset token repositories."""

import asyncio

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


class TestUserRepository:
    def test_create_and_get_by_email(self, db_factory):
        from modules.credit.repo_users import UserRepository

        async def _run():
            async with db_factory() as s:
                repo = UserRepository(s)
                user = await repo.create(
                    email="a@b.com", password_hash="h", role="viewer", org_id="org-1"
                )
                assert user.id is not None
                found = await repo.get_by_email("a@b.com")
                assert found is not None
                assert found.role == "viewer"

        asyncio.run(_run())

    def test_get_by_email_not_found(self, db_factory):
        from modules.credit.repo_users import UserRepository

        async def _run():
            async with db_factory() as s:
                repo = UserRepository(s)
                assert await repo.get_by_email("nope@x.com") is None

        asyncio.run(_run())

    def test_count(self, db_factory):
        from modules.credit.repo_users import UserRepository

        async def _run():
            async with db_factory() as s:
                repo = UserRepository(s)
                assert await repo.count() == 0
                await repo.create(
                    email="a@b.com", password_hash="h", role="viewer", org_id="o"
                )
                assert await repo.count() == 1

        asyncio.run(_run())

    def test_update_role(self, db_factory):
        from modules.credit.repo_users import UserRepository

        async def _run():
            async with db_factory() as s:
                repo = UserRepository(s)
                await repo.create(
                    email="a@b.com", password_hash="h", role="viewer", org_id="o"
                )
                updated = await repo.set_role("a@b.com", "admin")
                assert updated is True
                user = await repo.get_by_email("a@b.com")
                assert user.role == "admin"

        asyncio.run(_run())

    def test_list_all(self, db_factory):
        from modules.credit.repo_users import UserRepository

        async def _run():
            async with db_factory() as s:
                repo = UserRepository(s)
                await repo.create(
                    email="a@b.com", password_hash="h", role="viewer", org_id="o"
                )
                await repo.create(
                    email="c@d.com", password_hash="h", role="admin", org_id="o"
                )
                users = await repo.list_all()
                assert len(users) == 2

        asyncio.run(_run())

    def test_set_password_hash(self, db_factory):
        from modules.credit.repo_users import UserRepository

        async def _run():
            async with db_factory() as s:
                repo = UserRepository(s)
                await repo.create(
                    email="a@b.com", password_hash="old", role="viewer", org_id="o"
                )
                updated = await repo.set_password_hash("a@b.com", "new")
                assert updated is True
                user = await repo.get_by_email("a@b.com")
                assert user.password_hash == "new"

        asyncio.run(_run())

    def test_delete_by_email(self, db_factory):
        from modules.credit.repo_users import UserRepository

        async def _run():
            async with db_factory() as s:
                repo = UserRepository(s)
                await repo.create(
                    email="a@b.com", password_hash="h", role="viewer", org_id="o"
                )
                deleted = await repo.delete_by_email("a@b.com")
                assert deleted is True
                assert await repo.get_by_email("a@b.com") is None

        asyncio.run(_run())


class TestResetTokenRepository:
    def test_store_and_pop(self, db_factory):
        from modules.credit.repo_users import ResetTokenRepository

        async def _run():
            async with db_factory() as s:
                repo = ResetTokenRepository(s)
                await repo.store("tok-1", "a@b.com")
                email = await repo.pop("tok-1")
                assert email == "a@b.com"
                # second pop returns None (consumed)
                assert await repo.pop("tok-1") is None

        asyncio.run(_run())

    def test_expired_token_returns_none(self, db_factory):
        from modules.credit.repo_users import ResetTokenRepository

        async def _run():
            async with db_factory() as s:
                repo = ResetTokenRepository(s)
                await repo.store("tok-1", "a@b.com", ttl_minutes=0)
                # TTL of 0 means already expired
                assert await repo.pop("tok-1") is None

        asyncio.run(_run())

    def test_pop_expired_deletes_token(self, db_factory):
        from modules.credit.repo_users import ResetTokenRepository

        async def _run():
            async with db_factory() as s:
                repo = ResetTokenRepository(s)
                await repo.store("tok-1", "a@b.com")
                # Pop with ttl_minutes=0 treats any existing token as expired
                assert await repo.pop("tok-1", ttl_minutes=0) is None
                # Token was deleted during the expired pop
                assert await repo.pop("tok-1") is None

        asyncio.run(_run())

    def test_prune_expired(self, db_factory):
        from modules.credit.repo_users import ResetTokenRepository

        async def _run():
            async with db_factory() as s:
                repo = ResetTokenRepository(s)
                await repo.store("tok-1", "a@b.com")
                # Prune with ttl=0 treats all as expired
                count = await repo.prune_expired(ttl_minutes=0)
                assert count == 1

        asyncio.run(_run())
