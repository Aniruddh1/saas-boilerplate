"""
Logging middleware for request/response logging.
"""

import time
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from .request_id import get_request_id

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Log request/response details."""

    async def dispatch(self, request: Request, call_next) -> Response:
        start_time = time.perf_counter()

        # Log request
        logger.info(
            "Request started",
            extra={
                "request_id": get_request_id(),
                "method": request.method,
                "path": request.url.path,
                "query": str(request.query_params),
                "client_ip": request.client.host if request.client else None,
            },
        )

        # Process request
        response = await call_next(request)

        # Calculate duration
        duration_ms = (time.perf_counter() - start_time) * 1000

        # Log response
        logger.info(
            "Request completed",
            extra={
                "request_id": get_request_id(),
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": round(duration_ms, 2),
            },
        )

        return response
