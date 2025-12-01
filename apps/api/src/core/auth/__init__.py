"""
Authorization module - Progressive complexity authorization.

This module provides a flexible authorization system that scales from
simple is_admin checks to complex enterprise RBAC/ABAC.

Usage Levels:
=============

Level 1: Simple Admin Check (Zero Config)
-----------------------------------------
    from src.core.auth import CurrentUser, AdminUser

    @router.get("/admin")
    async def handler(user: AdminUser):  # 403 if not admin
        ...

Level 2: Permission Decorators
------------------------------
    from src.core.auth import require, CurrentUser

    @router.post("/posts")
    @require("posts:create")
    async def create_post(user: CurrentUser):
        ...

Level 3: Resource Authorization
-------------------------------
    from src.core.auth import Authorize

    @router.post("/transactions/{id}/approve")
    async def approve(id: UUID, auth: Authorize):
        tx = await get_transaction(id)
        await auth.require("approve", tx)
        ...

Level 4: Data Scoping
--------------------
    @router.get("/transactions")
    async def list_transactions(auth: Authorize):
        query = await auth.scoped(select(Transaction))
        ...

Level 5: Conditions
------------------
    await auth.require("approve", tx, conditions={
        "max_amount": True,      # Check user's approval limit
        "not_creator": True,     # Segregation of duties
        "status": "pending",     # Must be pending status
    })

Configuration:
==============

Environment variables (or in config):
- AUTH_POLICY_ENGINE: "simple" (default), "rbac", "casbin"
- AUTH_SCOPE_PROVIDER: "none" (default), "ownership", "hierarchical"
- AUTH_MULTI_TENANT: false (default), true
- AUTH_TENANT_FIELD: "organization_id" (default)

Extensibility:
=============

Add custom policy engines:
    @AuthRegistry.policy_engine("custom")
    class CustomPolicyEngine(PolicyEngine):
        ...

Add custom conditions:
    @AuthRegistry.condition("business_hours")
    class BusinessHoursCondition(ConditionEvaluator):
        ...
"""

# Core interfaces (for type hints and custom implementations)
from .interfaces import (
    PolicyEngine,
    ScopeProvider,
    ConditionEvaluator,
    PolicyDecision,
    DataScope,
    AuthorizationServiceBase,
)

# Registry (for extending with custom implementations)
from .registry import AuthRegistry

# Service (main facade)
from .service import AuthorizationService

# Dependencies (what you'll use in routes)
from .dependencies import (
    CurrentUser,
    OptionalUser,
    AdminUser,
    Authorize,
    get_current_user,
    get_current_user_optional,
    require_admin_user,
    get_authorization_service,
    get_policy_engine,
    get_scope_provider,
)

# Decorators (for simple permission checks)
from .decorators import (
    require,
    require_admin,
    scoped,
)

# Default implementations (auto-registered)
from .policy import SimplePolicyEngine
from .scope import NoScopeProvider, OwnershipScopeProvider

__all__ = [
    # Interfaces
    "PolicyEngine",
    "ScopeProvider",
    "ConditionEvaluator",
    "PolicyDecision",
    "DataScope",
    "AuthorizationServiceBase",
    # Registry
    "AuthRegistry",
    # Service
    "AuthorizationService",
    # Dependencies
    "CurrentUser",
    "OptionalUser",
    "AdminUser",
    "Authorize",
    "get_current_user",
    "get_current_user_optional",
    "require_admin_user",
    "get_authorization_service",
    "get_policy_engine",
    "get_scope_provider",
    # Decorators
    "require",
    "require_admin",
    "scoped",
    # Default implementations
    "SimplePolicyEngine",
    "NoScopeProvider",
    "OwnershipScopeProvider",
]
