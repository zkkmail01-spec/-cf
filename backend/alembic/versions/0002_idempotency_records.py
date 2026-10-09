"""Add idempotency records."""

from alembic import op
import sqlalchemy as sa


revision = "0002_idempotency_records"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "idempotency_records",
        sa.Column("family_id", sa.String(36), nullable=False),
        sa.Column("openid", sa.String(128), nullable=False),
        sa.Column("key", sa.String(128), nullable=False),
        sa.Column("request_fingerprint", sa.String(64), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=False),
        sa.Column("response_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.String(36), primary_key=True),
        sa.ForeignKeyConstraint(["family_id"], ["families.id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "family_id", "openid", "key", name="uq_idempotency_actor_key"
        ),
    )
    op.create_index(
        "ix_idempotency_records_family_id", "idempotency_records", ["family_id"]
    )


def downgrade() -> None:
    op.drop_table("idempotency_records")
