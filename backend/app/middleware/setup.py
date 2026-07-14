"""
AutoWebAgent - Middleware
===========================
Rate limiting, security headers, request logging, CORS.
"""

import time
from typing import Callable
from fastapi import Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from loguru import logger

from app.core.config import settings
from app.core.exceptions import RateLimitExceededError


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Simple in-memory rate limiting middleware.

    Tracks requests per IP/endpoint. Uses a sliding window approach.
    For production, replace with Redis-based rate limiting.
    """

    def __init__(self, app, max_requests: int = 60, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._store: dict[str, list[float]] = {}

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip rate limiting for certain paths
        if request.url.path in ["/health", "/api/v1/health", "/metrics"]:
            return await call_next(request)

        client_ip = self._get_client_ip(request)
        window_key = f"{client_ip}:{request.url.path}"

        now = time.time()
        window_start = now - self.window_seconds

        # Get or create request timestamps for this key
        if window_key not in self._store:
            self._store[window_key] = []

        # Remove old entries outside the window
        self._store[window_key] = [
            ts for ts in self._store[window_key] if ts > window_start
        ]

        # Check rate limit
        if len(self._store[window_key]) >= self.max_requests:
            logger.warning(f"🚫 Rate limit exceeded: {client_ip} → {request.url.path}")
            retry_after = int(window_start + self.window_seconds - now) + 1
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limit exceeded",
                    "retry_after": max(retry_after, 1),
                },
                headers={"Retry-After": str(max(retry_after, 1))},
            )

        # Record this request
        self._store[window_key].append(now)

        # Cleanup old keys periodically
        if len(self._store) > 10000:
            self._cleanup()

        return await call_next(request)

    def _get_client_ip(self, request: Request) -> str:
        """Get real client IP, respecting proxy headers."""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        return request.client.host if request.client else "unknown"

    def _cleanup(self):
        """Remove expired entries to prevent memory leaks."""
        now = time.time()
        window_start = now - self.window_seconds
        self._store = {
            k: [ts for ts in v if ts > window_start]
            for k, v in self._store.items()
            if any(ts > window_start for ts in v)
        }


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log all incoming requests with timing information."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()

        # Log request
        logger.debug(
            f"⬅️  {request.method} {request.url.path} "
            f"from {request.client.host if request.client else 'unknown'}"
        )

        response = await call_next(request)

        # Calculate duration
        duration_ms = (time.time() - start_time) * 1000

        # Log response
        logger.debug(
            f"➡️  {request.method} {request.url.path} "
            f"→ {response.status_code} ({duration_ms:.0f}ms)"
        )

        # Add timing header
        response.headers["X-Response-Time"] = f"{duration_ms:.0f}ms"

        return response


class TrailingSlashMiddleware(BaseHTTPMiddleware):
    """
    Strip trailing slashes from all API requests silently.
    
    Routes are defined without trailing slashes (e.g., @router.post("/register")).
    This middleware normalizes incoming paths so both /api/v1/auth/register 
    and /api/v1/auth/register/ work identically — no redirects, no 404s.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path
        
        # Strip trailing slash from API paths (skip root / and files with extensions)
        if path.startswith("/api/") and len(path) > 1 and path.endswith("/"):
            last_segment = path.rstrip("/").split("/")[-1]
            if "." not in last_segment:
                new_path = path.rstrip("/")
                request.scope["path"] = new_path
                request.scope["raw_path"] = new_path.encode()
        
        return await call_next(request)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security-related HTTP headers to all responses.
    Also fixes redirect URLs from internal docker hostname to external host."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        # Fix redirect Location headers: replace docker internal host with external host
        if 300 <= response.status_code < 400:
            location = response.headers.get("location", "")
            if "backend:8000" in location:
                # Use X-Forwarded-Host if available, else request host
                forwarded_host = request.headers.get("x-forwarded-host", "")
                if forwarded_host:
                    new_location = location.replace(
                        "http://backend:8000",
                        f"http://{forwarded_host}"
                    )
                else:
                    # Fallback: use request host if not docker internal
                    host = request.headers.get("host", "localhost:3000")
                    if "backend" not in host:
                        new_location = location.replace(
                            "http://backend:8000",
                            f"http://{host}"
                        )
                    else:
                        new_location = location.replace(
                            "http://backend:8000",
                            "http://localhost:3000"
                        )
                response.headers["location"] = new_location

        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "geolocation=(), microphone=(), camera=()"
        )

        # Remove server signature
        try:
            del response.headers["Server"]
        except (KeyError, AttributeError):
            pass

        return response


def setup_middleware(app) -> None:
    """
    Register all middleware on the FastAPI app instance.

    Order matters: CORS → Security → Logging → Rate Limit.
    """

    # 1. CORS — must be first
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Response-Time"],
    )

    # 2. Trailing slash - must be BEFORE routers process the request
    app.add_middleware(TrailingSlashMiddleware)

    # 3. Security headers
    app.add_middleware(SecurityHeadersMiddleware)

    # 4. Request logging
    app.add_middleware(RequestLoggingMiddleware)

    # 5. Rate limiting
    app.add_middleware(
        RateLimitMiddleware,
        max_requests=settings.RATE_LIMIT_PER_MINUTE,
        window_seconds=60,
    )

    logger.info("🔒 Middleware registered: CORS, Security, Logging, RateLimit")
