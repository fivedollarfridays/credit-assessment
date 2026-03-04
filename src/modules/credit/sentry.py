"""Sentry error tracking integration."""

from __future__ import annotations

import sentry_sdk


def setup_sentry(
    *,
    dsn: str | None,
    environment: str,
    traces_sample_rate: float = 0.1,
) -> None:
    """Initialize Sentry SDK. No-op when DSN is not set."""
    if dsn is None:
        return
    sentry_sdk.init(
        dsn=dsn,
        environment=environment,
        traces_sample_rate=traces_sample_rate,
    )


def set_request_id_tag(request_id: str) -> None:
    """Set request_id as a Sentry tag for correlation."""
    sentry_sdk.set_tag("request_id", request_id)
