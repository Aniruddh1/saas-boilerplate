"""
Authorization decorators for route handlers.

Usage:
    from src.core.auth import require, require_admin

    @router.get("/admin")
    @require_admin
    async def admin_only(user: CurrentUser):
        ...

    @router.post("/posts")
    @require("posts:create")
    async def create_post(user: CurrentUser):
        ...

    @router.post("/publish")
    @require("posts:create", "posts:publish")  # AND - needs both
    async def create_and_publish(user: CurrentUser):
        ...

    @router.delete("/posts/{id}")
    @require(any_of=["posts:delete", "admin"])  # OR - needs any
    async def delete_post(user: CurrentUser):
        ...
"""

from functools import wraps
from typing import Callable, Any
from fastapi import HTTPException, status, Request

from .dependencies import get_policy_engine


def require(*permissions: str, any_of: list[str] | None = None) -> Callable:
    """
    Decorator to require specific permissions.

    Args:
        *permissions: Permission strings that are ALL required (AND logic)
        any_of: Permission strings where ANY is sufficient (OR logic)

    Usage:
        @require("posts:create")
        async def create_post(user: CurrentUser):
            ...

        @require("posts:create", "posts:publish")  # needs BOTH
        async def create_and_publish(user: CurrentUser):
            ...

        @require(any_of=["posts:delete", "admin"])  # needs ANY
        async def delete_post(user: CurrentUser):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Find user in kwargs (could be named 'user', 'current_user', etc.)
            user = None
            for key in ['user', 'current_user', 'actor']:
                if key in kwargs:
                    user = kwargs[key]
                    break

            # Also check positional args (first arg might be self/cls for methods)
            if user is None:
                for arg in args:
                    if hasattr(arg, 'id') and hasattr(arg, 'is_admin'):
                        user = arg
                        break

            if user is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required",
                )

            policy_engine = get_policy_engine()

            # Check AND permissions (all required)
            if permissions:
                for perm in permissions:
                    has_perm = await policy_engine.has_permission(user, perm)
                    if not has_perm:
                        raise HTTPException(
                            status_code=status.HTTP_403_FORBIDDEN,
                            detail=f"Permission required: {perm}",
                        )

            # Check OR permissions (any sufficient)
            if any_of:
                has_any = False
                for perm in any_of:
                    if await policy_engine.has_permission(user, perm):
                        has_any = True
                        break

                if not has_any:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"One of these permissions required: {any_of}",
                    )

            return await func(*args, **kwargs)

        return wrapper
    return decorator


def require_admin(func: Callable) -> Callable:
    """
    Decorator to require admin user.

    Usage:
        @router.get("/admin")
        @require_admin
        async def admin_only(user: CurrentUser):
            ...
    """
    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        # Find user in kwargs
        user = None
        for key in ['user', 'current_user', 'actor']:
            if key in kwargs:
                user = kwargs[key]
                break

        if user is None:
            for arg in args:
                if hasattr(arg, 'id') and hasattr(arg, 'is_admin'):
                    user = arg
                    break

        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )

        if not getattr(user, 'is_admin', False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required",
            )

        return await func(*args, **kwargs)

    return wrapper


def scoped(resource_type: str | None = None) -> Callable:
    """
    Decorator to indicate that a route returns scoped data.

    This is primarily for documentation/introspection.
    Actual scoping should be done via auth.scoped() in the handler.

    Usage:
        @router.get("/transactions")
        @scoped("transactions")
        async def list_transactions(auth: Authorize):
            return await auth.scoped(select(Transaction))
    """
    def decorator(func: Callable) -> Callable:
        # Add metadata for introspection
        func._scoped_resource_type = resource_type
        return func
    return decorator
