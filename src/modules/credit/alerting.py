"""Alerting rules and health check monitoring."""

from __future__ import annotations

import enum
from dataclasses import dataclass


class AlertSeverity(str, enum.Enum):
    """Severity levels for alert rules."""

    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


ERROR_RATE_THRESHOLD = 0.05
LATENCY_P95_THRESHOLD = 0.5


@dataclass(frozen=True)
class AlertRule:
    """A single alerting rule definition."""

    name: str
    condition: str
    threshold: float
    severity: AlertSeverity
    runbook_url: str
    description: str


_DEFAULT_RULES = [
    AlertRule(
        name="high_error_rate",
        condition="error_rate_5m",
        threshold=ERROR_RATE_THRESHOLD,
        severity=AlertSeverity.CRITICAL,
        runbook_url="/docs/runbooks/service-outage.md",
        description="Error rate exceeds 5% over 5 minutes",
    ),
    AlertRule(
        name="high_latency_p95",
        condition="latency_p95_5m",
        threshold=LATENCY_P95_THRESHOLD,
        severity=AlertSeverity.WARNING,
        runbook_url="/docs/runbooks/service-outage.md",
        description="p95 latency exceeds 500ms over 5 minutes",
    ),
    AlertRule(
        name="health_check_failure",
        condition="health_check_up",
        threshold=0.0,
        severity=AlertSeverity.CRITICAL,
        runbook_url="/docs/runbooks/service-outage.md",
        description="Health check endpoint is failing",
    ),
]


def get_alert_rules() -> list[AlertRule]:
    """Return a copy of all default alert rules."""
    return list(_DEFAULT_RULES)


def check_error_rate(
    total_requests: int,
    error_count: int,
    threshold: float = ERROR_RATE_THRESHOLD,
) -> bool:
    """Return True if error rate exceeds the threshold."""
    if total_requests == 0:
        return False
    return (error_count / total_requests) > threshold


def check_latency(p95_seconds: float, threshold: float = LATENCY_P95_THRESHOLD) -> bool:
    """Return True if p95 latency exceeds the threshold."""
    return p95_seconds > threshold
