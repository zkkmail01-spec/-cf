"""Initial family menu schema."""

from alembic import op
import sqlalchemy as sa


revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "families",
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("owner_openid", sa.String(128), nullable=False),
        sa.Column("avatar_file_id", sa.String(512)),
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_families_owner_openid", "families", ["owner_openid"])
    op.create_table(
        "family_members",
        sa.Column("family_id", sa.String(36), nullable=False),
        sa.Column("openid", sa.String(128), nullable=False),
        sa.Column("nickname", sa.String(80), nullable=False),
        sa.Column("avatar_url", sa.String(1024)),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.String(36), primary_key=True),
        sa.ForeignKeyConstraint(["family_id"], ["families.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("family_id", "openid", name="uq_family_member_openid"),
        sa.CheckConstraint("role IN ('chef', 'member')", name="ck_member_role"),
        sa.CheckConstraint("status IN ('active', 'left')", name="ck_member_status"),
    )
    op.create_index(
        "ix_family_members_openid_status", "family_members", ["openid", "status"]
    )
    op.create_table(
        "dish_categories",
        sa.Column("family_id", sa.String(36), nullable=False),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["family_id"], ["families.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("family_id", "name", name="uq_category_family_name"),
    )
    op.create_index("ix_dish_categories_family_id", "dish_categories", ["family_id"])
    op.create_table(
        "dishes",
        sa.Column("family_id", sa.String(36), nullable=False),
        sa.Column("category_id", sa.String(36), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("image_file_id", sa.String(512)),
        sa.Column("description", sa.Text()),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_by", sa.String(128), nullable=False),
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["family_id"], ["families.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["category_id"], ["dish_categories.id"]),
        sa.UniqueConstraint("family_id", "name", name="uq_dish_family_name"),
    )
    op.create_index("ix_dishes_family_id", "dishes", ["family_id"])
    op.create_index("ix_dishes_category_id", "dishes", ["category_id"])
    op.create_table(
        "dish_ingredients",
        sa.Column("dish_id", sa.String(36), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("quantity", sa.Numeric(12, 3), nullable=False),
        sa.Column("unit", sa.String(32), nullable=False),
        sa.Column("note", sa.String(255)),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("id", sa.String(36), primary_key=True),
        sa.ForeignKeyConstraint(["dish_id"], ["dishes.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_dish_ingredients_dish_id", "dish_ingredients", ["dish_id"])
    op.create_table(
        "meal_orders",
        sa.Column("family_id", sa.String(36), nullable=False),
        sa.Column("meal_date", sa.Date(), nullable=False),
        sa.Column("meal_type", sa.String(16), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["family_id"], ["families.id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "family_id", "meal_date", "meal_type", name="uq_meal_family_date_type"
        ),
        sa.CheckConstraint(
            "meal_type IN ('breakfast', 'lunch', 'dinner')", name="ck_meal_type"
        ),
    )
    op.create_index("ix_meal_orders_family_id", "meal_orders", ["family_id"])
    op.create_index("ix_meal_orders_meal_date", "meal_orders", ["meal_date"])
    op.create_table(
        "meal_order_items",
        sa.Column("meal_order_id", sa.String(36), nullable=False),
        sa.Column("dish_id", sa.String(36)),
        sa.Column("dish_name", sa.String(120), nullable=False),
        sa.Column("image_file_id", sa.String(512)),
        sa.Column("category_name", sa.String(80), nullable=False),
        sa.Column("ingredients_snapshot", sa.JSON(), nullable=False),
        sa.Column("id", sa.String(36), primary_key=True),
        sa.ForeignKeyConstraint(["meal_order_id"], ["meal_orders.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("meal_order_id", "dish_id", name="uq_meal_item_dish"),
    )
    op.create_index("ix_meal_order_items_meal_order_id", "meal_order_items", ["meal_order_id"])
    op.create_table(
        "meal_item_selectors",
        sa.Column("meal_order_item_id", sa.String(36), nullable=False),
        sa.Column("openid", sa.String(128), nullable=False),
        sa.Column("nickname", sa.String(80), nullable=False),
        sa.Column("selected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.String(36), primary_key=True),
        sa.ForeignKeyConstraint(
            ["meal_order_item_id"], ["meal_order_items.id"], ondelete="CASCADE"
        ),
        sa.UniqueConstraint(
            "meal_order_item_id", "openid", name="uq_meal_item_selector_openid"
        ),
    )
    op.create_index(
        "ix_meal_item_selectors_meal_order_item_id",
        "meal_item_selectors",
        ["meal_order_item_id"],
    )
    op.create_table(
        "invitations",
        sa.Column("family_id", sa.String(36), nullable=False),
        sa.Column("created_by", sa.String(128), nullable=False),
        sa.Column("code_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("max_uses", sa.Integer(), nullable=False),
        sa.Column("used_count", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.String(36), primary_key=True),
        sa.ForeignKeyConstraint(["family_id"], ["families.id"], ondelete="CASCADE"),
        sa.CheckConstraint(
            "status IN ('active', 'revoked', 'expired')", name="ck_invitation_status"
        ),
    )
    op.create_index("ix_invitations_family_id", "invitations", ["family_id"])
    op.create_index("ix_invitations_expires_at", "invitations", ["expires_at"])
    op.create_table(
        "shopping_checks",
        sa.Column("family_id", sa.String(36), nullable=False),
        sa.Column("range_start", sa.Date(), nullable=False),
        sa.Column("range_end", sa.Date(), nullable=False),
        sa.Column("checked_keys", sa.JSON(), nullable=False),
        sa.Column("updated_by", sa.String(128), nullable=False),
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["family_id"], ["families.id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "family_id", "range_start", "range_end", name="uq_shopping_family_range"
        ),
    )
    op.create_index("ix_shopping_checks_family_id", "shopping_checks", ["family_id"])


def downgrade() -> None:
    for table in [
        "shopping_checks",
        "invitations",
        "meal_item_selectors",
        "meal_order_items",
        "meal_orders",
        "dish_ingredients",
        "dishes",
        "dish_categories",
        "family_members",
        "families",
    ]:
        op.drop_table(table)
