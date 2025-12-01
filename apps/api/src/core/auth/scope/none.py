"""
No-scope provider - DEFAULT implementation.

No data filtering applied (except tenant if multi-tenant enabled).
User sees all data they have permission to access.

Usage:
    # This is used automatically when no scope provider is configured
    # Or explicitly:
    AUTH_SCOPE_PROVIDER=none
"""

from typing import Any
from sqlalchemy import Select
from ..interfaces import ScopeProvider, DataScope
from ..registry import AuthRegistry


@AuthRegistry.scope_provider("none")
class NoScopeProvider(ScopeProvider):
    """
    Default scope provider - no data restrictions.

    If multi_tenant is True, automatically filters by tenant field.
    Otherwise, user sees all data.

    Configuration:
        multi_tenant: Enable tenant isolation (default: False)
        tenant_field: Field name for tenant ID (default: "organization_id")
        tenant_actor_field: Field on actor containing tenant ID (default: "organization_id")

    To upgrade: Change AUTH_SCOPE_PROVIDER to "ownership" or "hierarchical"
    """

    def __init__(
        self,
        multi_tenant: bool = False,
        tenant_field: str = "organization_id",
        tenant_actor_field: str = "organization_id",
        **kwargs: Any,
    ):
        self.multi_tenant = multi_tenant
        self.tenant_field = tenant_field
        self.tenant_actor_field = tenant_actor_field

    async def get_scope(
        self,
        actor: Any,
        resource_type: str | None = None,
        action: str | None = None,
    ) -> DataScope:
        """
        Get data scope for actor.

        Returns global access or tenant-scoped based on config.
        """
        if self.multi_tenant:
            tenant_id = getattr(actor, self.tenant_actor_field, None)
            if tenant_id:
                return DataScope.tenant(tenant_id, field_name=self.tenant_field)

        return DataScope.global_access()

    def apply_to_query(
        self,
        query: Select,
        scope: DataScope,
        model: type,
    ) -> Select:
        """
        Apply scope to SQLAlchemy query.

        For global scope: returns query unchanged.
        For tenant scope: adds WHERE clause for tenant field.
        """
        if scope.level == "global":
            return query

        if scope.level == "tenant":
            tenant_field_name = self.tenant_field
            tenant_id = scope.filters.get(tenant_field_name)

            if tenant_id and hasattr(model, tenant_field_name):
                column = getattr(model, tenant_field_name)
                return query.where(column == tenant_id)

        # For other scope levels, apply filters generically
        for field_name, value in scope.filters.items():
            if hasattr(model, field_name):
                column = getattr(model, field_name)
                if isinstance(value, (list, tuple, set)):
                    query = query.where(column.in_(value))
                else:
                    query = query.where(column == value)

        return query


@AuthRegistry.scope_provider("ownership")
class OwnershipScopeProvider(ScopeProvider):
    """
    Ownership-based scope provider.

    Users can only see records they created.
    Admins see all records.

    Configuration:
        owner_field: Field name for owner ID (default: "created_by_id")
        admin_field: Field on actor to check admin status (default: "is_admin")
        multi_tenant: Enable tenant isolation (default: False)
        tenant_field: Field name for tenant ID (default: "organization_id")
    """

    def __init__(
        self,
        owner_field: str = "created_by_id",
        admin_field: str = "is_admin",
        multi_tenant: bool = False,
        tenant_field: str = "organization_id",
        **kwargs: Any,
    ):
        self.owner_field = owner_field
        self.admin_field = admin_field
        self.multi_tenant = multi_tenant
        self.tenant_field = tenant_field

    async def get_scope(
        self,
        actor: Any,
        resource_type: str | None = None,
        action: str | None = None,
    ) -> DataScope:
        """Get ownership-based scope."""
        # Admins see all
        is_admin = getattr(actor, self.admin_field, False)
        if is_admin:
            if self.multi_tenant:
                tenant_id = getattr(actor, self.tenant_field, None)
                if tenant_id:
                    return DataScope.tenant(tenant_id, field_name=self.tenant_field)
            return DataScope.global_access()

        # Non-admins see only their records
        actor_id = getattr(actor, "id", None)
        filters = {self.owner_field: actor_id}

        # Add tenant filter if multi-tenant
        if self.multi_tenant:
            tenant_id = getattr(actor, self.tenant_field, None)
            if tenant_id:
                filters[self.tenant_field] = tenant_id

        return DataScope(level="ownership", filters=filters)

    def apply_to_query(
        self,
        query: Select,
        scope: DataScope,
        model: type,
    ) -> Select:
        """Apply ownership scope to query."""
        if scope.level == "global":
            return query

        for field_name, value in scope.filters.items():
            if hasattr(model, field_name):
                column = getattr(model, field_name)
                if isinstance(value, (list, tuple, set)):
                    query = query.where(column.in_(value))
                else:
                    query = query.where(column == value)

        return query
