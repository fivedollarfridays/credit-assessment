"""Tests for Settings-based configuration — TDD: written before implementation."""

from unittest.mock import patch

import pytest

from modules.credit.config import _DEFAULT_JWT_SECRET, _DEFAULT_PII_PEPPER


class TestSettingsDefaults:
    """Test Settings class default values."""

    def test_default_api_key_is_none(self):
        with patch.dict("os.environ", {}, clear=True):
            from modules.credit.config import Settings

            s = Settings()
            assert s.api_key is None

    def test_default_environment(self):
        with patch.dict("os.environ", {}, clear=True):
            from modules.credit.config import Settings

            s = Settings()
            assert s.environment == "development"

    def test_default_cors_origins(self):
        with patch.dict("os.environ", {}, clear=True):
            from modules.credit.config import Settings

            s = Settings()
            assert s.cors_origins == ["http://localhost:3000"]

    def test_default_log_level(self):
        with patch.dict("os.environ", {}, clear=True):
            from modules.credit.config import Settings

            s = Settings()
            assert s.log_level == "INFO"

    def test_default_host(self):
        with patch.dict("os.environ", {}, clear=True):
            from modules.credit.config import Settings

            s = Settings()
            assert s.host == "0.0.0.0"

    def test_default_port(self):
        with patch.dict("os.environ", {}, clear=True):
            from modules.credit.config import Settings

            s = Settings()
            assert s.port == 8000


class TestSettingsFromEnv:
    """Test Settings reads from environment variables."""

    def test_api_key_from_env(self):
        with patch.dict("os.environ", {"API_KEY": "sk-test-123"}):
            from modules.credit.config import Settings

            s = Settings()
            assert s.api_key == "sk-test-123"

    def test_environment_from_env(self):
        with patch.dict(
            "os.environ",
            {
                "ENVIRONMENT": "production",
                "JWT_SECRET": "prod-env-secret",
                "PII_PEPPER": "prod-pepper",
            },
        ):
            from modules.credit.config import Settings

            s = Settings()
            assert s.environment == "production"

    def test_cors_origins_from_env(self):
        with patch.dict(
            "os.environ",
            {"CORS_ORIGINS": '["https://app.example.com","https://admin.example.com"]'},
        ):
            from modules.credit.config import Settings

            s = Settings()
            assert s.cors_origins == [
                "https://app.example.com",
                "https://admin.example.com",
            ]

    def test_log_level_from_env(self):
        with patch.dict("os.environ", {"LOG_LEVEL": "DEBUG"}):
            from modules.credit.config import Settings

            s = Settings()
            assert s.log_level == "DEBUG"

    def test_port_from_env(self):
        with patch.dict("os.environ", {"PORT": "9000"}):
            from modules.credit.config import Settings

            s = Settings()
            assert s.port == 9000


class TestSettingsHelpers:
    """Test helper methods on Settings."""

    def test_is_production_true(self):
        with patch.dict(
            "os.environ",
            {
                "ENVIRONMENT": "production",
                "JWT_SECRET": "prod-test-secret",
                "PII_PEPPER": "prod-pepper",
            },
        ):
            from modules.credit.config import Settings

            s = Settings()
            assert s.is_production is True

    def test_is_production_false(self):
        with patch.dict("os.environ", {"ENVIRONMENT": "development"}):
            from modules.credit.config import Settings

            s = Settings()
            assert s.is_production is False


class TestDatabaseSettings:
    """Test database-related settings."""

    def test_default_database_url_is_sqlite(self):
        with patch.dict("os.environ", {}, clear=True):
            from modules.credit.config import Settings

            s = Settings()
            assert s.database_url == "sqlite+aiosqlite:///./credit.db"

    def test_database_url_from_env(self):
        with patch.dict(
            "os.environ",
            {"DATABASE_URL": "postgresql+asyncpg://user:pass@localhost/credit"},
        ):
            from modules.credit.config import Settings

            s = Settings()
            assert s.database_url == "postgresql+asyncpg://user:pass@localhost/credit"


class TestProductionSecretValidation:
    """JWT secret must not be the default in production."""

    def test_rejects_default_jwt_secret_in_production(self):
        from pydantic import ValidationError

        from modules.credit.config import Settings

        with pytest.raises(ValidationError):
            Settings(environment="production")

    def test_accepts_custom_jwt_secret_in_production(self):
        from modules.credit.config import Settings

        s = Settings(
            environment="production",
            jwt_secret="a-real-secret-key-value",
            pii_pepper="real-pepper",
        )
        assert s.jwt_secret == "a-real-secret-key-value"

    def test_allows_default_jwt_secret_in_development(self):
        with patch.dict("os.environ", {}, clear=True):
            from modules.credit.config import Settings

            s = Settings()
            assert s.jwt_secret == _DEFAULT_JWT_SECRET


class TestPiiPepperConfig:
    """PII pepper must be configurable and validated in production."""

    def test_default_pii_pepper(self):
        from modules.credit.config import Settings

        s = Settings()
        assert s.pii_pepper == _DEFAULT_PII_PEPPER

    def test_pii_pepper_from_env(self):
        with patch.dict("os.environ", {"PII_PEPPER": "custom-pepper"}):
            from modules.credit.config import Settings

            s = Settings()
            assert s.pii_pepper == "custom-pepper"

    def test_rejects_default_pii_pepper_in_production(self):
        from pydantic import ValidationError

        from modules.credit.config import Settings

        with pytest.raises(ValidationError):
            Settings(environment="production", jwt_secret="real-secret")


class TestBackwardCompatFunctions:
    """Test that legacy standalone functions delegate to the settings singleton."""

    def test_get_api_key_delegates_to_settings(self):
        from modules.credit.config import Settings, get_api_key

        mock = Settings(api_key="legacy-key")
        with patch("modules.credit.config.settings", mock):
            assert get_api_key() == "legacy-key"

    def test_get_cors_origins_delegates_to_settings(self):
        from modules.credit.config import Settings, get_cors_origins

        mock = Settings(cors_origins=["https://example.com"])
        with patch("modules.credit.config.settings", mock):
            assert get_cors_origins() == ["https://example.com"]

    def test_is_production_delegates_to_settings(self):
        from modules.credit.config import Settings, is_production

        mock = Settings(
            environment="production", jwt_secret="prod-test-secret", pii_pepper="pp"
        )
        with patch("modules.credit.config.settings", mock):
            assert is_production() is True

    def test_get_environment_delegates_to_settings(self):
        from modules.credit.config import Settings, get_environment

        mock = Settings(environment="staging")
        with patch("modules.credit.config.settings", mock):
            assert get_environment() == "staging"
