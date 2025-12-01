"""
Simple policy engine - DEFAULT implementation.

Just checks is_admin flag. Perfect for MVPs and simple apps.
Zero configuration required.

Usage:
    # This is used automatically when no policy engine is configured
    # Or explicitly:
    AUTH_POLICY_ENGINE=simple
"""

from typing import Any
from ..interfaces import PolicyEngine, PolicyDecision
from ..registry import AuthRegistry


@AuthRegistry.policy_engine("simple")
class SimplePolicyEngine(PolicyEngine):
    """
    Minimal policy engine using is_admin flag.

    Authorization rules:
    - Admins can do anything
    - Non-admins can read and update their own resources
    - Specific permissions can be granted via user.permissions list

    Configuration:
        admin_field: Field name to check for admin status (default: "is_admin")
        owner_field: Field name on resources for ownership (default: "created_by_id")
        permissions_field: Field name for user permissions list (default: "permissions")

    To upgrade to RBAC: Change AUTH_POLICY_ENGINE=rbac
    """

    def __init__(
        self,
        admin_field: str = "is_admin",
        owner_field: str = "created_by_id",
        permissions_field: str = "permissions",
        **kwargs: Any,
    ):
        self.admin_field = admin_field
        self.owner_field = owner_field
        self.permissions_field = permissions_field

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
        2. Check if user has specific permission
        3. For resources: owner can read/update own resources
        4. Default: read is allowed, write requires permission
        """
        # Check admin status
        is_admin = getattr(actor, self.admin_field, False)
        if is_admin:
            return PolicyDecision.allow("Admin access")

        # Check explicit permissions on user
        user_permissions = getattr(actor, self.permissions_field, None) or []
        if action in user_permissions or "*" in user_permissions:
            return PolicyDecision.allow("Has permission")

        # Check permission with wildcards (e.g., "posts:*" matches "posts:create")
        if ":" in action:
            resource_type = action.split(":")[0]
            if f"{resource_type}:*" in user_permissions:
                return PolicyDecision.allow("Has wildcard permission")

        # For resources, check ownership
        if resource is not None:
            owner_id = getattr(resource, self.owner_field, None)
            actor_id = getattr(actor, "id", None)

            if owner_id is not None and actor_id is not None and owner_id == actor_id:
                # Owner can read and update own resources
                if action.endswith(":read") or action.endswith(":update") or action in ("read", "update"):
                    return PolicyDecision.allow("Resource owner")

        # Default: allow read operations, deny write
        if action.endswith(":read") or action == "read":
            return PolicyDecision.allow("Read allowed")

        return PolicyDecision.deny("Permission denied. Admin access or specific permission required.")

    async def get_permissions(
        self,
        actor: Any,
        resource: Any | None = None,
    ) -> set[str]:
        """Get permissions for an actor."""
        permissions: set[str] = set()

        # Admin has all permissions
        is_admin = getattr(actor, self.admin_field, False)
        if is_admin:
            return {"*"}

        # Get explicit permissions
        user_permissions = getattr(actor, self.permissions_field, None) or []
        permissions.update(user_permissions)

        # If resource owner, add read/update permissions
        if resource is not None:
            owner_id = getattr(resource, self.owner_field, None)
            actor_id = getattr(actor, "id", None)

            if owner_id is not None and actor_id is not None and owner_id == actor_id:
                resource_type = getattr(resource, "__tablename__", "resource")
                permissions.add(f"{resource_type}:read")
                permissions.add(f"{resource_type}:update")

        # Everyone can read by default
        permissions.add("read")

        return permissions
