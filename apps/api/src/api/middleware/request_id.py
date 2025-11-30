"""
Request ID middleware for request tracing.
"""

import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
import contextvars

# Context variable for request ID
request_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar(
    "request_id", default=""
)


def get_request_id() -> str:
    """Get current request ID from context."""
    return request_id_ctx.get()


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Add unique request ID to each request."""

    async def dispatch(self, request: Request, call_next) -> Response:
        # Check for incoming request ID header
        request_id = request.headers.get("X-Request-ID")

        if not request_id:
            request_id = str(uuid.uuid4())

        # Set in context
        token = request_id_ctx.set(request_id)

        try:
            # Add to request state
            request.state.request_id = request_id

            # Process request
            response = await call_next(request)

            # Add to response headers
            response.headers["X-Request-ID"] = request_id

            return response
        finally:
            request_id_ctx.reset(token)
