"""
In-memory backend for feature flags.

For development and testing. Data is lost on restart.
"""

from datetime import datetime
from typing import Any
from uuid import UUID
from collections import defaultdict

from ..interfaces import FeatureFlag, FeatureOverride, FeatureBackend


class MemoryFeatureBackend(FeatureBackend):
    """
    In-memory feature flag storage.

    Useful for:
    - Development without database
    - Unit testing
    - Quick prototyping
    """

    def __init__(self):
        self._flags: dict[str, FeatureFlag] = {}
        self._overrides: dict[tuple[UUID, str], FeatureOverride] = {}
        self._groups: dict[UUID, set[str]] = defaultdict(set)

    # ============================================================
    # FLAG OPERATIONS
    # ============================================================

    async def get_flag(self, key: str) -> FeatureFlag | None:
        """Get a feature flag by key."""
        return self._flags.get(key)

    async def list_flags(self) -> list[FeatureFlag]:
        """List all feature flags."""
        return list(self._flags.values())

    async def create_flag(self, flag: FeatureFlag) -> FeatureFlag:
        """Create a new feature flag."""
        now = datetime.utcnow()
        flag.created_at = now
        flag.updated_at = now
        self._flags[flag.key] = flag
        return flag

    async def update_flag(self, key: str, updates: dict[str, Any]) -> FeatureFlag | None:
        """Update a feature flag."""
        flag = self._flags.get(key)
        if not flag:
            return None

        for field, value in updates.items():
            if hasattr(flag, field):
                setattr(flag, field, value)

        flag.updated_at = datetime.utcnow()
        return flag

    async def delete_flag(self, key: str) -> bool:
        """Delete a feature flag."""
        if key in self._flags:
            del self._flags[key]
            return True
        return False

    # ============================================================
    # OVERRIDE OPERATIONS
    # ============================================================

    async def get_override(self, user_id: UUID, flag_key: str) -> FeatureOverride | None:
        """Get override for a specific user and flag."""
        override = self._overrides.get((user_id, flag_key))
        if override and override.is_expired:
            del self._overrides[(user_id, flag_key)]
            return None
        return override

    async def set_override(
        self,
        user_id: UUID,
        flag_key: str,
        enabled: bool,
        reason: str | None = None,
        expires_at: datetime | None = None,
    ) -> FeatureOverride:
        """Set override for a user."""
        override = FeatureOverride(
            user_id=user_id,
            flag_key=flag_key,
            enabled=enabled,
            reason=reason,
            expires_at=expires_at,
            created_at=datetime.utcnow(),
        )
        self._overrides[(user_id, flag_key)] = override
        return override

    async def remove_override(self, user_id: UUID, flag_key: str) -> bool:
        """Remove override for a user."""
        key = (user_id, flag_key)
        if key in self._overrides:
            del self._overrides[key]
            return True
        return False

    # ============================================================
    # GROUP OPERATIONS
    # ============================================================

    async def get_user_groups(self, user_id: UUID) -> set[str]:
        """Get all groups a user belongs to."""
        return self._groups.get(user_id, set())

    async def add_to_group(self, user_id: UUID, group: str) -> bool:
        """Add user to a feature group."""
        if group in self._groups[user_id]:
            return False
        self._groups[user_id].add(group)
        return True

    async def remove_from_group(self, user_id: UUID, group: str) -> bool:
        """Remove user from a feature group."""
        if group not in self._groups[user_id]:
            return False
        self._groups[user_id].discard(group)
        return True

    async def list_group_members(
        self,
        group: str,
        limit: int = 100,
        offset: int = 0,
    ) -> list[UUID]:
        """List users in a group."""
        members = [
            user_id
            for user_id, groups in self._groups.items()
            if group in groups
        ]
        return members[offset:offset + limit]

    # ============================================================
    # TEST HELPERS
    # ============================================================

    def clear(self) -> None:
        """Clear all data. Useful for testing."""
        self._flags.clear()
        self._overrides.clear()
        self._groups.clear()

    def seed(self, flags: list[FeatureFlag]) -> None:
        """Seed with initial flags. Useful for testing."""
        for flag in flags:
            self._flags[flag.key] = flag
