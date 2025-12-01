"""
Database backend for feature flags.

Uses PostgreSQL for persistent storage.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select, delete, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..interfaces import FeatureFlag, FeatureOverride, FeatureBackend
from ..models import FeatureFlagModel, UserFeatureGroup, FeatureFlagOverride


class DatabaseFeatureBackend(FeatureBackend):
    """
    PostgreSQL-backed feature flag storage.

    Production-ready with proper indexing.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    # ============================================================
    # FLAG OPERATIONS
    # ============================================================

    async def get_flag(self, key: str) -> FeatureFlag | None:
        """Get a feature flag by key."""
        query = select(FeatureFlagModel).where(FeatureFlagModel.key == key)
        result = await self.db.execute(query)
        model = result.scalar_one_or_none()

        if not model:
            return None

        return self._model_to_flag(model)

    async def list_flags(self) -> list[FeatureFlag]:
        """List all feature flags."""
        query = select(FeatureFlagModel).order_by(FeatureFlagModel.key)
        result = await self.db.execute(query)
        models = result.scalars().all()

        return [self._model_to_flag(m) for m in models]

    async def create_flag(self, flag: FeatureFlag) -> FeatureFlag:
        """Create a new feature flag."""
        model = FeatureFlagModel(
            key=flag.key,
            name=flag.name,
            description=flag.description,
            enabled=flag.enabled,
            percentage=flag.percentage,
            conditions=flag.conditions or {},
        )
        self.db.add(model)
        await self.db.flush()
        await self.db.refresh(model)

        return self._model_to_flag(model)

    async def update_flag(self, key: str, updates: dict[str, Any]) -> FeatureFlag | None:
        """Update a feature flag."""
        query = select(FeatureFlagModel).where(FeatureFlagModel.key == key)
        result = await self.db.execute(query)
        model = result.scalar_one_or_none()

        if not model:
            return None

        for field, value in updates.items():
            if hasattr(model, field):
                setattr(model, field, value)

        await self.db.flush()
        await self.db.refresh(model)

        return self._model_to_flag(model)

    async def delete_flag(self, key: str) -> bool:
        """Delete a feature flag."""
        query = delete(FeatureFlagModel).where(FeatureFlagModel.key == key)
        result = await self.db.execute(query)
        await self.db.flush()

        return result.rowcount > 0

    # ============================================================
    # OVERRIDE OPERATIONS
    # ============================================================

    async def get_override(self, user_id: UUID, flag_key: str) -> FeatureOverride | None:
        """Get override for a specific user and flag."""
        query = select(FeatureFlagOverride).where(
            FeatureFlagOverride.user_id == user_id,
            FeatureFlagOverride.flag_key == flag_key,
        )
        result = await self.db.execute(query)
        model = result.scalar_one_or_none()

        if not model:
            return None

        # Check expiration
        if model.is_expired:
            # Clean up expired override
            await self.remove_override(user_id, flag_key)
            return None

        return FeatureOverride(
            user_id=model.user_id,
            flag_key=model.flag_key,
            enabled=model.enabled,
            reason=model.reason,
            expires_at=model.expires_at,
            created_at=model.created_at,
        )

    async def set_override(
        self,
        user_id: UUID,
        flag_key: str,
        enabled: bool,
        reason: str | None = None,
        expires_at: datetime | None = None,
    ) -> FeatureOverride:
        """Set override for a user (upsert)."""
        # Check if exists
        query = select(FeatureFlagOverride).where(
            FeatureFlagOverride.user_id == user_id,
            FeatureFlagOverride.flag_key == flag_key,
        )
        result = await self.db.execute(query)
        model = result.scalar_one_or_none()

        if model:
            # Update existing
            model.enabled = enabled
            model.reason = reason
            model.expires_at = expires_at
        else:
            # Create new
            model = FeatureFlagOverride(
                user_id=user_id,
                flag_key=flag_key,
                enabled=enabled,
                reason=reason,
                expires_at=expires_at,
            )
            self.db.add(model)

        await self.db.flush()

        return FeatureOverride(
            user_id=model.user_id,
            flag_key=model.flag_key,
            enabled=model.enabled,
            reason=model.reason,
            expires_at=model.expires_at,
            created_at=model.created_at,
        )

    async def remove_override(self, user_id: UUID, flag_key: str) -> bool:
        """Remove override for a user."""
        query = delete(FeatureFlagOverride).where(
            FeatureFlagOverride.user_id == user_id,
            FeatureFlagOverride.flag_key == flag_key,
        )
        result = await self.db.execute(query)
        await self.db.flush()

        return result.rowcount > 0

    # ============================================================
    # GROUP OPERATIONS
    # ============================================================

    async def get_user_groups(self, user_id: UUID) -> set[str]:
        """Get all groups a user belongs to."""
        query = select(UserFeatureGroup.group_name).where(
            UserFeatureGroup.user_id == user_id
        )
        result = await self.db.execute(query)
        groups = result.scalars().all()

        return set(groups)

    async def add_to_group(self, user_id: UUID, group: str) -> bool:
        """Add user to a feature group."""
        # Check if already in group
        query = select(UserFeatureGroup).where(
            UserFeatureGroup.user_id == user_id,
            UserFeatureGroup.group_name == group,
        )
        result = await self.db.execute(query)
        existing = result.scalar_one_or_none()

        if existing:
            return False  # Already in group

        membership = UserFeatureGroup(
            user_id=user_id,
            group_name=group,
        )
        self.db.add(membership)
        await self.db.flush()

        return True

    async def remove_from_group(self, user_id: UUID, group: str) -> bool:
        """Remove user from a feature group."""
        query = delete(UserFeatureGroup).where(
            UserFeatureGroup.user_id == user_id,
            UserFeatureGroup.group_name == group,
        )
        result = await self.db.execute(query)
        await self.db.flush()

        return result.rowcount > 0

    async def list_group_members(
        self,
        group: str,
        limit: int = 100,
        offset: int = 0,
    ) -> list[UUID]:
        """List users in a group."""
        query = (
            select(UserFeatureGroup.user_id)
            .where(UserFeatureGroup.group_name == group)
            .limit(limit)
            .offset(offset)
        )
        result = await self.db.execute(query)
        user_ids = result.scalars().all()

        return list(user_ids)

    # ============================================================
    # HELPERS
    # ============================================================

    def _model_to_flag(self, model: FeatureFlagModel) -> FeatureFlag:
        """Convert SQLAlchemy model to dataclass."""
        return FeatureFlag(
            key=model.key,
            name=model.name,
            description=model.description,
            enabled=model.enabled,
            percentage=model.percentage,
            conditions=model.conditions or {},
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
