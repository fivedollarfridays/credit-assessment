"""Blue/green deployment utilities."""

from __future__ import annotations

import asyncio
import logging
import signal
import threading
from urllib.parse import urlparse

import httpx

logger = logging.getLogger(__name__)

# Graceful shutdown state — threading.Event for formal thread safety.
_shutdown_event = threading.Event()


def is_shutting_down() -> bool:
    """Check if the application is in graceful shutdown."""
    return _shutdown_event.is_set()


def reset_shutdown_state() -> None:
    """Reset shutdown state (for testing)."""
    _shutdown_event.clear()


def setup_graceful_shutdown() -> None:
    """Register SIGTERM handler for graceful shutdown."""

    def _handle_sigterm(signum: int, frame: object) -> None:
        _shutdown_event.set()
        logger.info("Received SIGTERM, starting graceful shutdown")

    signal.signal(signal.SIGTERM, _handle_sigterm)


async def validate_health(base_url: str, timeout: int = 30) -> bool:
    """Validate that a deployment is healthy by checking /health and /ready.

    Returns True only if both endpoints return HTTP 200.
    Only http:// and https:// URLs are accepted.
    """
    scheme = urlparse(base_url).scheme
    if scheme not in ("http", "https"):
        return False
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            health, ready = await asyncio.gather(
                client.get(f"{base_url}/health"),
                client.get(f"{base_url}/ready"),
            )
            return health.status_code == 200 and ready.status_code == 200
    except (httpx.HTTPError, OSError):
        return False
