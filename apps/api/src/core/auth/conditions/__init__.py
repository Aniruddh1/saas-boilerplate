"""
Condition evaluators for fine-grained authorization.

Built-in conditions:
- max_amount: Check amount limits
- not_creator: Segregation of duties
- status: Check resource status
- same_tenant: Tenant isolation

Add custom conditions with @AuthRegistry.condition decorator.
"""

from .builtin import (
    MaxAmountCondition,
    NotCreatorCondition,
    StatusCondition,
    SameTenantCondition,
)

__all__ = [
    "MaxAmountCondition",
    "NotCreatorCondition",
    "StatusCondition",
    "SameTenantCondition",
]
