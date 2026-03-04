"""Tests for User model and password hashing — T4.1 TDD."""

import asyncio

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from modules.credit.models_db import Base, User


def _run(coro):
    return asyncio.run(coro)


def _make_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")

    async def setup():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        return async_sessionmaker(engine, expire_on_commit=False)

    return _run(setup())


class TestUserModel:
    """Test User ORM model."""

    def test_user_table_exists(self):
        assert User.__tablename__ == "users"

    def test_user_has_email_field(self):
        u = User(email="test@example.com", password_hash="hash")
        assert u.email == "test@example.com"

    def test_user_has_password_hash_field(self):
        u = User(email="test@example.com", password_hash="hash")
        assert u.password_hash == "hash"

    def test_user_persists_to_database(self):
        factory = _make_session()

        async def _test():
            async with factory() as session:
                user = User(email="test@example.com", password_hash="bcrypt-hash")
                session.add(user)
                await session.commit()
                await session.refresh(user)
                assert user.id is not None

        _run(_test())

    def test_user_has_is_active_default_true(self):
        factory = _make_session()

        async def _test():
            async with factory() as session:
                user = User(email="active@example.com", password_hash="hash")
                session.add(user)
                await session.commit()
                await session.refresh(user)
                assert user.is_active is True

        _run(_test())


class TestPasswordHashing:
    """Test bcrypt password hashing utilities."""

    def test_hash_password_returns_string(self):
        from modules.credit.password import hash_password

        result = hash_password("mysecret")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_hash_password_not_plaintext(self):
        from modules.credit.password import hash_password

        result = hash_password("mysecret")
        assert result != "mysecret"

    def test_verify_correct_password(self):
        from modules.credit.password import hash_password, verify_password

        hashed = hash_password("mysecret")
        assert verify_password("mysecret", hashed) is True

    def test_verify_wrong_password(self):
        from modules.credit.password import hash_password, verify_password

        hashed = hash_password("mysecret")
        assert verify_password("wrongpassword", hashed) is False
