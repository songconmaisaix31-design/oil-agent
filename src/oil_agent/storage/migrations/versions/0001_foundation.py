"""Create minimal source persistence and explicit safe business defaults.

This migration is self-contained: it never imports mutable DTO or ORM models.
It does not create events/outbox or implement runtime transactional processing.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001_foundation"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "source_records",
        sa.Column("record_id", sa.String(160), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("source_id", sa.String(160), nullable=False),
        sa.Column("external_id", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("discovered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_fixture", sa.Boolean(), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("processing_state", sa.String(32), nullable=False, server_default="pending"),
        sa.PrimaryKeyConstraint("record_id", "revision"),
        sa.UniqueConstraint(
            "source_id", "external_id", "revision", name="uq_source_external_revision"
        ),
        sa.CheckConstraint("revision >= 1", name="ck_source_positive_revision"),
        sa.CheckConstraint("length(content_hash) = 64", name="ck_source_hash_length"),
    )
    op.create_table(
        "source_checkpoints",
        sa.Column("source_id", sa.String(160), primary_key=True),
        sa.Column("cursor", sa.Text()),
        sa.Column("watermark", sa.DateTime(timezone=True)),
        sa.Column("last_success_at", sa.DateTime(timezone=True)),
        sa.Column("expected_next_at", sa.DateTime(timezone=True)),
        sa.Column("gap_state", sa.String(32), nullable=False),
        sa.Column("gap_reason", sa.Text()),
    )
    config = op.create_table(
        "business_config",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.CheckConstraint("id = 1", name="ck_single_team_config"),
    )
    op.bulk_insert(
        config,
        [
            {
                "id": 1,
                "revision": 1,
                "payload": {
                    "regions": [],
                    "products": [],
                    "suppliers": [],
                    "watched_events": [],
                    "recipient_ids": [],
                    "first_report_policy": None,
                    "report_time": "06:00:00",
                    "report_timezone": "Asia/Shanghai",
                    "reminders_enabled": False,
                    "sms_enabled": False,
                    "phone_enabled": False,
                    "outbound_mode": "dry_run",
                },
            }
        ],
    )


def downgrade():
    op.drop_table("business_config")
    op.drop_table("source_checkpoints")
    op.drop_table("source_records")
