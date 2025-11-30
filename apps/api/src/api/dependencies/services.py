"""
Service dependencies.
"""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from .database import get_db
from src.services.user import UserService
from src.services.org import OrgService
from src.services.project import ProjectService
from src.services.api_key import APIKeyService


async def get_user_service(db: AsyncSession = Depends(get_db)) -> UserService:
    """Get user service instance."""
    return UserService(db)


async def get_org_service(db: AsyncSession = Depends(get_db)) -> OrgService:
    """Get organization service instance."""
    return OrgService(db)


async def get_project_service(db: AsyncSession = Depends(get_db)) -> ProjectService:
    """Get project service instance."""
    return ProjectService(db)


async def get_api_key_service(db: AsyncSession = Depends(get_db)) -> APIKeyService:
    """Get API key service instance."""
    return APIKeyService(db)
