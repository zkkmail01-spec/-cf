from decimal import Decimal

from sqlalchemy import Boolean, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class DishCategory(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "dish_categories"
    __table_args__ = (
        UniqueConstraint("family_id", "name", name="uq_category_family_name"),
    )

    family_id: Mapped[str] = mapped_column(
        ForeignKey("families.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    sort_order: Mapped[int] = mapped_column(default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    dishes: Mapped[list["Dish"]] = relationship(back_populates="category")


class Dish(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "dishes"
    __table_args__ = (
        UniqueConstraint("family_id", "name", name="uq_dish_family_name"),
    )

    family_id: Mapped[str] = mapped_column(
        ForeignKey("families.id", ondelete="CASCADE"), nullable=False, index=True
    )
    category_id: Mapped[str] = mapped_column(
        ForeignKey("dish_categories.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    image_file_id: Mapped[str | None] = mapped_column(String(512))
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_by: Mapped[str] = mapped_column(String(128), nullable=False)

    category: Mapped[DishCategory] = relationship(back_populates="dishes")
    ingredients: Mapped[list["DishIngredient"]] = relationship(
        back_populates="dish",
        cascade="all, delete-orphan",
        order_by="DishIngredient.sort_order",
    )


class DishIngredient(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "dish_ingredients"

    dish_id: Mapped[str] = mapped_column(
        ForeignKey("dishes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    unit: Mapped[str] = mapped_column(String(32), nullable=False)
    note: Mapped[str | None] = mapped_column(String(255))
    sort_order: Mapped[int] = mapped_column(default=0, nullable=False)

    dish: Mapped[Dish] = relationship(back_populates="ingredients")
