"""Block 1 foundation tests: imports, registry, configs, event bus."""

from __future__ import annotations

import json
import pathlib

from modules.credit.agents import CreditPulse, get_agent, list_agents, register
from modules.credit.agents.base import AgentResult, BaseAgent, load_config
from modules.credit.agents.resilience import (
    CircuitBreaker,
    DeadLetterQueue,
    PerformanceBenchmark,
)


class TestImports:
    def test_base_classes_importable(self):
        assert BaseAgent is not None
        assert AgentResult is not None

    def test_registry_functions_importable(self):
        assert callable(register)
        assert callable(get_agent)
        assert callable(list_agents)

    def test_resilience_classes_importable(self):
        assert CircuitBreaker is not None
        assert DeadLetterQueue is not None
        assert PerformanceBenchmark is not None


class TestConfigLoading:
    _DATA_DIR = (
        pathlib.Path(__file__).resolve().parent.parent.parent / "agents" / "data"
    )

    def test_all_17_configs_parse_as_valid_json(self):
        json_files = list(self._DATA_DIR.glob("*.json"))
        assert len(json_files) == 17, (
            f"Expected 17 configs, found {len(json_files)}: {[f.name for f in json_files]}"
        )
        for path in json_files:
            data = json.loads(path.read_text(encoding="utf-8"))
            assert isinstance(data, (dict, list)), (
                f"{path.name} did not parse to dict or list"
            )

    def test_city_config_has_required_fields(self):
        config = load_config("city_config")
        for key in (
            "population",
            "poverty_rate",
            "living_wage",
            "median_income",
            "minimum_wage",
            "poverty_population",
        ):
            assert key in config, f"city_config missing {key}"
        assert config["population"] == 193703
        assert config["poverty_rate"] == 21.54

    def test_load_config_caches(self):
        from modules.credit.agents.base import _load_config_cached

        _load_config_cached.cache_clear()
        c1 = load_config("city_config")
        c2 = load_config("city_config")
        # load_config returns deep copies, but underlying cache should hit
        assert c1 == c2
        assert c1 is not c2  # each call returns a fresh copy


class TestCreditPulseBus:
    def test_publish_subscribe(self):
        bus = CreditPulse()
        received = []
        bus.subscribe("test.event", lambda data: received.append(data))
        bus.publish("test.event", {"key": "value"})
        assert len(received) == 1
        assert received[0] == {"key": "value"}

    def test_publish_no_subscribers(self):
        bus = CreditPulse()
        results = bus.publish("no.one.listening", {"data": 1})
        assert results == []

    def test_clear_removes_all(self):
        bus = CreditPulse()
        bus.subscribe("evt", lambda d: d)
        bus.clear()
        assert bus.publish("evt", {}) == []


class TestDeadLetterQueueDrain:
    """Test DLQ drain() method returns entries and clears queue."""

    def test_drain_returns_entries(self):
        dlq = DeadLetterQueue()
        dlq.add(agent_name="parks", error=Exception("fail1"))
        dlq.add(agent_name="king", error=Exception("fail2"))
        entries = dlq.drain()
        assert len(entries) == 2
        assert entries[0].agent_name == "parks"
        assert entries[1].agent_name == "king"

    def test_drain_empties_queue(self):
        dlq = DeadLetterQueue()
        dlq.add(agent_name="parks", error=Exception("fail"))
        dlq.drain()
        assert dlq.count == 0

    def test_drain_empty_queue(self):
        dlq = DeadLetterQueue()
        entries = dlq.drain()
        assert entries == []


class TestCircuitBreakerReset:
    """Test CircuitBreaker reset() method."""

    def test_reset_closes_open_circuit(self):
        cb = CircuitBreaker(failure_threshold=2, timeout_seconds=60.0)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == "open"
        cb.reset()
        assert cb.state == "closed"
        assert cb.allow_request() is True

    def test_reset_clears_failure_count(self):
        cb = CircuitBreaker(failure_threshold=3)
        cb.record_failure()
        cb.record_failure()
        cb.reset()
        # One more failure should not open (count was reset)
        cb.record_failure()
        assert cb.state == "closed"
