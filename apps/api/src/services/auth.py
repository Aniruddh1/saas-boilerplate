"""
Authentication service.
"""

from datetime import datetime, timedelta
from uuid import UUID
from dataclasses import dataclass
from passlib.context import CryptContext
from jose import jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.core.config import settings
from src.core.hooks.manager import hooks
from src.models.user import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@dataclass
class TokenPair:
    """Access and refresh token pair."""
    access_token: str
    refresh_token: str


class AuthService:
    """Authentication service."""

    def __init__(self, db: AsyncSession):
        self.db = db

    def hash_password(self, password: str) -> str:
        """Hash a password."""
        return pwd_context.hash(password)

    def verify_password(self, plain: str, hashed: str) -> bool:
        """Verify password against hash."""
        return pwd_context.verify(plain, hashed)

    def create_access_token(self, user_id: UUID) -> str:
        """Create JWT access token."""
        expire = datetime.utcnow() + timedelta(
            minutes=settings.auth.access_token_expire_minutes
        )
        payload = {
            "sub": str(user_id),
            "exp": expire,
            "type": "access",
        }
        return jwt.encode(
            payload,
            settings.auth.secret_key,
            algorithm=settings.auth.algorithm,
        )

    def create_refresh_token(self, user_id: UUID) -> str:
        """Create JWT refresh token."""
        expire = datetime.utcnow() + timedelta(
            days=settings.auth.refresh_token_expire_days
        )
        payload = {
            "sub": str(user_id),
            "exp": expire,
            "type": "refresh",
        }
        return jwt.encode(
            payload,
            settings.auth.secret_key,
            algorithm=settings.auth.algorithm,
        )

    def create_tokens(self, user_id: UUID) -> TokenPair:
        """Create access and refresh token pair."""
        return TokenPair(
            access_token=self.create_access_token(user_id),
            refresh_token=self.create_refresh_token(user_id),
        )

    async def register(
        self,
        email: str,
        password: str,
        name: str,
    ) -> tuple[User, TokenPair]:
        """Register a new user."""
        # Check if email exists
        stmt = select(User).where(User.email == email)
        result = await self.db.execute(stmt)
        if result.scalar_one_or_none():
            raise ValueError("Email already registered")

        # Create user
        user = User(
            email=email,
            password_hash=self.hash_password(password),
            name=name,
        )
        self.db.add(user)
        await self.db.flush()

        # Trigger hook
        await hooks.trigger("user.created", user=user)

        # Create tokens
        tokens = self.create_tokens(user.id)

        return user, tokens

    async def login(self, email: str, password: str) -> TokenPair | None:
        """Authenticate user and return tokens."""
        stmt = select(User).where(User.email == email)
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user or not self.verify_password(password, user.password_hash):
            await hooks.trigger("auth.failed", email=email)
            return None

        if not user.is_active:
            return None

        # Update last login
        user.last_login_at = datetime.utcnow()
        await self.db.flush()

        # Trigger hook
        await hooks.trigger("auth.login", user=user)

        return self.create_tokens(user.id)

    async def refresh_tokens(self, refresh_token: str) -> TokenPair | None:
        """Refresh access token using refresh token."""
        try:
            payload = jwt.decode(
                refresh_token,
                settings.auth.secret_key,
                algorithms=[settings.auth.algorithm],
            )
            if payload.get("type") != "refresh":
                return None

            user_id = UUID(payload["sub"])
            return self.create_tokens(user_id)

        except Exception:
            return None

    async def logout(self, user_id: UUID) -> None:
        """Logout user (trigger hook, can be used for token blacklisting)."""
        await hooks.trigger("auth.logout", user_id=user_id)
