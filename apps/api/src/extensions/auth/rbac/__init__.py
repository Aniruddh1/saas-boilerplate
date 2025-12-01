"""
RBAC (Role-Based Access Control) Extension.

This is an OPTIONAL extension that adds full role and permission support.
To use it:

1. Enable RBAC in config:
   AUTH_POLICY_ENGINE=rbac

2. Import this module in your app startup:
   from src.extensions.auth import rbac  # Registers the engine

3. Run migrations to create roles/permissions tables:
   alembic revision --autogenerate -m "add_rbac"
   alembic upgrade head

4. Create roles and assign permissions:
   await create_role("editor", permissions=["posts:create", "posts:update"])
   await assign_role(user_id, "editor")

Models:
- Role: Named role with permissions
- Permission: Resource + action combination
- UserRole: Links users to roles (with optional scope)
"""

from .models import Role, Permission, UserRole
from .engine import RBACPolicyEngine
from .service import RBACService

__all__ = [
    "Role",
    "Permission",
    "UserRole",
    "RBACPolicyEngine",
    "RBACService",
]
