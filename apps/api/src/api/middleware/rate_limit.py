"""
Rate limiting middleware using Redis sliding window.
"""

import time
from typing import Callable
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse
import redis.asyncio as redis

from src.core.config import settings


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware using Redis sliding window algorithm.

    Limits requests per IP or per user (if authenticated).
    Configurable via settings:
        - rate_limit_enabled: Enable/disable rate limiting
        - rate_limit_requests: Max requests per window
        - rate_limit_window: Window size in seconds
    """

    def __init__(self, app, redis_client: redis.Redis | None = None):
        super().__init__(app)
        self.redis_client = redis_client
        self.enabled = settings.rate_limit_enabled
        self.max_requests = settings.rate_limit_requests
        self.window_seconds = settings.rate_limit_window

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if not self.enabled:
            return await call_next(request)

        # Skip rate limiting for certain paths
        if self._should_skip(request.url.path):
            return await call_next(request)

        # Get identifier (user_id if authenticated, else IP)
        identifier = self._get_identifier(request)

        # Check rate limit
        is_allowed, remaining, reset_time = await self._check_rate_limit(identifier)

        if not is_allowed:
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Too many requests",
                    "retry_after": reset_time,
                },
                headers={
                    "X-RateLimit-Limit": str(self.max_requests),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(reset_time),
                    "Retry-After": str(reset_time),
                },
            )

        # Process request
        response = await call_next(request)

        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(self.max_requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset_time)

        return response

    def _should_skip(self, path: str) -> bool:
        """Paths to skip rate limiting."""
        skip_paths = ["/health", "/docs", "/openapi.json", "/redoc"]
        return any(path.startswith(p) for p in skip_paths)

    def _get_identifier(self, request: Request) -> str:
        """Get rate limit identifier from request."""
        # Try to get user_id from request state (set by auth middleware)
        user_id = getattr(request.state, "user_id", None)
        if user_id:
            return f"user:{user_id}"

        # Fall back to IP address
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            ip = forwarded.split(",")[0].strip()
        else:
            ip = request.client.host if request.client else "unknown"

        return f"ip:{ip}"

    async def _check_rate_limit(
        self, identifier: str
    ) -> tuple[bool, int, int]:
        """
        Check rate limit using sliding window algorithm.

        Returns:
            (is_allowed, remaining_requests, seconds_until_reset)
        """
        if not self.redis_client:
            # No Redis, allow all requests
            return True, self.max_requests, 0

        now = time.time()
        window_start = now - self.window_seconds
        key = f"rate_limit:{identifier}"

        pipe = self.redis_client.pipeline()

        # Remove old entries
        pipe.zremrangebyscore(key, 0, window_start)
        # Add current request
        pipe.zadd(key, {str(now): now})
        # Count requests in window
        pipe.zcard(key)
        # Set expiry
        pipe.expire(key, self.window_seconds)

        results = await pipe.execute()
        request_count = results[2]

        remaining = max(0, self.max_requests - request_count)
        reset_time = int(self.window_seconds - (now - window_start))

        is_allowed = request_count <= self.max_requests

        return is_allowed, remaining, reset_time


# Decorator for per-endpoint rate limiting
def rate_limit(
    max_requests: int = 10,
    window_seconds: int = 60,
):
    """
    Decorator for per-endpoint rate limiting.

    Usage:
        @router.get("/expensive")
        @rate_limit(max_requests=5, window_seconds=60)
        async def expensive_endpoint():
            ...
    """
    def decorator(func: Callable) -> Callable:
        func._rate_limit = {
            "max_requests": max_requests,
            "window_seconds": window_seconds,
        }
        return func
    return decorator
