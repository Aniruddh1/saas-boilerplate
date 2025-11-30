"""
API routes aggregation.
"""

from fastapi import APIRouter

from .auth import router as auth_router
from .users import router as users_router
from .orgs import router as orgs_router
from .projects import router as projects_router
from .api_keys import router as api_keys_router
from .webhooks import router as webhooks_router
from .audit_logs import router as audit_logs_router

router = APIRouter()

router.include_router(auth_router, prefix="/auth", tags=["auth"])
router.include_router(users_router, prefix="/users", tags=["users"])
router.include_router(orgs_router, prefix="/orgs", tags=["organizations"])
router.include_router(projects_router, prefix="/projects", tags=["projects"])
router.include_router(api_keys_router, prefix="/api-keys", tags=["api-keys"])
router.include_router(webhooks_router)
router.include_router(audit_logs_router)
