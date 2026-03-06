"""Base agent class and shared types for Baby INERTIA agents."""

from __future__ import annotations

import functools
import json
import pathlib
import time
from abc import ABC, abstractmethod
from typing import Literal

from pydantic import BaseModel

from ..types import CreditProfile

_DATA_DIR = pathlib.Path(__file__).parent / "data"


class AgentResult(BaseModel):
    """Standard result envelope from any agent."""

    agent_name: str
    status: Literal["success", "error", "skipped"]
    data: dict = {}
    errors: list[str] = []
    execution_ms: float = 0.0


@functools.lru_cache(maxsize=32)
def load_config(config_name: str) -> dict:
    """Load a JSON config from agents/data/. Cached per-process."""
    path = _DATA_DIR / config_name
    if not path.suffix:
        path = path.with_suffix(".json")
    return json.loads(path.read_text(encoding="utf-8"))


class BaseAgent(ABC):
    """Abstract base for all Baby INERTIA agents."""

    name: str = "unnamed"
    description: str = ""

    def execute(self, profile: CreditProfile, context: dict | None = None) -> AgentResult:
        """Run agent logic with timing wrapper."""
        start = time.perf_counter()
        try:
            result = self._execute(profile, context)
            result.execution_ms = (time.perf_counter() - start) * 1000
            return result
        except Exception as exc:
            elapsed = (time.perf_counter() - start) * 1000
            return AgentResult(
                agent_name=self.name,
                status="error",
                errors=[str(exc)],
                execution_ms=elapsed,
            )

    @abstractmethod
    def _execute(self, profile: CreditProfile, context: dict | None = None) -> AgentResult:
        """Implement agent logic. Override in subclasses."""
        ...
