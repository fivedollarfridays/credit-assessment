"""Base agent class and shared types for Baby INERTIA agents."""

from __future__ import annotations

import copy
import functools
import json
import logging
import pathlib
import re
import time
from abc import ABC, abstractmethod
from typing import Literal

from pydantic import BaseModel

from ..types import CreditProfile

_logger = logging.getLogger(__name__)
_PATH_PATTERN = re.compile(r"[/\\](?:app|src|home|usr|var|tmp|modules)[/\\]\S+")

_DATA_DIR = pathlib.Path(__file__).parent / "data"
_DATA_DIR_RESOLVED = _DATA_DIR.resolve()


class AgentResult(BaseModel):
    """Standard result envelope from any agent."""

    agent_name: str
    status: Literal["success", "error", "skipped"]
    data: dict = {}
    errors: list[str] = []
    execution_ms: float = 0.0


@functools.lru_cache(maxsize=32)
def _load_config_cached(config_name: str) -> dict:
    """Internal: load and cache a JSON config from agents/data/."""
    path = _DATA_DIR / config_name
    if not path.suffix:
        path = path.with_suffix(".json")
    resolved = path.resolve()
    if not resolved.is_relative_to(_DATA_DIR_RESOLVED):
        raise ValueError(f"Path traversal blocked: {config_name}")
    return json.loads(resolved.read_text(encoding="utf-8"))


def load_config(config_name: str) -> dict:
    """Load a JSON config from agents/data/. Returns a deep copy (safe to mutate)."""
    return copy.deepcopy(_load_config_cached(config_name))


class BaseAgent(ABC):
    """Abstract base for all Baby INERTIA agents."""

    name: str = "unnamed"
    description: str = ""

    def execute(
        self, profile: CreditProfile, context: dict | None = None
    ) -> AgentResult:
        """Run agent logic with timing wrapper."""
        start = time.perf_counter()
        try:
            result = self._execute(profile, context)
            result.execution_ms = (time.perf_counter() - start) * 1000
            return result
        except Exception as exc:
            elapsed = (time.perf_counter() - start) * 1000
            msg = str(exc)
            safe_msg = _PATH_PATTERN.sub("<redacted>", msg)
            _logger.error("Agent %s failed: %s", self.name, safe_msg)
            return AgentResult(
                agent_name=self.name,
                status="error",
                errors=[safe_msg],
                execution_ms=elapsed,
            )

    @abstractmethod
    def _execute(
        self, profile: CreditProfile, context: dict | None = None
    ) -> AgentResult:
        """Implement agent logic. Override in subclasses."""
        ...
