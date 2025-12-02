# Analytics & Custom Dashboards Extension

Multi-tenant analytics with customer-defined metrics and dashboards using Cube.js as the semantic layer.

## Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           YOUR SAAS                                     │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────┐    ┌──────────────┐    ┌─────────────────────────┐    │
│  │   React     │    │   FastAPI    │    │      Cube.js            │    │
│  │   Frontend  │◄──►│   Backend    │◄──►│   (Semantic Layer)      │    │
│  │             │    │              │    │                         │    │
│  │ - Dashboard │    │ - Auth       │    │ - Metric definitions    │    │
│  │   Builder   │    │ - Tenant mgmt│    │ - Multi-tenant queries  │    │
│  │ - Widgets   │    │ - Dashboards │    │ - Caching               │    │
│  │ - Charts    │    │ - Metrics API│    │ - Pre-aggregations      │    │
│  └─────────────┘    └──────────────┘    └───────────┬─────────────┘    │
│                                                      │                  │
│                                                      ▼                  │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                     PostgreSQL                                    │  │
│  │  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐      │  │
│  │  │ tenant_acme.*  │  │ tenant_globex.*│  │ public.*       │      │  │
│  │  │ - transactions │  │ - inventory    │  │ - dashboards   │      │  │
│  │  │ - accounts     │  │ - suppliers    │  │ - metrics      │      │  │
│  │  └────────────────┘  └────────────────┘  └────────────────┘      │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

## When to Use This

**Add this extension when:**
- Customers need to create their own reports/dashboards
- Your product is data-centric (treasury, supply chain, HR analytics)
- You have 10+ customers asking for custom metrics
- Post-MVP with real data to visualize

**Don't use when:**
- Building MVP (use pre-built dashboards)
- Simple admin reports suffice
- Data visualization is not core to your product

## Tech Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| Semantic Layer | Cube.js | Metric definitions, caching, multi-tenant |
| Dashboard UI | React + react-grid-layout | Drag-drop dashboard builder |
| Charts | Recharts or Apache ECharts | Visualizations |
| Tables | TanStack Table | Data tables |
| State | TanStack Query | Data fetching |

## Implementation Effort

| Phase | Effort | Description |
|-------|--------|-------------|
| Cube.js setup | 2-3 days | Deploy, configure multi-tenant |
| Core models + API | 1 week | Dashboards, metrics, widgets |
| Metric builder UI | 1 week | No-code metric creation |
| Dashboard builder | 1-2 weeks | Drag-drop, widget config |
| Pre-built templates | 3-5 days | Domain-specific dashboards |
| **Total** | **4-5 weeks** | Full feature |

---

## Phase 1: Infrastructure

### 1.1 Deploy Cube.js

```yaml
# docker-compose.yml
services:
  cube:
    image: cubejs/cube:latest
    ports:
      - "4000:4000"
    environment:
      CUBEJS_DB_TYPE: postgres
      CUBEJS_DB_HOST: postgres
      CUBEJS_DB_NAME: your_db
      CUBEJS_DB_USER: your_user
      CUBEJS_DB_PASS: your_pass
      CUBEJS_API_SECRET: your-secret-key
      CUBEJS_DEV_MODE: "true"
    volumes:
      - ./cube/schema:/cube/conf/schema
```

### 1.2 Cube.js Configuration

```javascript
// cube.js
module.exports = {
  // Separate app per tenant for isolation
  contextToAppId: ({ securityContext }) => {
    return `CUBE_${securityContext.tenantId}`;
  },

  // Row-level security via query rewrite
  queryRewrite: (query, { securityContext }) => {
    if (!securityContext.tenantId) {
      throw new Error('Tenant context required');
    }

    // Skip RLS for full access users
    if (securityContext.hasFullAccess) {
      return query;
    }

    query.filters = query.filters || [];

    // Auto-inject data scope filters
    if (securityContext.regions?.length > 0) {
      query.filters.push({
        member: `${getCubeName(query)}.region`,
        operator: 'equals',
        values: securityContext.regions
      });
    }

    if (securityContext.departments?.length > 0) {
      query.filters.push({
        member: `${getCubeName(query)}.department`,
        operator: 'equals',
        values: securityContext.departments
      });
    }

    return query;
  },

  scheduledRefreshContexts: async () => {
    const tenants = await fetchAllTenants();
    return tenants.map(t => ({
      securityContext: {
        tenantId: t.id,
        tenantSchema: t.schema_name,
        hasFullAccess: true,
      }
    }));
  }
};

function getCubeName(query) {
  const measure = query.measures?.[0] || query.dimensions?.[0];
  return measure?.split('.')[0];
}
```

### 1.3 Example Cube Schema

```javascript
// cube/schema/Transactions.js
cube(`Transactions`, {
  sql: `SELECT * FROM ${SECURITY_CONTEXT.tenantSchema}.transactions`,

  measures: {
    totalAmount: {
      type: `sum`,
      sql: `amount`,
      format: `currency`
    },
    count: {
      type: `count`
    },
    avgAmount: {
      type: `avg`,
      sql: `amount`,
      format: `currency`
    }
  },

  dimensions: {
    id: { type: `string`, sql: `id`, primaryKey: true },
    region: { type: `string`, sql: `region` },
    department: { type: `string`, sql: `department` },
    category: { type: `string`, sql: `category` },
    transactionDate: { type: `time`, sql: `transaction_date` }
  }
});
```

---

## Phase 2: Database Models

### 2.1 Core Models

```python
# src/extensions/analytics/models.py

from uuid import UUID, uuid4
from sqlalchemy import String, ForeignKey, JSON, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.models.base import Base, TimestampMixin


class TenantDataSource(Base, TimestampMixin):
    """Available data sources (tables) for a tenant."""
    __tablename__ = "tenant_data_sources"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id"))

    schema_name: Mapped[str] = mapped_column(String(100))
    table_name: Mapped[str] = mapped_column(String(100))
    display_name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, nullable=True)

    # Column definitions for metric builder
    columns: Mapped[dict] = mapped_column(JSON, default=dict)
    # Example: {"amount": {"type": "number", "label": "Amount"}, ...}

    cube_name: Mapped[str] = mapped_column(String(100))
    is_active: Mapped[bool] = mapped_column(default=True)


class MetricDefinition(Base, TimestampMixin):
    """Customer-defined metric."""
    __tablename__ = "metric_definitions"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id"))

    # Basic info
    name: Mapped[str] = mapped_column(String(200))
    key: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(Text, nullable=True)

    # Data source
    data_source_id: Mapped[UUID] = mapped_column(ForeignKey("tenant_data_sources.id"))

    # Aggregation config (no-code friendly)
    aggregation_type: Mapped[str] = mapped_column(String(50))
    # "sum", "avg", "count", "min", "max", "formula"
    field: Mapped[str] = mapped_column(String(100), nullable=True)
    formula: Mapped[str] = mapped_column(Text, nullable=True)
    # For complex: "{sum_amount} / {count_transactions}"

    # Dimensions users can break down by
    dimensions: Mapped[list] = mapped_column(JSON, default=list)

    # Display formatting
    format_type: Mapped[str] = mapped_column(String(50), default="number")
    # "currency", "percentage", "number", "integer"
    format_options: Mapped[dict] = mapped_column(JSON, default=dict)
    # {"decimals": 2, "prefix": "$", "suffix": "%"}

    # Time field for time-series
    default_time_field: Mapped[str] = mapped_column(String(100), nullable=True)

    # Sensitivity for RLS
    sensitivity_level: Mapped[str] = mapped_column(String(50), nullable=True)
    # "financial", "hr", "executive" - requires matching permission

    # Status
    is_template: Mapped[bool] = mapped_column(default=False)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_by_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))


class Dashboard(Base, TimestampMixin):
    """Customer-created dashboard."""
    __tablename__ = "dashboards"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id"))

    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, nullable=True)

    # Layout (react-grid-layout format)
    layout: Mapped[dict] = mapped_column(JSON, default=dict)
    # {"lg": [...], "md": [...], "sm": [...]}

    # Access control
    visibility: Mapped[str] = mapped_column(String(50), default="private")
    # "private", "shared", "tenant"
    shared_with: Mapped[list] = mapped_column(JSON, default=list)

    is_default: Mapped[bool] = mapped_column(default=False)
    created_by_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))

    # Relationships
    widgets = relationship("DashboardWidget", back_populates="dashboard", cascade="all, delete-orphan")


class DashboardWidget(Base, TimestampMixin):
    """Individual widget on a dashboard."""
    __tablename__ = "dashboard_widgets"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    dashboard_id: Mapped[UUID] = mapped_column(ForeignKey("dashboards.id"))

    # Widget type
    widget_type: Mapped[str] = mapped_column(String(50))
    # "kpi", "line", "bar", "pie", "area", "table"

    # Data config
    metric_id: Mapped[UUID] = mapped_column(ForeignKey("metric_definitions.id"))
    dimensions: Mapped[list] = mapped_column(JSON, default=list)
    filters: Mapped[dict] = mapped_column(JSON, default=dict)
    time_range: Mapped[str] = mapped_column(String(50), default="last_30_days")
    time_range_custom: Mapped[dict] = mapped_column(JSON, nullable=True)

    # Comparison (for KPIs)
    comparison_type: Mapped[str] = mapped_column(String(50), nullable=True)
    # "previous_period", "same_period_last_year"

    # Display
    title: Mapped[str] = mapped_column(String(200))
    subtitle: Mapped[str] = mapped_column(String(500), nullable=True)
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    # Chart-specific: colors, legend position, etc.

    # Relationships
    dashboard = relationship("Dashboard", back_populates="widgets")
```

### 2.2 User Data Scope Model

```python
# Add to User model or create separate table

class UserDataScope(Base):
    """User's row-level data access permissions."""
    __tablename__ = "user_data_scopes"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id"))

    scope_type: Mapped[str] = mapped_column(String(50))
    # "region", "department", "cost_center", etc.

    scope_values: Mapped[list] = mapped_column(JSON)
    # ["US-West", "US-East"]

    include_children: Mapped[bool] = mapped_column(default=True)
    # For hierarchical scopes
```

---

## Phase 3: FastAPI Integration

### 3.1 Cube.js Client

```python
# src/extensions/analytics/cube_client.py

import httpx
import jwt
from uuid import UUID

class CubeClient:
    """Client for Cube.js API with security context."""

    def __init__(self, base_url: str, api_secret: str):
        self.base_url = base_url
        self.api_secret = api_secret

    async def query(
        self,
        query: dict,
        security_context: dict,
    ) -> dict:
        """Execute Cube.js query with security context."""

        token = jwt.encode(security_context, self.api_secret, algorithm="HS256")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/cubejs-api/v1/load",
                json={"query": query},
                headers={"Authorization": token},
                timeout=30.0,
            )
            response.raise_for_status()
            return response.json()

    async def meta(self, security_context: dict) -> dict:
        """Get available cubes and measures."""

        token = jwt.encode(security_context, self.api_secret, algorithm="HS256")

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/cubejs-api/v1/meta",
                headers={"Authorization": token},
            )
            response.raise_for_status()
            return response.json()
```

### 3.2 Query Service with RLS

```python
# src/extensions/analytics/services.py

from uuid import UUID
from src.core.auth.tenant import TenantContext

class AnalyticsQueryService:
    """Service for querying metrics with automatic RLS."""

    def __init__(
        self,
        cube_client: CubeClient,
        tenant: TenantContext,
        db: AsyncSession,
    ):
        self.cube = cube_client
        self.tenant = tenant
        self.db = db

    async def query_metric(
        self,
        metric: MetricDefinition,
        dimensions: list[str] = None,
        filters: list[dict] = None,
        time_range: dict = None,
    ) -> dict:
        """Query metric with user's data scope automatically applied."""

        # Build Cube.js query
        query = {
            "measures": [f"{metric.data_source.cube_name}.{metric.key}"],
            "dimensions": [
                f"{metric.data_source.cube_name}.{d}"
                for d in (dimensions or [])
            ],
            "filters": filters or [],
        }

        if time_range:
            query["timeDimensions"] = [{
                "dimension": f"{metric.data_source.cube_name}.{metric.default_time_field}",
                "dateRange": [time_range["start"], time_range["end"]],
                "granularity": time_range.get("granularity"),
            }]

        # Build security context (RLS filters applied in Cube.js)
        security_context = await self._build_security_context()

        return await self.cube.query(query, security_context)

    async def _build_security_context(self) -> dict:
        """Build Cube.js security context from user's data scope."""

        user = self.tenant.user
        scopes = await self._get_user_scopes(user.id)

        return {
            "tenantId": str(self.tenant.tenant_id),
            "tenantSchema": self.tenant.schema_name,
            "userId": str(user.id),
            "hasFullAccess": user.data_scope_level == "all",
            "regions": scopes.get("region", []),
            "departments": scopes.get("department", []),
            "costCenters": scopes.get("cost_center", []),
        }

    async def _get_user_scopes(self, user_id: UUID) -> dict:
        """Get user's data scopes from database."""
        query = select(UserDataScope).where(UserDataScope.user_id == user_id)
        result = await self.db.execute(query)

        scopes = {}
        for scope in result.scalars():
            if scope.scope_type not in scopes:
                scopes[scope.scope_type] = []
            scopes[scope.scope_type].extend(scope.scope_values)

        return scopes
```

### 3.3 API Routes

```python
# src/extensions/analytics/routes.py

from fastapi import APIRouter, Depends, HTTPException
from src.core.auth import require, Authorize
from src.core.auth.tenant import TenantUser

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/dashboards")
@require("dashboards:view")
async def list_dashboards(
    tenant: TenantUser,
    db: AsyncSession = Depends(get_db),
):
    """List dashboards user can access."""
    query = (
        select(Dashboard)
        .where(Dashboard.tenant_id == tenant.tenant_id)
        .where(
            or_(
                Dashboard.created_by_id == tenant.user.id,
                Dashboard.visibility == "tenant",
                Dashboard.shared_with.contains([str(tenant.user.id)]),
            )
        )
    )
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/dashboards")
@require("dashboards:create")
async def create_dashboard(
    data: DashboardCreate,
    tenant: TenantUser,
    db: AsyncSession = Depends(get_db),
):
    """Create a new dashboard."""
    dashboard = Dashboard(
        tenant_id=tenant.tenant_id,
        created_by_id=tenant.user.id,
        **data.dict()
    )
    db.add(dashboard)
    await db.commit()
    return dashboard


@router.post("/metrics/{metric_id}/query")
@require("metrics:view")
async def query_metric(
    metric_id: UUID,
    request: MetricQueryRequest,
    tenant: TenantUser,
    cube: CubeClient = Depends(get_cube_client),
    db: AsyncSession = Depends(get_db),
):
    """
    Query metric data.

    Row-level security is automatically applied based on user's data scope.
    """
    metric = await db.get(MetricDefinition, metric_id)
    if not metric or metric.tenant_id != tenant.tenant_id:
        raise HTTPException(404)

    service = AnalyticsQueryService(cube, tenant, db)
    result = await service.query_metric(
        metric=metric,
        dimensions=request.dimensions,
        filters=request.filters,
        time_range=request.time_range,
    )

    return result
```

---

## Phase 4: Auth Integration

### 4.1 New Permissions

```python
# Add to RBAC setup

ANALYTICS_PERMISSIONS = [
    # Dashboards
    ("dashboards", "view"),
    ("dashboards", "create"),
    ("dashboards", "edit"),
    ("dashboards", "delete"),
    ("dashboards", "share"),

    # Metrics
    ("metrics", "view"),
    ("metrics", "create"),
    ("metrics", "edit"),
    ("metrics", "delete"),

    # Data sources (admin)
    ("datasources", "view"),
    ("datasources", "manage"),

    # Sensitive data categories
    ("data", "financial"),
    ("data", "hr"),
    ("data", "executive"),
]

# Example roles
ANALYTICS_ROLES = {
    "viewer": ["dashboards:view", "metrics:view"],
    "analyst": ["dashboards:*", "metrics:*", "datasources:view"],
    "admin": ["dashboards:*", "metrics:*", "datasources:*", "data:*"],
}
```

### 4.2 ABAC Conditions

```python
# Dashboard ownership condition
@AuthRegistry.condition("is_owner")
class IsOwnerCondition(ConditionEvaluator):
    async def evaluate(self, expected, actor, resource, context):
        is_owner = resource.created_by_id == actor.id
        if expected and not is_owner:
            return False, "You must be the owner"
        return True, None
```

---

## Phase 5: Frontend Components

### 5.1 Dashboard Builder

```tsx
// apps/web/src/components/analytics/DashboardBuilder.tsx

import GridLayout from 'react-grid-layout';
import { useQuery, useMutation } from '@tanstack/react-query';

export function DashboardBuilder({ dashboardId }: { dashboardId: string }) {
  const { data: dashboard } = useQuery({
    queryKey: ['dashboard', dashboardId],
    queryFn: () => api.get(`/analytics/dashboards/${dashboardId}`),
  });

  const updateLayout = useMutation({
    mutationFn: (layout) =>
      api.put(`/analytics/dashboards/${dashboardId}`, { layout }),
  });

  return (
    <GridLayout
      className="layout"
      layout={dashboard?.layout}
      cols={12}
      rowHeight={100}
      onLayoutChange={(layout) => updateLayout.mutate(layout)}
    >
      {dashboard?.widgets.map((widget) => (
        <div key={widget.id}>
          <Widget widget={widget} />
        </div>
      ))}
    </GridLayout>
  );
}
```

### 5.2 Metric Builder

```tsx
// apps/web/src/components/analytics/MetricBuilder.tsx

export function MetricBuilder() {
  const [metric, setMetric] = useState({
    name: '',
    dataSource: '',
    aggregationType: 'sum',
    field: '',
    formatType: 'number',
  });

  return (
    <form>
      <Input
        label="Metric Name"
        value={metric.name}
        onChange={(e) => setMetric({ ...metric, name: e.target.value })}
      />

      <Select
        label="Data Source"
        options={dataSources}
        value={metric.dataSource}
        onChange={(v) => setMetric({ ...metric, dataSource: v })}
      />

      <Select
        label="Aggregation"
        options={['sum', 'avg', 'count', 'min', 'max']}
        value={metric.aggregationType}
        onChange={(v) => setMetric({ ...metric, aggregationType: v })}
      />

      <Select
        label="Field"
        options={fields}
        value={metric.field}
        onChange={(v) => setMetric({ ...metric, field: v })}
      />

      <Select
        label="Format"
        options={['number', 'currency', 'percentage']}
        value={metric.formatType}
        onChange={(v) => setMetric({ ...metric, formatType: v })}
      />

      <Button type="submit">Create Metric</Button>
    </form>
  );
}
```

---

## Data Flow Summary

```
┌─────────────────────────────────────────────────────────────────────────┐
│  User: Sarah (regions: ["US-West"], departments: ["Sales"])             │
│  Request: Query "Total Sales" metric                                    │
└─────────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  FastAPI: Build security context                                        │
│  {                                                                      │
│    tenantSchema: "tenant_acme",                                         │
│    hasFullAccess: false,                                                │
│    regions: ["US-West"],                                                │
│    departments: ["Sales"]                                               │
│  }                                                                      │
└─────────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  Cube.js: queryRewrite auto-injects RLS filters                         │
│  WHERE region IN ('US-West') AND department IN ('Sales')                │
└─────────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  Result: Sarah sees only US-West Sales data                             │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Alternatives

| Alternative | Pros | Cons |
|-------------|------|------|
| **Metabase Embedded** | Full BI, less code | Less customization, iframe |
| **Apache Superset** | Open source, powerful | Complex setup |
| **Custom SQL Builder** | No dependencies | Build caching yourself |
| **Preset (managed Superset)** | Easy setup | Cost, vendor lock-in |

## Resources

- [Cube.js Documentation](https://cube.dev/docs)
- [Cube.js Multi-Tenancy Guide](https://cube.dev/docs/config/multiple-data-sources)
- [React Grid Layout](https://github.com/react-grid-layout/react-grid-layout)
- [Recharts](https://recharts.org/)
