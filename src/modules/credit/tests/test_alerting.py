"""Tests for alerting rules and health check monitoring."""

from __future__ import annotations


# --- Cycle 1: AlertSeverity enum ---


def test_alert_severity_has_critical():
    """AlertSeverity enum includes a 'critical' value."""
    from modules.credit.alerting import AlertSeverity

    assert AlertSeverity.CRITICAL == "critical"


def test_alert_severity_has_warning():
    """AlertSeverity enum includes a 'warning' value."""
    from modules.credit.alerting import AlertSeverity

    assert AlertSeverity.WARNING == "warning"


def test_alert_severity_has_info():
    """AlertSeverity enum includes an 'info' value."""
    from modules.credit.alerting import AlertSeverity

    assert AlertSeverity.INFO == "info"


def test_alert_severity_has_exactly_three_members():
    """AlertSeverity enum has exactly three members."""
    from modules.credit.alerting import AlertSeverity

    assert len(AlertSeverity) == 3


# --- Cycle 2: AlertRule dataclass ---


def test_alert_rule_has_required_fields():
    """AlertRule dataclass has all required fields."""
    from modules.credit.alerting import AlertRule, AlertSeverity

    rule = AlertRule(
        name="test_rule",
        condition="test_condition",
        threshold=0.05,
        severity=AlertSeverity.CRITICAL,
        runbook_url="/docs/runbooks/test.md",
        description="A test rule",
    )
    assert rule.name == "test_rule"
    assert rule.condition == "test_condition"
    assert rule.threshold == 0.05
    assert rule.severity == AlertSeverity.CRITICAL
    assert rule.runbook_url == "/docs/runbooks/test.md"
    assert rule.description == "A test rule"


def test_alert_rule_is_dataclass():
    """AlertRule is a proper dataclass."""
    import dataclasses

    from modules.credit.alerting import AlertRule

    assert dataclasses.is_dataclass(AlertRule)


# --- Cycle 3: Default rules and get_alert_rules ---


def test_get_alert_rules_returns_list():
    """get_alert_rules returns a list of AlertRule instances."""
    from modules.credit.alerting import AlertRule, get_alert_rules

    rules = get_alert_rules()
    assert isinstance(rules, list)
    assert all(isinstance(r, AlertRule) for r in rules)


def test_get_alert_rules_contains_three_defaults():
    """get_alert_rules returns exactly three default rules."""
    from modules.credit.alerting import get_alert_rules

    assert len(get_alert_rules()) == 3


def test_default_rules_include_error_rate():
    """Default rules include a high_error_rate rule."""
    from modules.credit.alerting import AlertSeverity, get_alert_rules

    rules = get_alert_rules()
    names = [r.name for r in rules]
    assert "high_error_rate" in names

    error_rule = next(r for r in rules if r.name == "high_error_rate")
    assert error_rule.threshold == 0.05
    assert error_rule.severity == AlertSeverity.CRITICAL


def test_default_rules_include_latency_p95():
    """Default rules include a high_latency_p95 rule."""
    from modules.credit.alerting import AlertSeverity, get_alert_rules

    rules = get_alert_rules()
    latency_rule = next(r for r in rules if r.name == "high_latency_p95")
    assert latency_rule.threshold == 0.5
    assert latency_rule.severity == AlertSeverity.WARNING


def test_default_rules_include_health_check():
    """Default rules include a health_check_failure rule."""
    from modules.credit.alerting import AlertSeverity, get_alert_rules

    rules = get_alert_rules()
    hc_rule = next(r for r in rules if r.name == "health_check_failure")
    assert hc_rule.severity == AlertSeverity.CRITICAL


def test_get_alert_rules_returns_copy():
    """get_alert_rules returns a new list each call (not mutable reference)."""
    from modules.credit.alerting import get_alert_rules

    rules1 = get_alert_rules()
    rules2 = get_alert_rules()
    assert rules1 is not rules2


# --- Cycle 4: check_error_rate ---


def test_check_error_rate_above_threshold():
    """check_error_rate returns True when error rate exceeds threshold."""
    from modules.credit.alerting import check_error_rate

    # 6 errors out of 100 = 6% > 5% threshold
    assert check_error_rate(total_requests=100, error_count=6) is True


def test_check_error_rate_below_threshold():
    """check_error_rate returns False when error rate is below threshold."""
    from modules.credit.alerting import check_error_rate

    # 4 errors out of 100 = 4% < 5% threshold
    assert check_error_rate(total_requests=100, error_count=4) is False


def test_check_error_rate_at_threshold():
    """check_error_rate returns False when error rate equals threshold (not exceeded)."""
    from modules.credit.alerting import check_error_rate

    # 5 errors out of 100 = exactly 5% = not exceeded
    assert check_error_rate(total_requests=100, error_count=5) is False


def test_check_error_rate_zero_requests():
    """check_error_rate returns False when total_requests is zero (no division error)."""
    from modules.credit.alerting import check_error_rate

    assert check_error_rate(total_requests=0, error_count=0) is False


def test_check_error_rate_custom_threshold():
    """check_error_rate respects a custom threshold."""
    from modules.credit.alerting import check_error_rate

    # 2 errors out of 100 = 2% > 1% custom threshold
    assert check_error_rate(total_requests=100, error_count=2, threshold=0.01) is True
    # 2 errors out of 100 = 2% < 10% custom threshold
    assert check_error_rate(total_requests=100, error_count=2, threshold=0.10) is False


# --- Cycle 5: check_latency ---


def test_check_latency_above_threshold():
    """check_latency returns True when p95 exceeds threshold."""
    from modules.credit.alerting import check_latency

    assert check_latency(p95_seconds=0.6) is True


def test_check_latency_below_threshold():
    """check_latency returns False when p95 is below threshold."""
    from modules.credit.alerting import check_latency

    assert check_latency(p95_seconds=0.4) is False


def test_check_latency_at_threshold():
    """check_latency returns False when p95 equals threshold (not exceeded)."""
    from modules.credit.alerting import check_latency

    assert check_latency(p95_seconds=0.5) is False


def test_check_latency_custom_threshold():
    """check_latency respects a custom threshold."""
    from modules.credit.alerting import check_latency

    assert check_latency(p95_seconds=0.3, threshold=0.2) is True
    assert check_latency(p95_seconds=0.3, threshold=1.0) is False


# --- Cycle 6: YAML configuration files ---

_PROJECT_ROOT = __import__("pathlib").Path(__file__).resolve().parents[4]


def test_prometheus_rules_yaml_exists():
    """Prometheus alerting rules YAML file exists."""
    rules_path = _PROJECT_ROOT / "alerting" / "prometheus_rules.yml"
    assert rules_path.exists(), f"Missing {rules_path}"


def test_prometheus_rules_yaml_is_valid():
    """Prometheus alerting rules YAML parses without errors."""
    import yaml

    rules_path = _PROJECT_ROOT / "alerting" / "prometheus_rules.yml"
    with open(rules_path) as f:
        data = yaml.safe_load(f)
    assert "groups" in data
    assert len(data["groups"]) >= 1
    group = data["groups"][0]
    assert "rules" in group
    assert len(group["rules"]) >= 3


def test_prometheus_rules_contain_expected_alerts():
    """Prometheus rules YAML has HighErrorRate, HighLatencyP95, HealthCheckFailure."""
    import yaml

    rules_path = _PROJECT_ROOT / "alerting" / "prometheus_rules.yml"
    with open(rules_path) as f:
        data = yaml.safe_load(f)
    alert_names = [r["alert"] for r in data["groups"][0]["rules"]]
    assert "HighErrorRate" in alert_names
    assert "HighLatencyP95" in alert_names
    assert "HealthCheckFailure" in alert_names


def test_alertmanager_yaml_exists():
    """Alertmanager configuration YAML file exists."""
    am_path = _PROJECT_ROOT / "alerting" / "alertmanager.yml"
    assert am_path.exists(), f"Missing {am_path}"


def test_alertmanager_yaml_is_valid():
    """Alertmanager configuration YAML parses and has required sections."""
    import yaml

    am_path = _PROJECT_ROOT / "alerting" / "alertmanager.yml"
    with open(am_path) as f:
        data = yaml.safe_load(f)
    assert "route" in data
    assert "receivers" in data


def test_alertmanager_has_pagerduty_receiver():
    """Alertmanager config routes critical alerts to PagerDuty."""
    import yaml

    am_path = _PROJECT_ROOT / "alerting" / "alertmanager.yml"
    with open(am_path) as f:
        data = yaml.safe_load(f)
    receiver_names = [r["name"] for r in data["receivers"]]
    assert "pagerduty" in receiver_names
