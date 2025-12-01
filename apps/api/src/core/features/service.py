"""
Feature Flag Service - Main evaluation logic.

Evaluates feature flags with support for:
- Percentage rollouts (consistent hashing)
- Attribute targeting (user.tier, user.country, etc.)
- Group membership (beta_testers, internal)
- Individual overrides (force on/off)
"""

import hashlib
from datetime import datetime
from typing import Any
from uuid import UUID

from .interfaces import (
    FeatureFlag,
    FeatureOverride,
    FeatureBackend,
    FeatureServiceBase,
    EvaluationResult,
)


class FeatureService(FeatureServiceBase):
    """
    Feature flag evaluation service.

    Evaluation order (first match wins):
    1. Individual override (highest priority)
    2. Global enabled check
    3. Percentage rollout
    4. Attribute conditions
    5. Group conditions
    """

    def __init__(
        self,
        backend: FeatureBackend,
        default_enabled: bool = False,
    ):
        self.backend = backend
        self.default_enabled = default_enabled

    # ============================================================
    # MAIN EVALUATION
    # ============================================================

    async def is_enabled(
        self,
        key: str,
        user: Any | None = None,
        default: bool | None = None,
    ) -> bool:
        """
        Check if a feature is enabled.

        Args:
            key: Feature flag key
            user: User object (optional, needed for targeting)
            default: Default if flag doesn't exist

        Returns:
            True if feature is enabled
        """
        result = await self.evaluate(key, user)
        if result.reason == "Flag not found":
            return default if default is not None else self.default_enabled
        return result.enabled

    async def evaluate(
        self,
        key: str,
        user: Any | None = None,
    ) -> EvaluationResult:
        """
        Evaluate a feature flag with detailed result.

        Returns EvaluationResult with reason for debugging.
        """
        user_id = getattr(user, "id", None) if user else None

        # 1. Check individual override first
        if user_id:
            override = await self.backend.get_override(user_id, key)
            if override:
                return EvaluationResult(
                    enabled=override.enabled,
                    reason=f"Override: {override.reason or 'User override'}",
                    flag_key=key,
                    user_id=user_id,
                )

        # 2. Get flag
        flag = await self.backend.get_flag(key)
        if not flag:
            return EvaluationResult.no(key, "Flag not found", user_id)

        # 3. Check global enabled
        if not flag.enabled:
            return EvaluationResult.no(key, "Flag disabled globally", user_id)

        # 4. Check percentage rollout
        if flag.percentage < 100:
            if not user_id:
                return EvaluationResult.no(key, "Percentage rollout requires user", user_id)

            if not self._in_percentage(user_id, key, flag.percentage):
                return EvaluationResult.no(
                    key,
                    f"Outside {flag.percentage}% rollout",
                    user_id,
                )

        # 5. Check conditions (if any)
        if flag.conditions:
            condition_result = await self._check_conditions(flag.conditions, user, user_id)
            if not condition_result[0]:
                return EvaluationResult.no(key, condition_result[1], user_id)

        # All checks passed
        return EvaluationResult.yes(key, "All conditions met", user_id)

    async def get_all_flags(self, user: Any | None = None) -> dict[str, bool]:
        """
        Get all flags and their status for a user.

        Useful for sending to frontend.
        """
        flags = await self.backend.list_flags()
        result = {}

        for flag in flags:
            result[flag.key] = await self.is_enabled(flag.key, user)

        return result

    # ============================================================
    # CONDITION CHECKING
    # ============================================================

    async def _check_conditions(
        self,
        conditions: dict[str, Any],
        user: Any | None,
        user_id: UUID | None,
    ) -> tuple[bool, str]:
        """
        Check if user matches flag conditions.

        Conditions use OR logic at the top level:
        - If user matches attributes OR groups, they're in.

        Returns (passed, reason)
        """
        if not conditions:
            return True, "No conditions"

        # Track what we checked
        checks_made = []
        any_passed = False

        # Check attribute conditions
        attributes = conditions.get("attributes", {})
        if attributes:
            if not user:
                checks_made.append("attributes (no user)")
            else:
                attr_result = self._check_attributes(attributes, user)
                if attr_result[0]:
                    any_passed = True
                checks_made.append(f"attributes: {attr_result[1]}")

        # Check group conditions
        groups = conditions.get("groups", [])
        if groups:
            if not user_id:
                checks_made.append("groups (no user)")
            else:
                user_groups = await self.backend.get_user_groups(user_id)
                required_groups = set(groups)
                matching = user_groups & required_groups

                if matching:
                    any_passed = True
                    checks_made.append(f"groups: in {matching}")
                else:
                    checks_made.append(f"groups: not in {required_groups}")

        # If no conditions to check, pass
        if not checks_made:
            return True, "No conditions to check"

        # OR logic - any passing condition is enough
        if any_passed:
            return True, " | ".join(checks_made)
        else:
            return False, " | ".join(checks_made)

    def _check_attributes(
        self,
        attributes: dict[str, Any],
        user: Any,
    ) -> tuple[bool, str]:
        """
        Check if user matches attribute conditions.

        All attribute conditions must match (AND logic within attributes).
        """
        if not attributes:
            return True, "No attributes"

        for attr_name, expected in attributes.items():
            actual = getattr(user, attr_name, None)

            # Handle list (any value matches)
            if isinstance(expected, list):
                if actual not in expected:
                    return False, f"{attr_name}={actual} not in {expected}"

            # Handle comparison operators
            elif isinstance(expected, dict):
                if "gte" in expected and actual < expected["gte"]:
                    return False, f"{attr_name}={actual} < {expected['gte']}"
                if "lte" in expected and actual > expected["lte"]:
                    return False, f"{attr_name}={actual} > {expected['lte']}"
                if "gt" in expected and actual <= expected["gt"]:
                    return False, f"{attr_name}={actual} <= {expected['gt']}"
                if "lt" in expected and actual >= expected["lt"]:
                    return False, f"{attr_name}={actual} >= {expected['lt']}"

            # Direct equality
            else:
                if actual != expected:
                    return False, f"{attr_name}={actual} != {expected}"

        return True, "All attributes match"

    # ============================================================
    # PERCENTAGE ROLLOUT
    # ============================================================

    def _in_percentage(self, user_id: UUID, flag_key: str, percentage: int) -> bool:
        """
        Determine if user is in percentage rollout.

        Uses consistent hashing so user always gets same result for same flag.
        """
        hash_input = f"{user_id}:{flag_key}"
        hash_value = int(hashlib.md5(hash_input.encode()).hexdigest(), 16)
        bucket = hash_value % 100

        return bucket < percentage

    # ============================================================
    # MANAGEMENT METHODS (passthrough to backend)
    # ============================================================

    async def create_flag(
        self,
        key: str,
        name: str,
        description: str | None = None,
        enabled: bool = False,
        percentage: int = 100,
        conditions: dict | None = None,
    ) -> FeatureFlag:
        """Create a new feature flag."""
        flag = FeatureFlag(
            key=key,
            name=name,
            description=description,
            enabled=enabled,
            percentage=percentage,
            conditions=conditions or {},
        )
        return await self.backend.create_flag(flag)

    async def update_flag(self, key: str, **updates) -> FeatureFlag | None:
        """Update a feature flag."""
        return await self.backend.update_flag(key, updates)

    async def delete_flag(self, key: str) -> bool:
        """Delete a feature flag."""
        return await self.backend.delete_flag(key)

    async def get_flag(self, key: str) -> FeatureFlag | None:
        """Get a feature flag."""
        return await self.backend.get_flag(key)

    async def list_flags(self) -> list[FeatureFlag]:
        """List all feature flags."""
        return await self.backend.list_flags()

    async def set_override(
        self,
        user_id: UUID,
        flag_key: str,
        enabled: bool,
        reason: str | None = None,
        expires_at: datetime | None = None,
    ) -> FeatureOverride:
        """Set override for a user."""
        return await self.backend.set_override(
            user_id, flag_key, enabled, reason, expires_at
        )

    async def remove_override(self, user_id: UUID, flag_key: str) -> bool:
        """Remove override for a user."""
        return await self.backend.remove_override(user_id, flag_key)

    async def add_to_group(self, user_id: UUID, group: str) -> bool:
        """Add user to a feature group."""
        return await self.backend.add_to_group(user_id, group)

    async def remove_from_group(self, user_id: UUID, group: str) -> bool:
        """Remove user from a feature group."""
        return await self.backend.remove_from_group(user_id, group)

    async def get_user_groups(self, user_id: UUID) -> set[str]:
        """Get all groups a user belongs to."""
        return await self.backend.get_user_groups(user_id)
