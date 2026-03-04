"""Tests for load testing scripts — verify locustfile structure and docker-compose.

Uses AST parsing instead of importing locust to avoid gevent monkey-patching
conflicts with the asyncio-based test suite.
"""

import ast
from pathlib import Path

import pytest
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[4]
LOCUSTFILE = PROJECT_ROOT / "loadtests" / "locustfile.py"
COMPOSE_FILE = PROJECT_ROOT / "docker-compose.loadtest.yml"


@pytest.fixture()
def locust_ast() -> ast.Module:
    """Parse loadtests/locustfile.py into an AST tree."""
    source = LOCUSTFILE.read_text()
    return ast.parse(source, filename=str(LOCUSTFILE))


@pytest.fixture()
def user_class_node(locust_ast: ast.Module) -> ast.ClassDef:
    """Extract the CreditApiUser class definition from the AST."""
    for node in ast.walk(locust_ast):
        if isinstance(node, ast.ClassDef) and node.name == "CreditApiUser":
            return node
    pytest.fail("CreditApiUser class not found in AST")


def _get_method_names(cls_node: ast.ClassDef) -> list[str]:
    """Return method names defined directly on a class."""
    return [
        node.name
        for node in cls_node.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]


def _get_task_weight(func_node: ast.FunctionDef) -> int | None:
    """Extract the @task(N) weight from a decorated function. Returns None if no @task."""
    for dec in func_node.decorator_list:
        if isinstance(dec, ast.Call) and isinstance(dec.func, ast.Name):
            if dec.func.id == "task" and dec.args:
                arg = dec.args[0]
                if isinstance(arg, ast.Constant) and isinstance(arg.value, int):
                    return arg.value
        if isinstance(dec, ast.Name) and dec.id == "task":
            return 1  # @task without args defaults to weight 1
    return None


# --- Cycle 1: Locustfile exists and is valid Python ---


def test_locustfile_exists():
    """loadtests/locustfile.py must exist on disk."""
    assert LOCUSTFILE.is_file(), f"Missing {LOCUSTFILE}"


def test_locustfile_valid_python(locust_ast: ast.Module):
    """loadtests/locustfile.py must be valid Python (parseable by ast)."""
    assert isinstance(locust_ast, ast.Module)


def test_locustfile_imports_locust(locust_ast: ast.Module):
    """locustfile must import from the locust package."""
    imported_modules: list[str] = []
    for node in ast.walk(locust_ast):
        if isinstance(node, ast.ImportFrom) and node.module:
            imported_modules.append(node.module)
    assert "locust" in imported_modules, (
        f"Expected 'from locust import ...' but found imports: {imported_modules}"
    )


def test_credit_api_user_class_exists(user_class_node: ast.ClassDef):
    """CreditApiUser class must be defined."""
    assert user_class_node.name == "CreditApiUser"


def test_user_inherits_http_user(user_class_node: ast.ClassDef):
    """CreditApiUser must inherit from HttpUser."""
    base_names = []
    for base in user_class_node.bases:
        if isinstance(base, ast.Name):
            base_names.append(base.id)
        elif isinstance(base, ast.Attribute):
            base_names.append(base.attr)
    assert "HttpUser" in base_names, (
        f"Expected HttpUser base class, found: {base_names}"
    )


# --- Cycle 2: Task definitions ---


def test_health_check_task_defined(user_class_node: ast.ClassDef):
    """CreditApiUser must have a health_check method."""
    methods = _get_method_names(user_class_node)
    assert "health_check" in methods, f"health_check not found. Methods: {methods}"


def test_assess_task_defined(user_class_node: ast.ClassDef):
    """CreditApiUser must have an assess method."""
    methods = _get_method_names(user_class_node)
    assert "assess" in methods, f"assess not found. Methods: {methods}"


def test_health_check_has_task_decorator(user_class_node: ast.ClassDef):
    """health_check must be decorated with @task."""
    for node in user_class_node.body:
        if isinstance(node, ast.FunctionDef) and node.name == "health_check":
            weight = _get_task_weight(node)
            assert weight is not None, "health_check missing @task decorator"
            return
    pytest.fail("health_check method not found")


def test_assess_has_task_decorator(user_class_node: ast.ClassDef):
    """assess must be decorated with @task."""
    for node in user_class_node.body:
        if isinstance(node, ast.FunctionDef) and node.name == "assess":
            weight = _get_task_weight(node)
            assert weight is not None, "assess missing @task decorator"
            return
    pytest.fail("assess method not found")


def test_assess_has_higher_weight(user_class_node: ast.ClassDef):
    """assess task should have higher weight than health_check."""
    weights: dict[str, int] = {}
    for node in user_class_node.body:
        if isinstance(node, ast.FunctionDef):
            w = _get_task_weight(node)
            if w is not None:
                weights[node.name] = w
    assert weights.get("assess", 0) > weights.get("health_check", 0), (
        f"assess weight ({weights.get('assess', 0)}) should exceed "
        f"health_check weight ({weights.get('health_check', 0)})"
    )


def test_wait_time_assigned(user_class_node: ast.ClassDef):
    """CreditApiUser must assign wait_time at class level."""
    assigned_names = []
    for node in user_class_node.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    assigned_names.append(target.id)
    assert "wait_time" in assigned_names, (
        f"wait_time not assigned. Class-level assigns: {assigned_names}"
    )


# --- Cycle 3: Docker compose for load tests ---


def test_docker_compose_loadtest_exists():
    """docker-compose.loadtest.yml must exist."""
    assert COMPOSE_FILE.is_file(), f"Missing {COMPOSE_FILE}"


def test_docker_compose_loadtest_valid_yaml():
    """docker-compose.loadtest.yml must be valid YAML."""
    with open(COMPOSE_FILE) as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict), "YAML must parse to a dict"


def test_docker_compose_loadtest_has_locust_service():
    """docker-compose.loadtest.yml must define a 'locust' service."""
    with open(COMPOSE_FILE) as f:
        data = yaml.safe_load(f)
    assert "services" in data, "Missing 'services' key"
    assert "locust" in data["services"], "Missing 'locust' service"


def test_docker_compose_loadtest_locust_ports():
    """Locust service must expose the web UI port (8089)."""
    with open(COMPOSE_FILE) as f:
        data = yaml.safe_load(f)
    locust_svc = data["services"]["locust"]
    ports = locust_svc.get("ports", [])
    port_strings = [str(p) for p in ports]
    assert any("8089" in p for p in port_strings), (
        "Locust service must expose port 8089"
    )
