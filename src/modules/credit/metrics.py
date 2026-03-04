"""Prometheus metrics instrumentation for FastAPI."""

from __future__ import annotations

from fastapi import Depends
from prometheus_fastapi_instrumentator import Instrumentator

from .assess_routes import verify_auth


def setup_metrics(app) -> Instrumentator:
    """Instrument the FastAPI app with Prometheus metrics."""
    instrumentator = Instrumentator(
        should_group_status_codes=False,
        excluded_handlers=["/metrics"],
    )
    instrumentator.instrument(app)
    instrumentator.expose(
        app,
        endpoint="/metrics",
        include_in_schema=False,
        dependencies=[Depends(verify_auth)],
    )
    return instrumentator
