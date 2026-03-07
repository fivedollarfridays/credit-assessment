"""Tests for CircuitBreaker thread safety and DLQ bounds."""

from __future__ import annotations

import threading

from modules.credit.agents.resilience import (
    CircuitBreaker,
    DeadLetterQueue,
    _DLQ_MAX_ENTRIES,
)


class TestCircuitBreakerThreadSafety:
    """CircuitBreaker must be safe under concurrent access."""

    def test_concurrent_record_failure_reaches_open(self) -> None:
        """Many threads calling record_failure should eventually open the breaker."""
        cb = CircuitBreaker(failure_threshold=3, timeout_seconds=60.0)
        barrier = threading.Barrier(10)

        def hammer():
            barrier.wait()
            for _ in range(5):
                cb.record_failure()

        threads = [threading.Thread(target=hammer) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert cb.state == "open"
        assert cb._failure_count >= 3

    def test_concurrent_record_success_resets(self) -> None:
        """Concurrent record_success should leave breaker closed."""
        cb = CircuitBreaker(failure_threshold=3, timeout_seconds=60.0)
        # Trip it first
        for _ in range(3):
            cb.record_failure()
        assert cb.state == "open"

        barrier = threading.Barrier(10)

        def reset_it():
            barrier.wait()
            cb.record_success()

        threads = [threading.Thread(target=reset_it) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert cb.state == "closed"
        assert cb._failure_count == 0


class TestDeadLetterQueueBounds:
    """DLQ must cap entries at _DLQ_MAX_ENTRIES."""

    def test_evicts_oldest_when_over_limit(self) -> None:
        """Adding beyond max keeps only the most recent entries."""
        dlq = DeadLetterQueue()
        for i in range(_DLQ_MAX_ENTRIES + 50):
            dlq.add(agent_name=f"agent_{i}", error=Exception(f"err_{i}"))
        assert dlq.count == _DLQ_MAX_ENTRIES
        dicts = dlq.to_dicts()
        assert dicts[0]["agent_name"] == "agent_50"
        assert dicts[-1]["agent_name"] == f"agent_{_DLQ_MAX_ENTRIES + 49}"


# ---------------------------------------------------------------------------
# TestCircuitBreakerHalfOpen
# ---------------------------------------------------------------------------


class TestCircuitBreakerHalfOpen:
    """Cover resilience.py line 51: allow_request transitions open -> half-open."""

    def test_allow_request_transitions_to_half_open_after_timeout(self) -> None:
        """After timeout elapses, allow_request moves state to half-open."""
        import time

        cb = CircuitBreaker(failure_threshold=3, timeout_seconds=0.05)
        # Trip the breaker
        for _ in range(3):
            cb.record_failure()
        assert cb.state == "open"
        assert cb.allow_request() is False

        # Wait for timeout to elapse
        time.sleep(0.06)

        # allow_request should transition to half-open and return True
        assert cb.allow_request() is True
        assert cb.state == "half-open"

    def test_state_property_also_transitions_to_half_open(self) -> None:
        """The state property transitions from open to half-open after timeout."""
        import time

        cb = CircuitBreaker(failure_threshold=2, timeout_seconds=0.05)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == "open"

        time.sleep(0.06)

        assert cb.state == "half-open"
