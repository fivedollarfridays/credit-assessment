"""Blue/green deployment utilities."""

from __future__ import annotations

import asyncio
import logging
import signal

import httpx

logger = logging.getLogger(__name__)

# Graceful shutdown state
_shutting_down = False


def is_shutting_down() -> bool:
    """Check if the application is in graceful shutdown."""
    return _shutting_down


def reset_shutdown_state() -> None:
    """Reset shutdown state (for testing)."""
    global _shutting_down
    _shutting_down = False


def setup_graceful_shutdown() -> None:
    """Register SIGTERM handler for graceful shutdown."""

    def _handle_sigterm(signum: int, frame: object) -> None:
        global _shutting_down
        _shutting_down = True
        logger.info("Received SIGTERM, starting graceful shutdown")

    signal.signal(signal.SIGTERM, _handle_sigterm)


async def validate_health(base_url: str, timeout: int = 30) -> bool:
    """Validate that a deployment is healthy by checking /health and /ready.

    Returns True only if both endpoints return HTTP 200.
    """
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            health, ready = await asyncio.gather(
                client.get(f"{base_url}/health"),
                client.get(f"{base_url}/ready"),
            )
            return health.status_code == 200 and ready.status_code == 200
    except (httpx.HTTPError, OSError):
        return False
