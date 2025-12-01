"""
Feature Flag Models - SQLAlchemy models for feature flags.

Tables:
- feature_flags: Flag definitions with targeting rules
- user_feature_groups: User-to-group membership
- feature_flag_overrides: Individual user overrides
"""

from datetime import datetime
from uuid import UUID, uuid4
from sqlalchemy import String, Integer, Boolean, Text, ForeignKey, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB

from src.models.base import Base, TimestampMixin


class FeatureFlagModel(Base, TimestampMixin):
    """
    Feature flag definition.

    Stores the flag configuration and targeting rules.
    """

    __tablename__ = "feature_flags"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    key: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Global settings
    enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    percentage: Mapped[int] = mapped_column(Integer, default=100, nullable=False)

    # Targeting conditions (attributes, groups)
    # Example: {"attributes": {"tier": ["premium"]}, "groups": ["beta"]}
    conditions: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    # Metadata
    created_by_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    def __repr__(self) -> str:
        status = "ON" if self.enabled else "OFF"
        return f"<FeatureFlag {self.key} [{status}]>"


class UserFeatureGroup(Base):
    """
    User membership in feature groups.

    Groups are used for targeting specific cohorts:
    - beta_testers
    - internal_users
    - early_adopters
    """

    __tablename__ = "user_feature_groups"
    __table_args__ = (
        Index("idx_user_feature_groups_group", "group_name"),
    )

    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    group_name: Mapped[str] = mapped_column(
        String(100),
        primary_key=True,
    )
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )
    added_by_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    def __repr__(self) -> str:
        return f"<UserFeatureGroup {self.user_id} in {self.group_name}>"


class FeatureFlagOverride(Base):
    """
    Individual user override for a feature flag.

    Overrides have highest priority:
    - enabled=True: Force feature ON for user
    - enabled=False: Force feature OFF for user

    Use cases:
    - VIP customers get early access
    - Disable buggy feature for affected user
    - Testing features for specific accounts
    """

    __tablename__ = "feature_flag_overrides"
    __table_args__ = (
        Index("idx_feature_flag_overrides_flag", "flag_key"),
    )

    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    flag_key: Mapped[str] = mapped_column(
        String(100),
        primary_key=True,
    )
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False)
    reason: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Optional expiration
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )
    created_by_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    @property
    def is_expired(self) -> bool:
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at

    def __repr__(self) -> str:
        status = "ON" if self.enabled else "OFF"
        return f"<FeatureFlagOverride {self.flag_key}={status} for {self.user_id}>"
