"""Minimal foundation persistence; later C runtime adds events/outbox/authorization.

Source checkpoint and source record models intentionally share one database so
runtime can commit them atomically. JSON payloads store validated DTO snapshots;
typed identity/time columns support constraints and restart-safe queries.
"""

from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class SourceRecordRow(Base):
    __tablename__ = "source_records"
    __table_args__ = (
        UniqueConstraint(
            "source_id", "external_id", "revision", name="uq_source_external_revision"
        ),
        CheckConstraint("revision >= 1", name="ck_source_positive_revision"),
        CheckConstraint("length(content_hash) = 64", name="ck_source_hash_length"),
    )

    record_id: Mapped[str] = mapped_column(String(160), primary_key=True)
    revision: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[str] = mapped_column(String(160), nullable=False)
    external_id: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    discovered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_fixture: Mapped[bool] = mapped_column(Boolean, nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    processing_state: Mapped[str] = mapped_column(
        String(32), nullable=False, server_default="pending"
    )


class SourceCheckpointRow(Base):
    __tablename__ = "source_checkpoints"

    source_id: Mapped[str] = mapped_column(String(160), primary_key=True)
    cursor: Mapped[str | None] = mapped_column(Text)
    watermark: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expected_next_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    gap_state: Mapped[str] = mapped_column(String(32), nullable=False)
    gap_reason: Mapped[str | None] = mapped_column(Text)


class BusinessConfigRow(Base):
    __tablename__ = "business_config"
    __table_args__ = (CheckConstraint("id = 1", name="ck_single_team_config"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
