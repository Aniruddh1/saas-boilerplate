# SaaS API Boilerplate

Production-ready FastAPI backend with authentication, authorization, and audit logging.

## Features

- **Authentication**: JWT-based auth with access/refresh tokens
- **Authorization**: Progressive-complexity system (simple to enterprise RBAC/ABAC)
- **User Management**: Registration, login, profile, admin controls
- **Audit Logging**: Track all user actions
- **Async Database**: SQLAlchemy 2.0 with PostgreSQL
- **API Documentation**: Auto-generated OpenAPI/Swagger docs
- **Docker Ready**: Docker Compose for local development

## Tech Stack

- **Framework**: FastAPI
- **Database**: PostgreSQL + SQLAlchemy 2.0 (async)
- **Auth**: JWT (python-jose) + bcrypt
- **Migrations**: Alembic
- **Validation**: Pydantic v2

## Quick Start

```bash
# With Docker
docker compose up -d
docker compose exec api alembic upgrade head

# Manual
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
uvicorn src.main:app --reload
```

API runs at http://localhost:8000

## Documentation

| Document | Description |
|----------|-------------|
| [Getting Started](./docs/GETTING_STARTED.md) | Setup and basic usage |
| [Authorization](./docs/AUTHORIZATION.md) | Full auth system guide |
| [API Docs](http://localhost:8000/docs) | Interactive Swagger UI |

## Project Structure

```
src/
├── main.py                 # Application entry point
├── api/
│   ├── routes/             # API endpoints
│   │   ├── auth.py         # Login, register, refresh
│   │   ├── users.py        # User CRUD
│   │   └── audit_logs.py   # Audit log access
│   └── dependencies/       # FastAPI dependencies
├── core/
│   ├── config.py           # Settings
│   ├── database.py         # DB connection
│   ├── security.py         # Password, JWT
│   └── auth/               # Authorization system
│       ├── interfaces.py   # Abstract contracts
│       ├── service.py      # AuthorizationService
│       ├── dependencies.py # CurrentUser, AdminUser, Authorize
│       ├── decorators.py   # @require, @require_admin
│       └── policy/         # Policy engines
├── models/                 # SQLAlchemy models
├── schemas/                # Pydantic schemas
├── services/               # Business logic
└── extensions/
    └── auth/rbac/          # Optional RBAC extension
```

## Authorization Levels

The auth system supports progressive complexity:

```python
# Level 1: Simple dependencies
@router.get("/profile")
async def profile(user: CurrentUser):
    return user

# Level 2: Permission decorators
@router.post("/posts")
@require("posts:create")
async def create_post(user: CurrentUser):
    ...

# Level 3: Authorization service
@router.post("/approve/{id}")
async def approve(id: str, auth: Authorize):
    await auth.require("transactions:approve", resource)
    ...

# Level 4: With conditions
await auth.require("approve", tx, conditions={"max_amount": 10000})

# Level 5: Full RBAC (enable with AUTH_POLICY_ENGINE=rbac)
```

See [Authorization Guide](./docs/AUTHORIZATION.md) for full details.

## Environment Variables

```env
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/db

# JWT
JWT_SECRET_KEY=change-this-in-production
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# Authorization (optional)
AUTH_POLICY_ENGINE=simple      # simple or rbac
AUTH_SCOPE_PROVIDER=none       # none, ownership, tenant
AUTH_MULTI_TENANT=false
```

## API Endpoints

### Auth
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login (returns tokens)
- `POST /api/auth/refresh` - Refresh access token
- `POST /api/auth/logout` - Logout

### Users
- `GET /api/users/me` - Current user profile
- `PATCH /api/users/me` - Update profile
- `GET /api/users` - List users (admin)
- `GET /api/users/{id}` - Get user (admin)
- `PATCH /api/users/{id}` - Update user (admin)
- `DELETE /api/users/{id}` - Delete user (admin)

### Audit
- `GET /api/audit-logs` - List audit logs (admin)

## Development

```bash
# Run with auto-reload
uvicorn src.main:app --reload

# Run tests
pytest

# Create migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head
```

## License

MIT
