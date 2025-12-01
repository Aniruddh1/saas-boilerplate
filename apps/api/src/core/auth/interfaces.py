"""
Authorization interfaces - Core abstractions.

These define the contracts that all authorization implementations must follow.
Application code depends ONLY on these interfaces, never on implementations.

Usage Levels:
- Level 1: Just use CurrentUser, AdminUser (no config needed)
- Level 2: Use @require("permission") decorator
- Level 3: Use auth.require("action", resource) for resource-based auth
- Level 4: Use auth.scoped(query) for data filtering
- Level 5: Full config with conditions, RLS, etc.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, TypeVar, Generic, Sequence
from enum import Enum


# ============================================================
# GENERIC TYPE VARIABLES
# No assumptions about ID types or structure
# ============================================================

ActorT = TypeVar("ActorT")  # User, ServiceAccount, APIKey, etc.
ResourceT = TypeVar("ResourceT")  # Any model/entity


# ============================================================
# POLICY DECISION
# ============================================================

@dataclass
class PolicyDecision:
    """
    Result of a policy evaluation.

    Attributes:
        allowed: Whether the action is permitted
        reason: Human-readable explanation (for errors/logging)
        metadata: Additional data (conditions applied, cache info, etc.)
    """
    allowed: bool
    reason: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def allow(cls, reason: str | None = None) -> "PolicyDecision":
        return cls(allowed=True, reason=reason)

    @classmethod
    def deny(cls, reason: str = "Permission denied") -> "PolicyDecision":
        return cls(allowed=False, reason=reason)


# ============================================================
# POLICY ENGINE
# ============================================================

class PolicyEngine(ABC):
    """
    Abstract policy engine interface.

    Evaluates whether an actor can perform an action on a resource.

    Implementations:
    - SimplePolicyEngine: is_admin flag only (default)
    - RBACPolicyEngine: Role-based with permissions
    - CasbinPolicyEngine: Casbin-backed policies
    - OPAPolicyEngine: Open Policy Agent
    """

    @abstractmethod
    async def evaluate(
        self,
        actor: Any,
        action: str,
        resource: Any | None = None,
        context: dict[str, Any] | None = None,
    ) -> PolicyDecision:
        """
        Evaluate if actor can perform action on resource.

        Args:
            actor: The user/service performing the action
            action: Action identifier (e.g., "approve", "posts:create")
            resource: Optional resource being acted upon
            context: Additional context (request info, conditions, etc.)

        Returns:
            PolicyDecision with allowed status and reason
        """
        pass

    @abstractmethod
    async def get_permissions(
        self,
        actor: Any,
        resource: Any | None = None,
    ) -> set[str]:
        """
        Get all permissions actor has (optionally for a specific resource).

        Returns:
            Set of permission strings the actor has
        """
        pass

    async def has_permission(
        self,
        actor: Any,
        permission: str,
        resource: Any | None = None,
    ) -> bool:
        """Check if actor has a specific permission."""
        permissions = await self.get_permissions(actor, resource)
        return permission in permissions or "*" in permissions


# ============================================================
# DATA SCOPE
# ============================================================

@dataclass
class DataScope:
    """
    Represents boundaries of what data an actor can access.

    The filters dict is implementation-agnostic:
    - SQL: Will be converted to WHERE clauses
    - NoSQL: Will be converted to query filters
    - GraphQL: Will be converted to resolver filters

    Examples:
        DataScope.global_access()  # No restrictions
        DataScope(level="tenant", filters={"organization_id": uuid})
        DataScope(level="ownership", filters={"created_by_id": user_id})
        DataScope(level="geographic", filters={"country_codes": ["US", "UK"]})
    """
    level: str  # "global", "tenant", "ownership", "hierarchical", custom...
    filters: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def global_access(cls) -> "DataScope":
        """No data restrictions."""
        return cls(level="global", filters={})

    @classmethod
    def tenant(cls, tenant_id: Any, field_name: str = "organization_id") -> "DataScope":
        """Restrict to single tenant."""
        return cls(level="tenant", filters={field_name: tenant_id})

    @classmethod
    def ownership(cls, owner_id: Any, field_name: str = "created_by_id") -> "DataScope":
        """Restrict to owned records."""
        return cls(level="ownership", filters={field_name: owner_id})


# ============================================================
# SCOPE PROVIDER
# ============================================================

class ScopeProvider(ABC):
    """
    Abstract scope provider interface.

    Determines what data an actor can access and applies
    appropriate filters to queries.

    Implementations:
    - NoScopeProvider: No restrictions (default)
    - TenantScopeProvider: Multi-tenant isolation
    - OwnershipScopeProvider: User sees own records
    - HierarchicalScopeProvider: Org hierarchy based
    - GeographicScopeProvider: Region/country based
    """

    @abstractmethod
    async def get_scope(
        self,
        actor: Any,
        resource_type: str | None = None,
        action: str | None = None,
    ) -> DataScope:
        """
        Get the data access scope for an actor.

        Args:
            actor: The user/service requesting access
            resource_type: Optional type of resource being accessed
            action: Optional action being performed (may affect scope)

        Returns:
            DataScope defining what data actor can access
        """
        pass

    @abstractmethod
    def apply_to_query(
        self,
        query: Any,
        scope: DataScope,
        model: type,
    ) -> Any:
        """
        Apply scope filters to a SQLAlchemy query.

        Args:
            query: SQLAlchemy Select statement
            scope: DataScope to apply
            model: SQLAlchemy model class (to get column references)

        Returns:
            Modified query with scope filters applied
        """
        pass


# ============================================================
# CONDITION EVALUATOR
# ============================================================

class ConditionEvaluator(ABC):
    """
    Evaluates a single type of condition.

    Register multiple evaluators for different condition types.
    This allows extending authorization with custom business rules.

    Examples:
        MaxAmountCondition - checks amount <= user's limit
        SegregationCondition - checks actor != creator
        TimeBasedCondition - checks within allowed hours
    """

    @property
    @abstractmethod
    def condition_type(self) -> str:
        """Unique identifier for this condition type."""
        pass

    @abstractmethod
    async def evaluate(
        self,
        expected: Any,
        actor: Any,
        resource: Any | None,
        context: dict[str, Any],
    ) -> tuple[bool, str | None]:
        """
        Evaluate the condition.

        Args:
            expected: The expected/configured value for this condition
            actor: The user/service performing the action
            resource: The resource being acted upon (if any)
            context: Additional context data

        Returns:
            Tuple of (passed: bool, reason: str | None)
        """
        pass


# ============================================================
# AUTHORIZATION SERVICE
# ============================================================

class AuthorizationServiceBase(ABC):
    """
    High-level authorization service interface.

    This is the main entry point for authorization checks.
    Combines policy engine, scope provider, and conditions.
    """

    @abstractmethod
    async def authorize(
        self,
        actor: Any,
        action: str,
        resource: Any | None = None,
        context: dict[str, Any] | None = None,
    ) -> PolicyDecision:
        """
        Check if actor can perform action on resource.

        Returns PolicyDecision (does not raise).
        """
        pass

    @abstractmethod
    async def authorize_or_raise(
        self,
        actor: Any,
        action: str,
        resource: Any | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        """
        Check authorization or raise HTTPException(403).
        """
        pass

    @abstractmethod
    async def scoped_query(
        self,
        actor: Any,
        query: Any,
        model: type,
        action: str | None = None,
    ) -> Any:
        """
        Apply actor's data scope to a query.
        """
        pass

    @abstractmethod
    async def filter_authorized(
        self,
        actor: Any,
        action: str,
        resources: Sequence[Any],
    ) -> list[Any]:
        """
        Filter a list of resources to only those the actor can access.
        """
        pass

    @abstractmethod
    async def get_permissions(
        self,
        actor: Any,
        resource: Any | None = None,
    ) -> set[str]:
        """
        Get all permissions actor has for a resource.
        """
        pass
