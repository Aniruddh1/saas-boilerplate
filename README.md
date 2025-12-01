# Minimal App Boilerplate

A minimal, production-ready boilerplate with FastAPI backend, React frontend, and Celery workers.

This is a **minimal** version with just users, authentication, and audit logging. Perfect as a starting point for any application - add your domain-specific models and features on top.

## Tech Stack

### Backend (`apps/api`)
- **FastAPI** - Modern Python web framework
- **SQLAlchemy 2.0** - Async ORM with PostgreSQL
- **Pydantic v2** - Data validation
- **JWT Authentication** - Access/refresh token flow
- **Redis** - Caching and rate limiting
- **Alembic** - Database migrations

### Frontend (`apps/web`)
- **React 18** - UI library
- **Vite** - Build tool
- **TypeScript** - Type safety
- **TanStack Query** - Server state management
- **Zustand** - Client state management
- **Tailwind CSS** - Styling
- **shadcn/ui** - UI components
- **React Router v6** - Routing

### Worker (`apps/worker`)
- **Celery** - Distributed task queue
- **Redis** - Message broker
- **Scheduled tasks** - Cron-like jobs

### Infrastructure
- **PostgreSQL 16** - Primary database
- **Redis 7** - Cache, sessions, queue broker
- **Meilisearch** - Full-text search (optional)
- **MailHog** - Email testing
- **Docker Compose** - Local development

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Make (optional, for convenience commands)

### 1. Clone and Setup

```bash
git clone <repo-url> my-app
cd my-app
cp .env.example .env
```

### 2. Start Development Environment

```bash
# Using Make
make dev

# Or using Docker Compose directly
docker compose up -d
```

### 3. Access Services

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3001 |
| API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |
| MailHog | http://localhost:8025 |
| Flower | http://localhost:5555 |
| Meilisearch | http://localhost:7700 |

### 4. Create Database Tables

```bash
make db-migrate
# Or: docker compose exec api alembic upgrade head
```

## Project Structure

```
.
├── apps/
│   ├── api/                 # FastAPI backend
│   │   ├── src/
│   │   │   ├── api/         # Routes & middleware
│   │   │   ├── core/        # Config, plugins, hooks
│   │   │   ├── models/      # SQLAlchemy models
│   │   │   ├── schemas/     # Pydantic schemas
│   │   │   ├── services/    # Business logic
│   │   │   └── utils/       # Helpers
│   │   ├── migrations/      # Alembic migrations
│   │   └── tests/
│   │
│   ├── web/                 # React frontend
│   │   ├── src/
│   │   │   ├── components/  # UI components
│   │   │   ├── hooks/       # Custom hooks
│   │   │   ├── pages/       # Page components
│   │   │   ├── stores/      # Zustand stores
│   │   │   └── types/       # TypeScript types
│   │   └── public/
│   │
│   └── worker/              # Celery workers
│       └── src/
│           └── tasks/       # Background tasks
│
├── docker-compose.yml       # Development services
├── docker-compose.prod.yml  # Production services
├── Makefile                 # Common commands
└── README.md
```

## Common Commands

```bash
# Development
make dev              # Start all services
make down             # Stop all services
make logs             # View logs
make logs-api         # View API logs only

# Database
make db-migrate       # Run migrations
make db-revision      # Create new migration
make db-downgrade     # Rollback migration

# Testing
make test             # Run all tests
make test-api         # Run backend tests
make test-web         # Run frontend tests

# Code Quality
make lint             # Run linters
make format           # Format code

# Production
make build            # Build production images
make deploy           # Deploy (configure first)
```

## Features

### Authentication
- JWT-based authentication with access/refresh tokens
- Email/password registration and login
- Password reset flow (requires email config)
- Session management

### Audit Logging
- Track user actions
- Filterable audit trail
- Extensible for any resource type

### Extensible Architecture
- Clean service layer for business logic
- Repository pattern ready
- Plugin/hook system for extensibility
- Easy to add new models, routes, and services

## Configuration

### Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
# Database
DB_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/app

# Redis
REDIS_URL=redis://redis:6379/0

# Auth
AUTH_SECRET_KEY=your-secret-key-change-in-production
AUTH_ACCESS_TOKEN_EXPIRE_MINUTES=30
AUTH_REFRESH_TOKEN_EXPIRE_DAYS=7

# Email (for production)
EMAIL_SMTP_HOST=smtp.example.com
EMAIL_SMTP_PORT=587
EMAIL_SMTP_USER=your-user
EMAIL_SMTP_PASSWORD=your-password
EMAIL_FROM_ADDRESS=noreply@example.com
```

## Deployment

### Docker (Recommended)

```bash
# Build production images
docker compose -f docker-compose.prod.yml build

# Deploy
docker compose -f docker-compose.prod.yml up -d
```

### Kubernetes

Kubernetes manifests coming soon. For now:
1. Build and push images to your registry
2. Create k8s deployments for each service
3. Configure ingress for API and frontend

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting
5. Submit a pull request

## License

MIT License - see LICENSE file for details.
