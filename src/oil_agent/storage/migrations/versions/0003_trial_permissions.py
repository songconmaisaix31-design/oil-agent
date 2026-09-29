"""Scoped real authentication and durable bounded provider request authorization."""

import sqlalchemy as sa
from alembic import op

revision = "0003_trial"
down_revision = "0002_runtime"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("sessions", sa.Column("authentication_scope", sa.String(160), nullable=True))
    op.create_table(
        "permission_scopes",
        sa.Column("approval_id", sa.String(160), primary_key=True),
        sa.Column("scope_digest", sa.String(64), nullable=False),
        sa.Column("blocked", sa.Boolean(), nullable=False),
    )
    op.create_table(
        "provider_calls",
        sa.Column("reservation_id", sa.String(160), primary_key=True),
        sa.Column(
            "approval_id",
            sa.String(160),
            sa.ForeignKey("permission_scopes.approval_id"),
            nullable=False,
        ),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reserved_tokens", sa.Integer(), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("usage_recorded", sa.Boolean(), nullable=False),
        sa.CheckConstraint("reserved_tokens >= 0", name="ck_call_reservation_nonnegative"),
    )


def downgrade():
    op.drop_table("provider_calls")
    op.drop_table("permission_scopes")
    op.drop_column("sessions", "authentication_scope")
