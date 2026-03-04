"""Middleware for request IDs and security headers."""

from __future__ import annotations

import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from .sentry import set_request_id_tag

_HSTS_VALUE = "max-age=63072000; includeSubDomains; preload"


class HstsMiddleware(BaseHTTPMiddleware):
    """Adds Strict-Transport-Security header in production mode."""

    def __init__(self, app, prod_check=None) -> None:
        super().__init__(app)
        self._prod_check = prod_check or (lambda: False)

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        response = await call_next(request)
        if self._prod_check():
            response.headers["strict-transport-security"] = _HSTS_VALUE
        return response


class HttpsRedirectMiddleware(BaseHTTPMiddleware):
    """Redirects HTTP to HTTPS in production mode."""

    def __init__(self, app, prod_check=None) -> None:
        super().__init__(app)
        self._prod_check = prod_check or (lambda: False)

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        if self._prod_check() and request.url.scheme == "http":
            url = request.url.replace(scheme="https")
            return Response(status_code=307, headers={"location": str(url)})
        return await call_next(request)


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Adds X-Request-ID to every request/response and binds it to structlog context."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Generate or propagate request ID."""
        request_id = request.headers.get("x-request-id", str(uuid.uuid4()))

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)
        set_request_id_tag(request_id)
        try:
            response = await call_next(request)
            response.headers["x-request-id"] = request_id
            return response
        finally:
            structlog.contextvars.clear_contextvars()
