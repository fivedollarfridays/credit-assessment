"""Tests for medium-severity fixes (M-1, M-2, M-5)."""

from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# M-1: Path traversal in load_config
# ---------------------------------------------------------------------------


class TestLoadConfigPathTraversal:
    """Validate load_config blocks path traversal."""

    def test_blocks_parent_traversal(self) -> None:
        from modules.credit.agents.base import _load_config_cached, load_config

        _load_config_cached.cache_clear()
        with pytest.raises(ValueError, match="[Pp]ath traversal"):
            load_config("../../etc/passwd")

    def test_blocks_absolute_path(self) -> None:
        from modules.credit.agents.base import _load_config_cached, load_config

        _load_config_cached.cache_clear()
        with pytest.raises(ValueError, match="[Pp]ath traversal"):
            load_config("/etc/passwd")

    def test_allows_valid_config(self) -> None:
        from modules.credit.agents.base import _load_config_cached, load_config

        _load_config_cached.cache_clear()
        result = load_config("city_config")
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# M-2: CreateDisputeRequest.negative_item_data validation
# ---------------------------------------------------------------------------


class TestDisputeRequestValidation:
    """Validate negative_item_data has size constraints."""

    def test_rejects_oversized_dict(self) -> None:
        from pydantic import ValidationError
        from modules.credit.dispute_routes import CreateDisputeRequest

        # 21 keys should exceed the cap
        big_data = {f"key_{i}": f"value_{i}" for i in range(21)}
        with pytest.raises(ValidationError):
            CreateDisputeRequest(
                bureau="experian",
                negative_item_data=big_data,
            )

    def test_accepts_valid_fields(self) -> None:
        from modules.credit.dispute_routes import CreateDisputeRequest

        req = CreateDisputeRequest(
            bureau="experian",
            negative_item_data={
                "account_name": "Test Account",
                "type": "COLLECTION",
                "amount": 500.0,
            },
        )
        assert req.negative_item_data is not None
