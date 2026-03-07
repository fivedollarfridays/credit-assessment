"""Baby INERTIA agent registry and CreditPulse event bus."""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .base import BaseAgent

# Agent registry — populated by each agent module on import
_REGISTRY: dict[str, type[BaseAgent]] = {}


def register(agent_cls: type[BaseAgent]) -> type[BaseAgent]:
    """Class decorator to register an agent."""
    _REGISTRY[agent_cls.name] = agent_cls
    return agent_cls


def get_agent(name: str) -> type[BaseAgent] | None:
    """Look up an agent class by name."""
    return _REGISTRY.get(name)


def list_agents() -> list[str]:
    """Return names of all registered agents."""
    return sorted(_REGISTRY.keys())


def _ensure_all_imported() -> None:
    """Import all agent modules to trigger @register decorators."""
    from . import (  # noqa: F401
        parks,
        king,
        colvin,
        robinson,
        gray,
        tubman,
        lewis,
        phantom,
        truth,
        moses,
    )


_shared_resilience: tuple | None = None
_shared_lock = threading.Lock()


def _get_shared_resilience():
    """Return (breakers, dlq, benchmark) shared across all MosesAgent instances."""
    global _shared_resilience  # noqa: PLW0603
    if _shared_resilience is not None:
        return _shared_resilience
    with _shared_lock:
        if _shared_resilience is None:
            from .resilience import (
                CircuitBreaker,
                DeadLetterQueue,
                PerformanceBenchmark,
            )
            from .moses import _ALL_NAMES

            breakers = {
                n: CircuitBreaker(failure_threshold=3, timeout_seconds=60.0)
                for n in _ALL_NAMES
            }
            _shared_resilience = (breakers, DeadLetterQueue(), PerformanceBenchmark())
    return _shared_resilience


def create_wired_moses():
    """Create a MosesAgent with all registered agents wired in."""
    _ensure_all_imported()
    from .moses import MosesAgent

    breakers, dlq, benchmark = _get_shared_resilience()
    return MosesAgent(breakers=breakers, dlq=dlq, benchmark=benchmark)


class CreditPulse:
    """Lightweight in-memory pub/sub event bus for agent communication."""

    def __init__(self) -> None:
        self._subscribers: dict[str, list] = {}

    def subscribe(self, event: str, callback) -> None:
        self._subscribers.setdefault(event, []).append(callback)

    def publish(self, event: str, data: dict) -> list:
        results = []
        for cb in self._subscribers.get(event, []):
            results.append(cb(data))
        return results

    def clear(self) -> None:
        self._subscribers.clear()
