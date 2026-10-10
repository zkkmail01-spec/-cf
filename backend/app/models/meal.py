from datetime import date, datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, utc_now


class MealOrder(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "meal_orders"
    __table_args__ = (
        UniqueConstraint(
            "family_id", "meal_date", "meal_type", name="uq_meal_family_date_type"
        ),
        CheckConstraint(
            "meal_type IN ('breakfast', 'lunch', 'dinner')",
            name="ck_meal_type",
        ),
    )

    family_id: Mapped[str] = mapped_column(
        ForeignKey("families.id", ondelete="CASCADE"), nullable=False, index=True
    )
    meal_date: Mapped[date] = mapped_column(nullable=False, index=True)
    meal_type: Mapped[str] = mapped_column(String(16), nullable=False)
    version: Mapped[int] = mapped_column(default=1, nullable=False)

    family: Mapped["Family"] = relationship(back_populates="meal_orders")
    items: Mapped[list["MealOrderItem"]] = relationship(
        back_populates="meal_order", cascade="all, delete-orphan"
    )


class MealOrderItem(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "meal_order_items"
    __table_args__ = (
        UniqueConstraint("meal_order_id", "dish_id", name="uq_meal_item_dish"),
    )

    meal_order_id: Mapped[str] = mapped_column(
        ForeignKey("meal_orders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    dish_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    dish_name: Mapped[str] = mapped_column(String(120), nullable=False)
    image_file_id: Mapped[str | None] = mapped_column(String(512))
    category_name: Mapped[str] = mapped_column(String(80), nullable=False)
    ingredients_snapshot: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, default=list, nullable=False
    )

    meal_order: Mapped[MealOrder] = relationship(back_populates="items")
    selectors: Mapped[list["MealItemSelector"]] = relationship(
        back_populates="meal_order_item", cascade="all, delete-orphan"
    )


class MealItemSelector(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "meal_item_selectors"
    __table_args__ = (
        UniqueConstraint(
            "meal_order_item_id", "openid", name="uq_meal_item_selector_openid"
        ),
    )

    meal_order_item_id: Mapped[str] = mapped_column(
        ForeignKey("meal_order_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    openid: Mapped[str] = mapped_column(String(128), nullable=False)
    nickname: Mapped[str] = mapped_column(String(80), nullable=False)
    selected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    meal_order_item: Mapped[MealOrderItem] = relationship(back_populates="selectors")
