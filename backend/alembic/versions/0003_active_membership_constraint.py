"""Enforce one active family membership per WeChat identity."""

from alembic import op
import sqlalchemy as sa


revision = "0003_active_membership_constraint"
down_revision = "0002_idempotency_records"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "uq_family_members_active_openid",
        "family_members",
        ["openid"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
        sqlite_where=sa.text("status = 'active'"),
    )


def downgrade() -> None:
    op.drop_index("uq_family_members_active_openid", table_name="family_members")
