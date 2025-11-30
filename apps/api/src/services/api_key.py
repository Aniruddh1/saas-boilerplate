"""
API Key service.
"""

import secrets
import hashlib
from datetime import datetime
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.models.api_key import APIKey
from src.models.user import User
from src.models.org import OrgMember
from src.schemas.api_key import APIKeyCreate
from src.core.hooks.manager import hooks


class APIKeyService:
    """API key management service."""

    KEY_LENGTH = 32
    PREFIX_LENGTH = 8

    def __init__(self, db: AsyncSession):
        self.db = db

    def generate_key(self) -> tuple[str, str, str]:
        """Generate API key. Returns (full_key, prefix, hash)."""
        key = secrets.token_urlsafe(self.KEY_LENGTH)
        prefix = key[:self.PREFIX_LENGTH]
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        return key, prefix, key_hash

    def hash_key(self, key: str) -> str:
        """Hash an API key."""
        return hashlib.sha256(key.encode()).hexdigest()

    async def get_by_id(self, key_id: UUID) -> APIKey | None:
        """Get API key by ID."""
        stmt = select(APIKey).where(APIKey.id == key_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_key(self, key: str) -> APIKey | None:
        """Get API key by full key value."""
        key_hash = self.hash_key(key)
        stmt = select(APIKey).where(APIKey.key_hash == key_hash)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create(
        self,
        data: APIKeyCreate,
        created_by: UUID,
    ) -> tuple[str, APIKey]:
        """Create API key. Returns (full_key, api_key_record)."""
        full_key, prefix, key_hash = self.generate_key()

        api_key = APIKey(
            key_prefix=prefix,
            key_hash=key_hash,
            name=data.name,
            description=data.description,
            key_type=data.key_type,
            org_id=data.org_id,
            project_id=data.project_id,
            actions=data.actions,
            resources=data.resources,
            rate_limit=data.rate_limit,
            expires_at=data.expires_at,
            created_by=created_by,
        )
        self.db.add(api_key)
        await self.db.flush()

        await hooks.trigger("api_key.created", api_key=api_key)

        return full_key, api_key

    async def revoke(self, key_id: UUID) -> bool:
        """Revoke (delete) API key."""
        api_key = await self.get_by_id(key_id)
        if not api_key:
            return False

        await self.db.delete(api_key)
        await self.db.flush()
        return True

    async def rotate(self, key_id: UUID) -> tuple[str, APIKey] | tuple[None, None]:
        """Rotate API key (generate new key, keep settings)."""
        api_key = await self.get_by_id(key_id)
        if not api_key:
            return None, None

        # Generate new key
        full_key, prefix, key_hash = self.generate_key()
        api_key.key_prefix = prefix
        api_key.key_hash = key_hash
        api_key.use_count = 0
        api_key.last_used_at = None

        await self.db.flush()
        return full_key, api_key

    async def authenticate(self, key: str) -> User | None:
        """Authenticate with API key. Returns associated user or None."""
        api_key = await self.get_by_key(key)
        if not api_key:
            return None

        if api_key.is_expired:
            return None

        # Update usage stats
        api_key.last_used_at = datetime.utcnow()
        api_key.use_count += 1
        await self.db.flush()

        # Get creator user
        stmt = select(User).where(User.id == api_key.created_by)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_for_user(
        self,
        user_id: UUID,
        org_id: UUID | None = None,
        project_id: UUID | None = None,
    ) -> list[APIKey]:
        """List API keys accessible to user."""
        # Get user's org IDs
        stmt = select(OrgMember.org_id).where(OrgMember.user_id == user_id)
        result = await self.db.execute(stmt)
        user_org_ids = [row[0] for row in result.all()]

        # Query keys in those orgs
        stmt = select(APIKey).where(APIKey.org_id.in_(user_org_ids))

        if org_id:
            stmt = stmt.where(APIKey.org_id == org_id)
        if project_id:
            stmt = stmt.where(APIKey.project_id == project_id)

        result = await self.db.execute(stmt)
        return list(result.scalars().all())
