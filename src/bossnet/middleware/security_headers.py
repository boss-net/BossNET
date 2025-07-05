"""
Security middleware for FastAPI application.
Implements security best practices including:
- Security headers (CSP, HSTS, etc.)
- Rate limiting
- Request validation
"""

import logging
import time
from typing import Callable, Dict, List, Optional, Tuple

from fastapi import HTTPException, JSONResponse, Request
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from settings import settings
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware that adds security headers to all responses."""

    def __init__(self, app, **kwargs):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = "default-src 'self'"

        return response


class RateLimitMiddleware:
    """Middleware for rate limiting requests."""

    def __init__(self, app, limit: str = "100/minute", key_func=None):
        self.app = app
        self.limiter = Limiter(key_func=key_func or get_remote_address, default_limits=[limit])

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive)

        # Check rate limit
        endpoint = f"{request.method}:{request.url.path}"
        try:
            self.limiter.check(request, endpoint)
        except RateLimitExceeded:
            response = JSONResponse(status_code=429, content={"detail": "Too many requests"})
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)


def setup_security_middleware(app):
    """Configure all security-related middleware."""

    # Add security headers
    app.add_middleware(SecurityHeadersMiddleware)

    # Add rate limiting
    app.add_middleware(RateLimitMiddleware, limit="100/minute")

    # Add GZip compression
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    # Enforce HTTPS in production
    if not settings.DEBUG:
        app.add_middleware(HTTPSRedirectMiddleware)

    # Configure trusted hosts
    trusted_hosts = ["*"] if settings.DEBUG else settings.ALLOWED_HOSTS
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=trusted_hosts)

    logger.info("Security middleware configured successfully")
