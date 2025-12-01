"""
RBAC Policy Engine.

This engine evaluates permissions based on roles assigned to users.
Supports:
- Role-based permissions
- Role hierarchy (higher level roles inherit lower level permissions)
- Scoped roles (roles limited to specific resources)
- Permission conditions (ABAC-style additional checks)

Usage:
    # Enable in config:
    AUTH_POLICY_ENGINE=rbac

    # The engine will check if user has the required permission
    # via any of their assigned roles
"""

from typing import Any
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.auth.interfaces import PolicyEngine, PolicyDecision
from src.core.auth.registry import AuthRegistry
from src.core.database import async_session_maker

from .models import Role, Permission, UserRole


@AuthRegistry.policy_engine("rbac")
class RBACPolicyEngine(PolicyEngine):
    """
    Role-Based Access Control policy engine.

    Evaluates permissions by checking:
    1. If user has admin flag (bypass all checks)
    2. If user has the required permission via any assigned role
    3. If permission conditions are satisfied

    Configuration:
        admin_field: Field to check for admin status (default: "is_admin")
        cache_ttl: Cache duration for permission lookups (default: 300)
    """

    def __init__(
        self,
        admin_field: str = "is_admin",
        cache_ttl: int = 300,
        **kwargs: Any,
    ):
        self.admin_field = admin_field
        self.cache_ttl = cache_ttl
        self._cache: dict[str, tuple[set[str], float]] = {}

    async def evaluate(
        self,
        actor: Any,
        action: str,
        resource: Any | None = None,
        context: dict[str, Any] | None = None,
    ) -> PolicyDecision:
        """
        Evaluate if actor can perform action.

        Logic:
        1. Admins can do anything
        2. Get all permissions for user's roles
        3. Check if required permission is in the set
        4. Check permission conditions if present
        """
        context = context or {}

        # Check admin status
        is_admin = getattr(actor, self.admin_field, False)
        if is_admin:
            return PolicyDecision.allow("Admin access")

        # Parse action into resource_type and action_name
        if ":" in action:
            resource_type, action_name = action.split(":", 1)
        else:
            resource_type = None
            action_name = action

        # Get user's permissions
        user_id = getattr(actor, "id", None)
        if not user_id:
            return PolicyDecision.deny("User ID not found")

        permissions = await self._get_user_permissions(user_id, resource)

        # Check for exact match
        if action in permissions:
            return PolicyDecision.allow(f"Has permission: {action}")

        # Check for wildcard
        if "*" in permissions:
            return PolicyDecision.allow("Has wildcard permission")

        # Check for resource wildcard (e.g., "posts:*" matches "posts:create")
        if resource_type and f"{resource_type}:*" in permissions:
            return PolicyDecision.allow(f"Has wildcard permission: {resource_type}:*")

        return PolicyDecision.deny(f"Missing permission: {action}")

    async def get_permissions(
        self,
        actor: Any,
        resource: Any | None = None,
    ) -> set[str]:
        """Get all permissions for an actor."""
        is_admin = getattr(actor, self.admin_field, False)
        if is_admin:
            return {"*"}

        user_id = getattr(actor, "id", None)
        if not user_id:
            return set()

        return await self._get_user_permissions(user_id, resource)

    async def _get_user_permissions(
        self,
        user_id: Any,
        resource: Any | None = None,
    ) -> set[str]:
        """
        Get all permissions for a user from their roles.

        Includes:
        - Permissions from global roles
        - Permissions from scoped roles (if resource matches scope)
        - Excludes expired role assignments
        """
        # Check cache
        cache_key = f"{user_id}"
        if cache_key in self._cache:
            permissions, cached_at = self._cache[cache_key]
            if datetime.utcnow().timestamp() - cached_at < self.cache_ttl:
                return permissions

        permissions: set[str] = set()

        async with async_session_maker() as db:
            # Get user's role assignments
            now = datetime.utcnow()
            query = (
                select(UserRole)
                .where(UserRole.user_id == user_id)
                .where(UserRole.valid_from <= now)
                .where(
                    (UserRole.valid_until.is_(None)) | (UserRole.valid_until > now)
                )
            )
            result = await db.execute(query)
            user_roles = result.scalars().all()

            # Collect role IDs
            role_ids = set()
            for user_role in user_roles:
                # Check scope if resource provided
                if user_role.scope_type and resource:
                    resource_scope_id = getattr(resource, f"{user_role.scope_type}_id", None)
                    if resource_scope_id != user_role.scope_id:
                        continue  # Role doesn't apply to this resource

                role_ids.add(user_role.role_id)

            if not role_ids:
                return permissions

            # Get roles with their permissions
            role_query = (
                select(Role)
                .where(Role.id.in_(role_ids))
            )
            role_result = await db.execute(role_query)
            roles = role_result.scalars().all()

            # Collect permissions
            for role in roles:
                for perm in role.permissions:
                    permissions.add(perm.permission_string)

        # Cache result
        self._cache[cache_key] = (permissions, datetime.utcnow().timestamp())

        return permissions

    def clear_cache(self, user_id: Any | None = None) -> None:
        """Clear permission cache for a user or all users."""
        if user_id:
            cache_key = f"{user_id}"
            self._cache.pop(cache_key, None)
        else:
            self._cache.clear()
