# Feature Flags

A scalable feature flag system with progressive complexity, supporting percentage rollouts, attribute targeting, group membership, and individual overrides.

## Overview

| Level | Complexity | Use Case |
|-------|------------|----------|
| 1 | Simple | Global on/off toggle |
| 2 | User-targeted | Enable for specific users |
| 3 | Decorator | Gate entire endpoints |
| 4 | Targeting rules | Attributes + groups |
| 5 | Management | Create/update flags via API |

## Quick Start

### Level 1: Simple Check

```python
from src.core.features import Feature

@router.get("/dashboard")
async def dashboard(feature: Feature):
    if await feature.is_enabled("new_dashboard"):
        return new_dashboard_data()
    return old_dashboard_data()
```

### Level 2: User-Targeted

```python
from src.core.features import UserFeature

@router.get("/analytics")
async def analytics(feature: UserFeature):
    # Automatically uses current user for targeting
    if await feature.is_enabled("advanced_analytics"):
        return advanced_analytics()
    return basic_analytics()
```

### Level 3: Decorator Style

```python
from src.core.features import require_feature, UserFeature

@router.get("/beta-feature")
@require_feature("beta_feature")
async def beta_endpoint(feature: UserFeature):
    return {"status": "beta"}

# With redirect instead of error
@router.get("/new-ui")
@require_feature("new_ui", redirect_url="/old-ui")
async def new_ui(feature: UserFeature):
    return {"ui": "new"}

# With 403 instead of 404
@router.get("/premium")
@require_feature("premium_feature", status_code=403)
async def premium(feature: UserFeature):
    return {"tier": "premium"}
```

### Level 4: Targeting Rules

Create flags with conditions in the database:

```python
# Target premium users
await feature.create_flag(
    key="advanced_reports",
    name="Advanced Reports",
    enabled=True,
    conditions={
        "attributes": {"tier": ["premium", "enterprise"]}
    }
)

# Target beta testers group
await feature.create_flag(
    key="new_checkout",
    name="New Checkout Flow",
    enabled=True,
    percentage=50,  # 50% rollout within the group
    conditions={
        "groups": ["beta_testers"]
    }
)

# Combined: premium users OR beta testers
await feature.create_flag(
    key="ai_insights",
    name="AI Insights",
    enabled=True,
    conditions={
        "attributes": {"tier": ["premium"]},
        "groups": ["beta_testers", "internal"]
    }
)
```

### Level 5: Management

```python
from src.core.features import Feature
from src.core.auth import AdminUser

@router.post("/admin/features")
async def create_feature(feature: Feature, admin: AdminUser):
    return await feature.create_flag(
        key="new_feature",
        name="New Feature",
        enabled=True,
        percentage=10,
    )

@router.get("/admin/features")
async def list_features(feature: Feature, admin: AdminUser):
    return await feature.list_flags()

@router.post("/admin/features/{key}/override")
async def set_override(
    key: str,
    user_id: UUID,
    enabled: bool,
    feature: Feature,
    admin: AdminUser,
):
    return await feature.set_override(user_id, key, enabled, reason="VIP access")

@router.post("/admin/features/groups/{group}/add")
async def add_to_group(group: str, user_id: UUID, feature: Feature, admin: AdminUser):
    return await feature.add_to_group(user_id, group)
```

## Architecture

```
src/core/features/
├── __init__.py          # Public exports
├── interfaces.py        # Abstract contracts
├── service.py           # FeatureService (evaluation logic)
├── dependencies.py      # FastAPI dependencies
├── decorators.py        # @require_feature
├── models.py            # SQLAlchemy models
└── backends/
    ├── database.py      # PostgreSQL backend
    └── memory.py        # In-memory (dev/testing)
```

## Configuration

```env
# Backend: database (default) or memory
FEATURE_BACKEND=database

# Default value when flag doesn't exist
FEATURE_DEFAULT_ENABLED=false

# Cache TTL in seconds
FEATURE_CACHE_TTL=60
```

## Database Schema

```sql
-- Feature flags
CREATE TABLE feature_flags (
    id UUID PRIMARY KEY,
    key VARCHAR(100) UNIQUE NOT NULL,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    enabled BOOLEAN DEFAULT FALSE,
    percentage INTEGER DEFAULT 100,
    conditions JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    created_by_id UUID REFERENCES users(id)
);

-- User groups (scalable targeting)
CREATE TABLE user_feature_groups (
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    group_name VARCHAR(100) NOT NULL,
    added_at TIMESTAMP DEFAULT NOW(),
    added_by_id UUID REFERENCES users(id),
    PRIMARY KEY (user_id, group_name)
);
CREATE INDEX idx_user_feature_groups_group ON user_feature_groups(group_name);

-- Individual overrides (highest priority)
CREATE TABLE feature_flag_overrides (
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    flag_key VARCHAR(100) NOT NULL,
    enabled BOOLEAN NOT NULL,
    reason VARCHAR(500),
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    created_by_id UUID REFERENCES users(id),
    PRIMARY KEY (user_id, flag_key)
);
```

## Evaluation Order

When checking if a feature is enabled:

1. **Override** (highest priority) - Check individual user override
2. **Global enabled** - Is the flag enabled at all?
3. **Percentage** - Is user in the rollout percentage?
4. **Conditions** - Do attributes or groups match?

```
Override → Enabled → Percentage → Conditions
   ↓          ↓          ↓           ↓
  Yes/No    False?     Not in?    No match?
   ↓          ↓          ↓           ↓
  Return    Return     Return      Return
            False      False       False
```

## Targeting Strategies

### 1. Attribute-Based

Use existing user fields - no extra storage:

```python
conditions = {
    "attributes": {
        "tier": ["premium", "enterprise"],  # user.tier in list
        "is_verified": True,                 # user.is_verified == True
        "country": ["US", "UK"],             # user.country in list
    }
}
```

Comparison operators:

```python
conditions = {
    "attributes": {
        "created_at": {"lt": "2024-01-01"},  # Before date
        "usage_count": {"gte": 100},          # Greater than or equal
    }
}
```

### 2. Group-Based

Add users to groups for cohort targeting:

```python
# Add user to beta testers
await feature.add_to_group(user_id, "beta_testers")

# Target beta testers
conditions = {"groups": ["beta_testers"]}
```

Common groups:
- `beta_testers` - Early access users
- `internal` - Company employees
- `early_adopters` - First users
- `vip` - Special customers

### 3. Individual Overrides

Force on/off for specific users:

```python
# VIP customer gets early access
await feature.set_override(
    user_id=vip_user_id,
    flag_key="premium_feature",
    enabled=True,
    reason="VIP customer",
)

# Disable buggy feature for affected user
await feature.set_override(
    user_id=affected_user_id,
    flag_key="new_checkout",
    enabled=False,
    reason="Bug workaround",
    expires_at=datetime(2024, 12, 31),  # Temporary
)
```

## Percentage Rollouts

Gradual rollout to N% of users:

```python
await feature.create_flag(
    key="new_checkout",
    name="New Checkout Flow",
    enabled=True,
    percentage=10,  # 10% of users
)
```

Percentage uses consistent hashing:
- Same user always gets same result for same flag
- Increase percentage to roll out to more users
- Users don't flip-flop between enabled/disabled

## Best Practices

1. **Start with percentage rollouts** - Roll out 1% → 10% → 50% → 100%

2. **Use attributes for broad targeting** - Premium tier, verified users

3. **Use groups for specific cohorts** - Beta testers, internal team

4. **Use overrides sparingly** - VIPs, bug workarounds

5. **Clean up old flags** - Delete flags after 100% rollout

6. **Log evaluations** - Track which flags are checked

7. **Cache flag values** - Reduce database queries

## Frontend Integration

Get all flags for current user:

```python
@router.get("/api/features")
async def get_features(feature: UserFeature):
    return await feature.get_all()

# Returns: {"new_dashboard": true, "beta_feature": false, ...}
```

Frontend can cache and use:

```typescript
const features = await api.get('/api/features');

if (features.new_dashboard) {
  showNewDashboard();
}
```

## Testing

Use memory backend for tests:

```python
# In tests
from src.core.features.backends.memory import MemoryFeatureBackend

@pytest.fixture
def feature_backend():
    backend = MemoryFeatureBackend()
    backend.seed([
        FeatureFlag(key="test_feature", name="Test", enabled=True),
    ])
    return backend

async def test_feature_enabled(feature_backend):
    service = FeatureService(feature_backend)
    assert await service.is_enabled("test_feature")
```
