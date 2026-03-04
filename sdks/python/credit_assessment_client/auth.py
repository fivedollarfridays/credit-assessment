"""Authentication helpers for the Credit Assessment API."""

from __future__ import annotations


class ApiKeyAuth:
    """API key authentication via X-API-Key header."""

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    def headers(self) -> dict[str, str]:
        return {"X-API-Key": self._api_key}

    def __repr__(self) -> str:
        return "ApiKeyAuth(***)"


class BearerAuth:
    """JWT Bearer token authentication."""

    def __init__(self, token: str) -> None:
        self._token = token

    def headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._token}"}

    def __repr__(self) -> str:
        return "BearerAuth(***)"
