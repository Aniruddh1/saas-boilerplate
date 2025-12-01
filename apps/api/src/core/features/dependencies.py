"""
FastAPI dependencies for feature flags.

Usage:
    from src.core.features import Feature, is_feature_enabled

    @router.get("/dashboard")
    async def dashboard(feature: Feature):
        if await feature.is_enabled("new_dashboard"):
            return new_dashboard()
        return old_dashboard()
"""

from functools import lru_cache
from typing import Annotated

from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.api.dependencies.database import get_db
from src.core.auth import get_current_user_optional

from .interfaces import FeatureBackend
from .service import FeatureService
from .backends.database import DatabaseFeatureBackend
from .backends.memory import MemoryFeatureBackend


# ============================================================
# BACKEND FACTORY
# ============================================================

# In-memory backend singleton (for development)
_memory_backend: MemoryFeatureBackend | None = None


def get_memory_backend() -> MemoryFeatureBackend:
    """Get or create memory backend singleton."""
    global _memory_backend
    if _memory_backend is None:
        _memory_backend = MemoryFeatureBackend()
    return _memory_backend


async def get_feature_backend(
    db: AsyncSession = Depends(get_db),
) -> FeatureBackend:
    """
    Get feature backend based on configuration.

    Uses FEATURE_BACKEND setting:
    - "database": PostgreSQL (default, production)
    - "memory": In-memory (development/testing)
    """
    backend_type = settings.features.backend

    if backend_type == "memory":
        return get_memory_backend()
    else:
        return DatabaseFeatureBackend(db)


# ============================================================
# FEATURE SERVICE DEPENDENCY
# ============================================================

async def get_feature_service(
    backend: FeatureBackend = Depends(get_feature_backend),
) -> FeatureService:
    """Get feature service instance."""
    default_enabled = settings.features.default_enabled
    return FeatureService(backend, default_enabled=default_enabled)


# Type alias for cleaner injection
Feature = Annotated[FeatureService, Depends(get_feature_service)]


# ============================================================
# USER-AWARE FEATURE SERVICE
# ============================================================

class UserFeatureService:
    """
    Feature service bound to current user.

    Provides convenient methods that automatically use the current user.
    """

    def __init__(self, service: FeatureService, user):
        self._service = service
        self._user = user

    async def is_enabled(self, key: str, default: bool = False) -> bool:
        """Check if feature is enabled for current user."""
        return await self._service.is_enabled(key, self._user, default)

    async def evaluate(self, key: str):
        """Evaluate feature with detailed result."""
        return await self._service.evaluate(key, self._user)

    async def get_all(self) -> dict[str, bool]:
        """Get all flags for current user."""
        return await self._service.get_all_flags(self._user)

    async def require(self, key: str) -> None:
        """
        Require feature to be enabled.

        Raises 404 if feature is disabled (feature doesn't exist for user).
        """
        if not await self.is_enabled(key):
            raise HTTPException(status_code=404, detail="Not found")

    async def require_or_403(self, key: str) -> None:
        """
        Require feature to be enabled.

        Raises 403 if feature is disabled.
        """
        if not await self.is_enabled(key):
            raise HTTPException(
                status_code=403,
                detail=f"Feature '{key}' is not available"
            )

    # Passthrough to underlying service
    @property
    def service(self) -> FeatureService:
        return self._service


async def get_user_feature_service(
    service: FeatureService = Depends(get_feature_service),
    user=Depends(get_current_user_optional),
) -> UserFeatureService:
    """Get feature service bound to current user."""
    return UserFeatureService(service, user)


# Type alias
UserFeature = Annotated[UserFeatureService, Depends(get_user_feature_service)]


# ============================================================
# SIMPLE FUNCTION (no user context)
# ============================================================

async def is_feature_enabled(
    key: str,
    service: FeatureService = Depends(get_feature_service),
) -> bool:
    """
    Simple check without user context.

    Only works for globally enabled flags (no percentage/targeting).
    """
    return await service.is_enabled(key)
