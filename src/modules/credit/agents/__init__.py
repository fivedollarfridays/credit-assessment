"""Baby INERTIA agent registry and CreditPulse event bus."""

from __future__ import annotations

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
