# Timestamps & Metadata Columns

Standard patterns for timestamps, timezones, and audit fields.

## Timezone Handling

### Golden Rules

| Layer | Rule |
|-------|------|
| **Database** | Always store UTC |
| **API** | Return ISO 8601 with `Z` suffix |
| **Frontend** | Browser auto-converts via `Intl` API |

### Why Browser Auto-Detection?

```
┌──────────┐   UTC    ┌─────────┐   UTC    ┌──────────────────┐
│ Database │ ───────► │   API   │ ───────► │     Frontend     │
│  (UTC)   │          │  (UTC)  │          │ (auto-local via  │
└──────────┘          └─────────┘          │  browser Intl)   │
                                           └──────────────────┘
```

- **No config needed** - Browser knows user's timezone
- **DST handled** - Automatic daylight saving adjustments
- **Locale aware** - Date format matches user's region
- **Real-time** - No server round-trip to change display

### Frontend (Auto-Detect)

```typescript
// API returns UTC
const response = await fetch('/api/orders');
const order = await response.json();
// order.created_at = "2024-01-15T14:30:00Z"

// Browser auto-converts to local
const date = new Date(order.created_at);
const local = date.toLocaleString();
// "1/15/2024, 9:30:00 AM" (if user is in EST)

// With formatting control
new Intl.DateTimeFormat('en-US', {
  dateStyle: 'medium',
  timeStyle: 'short',
}).format(date);
// "Jan 15, 2024, 9:30 AM"

// Relative time
const rtf = new Intl.RelativeTimeFormat('en', { numeric: 'auto' });
// "2 hours ago"
```

### Backend (UTC Only)

```python
from src.utils.timezone import utc_now, to_iso8601

# Always use utc_now() instead of datetime.utcnow()
record.created_at = utc_now()

# API serialization
return {"created_at": to_iso8601(record.created_at)}
# "2024-01-15T14:30:00Z"
```

### Server-Side Rendering (Emails, PDFs)

Only case where backend converts timezone:

```python
from src.utils.timezone import format_for_user

# Email template
body = f"""
Your order was placed on {format_for_user(
    order.created_at,
    user.timezone,  # From user profile
    "%B %d, %Y at %I:%M %p"
)}
"""
# "January 15, 2024 at 09:30 AM"
```

## Metadata Columns

### Available Mixins

```python
from src.models import (
    Base,
    TimestampMixin,      # created_at, updated_at
    AuditMixin,          # created_by, updated_by
    SoftDeleteMixin,     # deleted_at, deleted_by
    TenantMixin,         # tenant_id
    VersionMixin,        # version (optimistic locking)
    UUIDMixin,           # id (UUID primary key)
    # Combined
    StandardMixin,       # UUID + timestamps
    AuditedMixin,        # UUID + timestamps + audit
    TenantAuditedMixin,  # UUID + timestamps + audit + tenant
)
```

### When to Use Each

| Mixin | Use Case | Example |
|-------|----------|---------|
| `StandardMixin` | Most models | Products, Categories |
| `AuditedMixin` | Need to track WHO | Documents, Settings |
| `TenantAuditedMixin` | Multi-tenant + audit | Tenant-specific data |
| `SoftDeleteMixin` | Recoverable deletes | Users, Orders |
| `VersionMixin` | Concurrent edits | Collaborative docs |

### Example Model

```python
from src.models import Base, AuditedMixin, SoftDeleteMixin

class Document(Base, AuditedMixin, SoftDeleteMixin):
    """
    Gets automatically:
    - id: UUID primary key
    - created_at, updated_at: UTC timestamps
    - created_by, updated_by: User references
    - deleted_at, deleted_by: Soft delete
    """
    __tablename__ = "documents"

    title: Mapped[str] = mapped_column(String(255))
    content: Mapped[str] = mapped_column(Text)
```

### Setting Audit Fields

```python
# In service layer
async def create_document(
    data: DocumentCreate,
    current_user: User,
    db: AsyncSession,
) -> Document:
    doc = Document(
        **data.model_dump(),
        created_by=current_user.id,
        updated_by=current_user.id,
    )
    db.add(doc)
    await db.commit()
    return doc

async def update_document(
    doc: Document,
    data: DocumentUpdate,
    current_user: User,
    db: AsyncSession,
) -> Document:
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(doc, key, value)
    doc.updated_by = current_user.id  # Track who updated
    await db.commit()
    return doc
```

### Soft Delete Pattern

```python
from src.utils.timezone import utc_now

async def soft_delete(
    record: Document,
    current_user: User,
    db: AsyncSession,
):
    record.deleted_at = utc_now()
    record.deleted_by = current_user.id
    await db.commit()

# Query non-deleted records
query = select(Document).where(Document.deleted_at.is_(None))
```

### Optimistic Locking

```python
from sqlalchemy import update

async def update_with_version(
    record_id: UUID,
    expected_version: int,
    data: dict,
    db: AsyncSession,
):
    result = await db.execute(
        update(Document)
        .where(Document.id == record_id)
        .where(Document.version == expected_version)
        .values(**data, version=Document.version + 1)
    )

    if result.rowcount == 0:
        raise HTTPException(
            status_code=409,
            detail="Record was modified by another user"
        )
```

## API Response Format

```python
from pydantic import BaseModel
from datetime import datetime

class DocumentResponse(BaseModel):
    id: str
    title: str
    created_at: datetime  # Pydantic serializes as ISO 8601
    updated_at: datetime

    class Config:
        from_attributes = True
```

Response:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "title": "My Document",
  "created_at": "2024-01-15T14:30:00Z",
  "updated_at": "2024-01-15T15:45:00Z"
}
```

## User Timezone Field

The `User.timezone` field exists ONLY for:

1. **Email templates** - Server-rendered, no JS
2. **PDF reports** - Generated server-side
3. **Scheduled notifications** - "Send at 9 AM user's time"
4. **Date range queries** - "Show today's orders" in user's day

**NOT for API responses** - Frontend handles display automatically.

```python
# User model has timezone field
class User(Base, TimestampMixin):
    timezone: Mapped[str] = mapped_column(String(50), default="UTC")
```

Frontend can detect and save user's timezone on login:

```typescript
// On login/signup, save browser timezone
const userTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
// "America/New_York"

await fetch('/api/users/me', {
  method: 'PATCH',
  body: JSON.stringify({ timezone: userTimezone })
});
```
