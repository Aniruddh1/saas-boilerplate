"""
Feature Flag System.

Progressive complexity feature flags with:
- Percentage rollouts
- Attribute targeting
- Group membership
- Individual overrides

Usage Levels:

Level 1 - Simple global check:
    from src.core.features import Feature

    @router.get("/dashboard")
    async def dashboard(feature: Feature):
        if await feature.is_enabled("new_dashboard"):
            return new_data()
        return old_data()

Level 2 - User-targeted:
    from src.core.features import UserFeature

    @router.get("/analytics")
    async def analytics(feature: UserFeature):
        if await feature.is_enabled("advanced_analytics"):
            return advanced_data()
        return basic_data()

Level 3 - Decorator style:
    from src.core.features import require_feature

    @router.get("/beta")
    @require_feature("beta_feature")
    async def beta_endpoint(feature: UserFeature):
        return beta_data()

Level 4 - With targeting:
    # In admin panel, create flag with conditions:
    # {
    #     "key": "premium_reports",
    #     "enabled": true,
    #     "conditions": {
    #         "attributes": {"tier": ["premium", "enterprise"]},
    #         "groups": ["beta_testers"]
    #     }
    # }

Level 5 - Management:
    @router.post("/admin/features")
    async def create_feature(feature: Feature, admin: AdminUser):
        await feature.create_flag(
            key="new_feature",
            name="New Feature",
            enabled=True,
            percentage=10,  # 10% rollout
        )
"""

from .interfaces import (
    FeatureFlag,
    FeatureOverride,
    EvaluationResult,
    FeatureBackend,
    FeatureServiceBase,
)

from .service import FeatureService

from .dependencies import (
    Feature,
    UserFeature,
    get_feature_service,
    get_user_feature_service,
    get_feature_backend,
    is_feature_enabled,
)

from .decorators import (
    require_feature,
    feature_variant,
)

from .backends import (
    DatabaseFeatureBackend,
    MemoryFeatureBackend,
)

__all__ = [
    # Interfaces
    "FeatureFlag",
    "FeatureOverride",
    "EvaluationResult",
    "FeatureBackend",
    "FeatureServiceBase",
    # Service
    "FeatureService",
    # Dependencies
    "Feature",
    "UserFeature",
    "get_feature_service",
    "get_user_feature_service",
    "get_feature_backend",
    "is_feature_enabled",
    # Decorators
    "require_feature",
    "feature_variant",
    # Backends
    "DatabaseFeatureBackend",
    "MemoryFeatureBackend",
]
