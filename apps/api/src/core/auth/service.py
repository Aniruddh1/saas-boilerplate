"""
Authorization service - Main facade for authorization.

This is the primary entry point for authorization checks.
Combines policy engine, scope provider, and conditions.

Usage:
    # In route handlers:
    async def handler(auth: Authorize):
        await auth.require("action", resource)
        query = await auth.scoped(select(Model))
"""

from typing import Any, Sequence
from fastapi import HTTPException, status

from .interfaces import (
    AuthorizationServiceBase,
    PolicyEngine,
    ScopeProvider,
    PolicyDecision,
    DataScope,
)
from .registry import AuthRegistry


class AuthorizationService(AuthorizationServiceBase):
    """
    Default authorization service implementation.

    Combines:
    - Policy engine: Determines if action is allowed
    - Scope provider: Determines what data can be accessed
    - Condition evaluators: Fine-grained checks

    Usage:
        auth = AuthorizationService(actor=current_user)
        await auth.require("approve", transaction)
        query = await auth.scoped(select(Transaction))
    """

    def __init__(
        self,
        actor: Any,
        policy_engine: PolicyEngine,
        scope_provider: ScopeProvider,
    ):
        self.actor = actor
        self.policy_engine = policy_engine
        self.scope_provider = scope_provider

    async def authorize(
        self,
        actor: Any | None,
        action: str,
        resource: Any | None = None,
        context: dict[str, Any] | None = None,
    ) -> PolicyDecision:
        """
        Check if actor can perform action on resource.

        Args:
            actor: The user (uses self.actor if None)
            action: Action identifier
            resource: Optional resource
            context: Additional context including conditions

        Returns:
            PolicyDecision (does not raise)
        """
        actor = actor or self.actor
        context = context or {}

        # Evaluate policy
        decision = await self.policy_engine.evaluate(actor, action, resource, context)

        if not decision.allowed:
            return decision

        # Evaluate conditions if provided
        conditions = context.get("conditions", {})
        for condition_type, expected in conditions.items():
            if not AuthRegistry.has_condition(condition_type):
                continue

            evaluator = AuthRegistry.get_condition_evaluator(condition_type)
            passed, reason = await evaluator.evaluate(expected, actor, resource, context)

            if not passed:
                return PolicyDecision.deny(reason or f"Condition '{condition_type}' not met")

        return decision

    async def authorize_or_raise(
        self,
        actor: Any | None,
        action: str,
        resource: Any | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        """
        Check authorization or raise HTTPException(403).

        Args:
            actor: The user (uses self.actor if None)
            action: Action identifier
            resource: Optional resource
            context: Additional context

        Raises:
            HTTPException: 403 if not authorized
        """
        decision = await self.authorize(actor, action, resource, context)

        if not decision.allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=decision.reason or "Permission denied",
            )

    async def require(
        self,
        action: str,
        resource: Any | None = None,
        conditions: dict[str, Any] | None = None,
        **context_kwargs: Any,
    ) -> None:
        """
        Convenience method: require authorization or raise.

        Usage:
            await auth.require("approve", transaction)
            await auth.require("approve", transaction, conditions={"max_amount": True})
        """
        context = context_kwargs
        if conditions:
            context["conditions"] = conditions

        await self.authorize_or_raise(self.actor, action, resource, context)

    async def can(
        self,
        action: str,
        resource: Any | None = None,
        conditions: dict[str, Any] | None = None,
        **context_kwargs: Any,
    ) -> bool:
        """
        Check if action is allowed (returns bool, no exception).

        Usage:
            if await auth.can("delete", resource):
                # show delete button
        """
        context = context_kwargs
        if conditions:
            context["conditions"] = conditions

        decision = await self.authorize(self.actor, action, resource, context)
        return decision.allowed

    async def scoped_query(
        self,
        actor: Any | None,
        query: Any,
        model: type,
        action: str | None = None,
    ) -> Any:
        """
        Apply actor's data scope to a query.

        Args:
            actor: The user (uses self.actor if None)
            query: SQLAlchemy Select statement
            model: Model class for column references
            action: Optional action (may affect scope)

        Returns:
            Query with scope filters applied
        """
        actor = actor or self.actor
        resource_type = getattr(model, "__tablename__", None)

        scope = await self.scope_provider.get_scope(actor, resource_type, action)
        return self.scope_provider.apply_to_query(query, scope, model)

    async def scoped(
        self,
        query: Any,
        model: type | None = None,
        action: str | None = None,
    ) -> Any:
        """
        Convenience method: apply scope to query.

        Usage:
            query = await auth.scoped(select(Transaction))

        If model is not provided, attempts to extract from query.
        """
        if model is None:
            # Try to extract model from query
            try:
                model = query.column_descriptions[0]["entity"]
            except (AttributeError, IndexError, KeyError):
                raise ValueError("Could not determine model from query. Please provide model parameter.")

        return await self.scoped_query(self.actor, query, model, action)

    async def filter_authorized(
        self,
        actor: Any | None,
        action: str,
        resources: Sequence[Any],
    ) -> list[Any]:
        """
        Filter a list of resources to only those the actor can access.

        Args:
            actor: The user
            action: Action to check
            resources: List of resources to filter

        Returns:
            List of authorized resources
        """
        actor = actor or self.actor
        authorized = []

        for resource in resources:
            decision = await self.authorize(actor, action, resource)
            if decision.allowed:
                authorized.append(resource)

        return authorized

    async def get_permissions(
        self,
        actor: Any | None,
        resource: Any | None = None,
    ) -> set[str]:
        """
        Get all permissions actor has for a resource.

        Args:
            actor: The user
            resource: Optional resource

        Returns:
            Set of permission strings
        """
        actor = actor or self.actor
        return await self.policy_engine.get_permissions(actor, resource)

    async def get_scope(self, action: str | None = None) -> DataScope:
        """Get actor's data scope."""
        return await self.scope_provider.get_scope(self.actor, action=action)
