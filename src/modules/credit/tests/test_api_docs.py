"""Tests for API documentation: OpenAPI spec, integration guide, code examples."""

from __future__ import annotations


# ---------------------------------------------------------------------------
# Cycle 1: OpenAPI spec enhancements
# ---------------------------------------------------------------------------


class TestOpenApiSpec:
    """Tests for enriched OpenAPI specification."""

    def test_openapi_has_description(self) -> None:
        from fastapi.testclient import TestClient

        from modules.credit.router import app

        client = TestClient(app)
        spec = client.get("/openapi.json").json()
        assert "description" in spec["info"]
        assert len(spec["info"]["description"]) > 50

    def test_openapi_has_version(self) -> None:
        from fastapi.testclient import TestClient

        from modules.credit.router import app

        client = TestClient(app)
        spec = client.get("/openapi.json").json()
        assert spec["info"]["version"] == "1.0.0"

    def test_openapi_has_tags(self) -> None:
        from fastapi.testclient import TestClient

        from modules.credit.router import app

        client = TestClient(app)
        spec = client.get("/openapi.json").json()
        assert "tags" in spec
        tag_names = [t["name"] for t in spec["tags"]]
        assert "assessment" in tag_names

    def test_openapi_assess_has_request_example(self) -> None:
        from fastapi.testclient import TestClient

        from modules.credit.router import app

        client = TestClient(app)
        spec = client.get("/openapi.json").json()
        # Check that /v1/assess POST has a request body schema
        assess_path = spec["paths"].get("/v1/assess", {})
        assert "post" in assess_path
        post_op = assess_path["post"]
        assert "requestBody" in post_op


# ---------------------------------------------------------------------------
# Cycle 2: Integration guide content
# ---------------------------------------------------------------------------


class TestIntegrationGuide:
    """Tests for integration guide module."""

    def test_guide_exists(self) -> None:
        from modules.credit.api_docs import get_integration_guide

        guide = get_integration_guide()
        assert isinstance(guide, dict)

    def test_guide_has_authentication_section(self) -> None:
        from modules.credit.api_docs import get_integration_guide

        guide = get_integration_guide()
        assert "authentication" in guide

    def test_guide_has_endpoints_section(self) -> None:
        from modules.credit.api_docs import get_integration_guide

        guide = get_integration_guide()
        assert "endpoints" in guide
        assert isinstance(guide["endpoints"], list)
        assert len(guide["endpoints"]) > 0

    def test_guide_has_error_handling_section(self) -> None:
        from modules.credit.api_docs import get_integration_guide

        guide = get_integration_guide()
        assert "error_handling" in guide

    def test_guide_has_rate_limiting_section(self) -> None:
        from modules.credit.api_docs import get_integration_guide

        guide = get_integration_guide()
        assert "rate_limiting" in guide


# ---------------------------------------------------------------------------
# Cycle 3: Code examples
# ---------------------------------------------------------------------------


class TestCodeExamples:
    """Tests for code examples in Python, JavaScript, and curl."""

    def test_code_examples_exist(self) -> None:
        from modules.credit.api_docs import get_code_examples

        examples = get_code_examples()
        assert isinstance(examples, dict)

    def test_has_python_example(self) -> None:
        from modules.credit.api_docs import get_code_examples

        examples = get_code_examples()
        assert "python" in examples
        assert "requests" in examples["python"] or "httpx" in examples["python"]

    def test_has_javascript_example(self) -> None:
        from modules.credit.api_docs import get_code_examples

        examples = get_code_examples()
        assert "javascript" in examples
        assert "fetch" in examples["javascript"]

    def test_has_curl_example(self) -> None:
        from modules.credit.api_docs import get_code_examples

        examples = get_code_examples()
        assert "curl" in examples
        assert "curl" in examples["curl"]

    def test_examples_reference_assess_endpoint(self) -> None:
        from modules.credit.api_docs import get_code_examples

        examples = get_code_examples()
        for lang, code in examples.items():
            assert "/v1/assess" in code, f"{lang} example missing /v1/assess"


# ---------------------------------------------------------------------------
# Cycle 4: /docs/guide endpoint
# ---------------------------------------------------------------------------


class TestDocsEndpoint:
    """Tests for documentation API endpoints."""

    def test_guide_endpoint_returns_200(self) -> None:
        from fastapi.testclient import TestClient

        from modules.credit.router import app

        client = TestClient(app)
        resp = client.get("/v1/docs/guide")
        assert resp.status_code == 200

    def test_guide_endpoint_returns_all_sections(self) -> None:
        from fastapi.testclient import TestClient

        from modules.credit.router import app

        client = TestClient(app)
        data = client.get("/v1/docs/guide").json()
        assert "authentication" in data
        assert "endpoints" in data
        assert "error_handling" in data
        assert "code_examples" in data

    def test_examples_endpoint_returns_200(self) -> None:
        from fastapi.testclient import TestClient

        from modules.credit.router import app

        client = TestClient(app)
        resp = client.get("/v1/docs/examples")
        assert resp.status_code == 200

    def test_examples_endpoint_has_all_languages(self) -> None:
        from fastapi.testclient import TestClient

        from modules.credit.router import app

        client = TestClient(app)
        data = client.get("/v1/docs/examples").json()
        assert "python" in data
        assert "javascript" in data
        assert "curl" in data

    def test_docs_endpoints_no_auth_required(self) -> None:
        from fastapi.testclient import TestClient

        from modules.credit.router import app

        client = TestClient(app)
        assert client.get("/v1/docs/guide").status_code == 200
        assert client.get("/v1/docs/examples").status_code == 200
