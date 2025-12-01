"""
Feature Flag Interfaces - Core abstractions.

These define the contracts for feature flag implementations.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID


@dataclass
class FeatureFlag:
    """
    Feature flag definition.

    Attributes:
        key: Unique identifier (e.g., "new_dashboard")
        name: Human-readable name
        description: What this flag controls
        enabled: Global on/off switch
        percentage: Rollout percentage (0-100)
        conditions: Targeting rules (attributes, groups)
    """
    key: str
    name: str
    description: str | None = None
    enabled: bool = False
    percentage: int = 100
    conditions: dict[str, Any] = field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def is_globally_enabled(self) -> bool:
        """Check if flag is enabled globally (no user context)."""
        return self.enabled and self.percentage == 100 and not self.conditions


@dataclass
class FeatureOverride:
    """
    Individual user override for a feature flag.

    Overrides take highest priority - if set, ignores all other rules.
    """
    user_id: UUID
    flag_key: str
    enabled: bool
    reason: str | None = None
    expires_at: datetime | None = None
    created_at: datetime | None = None

    @property
    def is_expired(self) -> bool:
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at


@dataclass
class EvaluationResult:
    """
    Result of feature flag evaluation.

    Includes the decision and reason for debugging/logging.
    """
    enabled: bool
    reason: str
    flag_key: str
    user_id: UUID | None = None

    @classmethod
    def yes(cls, flag_key: str, reason: str, user_id: UUID | None = None) -> "EvaluationResult":
        return cls(enabled=True, reason=reason, flag_key=flag_key, user_id=user_id)

    @classmethod
    def no(cls, flag_key: str, reason: str, user_id: UUID | None = None) -> "EvaluationResult":
        return cls(enabled=False, reason=reason, flag_key=flag_key, user_id=user_id)


class FeatureBackend(ABC):
    """
    Abstract backend for feature flag storage.

    Implementations:
    - MemoryBackend: In-memory (dev/testing)
    - DatabaseBackend: PostgreSQL
    - RedisBackend: Redis for caching
    """

    @abstractmethod
    async def get_flag(self, key: str) -> FeatureFlag | None:
        """Get a feature flag by key."""
        pass

    @abstractmethod
    async def list_flags(self) -> list[FeatureFlag]:
        """List all feature flags."""
        pass

    @abstractmethod
    async def create_flag(self, flag: FeatureFlag) -> FeatureFlag:
        """Create a new feature flag."""
        pass

    @abstractmethod
    async def update_flag(self, key: str, updates: dict[str, Any]) -> FeatureFlag | None:
        """Update a feature flag."""
        pass

    @abstractmethod
    async def delete_flag(self, key: str) -> bool:
        """Delete a feature flag."""
        pass

    @abstractmethod
    async def get_override(self, user_id: UUID, flag_key: str) -> FeatureOverride | None:
        """Get override for a specific user and flag."""
        pass

    @abstractmethod
    async def set_override(
        self,
        user_id: UUID,
        flag_key: str,
        enabled: bool,
        reason: str | None = None,
        expires_at: datetime | None = None,
    ) -> FeatureOverride:
        """Set override for a user."""
        pass

    @abstractmethod
    async def remove_override(self, user_id: UUID, flag_key: str) -> bool:
        """Remove override for a user."""
        pass

    @abstractmethod
    async def get_user_groups(self, user_id: UUID) -> set[str]:
        """Get all groups a user belongs to."""
        pass

    @abstractmethod
    async def add_to_group(self, user_id: UUID, group: str) -> bool:
        """Add user to a feature group."""
        pass

    @abstractmethod
    async def remove_from_group(self, user_id: UUID, group: str) -> bool:
        """Remove user from a feature group."""
        pass

    @abstractmethod
    async def list_group_members(self, group: str, limit: int = 100, offset: int = 0) -> list[UUID]:
        """List users in a group."""
        pass


class FeatureServiceBase(ABC):
    """
    Abstract feature flag service.

    This is the main entry point for feature flag checks.
    """

    @abstractmethod
    async def is_enabled(
        self,
        key: str,
        user: Any | None = None,
        default: bool = False,
    ) -> bool:
        """
        Check if a feature is enabled.

        Args:
            key: Feature flag key
            user: User object (optional)
            default: Default value if flag doesn't exist

        Returns:
            True if feature is enabled for this context
        """
        pass

    @abstractmethod
    async def evaluate(
        self,
        key: str,
        user: Any | None = None,
    ) -> EvaluationResult:
        """
        Evaluate a feature flag with detailed result.

        Returns EvaluationResult with reason for debugging.
        """
        pass

    @abstractmethod
    async def get_all_flags(self, user: Any | None = None) -> dict[str, bool]:
        """
        Get all flags and their status for a user.

        Useful for sending to frontend.
        """
        pass
