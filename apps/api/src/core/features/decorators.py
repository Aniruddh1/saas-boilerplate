"""
Feature flag decorators.

Usage:
    from src.core.features import require_feature

    @router.get("/new-dashboard")
    @require_feature("new_dashboard")
    async def new_dashboard(user: CurrentUser):
        return {"dashboard": "new"}

    @router.get("/beta-feature")
    @require_feature("beta_feature", status_code=403)
    async def beta_feature(user: CurrentUser):
        return {"feature": "beta"}
"""

from functools import wraps
from typing import Callable, Any

from fastapi import HTTPException, Request
from fastapi.responses import RedirectResponse


def require_feature(
    feature_key: str,
    *,
    status_code: int = 404,
    detail: str | None = None,
    redirect_url: str | None = None,
):
    """
    Decorator to require a feature flag to be enabled.

    Args:
        feature_key: The feature flag key to check
        status_code: HTTP status code if disabled (default: 404)
        detail: Custom error message
        redirect_url: Redirect URL if disabled (instead of error)

    Usage:
        @router.get("/beta")
        @require_feature("beta_feature")
        async def beta_endpoint(user: CurrentUser):
            ...

        @router.get("/new-ui")
        @require_feature("new_ui", redirect_url="/old-ui")
        async def new_ui(user: CurrentUser):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            # Find request and user in kwargs
            request: Request | None = kwargs.get("request")
            user = kwargs.get("user")

            # Try to get feature service from request state
            feature_service = None
            if request and hasattr(request.state, "feature_service"):
                feature_service = request.state.feature_service

            # If no feature service, we need to get it from dependencies
            # This requires the endpoint to have Feature or UserFeature dependency
            if not feature_service:
                # Check if UserFeature or Feature was injected
                for key, value in kwargs.items():
                    if hasattr(value, "is_enabled") or hasattr(value, "_service"):
                        feature_service = value
                        break

            if feature_service is None:
                # No feature service available, allow through (fail open)
                # In production, you might want to fail closed instead
                return await func(*args, **kwargs)

            # Check feature
            if hasattr(feature_service, "_service"):
                # UserFeatureService
                enabled = await feature_service.is_enabled(feature_key)
            else:
                # FeatureService
                enabled = await feature_service.is_enabled(feature_key, user)

            if not enabled:
                if redirect_url:
                    return RedirectResponse(url=redirect_url, status_code=302)

                error_detail = detail or f"Feature '{feature_key}' is not available"
                raise HTTPException(status_code=status_code, detail=error_detail)

            return await func(*args, **kwargs)

        return wrapper
    return decorator


def feature_variant(
    feature_key: str,
    *,
    enabled_handler: Callable | None = None,
    disabled_handler: Callable | None = None,
):
    """
    Decorator for A/B testing - route to different handlers.

    Args:
        feature_key: The feature flag key
        enabled_handler: Handler when feature is enabled
        disabled_handler: Handler when feature is disabled

    Usage:
        async def new_checkout(user: CurrentUser):
            return {"version": "new"}

        async def old_checkout(user: CurrentUser):
            return {"version": "old"}

        @router.post("/checkout")
        @feature_variant("new_checkout",
            enabled_handler=new_checkout,
            disabled_handler=old_checkout)
        async def checkout(user: CurrentUser):
            # This body is never reached - just for signature
            pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            user = kwargs.get("user")

            # Get feature service from kwargs
            feature_service = None
            for key, value in kwargs.items():
                if hasattr(value, "is_enabled") or hasattr(value, "_service"):
                    feature_service = value
                    break

            # Determine which handler to use
            enabled = False
            if feature_service:
                if hasattr(feature_service, "_service"):
                    enabled = await feature_service.is_enabled(feature_key)
                else:
                    enabled = await feature_service.is_enabled(feature_key, user)

            if enabled and enabled_handler:
                return await enabled_handler(*args, **kwargs)
            elif not enabled and disabled_handler:
                return await disabled_handler(*args, **kwargs)
            else:
                # Fall through to decorated function
                return await func(*args, **kwargs)

        return wrapper
    return decorator
