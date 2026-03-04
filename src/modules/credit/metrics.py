"""Prometheus metrics instrumentation for FastAPI."""

from __future__ import annotations

from prometheus_fastapi_instrumentator import Instrumentator


def setup_metrics(app) -> Instrumentator:
    """Instrument the FastAPI app with Prometheus metrics."""
    instrumentator = Instrumentator(
        should_group_status_codes=False,
        excluded_handlers=["/metrics"],
    )
    instrumentator.instrument(app)
    instrumentator.expose(app, endpoint="/metrics", include_in_schema=False)
    return instrumentator
