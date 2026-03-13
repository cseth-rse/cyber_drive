"""
Phase 5: Security hardening
  - HTTP security headers (CSP, HSTS, X-Frame-Options, etc.)
  - Distributed rate limiting via Redis (scales across multiple app instances)
  - Per-route override helpers for stricter auth/upload limits
"""
import logging
from typing import Callable
from fastapi import Request, Response
from slowapi import Limiter
from slowapi.util import get_remote_address

logger = logging.getLogger(__name__)

# ── Security Headers ──────────────────────────────────────────────────────────
_SECURITY_HEADERS = {
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
    "X-Content-Type-Options":    "nosniff",
    "X-Frame-Options":           "DENY",
    "X-XSS-Protection":          "1; mode=block",
    "Referrer-Policy":           "strict-origin-when-cross-origin",
    "Permissions-Policy":        "geolocation=(), camera=(), microphone=(), payment=()",
    "Content-Security-Policy":   "default-src 'none'; frame-ancestors 'none'; base-uri 'none';",
    "Server":                    "cyber-drive",
}


class SecurityHeadersMiddleware:
    """
    Pure ASGI middleware — does NOT use BaseHTTPMiddleware.

    BaseHTTPMiddleware has a known Starlette bug where it intercepts 500
    error responses before CORSMiddleware can attach Access-Control headers,
    causing browsers to see a CORS error instead of the real error.

    A pure ASGI middleware sits outside the middleware stack cleanly and
    does not interfere with error handling or response streaming.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_security_headers(message):
            if message["type"] == "http.response.start":
                headers = dict(message.get("headers", []))
                for key, value in _SECURITY_HEADERS.items():
                    if value:
                        headers[key.lower().encode()] = value.encode()
                    else:
                        headers.pop(key.lower().encode(), None)
                message = {**message, "headers": list(headers.items())}
            await send(message)

        await self.app(scope, receive, send_with_security_headers)


# Keep the old function signature so nothing else in the codebase breaks
async def add_security_headers(request: Request, call_next: Callable) -> Response:
    """Legacy shim — only used if BaseHTTPMiddleware is still wired up somewhere."""
    response: Response = await call_next(request)
    for header, value in _SECURITY_HEADERS.items():
        if value:
            response.headers[header] = value
        elif header in response.headers:
            del response.headers[header]
    return response


# ── Distributed Rate Limiter ──────────────────────────────────────────────────
def make_rate_limiter(settings) -> Limiter:
    try:
        import redis as _redis
        r = _redis.from_url(settings.redis_url, socket_timeout=2)
        r.ping()
        storage_uri = settings.redis_url
        logger.info("Rate limiter: using Redis backend (%s)", settings.redis_url)
    except Exception as exc:
        storage_uri = "memory://"
        logger.warning(
            "Rate limiter: Redis not reachable (%s) — falling back to in-memory. "
            "This does NOT work correctly in multi-instance deployments.",
            exc,
        )
    return Limiter(
        key_func=get_remote_address,
        default_limits=["100/minute"],
        storage_uri=storage_uri,
    )


# ── Per-route limit decorators ────────────────────────────────────────────────
AUTH_LIMIT     = "10/minute"
UPLOAD_LIMIT   = "20/minute"
DOWNLOAD_LIMIT = "60/minute"
ADMIN_LIMIT    = "200/minute"