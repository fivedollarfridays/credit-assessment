"""Resilience primitives for agent orchestration."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone


class CircuitBreaker:
    """Prevents repeated calls to consistently failing agents.

    Opens after failure_threshold failures. Auto-resets after timeout_seconds.
    """

    def __init__(
        self, failure_threshold: int = 3, timeout_seconds: float = 60.0
    ) -> None:
        self.failure_threshold = failure_threshold
        self.timeout_seconds = timeout_seconds
        self._failure_count: int = 0
        self._state: str = "closed"  # closed | open | half-open
        self._last_failure_time: float = 0.0
        self._lock = threading.Lock()

    @property
    def state(self) -> str:
        with self._lock:
            if self._state == "open":
                if time.monotonic() - self._last_failure_time >= self.timeout_seconds:
                    self._state = "half-open"
            return self._state

    def record_success(self) -> None:
        with self._lock:
            self._failure_count = 0
            self._state = "closed"

    def record_failure(self) -> None:
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.monotonic()
            if self._failure_count >= self.failure_threshold:
                self._state = "open"

    def allow_request(self) -> bool:
        with self._lock:
            if self._state == "open":
                if time.monotonic() - self._last_failure_time >= self.timeout_seconds:
                    self._state = "half-open"
            return self._state in ("closed", "half-open")

    def reset(self) -> None:
        with self._lock:
            self._failure_count = 0
            self._state = "closed"
            self._last_failure_time = 0.0


@dataclass
class DLQEntry:
    """Single entry in the dead letter queue."""

    timestamp: str
    agent_name: str
    error_type: str
    error_message: str
    input_summary: dict = field(default_factory=dict)


_DLQ_MAX_ENTRIES = 1000


class DeadLetterQueue:
    """Audit trail for failed agent operations."""

    def __init__(self) -> None:
        self._entries: list[DLQEntry] = []
        self._lock = threading.Lock()

    def add(
        self, *, agent_name: str, error: Exception, input_summary: dict | None = None
    ) -> None:
        entry = DLQEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            agent_name=agent_name,
            error_type=type(error).__name__,
            error_message=str(error),
            input_summary=input_summary or {},
        )
        with self._lock:
            self._entries.append(entry)
            if len(self._entries) > _DLQ_MAX_ENTRIES:
                self._entries = self._entries[-_DLQ_MAX_ENTRIES:]

    @property
    def count(self) -> int:
        with self._lock:
            return len(self._entries)

    def drain(self) -> list[DLQEntry]:
        with self._lock:
            entries = list(self._entries)
            self._entries.clear()
        return entries

    def to_dicts(self) -> list[dict]:
        with self._lock:
            return [
                {
                    "timestamp": e.timestamp,
                    "agent_name": e.agent_name,
                    "error_type": e.error_type,
                    "error_message": e.error_message,
                }
                for e in self._entries
            ]


class PerformanceBenchmark:
    """Times individual agent executions."""

    def __init__(self) -> None:
        self._timings: dict[str, float] = {}
        self._lock = threading.Lock()

    def record(self, agent_name: str, ms: float) -> None:
        with self._lock:
            self._timings[agent_name] = ms

    @property
    def per_agent_ms(self) -> dict[str, float]:
        with self._lock:
            return dict(self._timings)

    @property
    def total_ms(self) -> float:
        with self._lock:
            return sum(self._timings.values())
