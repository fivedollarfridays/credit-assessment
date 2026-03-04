"""SDK exception hierarchy."""

from __future__ import annotations


class ApiError(Exception):
    """Base exception for API errors."""

    def __init__(self, message: str, *, status_code: int = 500) -> None:
        super().__init__(message)
        self.status_code = status_code


class AuthenticationError(ApiError):
    """Raised for 401/403 authentication failures."""

    def __init__(self, message: str = "Authentication failed") -> None:
        super().__init__(message, status_code=401)


class RateLimitError(ApiError):
    """Raised when rate limit is exceeded (429)."""

    def __init__(
        self, message: str = "Rate limit exceeded", retry_after: int | None = None
    ) -> None:
        super().__init__(message, status_code=429)
        self.retry_after = retry_after


class ValidationError(ApiError):
    """Raised for 422 validation errors."""

    def __init__(
        self,
        message: str = "Validation error",
        details: list[dict] | None = None,
    ) -> None:
        super().__init__(message, status_code=422)
        self.details = details or []
