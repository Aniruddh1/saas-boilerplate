"""
Built-in condition evaluators.

These are common conditions that can be used with any policy engine.
Add custom conditions by creating a class with @AuthRegistry.condition decorator.

Usage:
    await auth.require("approve", transaction, conditions={
        "max_amount": 10000,
        "not_creator": True,
    })
"""

from typing import Any
from ..interfaces import ConditionEvaluator
from ..registry import AuthRegistry


@AuthRegistry.condition("max_amount")
class MaxAmountCondition(ConditionEvaluator):
    """
    Check that a value doesn't exceed a maximum.

    Usage:
        conditions={"max_amount": 10000}

    Checks: context["amount"] <= 10000 OR actor.approval_limit >= context["amount"]

    Configuration:
        context_field: Field in context containing the amount (default: "amount")
        actor_limit_field: Field on actor containing their limit (default: "approval_limit")
    """

    condition_type = "max_amount"

    def __init__(
        self,
        context_field: str = "amount",
        actor_limit_field: str = "approval_limit",
        **kwargs: Any,
    ):
        self.context_field = context_field
        self.actor_limit_field = actor_limit_field

    async def evaluate(
        self,
        expected: Any,
        actor: Any,
        resource: Any | None,
        context: dict[str, Any],
    ) -> tuple[bool, str | None]:
        # Get the amount from context or resource
        amount = context.get(self.context_field)
        if amount is None and resource is not None:
            amount = getattr(resource, self.context_field, None)

        if amount is None:
            return True, None  # No amount to check

        # Check against expected value (static limit)
        if isinstance(expected, (int, float)) and amount > expected:
            return False, f"Amount {amount} exceeds limit {expected}"

        # Check against actor's limit if expected is True
        if expected is True:
            actor_limit = getattr(actor, self.actor_limit_field, None)
            if actor_limit is not None and amount > actor_limit:
                return False, f"Amount {amount} exceeds your approval limit {actor_limit}"

        return True, None


@AuthRegistry.condition("not_creator")
class NotCreatorCondition(ConditionEvaluator):
    """
    Check that actor is not the creator of the resource (segregation of duties).

    Usage:
        conditions={"not_creator": True}

    Configuration:
        creator_field: Field on resource containing creator ID (default: "created_by_id")
    """

    condition_type = "not_creator"

    def __init__(
        self,
        creator_field: str = "created_by_id",
        **kwargs: Any,
    ):
        self.creator_field = creator_field

    async def evaluate(
        self,
        expected: Any,
        actor: Any,
        resource: Any | None,
        context: dict[str, Any],
    ) -> tuple[bool, str | None]:
        if not expected:
            return True, None  # Condition disabled

        if resource is None:
            return True, None  # No resource to check

        creator_id = getattr(resource, self.creator_field, None)
        actor_id = getattr(actor, "id", None)

        if creator_id is not None and actor_id is not None and creator_id == actor_id:
            return False, "Cannot perform this action on your own resource (segregation of duties)"

        return True, None


@AuthRegistry.condition("status")
class StatusCondition(ConditionEvaluator):
    """
    Check that resource has a required status.

    Usage:
        conditions={"status": "pending"}
        conditions={"status": ["pending", "review"]}

    Configuration:
        status_field: Field on resource containing status (default: "status")
    """

    condition_type = "status"

    def __init__(
        self,
        status_field: str = "status",
        **kwargs: Any,
    ):
        self.status_field = status_field

    async def evaluate(
        self,
        expected: Any,
        actor: Any,
        resource: Any | None,
        context: dict[str, Any],
    ) -> tuple[bool, str | None]:
        if resource is None:
            return True, None

        current_status = getattr(resource, self.status_field, None)

        if isinstance(expected, (list, tuple, set)):
            if current_status not in expected:
                return False, f"Resource status must be one of {expected}, got {current_status}"
        else:
            if current_status != expected:
                return False, f"Resource status must be {expected}, got {current_status}"

        return True, None


@AuthRegistry.condition("same_tenant")
class SameTenantCondition(ConditionEvaluator):
    """
    Check that actor and resource belong to the same tenant.

    Usage:
        conditions={"same_tenant": True}

    Configuration:
        tenant_field: Field name for tenant ID (default: "organization_id")
    """

    condition_type = "same_tenant"

    def __init__(
        self,
        tenant_field: str = "organization_id",
        **kwargs: Any,
    ):
        self.tenant_field = tenant_field

    async def evaluate(
        self,
        expected: Any,
        actor: Any,
        resource: Any | None,
        context: dict[str, Any],
    ) -> tuple[bool, str | None]:
        if not expected:
            return True, None

        if resource is None:
            return True, None

        actor_tenant = getattr(actor, self.tenant_field, None)
        resource_tenant = getattr(resource, self.tenant_field, None)

        if actor_tenant is None or resource_tenant is None:
            return True, None  # Can't check, allow

        if actor_tenant != resource_tenant:
            return False, "Cannot access resources from another organization"

        return True, None
