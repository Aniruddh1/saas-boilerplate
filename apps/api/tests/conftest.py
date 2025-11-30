"""
Pytest fixtures for testing.

Provides:
- Async database session with rollback
- Test client with auth helpers
- Factory fixtures for creating test data
- Mock implementations for interfaces
"""

import asyncio
from typing import AsyncGenerator, Generator
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool

from src.main import app
from src.models.base import Base
from src.models.user import User
from src.api.dependencies.database import get_db
from src.services.auth import AuthService


# Test database URL (SQLite in-memory for speed)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db_engine():
    """Create test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db(db_engine) -> AsyncGenerator[AsyncSession, None]:
    """
    Create database session with automatic rollback.

    Each test gets a fresh transaction that's rolled back after.
    """
    session_factory = async_sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with session_factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture(scope="function")
async def client(db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    Test client with database session override.
    """

    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client

    app.dependency_overrides.clear()


# ============ Factory Fixtures ============


class UserFactory:
    """Factory for creating test users."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        email: str | None = None,
        password: str = "testpassword123",
        name: str = "Test User",
        is_admin: bool = False,
    ) -> User:
        """Create a user in the database."""
        from passlib.context import CryptContext

        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

        email = email or f"test-{uuid4().hex[:8]}@example.com"
        hashed_password = pwd_context.hash(password)

        user = User(
            email=email,
            hashed_password=hashed_password,
            name=name,
            is_admin=is_admin,
        )
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user


@pytest_asyncio.fixture
async def user_factory(db: AsyncSession) -> UserFactory:
    """Fixture that provides UserFactory."""
    return UserFactory(db)


@pytest_asyncio.fixture
async def test_user(user_factory: UserFactory) -> User:
    """Create a standard test user."""
    return await user_factory.create()


@pytest_asyncio.fixture
async def admin_user(user_factory: UserFactory) -> User:
    """Create an admin test user."""
    return await user_factory.create(
        email="admin@example.com",
        is_admin=True,
    )


# ============ Auth Helpers ============


@pytest_asyncio.fixture
async def auth_headers(test_user: User) -> dict[str, str]:
    """Get auth headers for test user."""
    auth_service = AuthService()
    token = auth_service.create_access_token(subject=str(test_user.id))
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def admin_auth_headers(admin_user: User) -> dict[str, str]:
    """Get auth headers for admin user."""
    auth_service = AuthService()
    token = auth_service.create_access_token(subject=str(admin_user.id))
    return {"Authorization": f"Bearer {token}"}


async def get_auth_headers(user: User) -> dict[str, str]:
    """Helper to get auth headers for any user."""
    auth_service = AuthService()
    token = auth_service.create_access_token(subject=str(user.id))
    return {"Authorization": f"Bearer {token}"}


# ============ Mock Implementations ============


class MockStorageBackend:
    """Mock storage backend for testing."""

    def __init__(self):
        self.files: dict[str, bytes] = {}

    async def upload(self, key: str, data: bytes) -> str:
        self.files[key] = data
        return f"mock://{key}"

    async def download(self, key: str) -> bytes | None:
        return self.files.get(key)

    async def delete(self, key: str) -> None:
        self.files.pop(key, None)

    async def exists(self, key: str) -> bool:
        return key in self.files


class MockEmailBackend:
    """Mock email backend for testing."""

    def __init__(self):
        self.sent_emails: list[dict] = []

    async def send(
        self,
        to: str,
        subject: str,
        body: str,
        html: str | None = None,
    ) -> bool:
        self.sent_emails.append({
            "to": to,
            "subject": subject,
            "body": body,
            "html": html,
        })
        return True

    def get_last_email(self) -> dict | None:
        return self.sent_emails[-1] if self.sent_emails else None

    def clear(self) -> None:
        self.sent_emails.clear()


class MockCacheBackend:
    """Mock cache backend for testing."""

    def __init__(self):
        self.data: dict[str, any] = {}

    async def get(self, key: str) -> any:
        return self.data.get(key)

    async def set(self, key: str, value: any, ttl: int | None = None) -> None:
        self.data[key] = value

    async def delete(self, key: str) -> None:
        self.data.pop(key, None)

    async def clear(self) -> None:
        self.data.clear()


@pytest.fixture
def mock_storage() -> MockStorageBackend:
    return MockStorageBackend()


@pytest.fixture
def mock_email() -> MockEmailBackend:
    return MockEmailBackend()


@pytest.fixture
def mock_cache() -> MockCacheBackend:
    return MockCacheBackend()
