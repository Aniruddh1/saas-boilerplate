"""
Request Context Utilities.

Provides correlation IDs and request context for:
- Distributed tracing
- Log correlation
- Debugging in production

Usage:
    # In middleware (automatic)
    app.add_middleware(RequestContextMiddleware)

    # Access anywhere in request lifecycle
    from src.utils.context import get_correlation_id, get_request_context

    correlation_id = get_correlation_id()
    logger.info("Processing", correlation_id=correlation_id)

    # In outgoing HTTP requests
    headers = {"X-Correlation-ID": get_correlation_id()}
"""

from __future__ import annotations

import uuid
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
import structlog

from src.utils.timezone import utc_now


# ============================================================
# CONTEXT VARIABLES
# ============================================================

# Request-scoped context using contextvars (async-safe)
_correlation_id: ContextVar[Optional[str]] = ContextVar("correlation_id", default=None)
_request_id: ContextVar[Optional[str]] = ContextVar("request_id", default=None)
_request_context: ContextVar[Optional["RequestContext"]] = ContextVar("request_context", default=None)


# ============================================================
# REQUEST CONTEXT
# ============================================================

@dataclass
class RequestContext:
    """
    Context for the current request.

    Contains all request-scoped metadata useful for logging,
    tracing, and debugging.
    """
    # IDs
    request_id: str  # Unique per request
    correlation_id: str  # Shared across service calls

    # Request info
    method: str = ""
    path: str = ""
    client_ip: str = ""

    # Auth info (populated by auth middleware)
    user_id: Optional[str] = None
    tenant_id: Optional[str] = None

    # Timing
    started_at: datetime = field(default_factory=utc_now)

    # Custom metadata
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for logging."""
        return {
            "request_id": self.request_id,
            "correlation_id": self.correlation_id,
            "method": self.method,
            "path": self.path,
            "user_id": self.user_id,
            "tenant_id": self.tenant_id,
            **self.metadata,
        }

    def add_metadata(self, key: str, value: Any) -> None:
        """Add custom metadata to context."""
        self.metadata[key] = value


# ============================================================
# CONTEXT ACCESSORS
# ============================================================

def get_correlation_id() -> Optional[str]:
    """
    Get the current correlation ID.

    Returns None if called outside of a request context.

    Usage:
        correlation_id = get_correlation_id()
        logger.info("Processing order", correlation_id=correlation_id)
    """
    return _correlation_id.get()


def get_request_id() -> Optional[str]:
    """Get the current request ID."""
    return _request_id.get()


def get_request_context() -> Optional[RequestContext]:
    """
    Get the full request context.

    Usage:
        ctx = get_request_context()
        if ctx:
            logger.info("Request", **ctx.to_dict())
    """
    return _request_context.get()


def set_context_user(user_id: str, tenant_id: Optional[str] = None) -> None:
    """
    Set user info in request context.

    Call this from auth middleware after authentication.

    Usage:
        # In auth middleware
        set_context_user(str(user.id), str(user.tenant_id))
    """
    ctx = _request_context.get()
    if ctx:
        ctx.user_id = user_id
        ctx.tenant_id = tenant_id


def add_context_metadata(key: str, value: Any) -> None:
    """
    Add metadata to current request context.

    Usage:
        add_context_metadata("order_id", order.id)
    """
    ctx = _request_context.get()
    if ctx:
        ctx.add_metadata(key, value)


# ============================================================
# MIDDLEWARE
# ============================================================

class RequestContextMiddleware(BaseHTTPMiddleware):
    """
    Middleware that creates request context for each request.

    Sets up:
    - request_id: Unique ID for this request
    - correlation_id: From X-Correlation-ID header or generated

    Usage:
        app.add_middleware(RequestContextMiddleware)
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate or extract IDs
        request_id = str(uuid.uuid4())
        correlation_id = (
            request.headers.get("X-Correlation-ID") or
            request.headers.get("X-Request-ID") or
            str(uuid.uuid4())
        )

        # Get client IP
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            client_ip = forwarded.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "unknown"

        # Create context
        ctx = RequestContext(
            request_id=request_id,
            correlation_id=correlation_id,
            method=request.method,
            path=request.url.path,
            client_ip=client_ip,
        )

        # Set context vars
        _correlation_id.set(correlation_id)
        _request_id.set(request_id)
        _request_context.set(ctx)

        # Store on request state for easy access
        request.state.request_id = request_id
        request.state.correlation_id = correlation_id
        request.state.context = ctx

        # Process request
        response = await call_next(request)

        # Add tracing headers to response
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Correlation-ID"] = correlation_id

        return response


# ============================================================
# STRUCTLOG PROCESSOR
# ============================================================

def add_request_context(
    logger: Any,
    method_name: str,
    event_dict: dict[str, Any],
) -> dict[str, Any]:
    """
    Structlog processor that adds request context to all logs.

    Usage:
        import structlog

        structlog.configure(
            processors=[
                add_request_context,
                structlog.processors.JSONRenderer(),
            ]
        )
    """
    correlation_id = get_correlation_id()
    request_id = get_request_id()

    if correlation_id:
        event_dict["correlation_id"] = correlation_id
    if request_id:
        event_dict["request_id"] = request_id

    ctx = get_request_context()
    if ctx:
        if ctx.user_id:
            event_dict["user_id"] = ctx.user_id
        if ctx.tenant_id:
            event_dict["tenant_id"] = ctx.tenant_id

    return event_dict


# ============================================================
# HTTP CLIENT HELPER
# ============================================================

def get_tracing_headers() -> dict[str, str]:
    """
    Get headers to propagate tracing context to downstream services.

    Usage:
        import httpx

        async with httpx.AsyncClient() as client:
            response = await client.get(
                "http://other-service/api",
                headers=get_tracing_headers(),
            )
    """
    headers = {}

    correlation_id = get_correlation_id()
    if correlation_id:
        headers["X-Correlation-ID"] = correlation_id

    request_id = get_request_id()
    if request_id:
        headers["X-Parent-Request-ID"] = request_id

    return headers


# ============================================================
# BACKGROUND TASK CONTEXT
# ============================================================

def copy_context() -> dict[str, Any]:
    """
    Copy current context for use in background tasks.

    Usage:
        ctx_copy = copy_context()

        async def background_task():
            restore_context(ctx_copy)
            # Now has access to correlation_id etc.
    """
    return {
        "correlation_id": get_correlation_id(),
        "request_id": get_request_id(),
        "context": get_request_context(),
    }


def restore_context(ctx: dict[str, Any]) -> None:
    """
    Restore context in a background task.

    Usage:
        def background_job(ctx_copy):
            restore_context(ctx_copy)
            correlation_id = get_correlation_id()
    """
    if ctx.get("correlation_id"):
        _correlation_id.set(ctx["correlation_id"])
    if ctx.get("request_id"):
        _request_id.set(ctx["request_id"])
    if ctx.get("context"):
        _request_context.set(ctx["context"])
