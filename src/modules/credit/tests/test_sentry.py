"""Tests for Sentry error tracking integration — T3.5 TDD."""

from unittest.mock import patch

from modules.credit.config import Settings


class TestSentryConfigSettings:
    """Test Sentry-related settings in config."""

    def test_default_sentry_dsn_is_none(self):
        with patch.dict("os.environ", {}, clear=True):
            s = Settings()
            assert s.sentry_dsn is None

    def test_sentry_dsn_from_env(self):
        with patch.dict("os.environ", {"SENTRY_DSN": "https://key@sentry.io/123"}):
            s = Settings()
            assert s.sentry_dsn == "https://key@sentry.io/123"

    def test_default_traces_sample_rate(self):
        with patch.dict("os.environ", {}, clear=True):
            s = Settings()
            assert s.sentry_traces_sample_rate == 0.1


class TestSentrySetup:
    """Test Sentry initialization."""

    def test_setup_called_when_dsn_set(self):
        from modules.credit.sentry import setup_sentry

        with patch("modules.credit.sentry.sentry_sdk") as mock_sdk:
            setup_sentry(dsn="https://key@sentry.io/123", environment="production")
            mock_sdk.init.assert_called_once()

    def test_setup_noop_when_dsn_none(self):
        from modules.credit.sentry import setup_sentry

        with patch("modules.credit.sentry.sentry_sdk") as mock_sdk:
            setup_sentry(dsn=None, environment="development")
            mock_sdk.init.assert_not_called()

    def test_setup_passes_environment(self):
        from modules.credit.sentry import setup_sentry

        with patch("modules.credit.sentry.sentry_sdk") as mock_sdk:
            setup_sentry(dsn="https://key@sentry.io/123", environment="staging")
            call_kwargs = mock_sdk.init.call_args[1]
            assert call_kwargs["environment"] == "staging"

    def test_setup_enables_traces(self):
        from modules.credit.sentry import setup_sentry

        with patch("modules.credit.sentry.sentry_sdk") as mock_sdk:
            setup_sentry(
                dsn="https://key@sentry.io/123",
                environment="production",
                traces_sample_rate=0.5,
            )
            call_kwargs = mock_sdk.init.call_args[1]
            assert call_kwargs["traces_sample_rate"] == 0.5

    def test_request_id_set_as_tag(self):
        from modules.credit.sentry import set_request_id_tag

        with patch("modules.credit.sentry.sentry_sdk") as mock_sdk:
            set_request_id_tag("abc-123")
            mock_sdk.set_tag.assert_called_once_with("request_id", "abc-123")
