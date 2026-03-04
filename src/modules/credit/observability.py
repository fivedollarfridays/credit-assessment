"""Observability setup: Prometheus metrics and Sentry error tracking."""

from __future__ import annotations

from .metrics import setup_metrics
from .sentry import setup_sentry


def setup_observability(app, *, dsn, environment, traces_sample_rate) -> None:
    """Initialize all observability tools."""
    setup_metrics(app)
    setup_sentry(
        dsn=dsn,
        environment=environment,
        traces_sample_rate=traces_sample_rate,
    )
