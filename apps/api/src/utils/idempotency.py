"""
Idempotency Key Utilities.

Ensures operations can be safely retried without side effects.
Critical for payments, webhooks, and any non-idempotent operations.

Usage:
    # As decorator
    @router.post("/payments")
    @idempotent(ttl=86400)  # Cache for 24 hours
    async def create_payment(data: PaymentCreate):
        ...

    # As dependency
    @router.post("/orders")
    async def create_order(
        data: OrderCreate,
        idem: IdempotencyGuard = Depends(get_idempotency_guard),
    ):
        async with idem.guard("create_order"):
            order = await process_order(data)
            return order

Pattern:
    1. Client sends: POST /payments with Idempotency-Key: "abc123"
    2. First request: Processes payment, caches response
    3. Retry request: Returns cached response (no duplicate payment)
"""

from __future__ import annotations

import hashlib
import json
import functools
from datetime import timedelta
from typing import Any, Callable, Optional
from uuid import UUID

from fastapi import Depends, Header, HTTPException, Request
from pydantic import BaseModel

from src.core.interfaces.cache import CacheBackend
from src.utils.caching import get_cache


# ============================================================
# MODELS
# ============================================================

class IdempotencyRecord(BaseModel):
    """Stored record of an idempotent operation."""
    key: str
    status: str  # "processing", "completed", "failed"
    status_code: int = 200
    response_body: Optional[str] = None
    created_at: str


class IdempotencyResult(BaseModel):
    """Result of idempotency check."""
    is_duplicate: bool
    cached_response: Optional[dict] = None
    cached_status_code: int = 200


# ============================================================
# IDEMPOTENCY GUARD
# ============================================================

class IdempotencyGuard:
    """
    Guard for idempotent operations.

    Usage:
        guard = IdempotencyGuard(cache, key="pay_abc123", ttl=86400)

        async with guard.guard("create_payment"):
            # This block only runs once per key
            result = await process_payment()
            return result
    """

    def __init__(
        self,
        cache: CacheBackend,
        idempotency_key: Optional[str],
        user_id: Optional[UUID] = None,
        ttl: int = 86400,  # 24 hours default
    ):
        self.cache = cache
        self.raw_key = idempotency_key
        self.user_id = user_id
        self.ttl = ttl

        # Build namespaced key
        if idempotency_key and user_id:
            self.key = f"idempotency:{user_id}:{idempotency_key}"
        elif idempotency_key:
            self.key = f"idempotency:{idempotency_key}"
        else:
            self.key = None

    async def check(self) -> IdempotencyResult:
        """
        Check if this is a duplicate request.

        Returns:
            IdempotencyResult with is_duplicate flag and cached response if any
        """
        if not self.key:
            return IdempotencyResult(is_duplicate=False)

        record = await self.cache.get(self.key)
        if not record:
            return IdempotencyResult(is_duplicate=False)

        # Found existing record
        if record.get("status") == "processing":
            # Request is still being processed (concurrent duplicate)
            raise HTTPException(
                status_code=409,
                detail="Request with this idempotency key is already being processed",
            )

        # Return cached response
        return IdempotencyResult(
            is_duplicate=True,
            cached_response=json.loads(record["response_body"]) if record.get("response_body") else None,
            cached_status_code=record.get("status_code", 200),
        )

    async def start(self, operation: str) -> None:
        """Mark operation as started (processing)."""
        if not self.key:
            return

        from src.utils.timezone import utc_now, to_iso8601

        record = {
            "key": self.raw_key,
            "status": "processing",
            "operation": operation,
            "created_at": to_iso8601(utc_now()),
        }
        # Short TTL for processing state (30 seconds)
        await self.cache.set(self.key, record, ttl=30)

    async def complete(
        self,
        response_body: Any,
        status_code: int = 200,
    ) -> None:
        """Mark operation as completed with response."""
        if not self.key:
            return

        from src.utils.timezone import utc_now, to_iso8601

        record = {
            "key": self.raw_key,
            "status": "completed",
            "status_code": status_code,
            "response_body": json.dumps(response_body, default=str),
            "created_at": to_iso8601(utc_now()),
        }
        await self.cache.set(self.key, record, ttl=self.ttl)

    async def fail(self, error: str, status_code: int = 500) -> None:
        """Mark operation as failed."""
        if not self.key:
            return

        from src.utils.timezone import utc_now, to_iso8601

        record = {
            "key": self.raw_key,
            "status": "failed",
            "status_code": status_code,
            "response_body": json.dumps({"error": error}),
            "created_at": to_iso8601(utc_now()),
        }
        # Cache failures for shorter time (1 hour)
        await self.cache.set(self.key, record, ttl=3600)

    class _GuardContext:
        """Context manager for idempotency guard."""

        def __init__(self, guard: "IdempotencyGuard", operation: str):
            self.guard = guard
            self.operation = operation
            self.result = None

        async def __aenter__(self):
            # Check for duplicate
            result = await self.guard.check()
            if result.is_duplicate:
                self.result = result
                return result

            # Start processing
            await self.guard.start(self.operation)
            return result

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            if exc_type:
                # Operation failed
                await self.guard.fail(str(exc_val))
            # Note: complete() must be called explicitly with response
            return False

    def guard(self, operation: str) -> _GuardContext:
        """
        Context manager for guarding an operation.

        Usage:
            async with idem.guard("create_payment") as result:
                if result.is_duplicate:
                    return JSONResponse(
                        content=result.cached_response,
                        status_code=result.cached_status_code,
                    )
                # Process normally
                response = await process()
                await idem.complete(response)
                return response
        """
        return self._GuardContext(self, operation)


# ============================================================
# FASTAPI DEPENDENCIES
# ============================================================

async def get_idempotency_guard(
    request: Request,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    cache: CacheBackend = Depends(get_cache),
) -> IdempotencyGuard:
    """
    FastAPI dependency for idempotency guard.

    Usage:
        @router.post("/payments")
        async def create_payment(
            data: PaymentCreate,
            idem: IdempotencyGuard = Depends(get_idempotency_guard),
        ):
            result = await idem.check()
            if result.is_duplicate:
                return JSONResponse(
                    content=result.cached_response,
                    status_code=result.cached_status_code,
                )

            payment = await process_payment(data)
            await idem.complete(payment.dict())
            return payment
    """
    # Get user_id from request state if available
    user_id = getattr(request.state, "user_id", None)

    return IdempotencyGuard(
        cache=cache,
        idempotency_key=idempotency_key,
        user_id=user_id,
    )


def require_idempotency_key(
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
) -> str:
    """
    Dependency that requires Idempotency-Key header.

    Usage:
        @router.post("/payments")
        async def create_payment(
            key: str = Depends(require_idempotency_key),
        ):
            ...
    """
    if not idempotency_key:
        raise HTTPException(
            status_code=400,
            detail="Idempotency-Key header is required for this operation",
        )
    return idempotency_key


# ============================================================
# DECORATOR
# ============================================================

def idempotent(
    ttl: int = 86400,
    require_key: bool = False,
):
    """
    Decorator for idempotent endpoints.

    Args:
        ttl: Time to cache response (seconds)
        require_key: If True, require Idempotency-Key header

    Usage:
        @router.post("/payments")
        @idempotent(ttl=86400, require_key=True)
        async def create_payment(data: PaymentCreate):
            return await process_payment(data)

    Note: This decorator requires the endpoint to have access to
    the cache backend. For more control, use IdempotencyGuard directly.
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract request from kwargs
            request = kwargs.get("request")
            if not request:
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break

            if not request:
                # No request found, just call function
                return await func(*args, **kwargs)

            # Get idempotency key from header
            key = request.headers.get("Idempotency-Key")

            if require_key and not key:
                raise HTTPException(
                    status_code=400,
                    detail="Idempotency-Key header is required",
                )

            if not key:
                # No key, just process normally
                return await func(*args, **kwargs)

            # Get cache
            cache = await get_cache()
            user_id = getattr(request.state, "user_id", None)

            guard = IdempotencyGuard(
                cache=cache,
                idempotency_key=key,
                user_id=user_id,
                ttl=ttl,
            )

            # Check for duplicate
            result = await guard.check()
            if result.is_duplicate:
                from fastapi.responses import JSONResponse
                return JSONResponse(
                    content=result.cached_response,
                    status_code=result.cached_status_code,
                    headers={"X-Idempotent-Replayed": "true"},
                )

            # Process request
            await guard.start(func.__name__)
            try:
                response = await func(*args, **kwargs)

                # Cache response
                if hasattr(response, "model_dump"):
                    await guard.complete(response.model_dump())
                elif hasattr(response, "dict"):
                    await guard.complete(response.dict())
                elif isinstance(response, dict):
                    await guard.complete(response)

                return response
            except Exception as e:
                await guard.fail(str(e))
                raise

        return wrapper
    return decorator


# ============================================================
# HELPERS
# ============================================================

def generate_idempotency_key(*args: Any) -> str:
    """
    Generate an idempotency key from arguments.

    Useful for creating deterministic keys based on operation parameters.

    Usage:
        key = generate_idempotency_key(
            "create_payment",
            user_id,
            amount,
            currency,
        )
    """
    content = json.dumps(args, sort_keys=True, default=str)
    return hashlib.sha256(content.encode()).hexdigest()[:32]
