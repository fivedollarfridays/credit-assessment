"""Credit Assessment API client."""

from __future__ import annotations

import httpx

from .auth import ApiKeyAuth, BearerAuth
from .exceptions import ApiError, AuthenticationError, RateLimitError, ValidationError
from .models import AssessmentResult, CreditProfile


class CreditAssessmentClient:
    """Typed Python client for the Credit Assessment API."""

    def __init__(
        self,
        base_url: str,
        *,
        auth: ApiKeyAuth | BearerAuth | None = None,
        timeout: float = 30.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.auth = auth
        self.timeout = timeout

    def _headers(self) -> dict[str, str]:
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self.auth is not None:
            headers.update(self.auth.headers())
        return headers

    def _handle_error(self, response: httpx.Response) -> None:
        if response.status_code == 401 or response.status_code == 403:
            raise AuthenticationError(response.text)
        if response.status_code == 422:
            data = response.json()
            raise ValidationError(details=data.get("detail", []))
        if response.status_code == 429:
            retry = response.headers.get("Retry-After")
            raise RateLimitError(
                retry_after=int(retry) if retry else None,
            )
        if response.status_code >= 400:
            raise ApiError(response.text, status_code=response.status_code)

    def assess(self, profile: CreditProfile) -> AssessmentResult:
        """Run a credit assessment."""
        with httpx.Client(timeout=self.timeout) as http:
            resp = http.post(
                f"{self.base_url}/v1/assess",
                json=profile.to_dict(),
                headers=self._headers(),
            )
        if resp.status_code >= 400:
            self._handle_error(resp)
        return AssessmentResult.from_dict(resp.json())

    def health(self) -> dict:
        """Check API health."""
        with httpx.Client(timeout=self.timeout) as http:
            resp = http.get(f"{self.base_url}/health")
        return resp.json()

    def get_disclosures(self) -> dict:
        """Get FCRA disclosures."""
        with httpx.Client(timeout=self.timeout) as http:
            resp = http.get(f"{self.base_url}/v1/disclosures")
        return resp.json()
