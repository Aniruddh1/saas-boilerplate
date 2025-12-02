# Extensions

Optional features that can be added to your SaaS when needed. These are not included in the core boilerplate but are documented for when your product requires them.

## Philosophy

The core boilerplate includes **universal patterns** that every SaaS needs:
- Authentication & Authorization (RBAC/ABAC)
- Pagination (offset, cursor, keyset)
- Caching (cache-aside, write-through, stampede protection)
- Background Jobs (fire-and-forget, delayed, scheduled)
- Notifications (multi-channel, broadcast)
- Feature Flags

Extensions are **domain-specific features** that some SaaS products need:

| Extension | When to Add | Complexity |
|-----------|-------------|------------|
| [Analytics & Dashboards](./extensions/ANALYTICS.md) | Data-heavy SaaS, customer-facing reports | High |
| [Workflows](./extensions/WORKFLOWS.md) | Approval processes, stage-based tracking | Medium |
| Billing (Stripe) | Paid subscriptions | Medium |
| Multi-tenancy | B2B with org isolation | High |
| White-labeling | Custom branding per customer | Medium |
| Audit Logging | Compliance requirements | Low |

## When to Add Extensions

### Analytics & Dashboards
Add when:
- 10+ customers asking for custom reports
- Your data IS the product (treasury, supply chain, analytics)
- Post-MVP with real data to visualize

Don't add when:
- Building MVP
- Simple admin dashboards suffice
- Data is secondary to core functionality

### Workflows
Add when:
- Multi-step approval processes needed
- Stage-based tracking (upload → review → approve)
- Human-in-the-loop operations

Don't add when:
- Simple status fields suffice
- Automated pipelines (use Jobs instead)
- Single-user operations

## Extension Structure

When implementing an extension:

```
apps/api/src/
├── extensions/
│   └── analytics/           # Extension code
│       ├── __init__.py
│       ├── routes.py
│       ├── services.py
│       └── models.py
│
├── core/interfaces/
│   └── analytics.py         # Interface in core (optional)
```

## Adding an Extension

1. Read the extension documentation
2. Decide if you need it (see "When to Add")
3. Follow the implementation guide
4. Integrate with existing auth/tenant system

## Available Extension Guides

- [Analytics & Custom Dashboards](./extensions/ANALYTICS.md) - Cube.js integration, metric builder, RLS
- [Human Task Workflows](./extensions/WORKFLOWS.md) - State machines, approvals, stage tracking
