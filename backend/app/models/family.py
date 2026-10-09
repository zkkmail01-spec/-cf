from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, utc_now


class Family(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "families"

    name: Mapped[str] = mapped_column(String(80), nullable=False)
    owner_openid: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    avatar_file_id: Mapped[str | None] = mapped_column(String(512))

    members: Mapped[list["FamilyMember"]] = relationship(
        back_populates="family", cascade="all, delete-orphan"
    )
    meal_orders: Mapped[list["MealOrder"]] = relationship(
        back_populates="family", cascade="all, delete-orphan"
    )


class FamilyMember(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "family_members"
    __table_args__ = (
        UniqueConstraint("family_id", "openid", name="uq_family_member_openid"),
        CheckConstraint("role IN ('chef', 'member')", name="ck_member_role"),
        CheckConstraint("status IN ('active', 'left')", name="ck_member_status"),
        Index("ix_family_members_openid_status", "openid", "status"),
    )

    family_id: Mapped[str] = mapped_column(
        ForeignKey("families.id", ondelete="CASCADE"), nullable=False
    )
    openid: Mapped[str] = mapped_column(String(128), nullable=False)
    nickname: Mapped[str] = mapped_column(String(80), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(1024))
    role: Mapped[str] = mapped_column(String(16), nullable=False, default="member")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")
    joined_at: Mapped[datetime] = mapped_column(default=utc_now, nullable=False)

    family: Mapped[Family] = relationship(back_populates="members")
