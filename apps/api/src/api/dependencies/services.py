"""
Service dependencies.
"""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from .database import get_db
from src.services.user import UserService


async def get_user_service(db: AsyncSession = Depends(get_db)) -> UserService:
    """Get user service instance."""
    return UserService(db)
