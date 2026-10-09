from datetime import date

from sqlalchemy import ForeignKey, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ShoppingCheck(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "shopping_checks"
    __table_args__ = (
        UniqueConstraint(
            "family_id", "range_start", "range_end", name="uq_shopping_family_range"
        ),
    )

    family_id: Mapped[str] = mapped_column(
        ForeignKey("families.id", ondelete="CASCADE"), nullable=False, index=True
    )
    range_start: Mapped[date] = mapped_column(nullable=False)
    range_end: Mapped[date] = mapped_column(nullable=False)
    checked_keys: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    updated_by: Mapped[str] = mapped_column(String(128), nullable=False)
