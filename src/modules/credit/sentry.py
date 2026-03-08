"""Sentry error tracking integration."""

from __future__ import annotations

import sentry_sdk

from .pii import scrub_value


def _scrub_pii_from_event(event: dict, hint: dict) -> dict:
    """Sentry before_send hook: scrub PII from event data."""
    return scrub_value(event)


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
        send_default_pii=False,
        before_send=_scrub_pii_from_event,
    )


def set_request_id_tag(request_id: str) -> None:
    """Set request_id as a Sentry tag for correlation."""
    sentry_sdk.set_tag("request_id", request_id)
