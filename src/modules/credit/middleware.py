"""Middleware for request IDs and security headers."""

from __future__ import annotations

import re
import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from .sentry import set_request_id_tag

_REQUEST_ID_PATTERN = re.compile(r"^[a-zA-Z0-9\-]{1,128}$")

_HSTS_VALUE = "max-age=63072000; includeSubDomains; preload"


class HstsMiddleware(BaseHTTPMiddleware):
    """Adds Strict-Transport-Security header in production mode."""

    def __init__(self, app, prod_check=None) -> None:
        super().__init__(app)
        self._is_prod = (prod_check or (lambda: False))()

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        response = await call_next(request)
        if self._is_prod:
            response.headers["strict-transport-security"] = _HSTS_VALUE
        return response


class HttpsRedirectMiddleware(BaseHTTPMiddleware):
    """Redirects HTTP to HTTPS in production mode."""

    def __init__(self, app, prod_check=None) -> None:
        super().__init__(app)
        self._is_prod = (prod_check or (lambda: False))()

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        if self._is_prod and request.url.scheme == "http":
            url = request.url.replace(scheme="https")
            return Response(status_code=307, headers={"location": str(url)})
        return await call_next(request)


class DeprecationMiddleware(BaseHTTPMiddleware):
    """Adds Deprecation and Sunset headers to legacy unversioned endpoints."""

    _DEPRECATED_PATHS = {"/assess"}

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        response = await call_next(request)
        if request.url.path in self._DEPRECATED_PATHS:
            response.headers["Deprecation"] = "true"
            response.headers["Sunset"] = "2026-09-01T00:00:00Z"
            response.headers["Link"] = '</v1/assess>; rel="successor-version"'
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Adds security headers to every response (Finding #8)."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        response = await call_next(request)
        response.headers["x-content-type-options"] = "nosniff"
        response.headers["referrer-policy"] = "strict-origin-when-cross-origin"
        response.headers["permissions-policy"] = (
            "camera=(), microphone=(), geolocation=()"
        )
        response.headers["x-frame-options"] = "DENY"
        return response


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Adds X-Request-ID to every request/response and binds it to structlog context."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Generate or propagate request ID."""
        client_id = request.headers.get("x-request-id")
        if client_id is not None and _REQUEST_ID_PATTERN.match(client_id):
            request_id = client_id
        else:
            request_id = str(uuid.uuid4())

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)
        set_request_id_tag(request_id)
        try:
            response = await call_next(request)
            response.headers["x-request-id"] = request_id
            return response
        finally:
            structlog.contextvars.clear_contextvars()
