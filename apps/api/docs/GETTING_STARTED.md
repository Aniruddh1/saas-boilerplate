# Getting Started

Quick guide to set up and run the API.

## Prerequisites

- Python 3.11+
- PostgreSQL 14+
- Docker & Docker Compose (recommended)

## Quick Start with Docker

```bash
# Clone and navigate
cd saas-monorepo/apps/api

# Copy environment file
cp .env.example .env

# Start all services
docker compose up -d

# Run migrations
docker compose exec api alembic upgrade head

# API is now running at http://localhost:8000
```

## Manual Setup

### 1. Install Dependencies

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
```

Edit `.env`:

```env
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/dbname

# JWT Settings
JWT_SECRET_KEY=your-secret-key-change-in-production
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# Optional: Authorization settings
AUTH_POLICY_ENGINE=simple
AUTH_SCOPE_PROVIDER=none
```

### 3. Setup Database

```bash
# Create database
createdb your_db_name

# Run migrations
alembic upgrade head
```

### 4. Run the Server

```bash
# Development (with auto-reload)
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# Production
uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## API Documentation

Once running, access:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

## Core Endpoints

### Authentication

```bash
# Register
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "securepass123", "name": "John Doe"}'

# Login
curl -X POST http://localhost:8000/api/auth/login \
  -d "username=user@example.com&password=securepass123"

# Response: {"access_token": "...", "refresh_token": "...", "token_type": "bearer"}

# Refresh token
curl -X POST http://localhost:8000/api/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "your_refresh_token"}'
```

### Users

```bash
# Get current user
curl http://localhost:8000/api/users/me \
  -H "Authorization: Bearer $TOKEN"

# Update profile
curl -X PATCH http://localhost:8000/api/users/me \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "New Name"}'

# List users (admin only)
curl http://localhost:8000/api/users \
  -H "Authorization: Bearer $TOKEN"
```

### Audit Logs

```bash
# List audit logs (admin only)
curl http://localhost:8000/api/audit-logs \
  -H "Authorization: Bearer $TOKEN"
```

## Project Structure

```
src/
├── main.py              # FastAPI application entry
├── api/
│   ├── routes/          # API route handlers
│   │   ├── auth.py      # Authentication endpoints
│   │   ├── users.py     # User management
│   │   └── audit_logs.py
│   └── dependencies/    # FastAPI dependencies
├── core/
│   ├── config.py        # Settings and configuration
│   ├── database.py      # Database connection
│   ├── security.py      # Password hashing, JWT
│   └── auth/            # Authorization system
├── models/              # SQLAlchemy models
├── schemas/             # Pydantic schemas
├── services/            # Business logic
└── extensions/          # Optional features
    └── auth/rbac/       # RBAC extension
```

## Adding New Features

### 1. Create Model

```python
# src/models/post.py
from sqlalchemy.orm import Mapped, mapped_column
from src.models.base import Base, TimestampMixin

class Post(Base, TimestampMixin):
    __tablename__ = "posts"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    title: Mapped[str] = mapped_column(String(200))
    content: Mapped[str] = mapped_column(Text)
    author_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
```

### 2. Create Schema

```python
# src/schemas/post.py
from pydantic import BaseModel

class PostCreate(BaseModel):
    title: str
    content: str

class PostResponse(BaseModel):
    id: UUID
    title: str
    content: str
    author_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True
```

### 3. Create Service

```python
# src/services/post.py
class PostService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, author_id: UUID, data: PostCreate) -> Post:
        post = Post(author_id=author_id, **data.model_dump())
        self.db.add(post)
        await self.db.commit()
        return post
```

### 4. Create Routes

```python
# src/api/routes/posts.py
from fastapi import APIRouter, Depends
from src.core.auth import CurrentUser, require

router = APIRouter()

@router.post("/")
@require("posts:create")
async def create_post(
    data: PostCreate,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    service = PostService(db)
    post = await service.create(user.id, data)
    return PostResponse.model_validate(post)
```

### 5. Register Routes

```python
# src/api/routes/__init__.py
from .posts import router as posts_router

router.include_router(posts_router, prefix="/posts", tags=["posts"])
```

### 6. Create Migration

```bash
alembic revision --autogenerate -m "Add posts table"
alembic upgrade head
```

## Next Steps

- Read [AUTHORIZATION.md](./AUTHORIZATION.md) for the full auth system guide
- Check the API docs at `/docs` for all available endpoints
- Review example code in `src/api/routes/` for patterns
