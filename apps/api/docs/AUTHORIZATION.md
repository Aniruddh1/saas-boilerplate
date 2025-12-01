# Authorization System

A progressive-complexity authorization system that scales from simple admin checks to full enterprise RBAC/ABAC.

## Overview

The authorization system is designed with **5 levels of complexity**. Start simple and add complexity only when needed:

| Level | Complexity | Use Case | What You Get |
|-------|------------|----------|--------------|
| 1 | Simple | MVP/Prototype | `CurrentUser`, `AdminUser` dependencies |
| 2 | Basic | Small apps | `@require("permission")` decorator |
| 3 | Standard | Growing apps | `auth.require()`, `auth.can()` methods |
| 4 | Advanced | Enterprise | Conditions (ABAC-style rules) |
| 5 | Full | Complex multi-tenant | RBAC extension, data scoping, RLS |

## Quick Start

### Level 1: Basic User Authentication

```python
from src.core.auth import CurrentUser, AdminUser, OptionalUser

@router.get("/profile")
async def get_profile(user: CurrentUser):
    """Requires any authenticated user."""
    return {"email": user.email}

@router.get("/admin/dashboard")
async def admin_dashboard(user: AdminUser):
    """Requires admin user (is_admin=True)."""
    return {"message": "Welcome, admin!"}

@router.get("/public")
async def public_endpoint(user: OptionalUser):
    """Works with or without authentication."""
    if user:
        return {"authenticated": True, "email": user.email}
    return {"authenticated": False}
```

### Level 2: Permission Decorators

```python
from src.core.auth import CurrentUser, require, require_admin

@router.get("/posts")
@require("posts:read")
async def list_posts(user: CurrentUser):
    """Requires 'posts:read' permission."""
    return {"posts": []}

@router.post("/posts")
@require("posts:create", "posts:publish")  # AND logic - needs BOTH
async def create_post(user: CurrentUser):
    """Requires both permissions."""
    return {"created": True}

@router.delete("/posts/{id}")
@require(any_of=["posts:delete", "admin"])  # OR logic - needs ANY
async def delete_post(user: CurrentUser, id: str):
    """Requires either permission."""
    return {"deleted": True}

@router.get("/admin/settings")
@require_admin
async def admin_settings(user: CurrentUser):
    """Requires admin via decorator."""
    return {"settings": {}}
```

### Level 3: Authorization Service

```python
from src.core.auth import Authorize

@router.post("/transactions/{id}/approve")
async def approve_transaction(id: str, auth: Authorize):
    """Fine-grained authorization with context."""
    transaction = await get_transaction(id)

    # Check permission (returns bool)
    if await auth.can("transactions:approve"):
        # User can approve
        pass

    # Or require permission (raises 403 if denied)
    await auth.require("transactions:approve", transaction)

    return {"approved": True}

@router.get("/transactions")
async def list_transactions(auth: Authorize, db: AsyncSession = Depends(get_db)):
    """Apply data scoping to queries."""
    query = select(Transaction)

    # Apply user's data scope (ownership, tenant, etc.)
    scoped_query = await auth.scoped(query, Transaction)

    result = await db.execute(scoped_query)
    return result.scalars().all()
```

### Level 4: Conditions (ABAC)

```python
@router.post("/transactions/{id}/approve")
async def approve_transaction(id: str, auth: Authorize):
    """Authorization with business rule conditions."""
    transaction = await get_transaction(id)

    # Check with conditions
    await auth.require(
        "transactions:approve",
        transaction,
        conditions={
            "max_amount": 10000,      # Amount must be <= 10000
            "not_creator": True,       # User can't approve own transaction
            "status": "pending",       # Transaction must be pending
        }
    )

    return {"approved": True}
```

### Level 5: Full RBAC Extension

Enable RBAC by setting environment variable:

```env
AUTH_POLICY_ENGINE=rbac
```

Then create and assign roles:

```python
from src.extensions.auth.rbac import RBACService

async def setup_roles(db: AsyncSession):
    rbac = RBACService(db)

    # Create roles with permissions
    viewer = await rbac.create_role(
        name="viewer",
        permissions=["posts:read", "comments:read"],
        level=10,
    )

    editor = await rbac.create_role(
        name="editor",
        permissions=["posts:read", "posts:create", "posts:update"],
        level=50,
    )

    admin = await rbac.create_role(
        name="admin",
        permissions=["*"],  # Wildcard = all permissions
        level=100,
    )

    # Assign role to user
    await rbac.assign_role(user_id, editor.id)

    # Assign scoped role (only for specific entity)
    await rbac.assign_role(
        user_id,
        editor.id,
        scope_type="entity",
        scope_id=entity_id,
    )

    # Temporary role (expires)
    await rbac.assign_role(
        user_id,
        approver.id,
        valid_until=datetime(2024, 12, 31),
    )

    await db.commit()
```

## Architecture

```
src/core/auth/
├── __init__.py          # Public exports
├── interfaces.py        # Abstract contracts (PolicyEngine, ScopeProvider, etc.)
├── registry.py          # Plugin registry for engines/providers
├── service.py           # AuthorizationService facade
├── dependencies.py      # FastAPI dependencies (CurrentUser, Authorize, etc.)
├── decorators.py        # @require, @require_admin decorators
├── policy/
│   └── simple.py        # SimplePolicyEngine (default)
├── scope/
│   └── none.py          # NoScopeProvider, OwnershipScopeProvider
└── conditions/
    └── builtin.py       # MaxAmount, NotCreator, Status conditions

src/extensions/auth/
└── rbac/
    ├── __init__.py
    ├── models.py        # Role, Permission, UserRole SQLAlchemy models
    ├── engine.py        # RBACPolicyEngine
    └── service.py       # RBACService for role management
```

## Configuration

Environment variables in `.env`:

```env
# Policy engine: "simple" (default) or "rbac"
AUTH_POLICY_ENGINE=simple

# Scope provider: "none" (default), "ownership", "tenant"
AUTH_SCOPE_PROVIDER=none

# Multi-tenant settings
AUTH_MULTI_TENANT=false
AUTH_TENANT_FIELD=organization_id
```

## Plugin System

The authorization system is fully pluggable. Register custom engines and providers:

### Custom Policy Engine

```python
from src.core.auth.registry import AuthRegistry
from src.core.auth.interfaces import PolicyEngine, PolicyDecision

@AuthRegistry.policy_engine("custom")
class CustomPolicyEngine(PolicyEngine):
    async def evaluate(self, actor, action, resource=None, context=None):
        # Your custom logic
        if your_custom_check(actor, action):
            return PolicyDecision.allow("Custom rule passed")
        return PolicyDecision.deny("Custom rule failed")

    async def get_permissions(self, actor, resource=None):
        return {"permission1", "permission2"}
```

### Custom Scope Provider

```python
from src.core.auth.registry import AuthRegistry
from src.core.auth.interfaces import ScopeProvider, DataScope

@AuthRegistry.scope_provider("geographic")
class GeographicScopeProvider(ScopeProvider):
    async def get_scope(self, actor, resource_type=None, action=None):
        # Get user's allowed countries
        countries = getattr(actor, "allowed_countries", [])
        return DataScope(
            level="geographic",
            filters={"country_code": countries}
        )

    def apply_to_query(self, query, scope, model):
        if "country_code" in scope.filters:
            query = query.where(
                model.country_code.in_(scope.filters["country_code"])
            )
        return query
```

### Custom Condition Evaluator

```python
from src.core.auth.registry import AuthRegistry
from src.core.auth.interfaces import ConditionEvaluator

@AuthRegistry.condition("business_hours")
class BusinessHoursCondition(ConditionEvaluator):
    @property
    def condition_type(self) -> str:
        return "business_hours"

    async def evaluate(self, expected, actor, resource, context):
        from datetime import datetime
        hour = datetime.now().hour
        if 9 <= hour <= 17:
            return True, None
        return False, "Action only allowed during business hours (9-17)"
```

## Built-in Condition Evaluators

| Condition | Description | Example |
|-----------|-------------|---------|
| `max_amount` | Resource amount must be <= value | `{"max_amount": 10000}` |
| `not_creator` | Actor must not be resource creator | `{"not_creator": True}` |
| `status` | Resource must have specific status | `{"status": "pending"}` |
| `same_tenant` | Actor and resource in same tenant | `{"same_tenant": True}` |

## Permission Format

Permissions follow the `resource:action` format:

```
posts:read        # Read posts
posts:create      # Create posts
posts:*           # All post actions (wildcard)
*                 # All permissions (super admin)
```

## Database Tables (RBAC Extension)

When using RBAC, create these tables:

```sql
-- Roles table
CREATE TABLE roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) UNIQUE NOT NULL,
    description VARCHAR(500),
    level INTEGER DEFAULT 0,
    organization_id UUID REFERENCES users(organization_id),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Permissions table
CREATE TABLE permissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    resource VARCHAR(100) NOT NULL,
    action VARCHAR(50) NOT NULL,
    description VARCHAR(500),
    conditions JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(resource, action)
);

-- Role-Permission mapping
CREATE TABLE role_permissions (
    role_id UUID REFERENCES roles(id) ON DELETE CASCADE,
    permission_id UUID REFERENCES permissions(id) ON DELETE CASCADE,
    PRIMARY KEY (role_id, permission_id)
);

-- User-Role assignments
CREATE TABLE user_roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE NOT NULL,
    role_id UUID REFERENCES roles(id) ON DELETE CASCADE NOT NULL,
    scope_type VARCHAR(50),
    scope_id UUID,
    valid_from TIMESTAMP DEFAULT NOW(),
    valid_until TIMESTAMP,
    granted_by_id UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, role_id, scope_type, scope_id)
);
```

## Migration from is_admin

If you're currently using just `is_admin` and want to migrate to RBAC:

1. Keep using `is_admin` - RBAC respects it as a super-admin bypass
2. Create roles for your permission groups
3. Assign roles to users (existing `is_admin=True` users still work)
4. Gradually replace `AdminUser` with `@require("specific:permission")`

## Testing

Test endpoints are available at `/api/auth-test/*` during development:

```bash
# Public endpoint
curl http://localhost:8000/api/auth-test/public

# Authenticated endpoint
curl http://localhost:8000/api/auth-test/authenticated \
  -H "Authorization: Bearer $TOKEN"

# Admin only
curl http://localhost:8000/api/auth-test/admin-only \
  -H "Authorization: Bearer $TOKEN"

# Check user permissions
curl http://localhost:8000/api/auth-test/authz-check \
  -H "Authorization: Bearer $TOKEN"
```

**Note:** Remove `auth_test.py` in production.

## Best Practices

1. **Start simple** - Use Level 1-2 for MVP, add complexity as needed
2. **Use specific permissions** - Prefer `posts:delete` over generic `delete`
3. **Admin bypass** - `is_admin=True` always passes all checks
4. **Cache permissions** - RBAC engine caches for 5 minutes by default
5. **Audit actions** - Log authorization decisions for compliance
6. **Test both success and failure** - Ensure denials work correctly
