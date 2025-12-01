"""
API routes aggregation.
"""

from fastapi import APIRouter

from .auth import router as auth_router
from .users import router as users_router
from .audit_logs import router as audit_logs_router
from .features import router as features_router
from .notifications import router as notifications_router

router = APIRouter()

router.include_router(auth_router, prefix="/auth", tags=["auth"])
router.include_router(users_router, prefix="/users", tags=["users"])
router.include_router(audit_logs_router, prefix="/audit-logs", tags=["audit-logs"])
router.include_router(features_router, prefix="/features", tags=["features"])
router.include_router(notifications_router, prefix="/notifications", tags=["notifications"])

# To enable auth test endpoints (for development/testing), see:
# examples/auth_test_routes.py
