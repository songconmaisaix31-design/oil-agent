"""PostgreSQL runtime persistence for evidence, revisions, outbox and authorization.

Source checkpoint and source record models intentionally share one database so
runtime can commit them atomically. JSON payloads store validated DTO snapshots;
typed identity/time columns support constraints and restart-safe queries.
"""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
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
    attempt: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    lease_token: Mapped[str | None] = mapped_column(String(64))
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_code: Mapped[str | None] = mapped_column(String(64))


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


class UserRow(Base):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("provider", "provider_subject", name="uq_user_identity"),)
    actor_id: Mapped[str] = mapped_column(String(160), primary_key=True)
    recipient_id: Mapped[str] = mapped_column(String(160), unique=True, nullable=False)
    provider: Mapped[str] = mapped_column(String(160), nullable=False)
    provider_subject: Mapped[str] = mapped_column(String(200), nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False)
    is_test_recipient: Mapped[bool] = mapped_column(Boolean, nullable=False)


class SessionRow(Base):
    __tablename__ = "sessions"
    session_id: Mapped[str] = mapped_column(String(160), primary_key=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    csrf_token: Mapped[str] = mapped_column(String(128), nullable=False)
    actor_id: Mapped[str] = mapped_column(ForeignKey("users.actor_id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    authentication_scope: Mapped[str | None] = mapped_column(String(160))


class LoginStateRow(Base):
    __tablename__ = "login_states"
    state_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    browser_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SubjectRow(Base):
    """Stable explicit candidate family or timezone/date report identity."""

    __tablename__ = "subjects"
    subject_id: Mapped[str] = mapped_column(String(160), primary_key=True)
    identity_key: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    current_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    report_date: Mapped[object | None] = mapped_column(Date)
    timezone: Mapped[str | None] = mapped_column(String(64))
    build_token: Mapped[str | None] = mapped_column(String(64))
    build_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class VersionRow(Base):
    __tablename__ = "subject_versions"
    subject_id: Mapped[str] = mapped_column(ForeignKey("subjects.subject_id"), primary_key=True)
    revision: Mapped[int] = mapped_column(Integer, primary_key=True)
    decision_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class EvidenceRow(Base):
    __tablename__ = "subject_evidence"
    __table_args__ = (
        ForeignKeyConstraint(
            ["subject_id", "revision"], ["subject_versions.subject_id", "subject_versions.revision"]
        ),
        ForeignKeyConstraint(
            ["record_id", "record_revision"],
            ["source_records.record_id", "source_records.revision"],
        ),
    )
    subject_id: Mapped[str] = mapped_column(String(160), primary_key=True)
    revision: Mapped[int] = mapped_column(Integer, primary_key=True)
    record_id: Mapped[str] = mapped_column(String(160), primary_key=True)
    record_revision: Mapped[int] = mapped_column(Integer, primary_key=True)


class AuthorizationRow(Base):
    __tablename__ = "recipient_authorizations"
    __table_args__ = (
        ForeignKeyConstraint(
            ["subject_id", "revision"], ["subject_versions.subject_id", "subject_versions.revision"]
        ),
    )
    subject_id: Mapped[str] = mapped_column(String(160), primary_key=True)
    revision: Mapped[int] = mapped_column(Integer, primary_key=True)
    recipient_id: Mapped[str] = mapped_column(ForeignKey("users.recipient_id"), primary_key=True)
    authorization_id: Mapped[str] = mapped_column(String(160), unique=True, nullable=False)
    authorized_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False)
    reminders_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False)


class IntentRow(Base):
    __tablename__ = "notification_intents"
    __table_args__ = (
        UniqueConstraint(
            "subject_id",
            "revision",
            "recipient_id",
            "kind",
            "channel",
            name="uq_intent_business_key",
        ),
        ForeignKeyConstraint(
            ["subject_id", "revision", "recipient_id"],
            [
                "recipient_authorizations.subject_id",
                "recipient_authorizations.revision",
                "recipient_authorizations.recipient_id",
            ],
        ),
    )
    intent_id: Mapped[str] = mapped_column(String(160), primary_key=True)
    subject_id: Mapped[str] = mapped_column(String(160), nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    recipient_id: Mapped[str] = mapped_column(String(160), nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    channel: Mapped[str] = mapped_column(String(32), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class DeliveryRow(Base):
    __tablename__ = "deliveries"
    delivery_id: Mapped[str] = mapped_column(String(160), primary_key=True)
    intent_id: Mapped[str] = mapped_column(
        ForeignKey("notification_intents.intent_id"), nullable=False, unique=True
    )
    state: Mapped[str] = mapped_column(String(32), nullable=False)
    attempt: Mapped[int] = mapped_column(Integer, nullable=False)
    lease_token: Mapped[str | None] = mapped_column(String(64))
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    platform_message_id: Mapped[str | None] = mapped_column(String(256))
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(64))


class AckRow(Base):
    __tablename__ = "acknowledgements"
    ack_id: Mapped[str] = mapped_column(String(160), primary_key=True)
    delivery_id: Mapped[str] = mapped_column(ForeignKey("deliveries.delivery_id"), nullable=False)
    callback_id: Mapped[str] = mapped_column(String(160), unique=True, nullable=False)
    actor_id: Mapped[str] = mapped_column(ForeignKey("users.actor_id"), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)


class FeedbackRow(Base):
    __tablename__ = "feedback"
    feedback_id: Mapped[str] = mapped_column(String(160), primary_key=True)
    actor_id: Mapped[str] = mapped_column(ForeignKey("users.actor_id"), nullable=False)
    subject_id: Mapped[str] = mapped_column(String(160), nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)


class AuditRow(Base):
    __tablename__ = "audit_log"
    audit_id: Mapped[str] = mapped_column(String(160), primary_key=True)
    actor_id: Mapped[str | None] = mapped_column(String(160))
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    object_id: Mapped[str] = mapped_column(String(160), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    details: Mapped[dict] = mapped_column(JSONB, nullable=False)


class PreviewRow(Base):
    __tablename__ = "quote_previews"
    preview_id: Mapped[str] = mapped_column(String(160), primary_key=True)
    actor_id: Mapped[str] = mapped_column(ForeignKey("users.actor_id"), nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    source_records: Mapped[list] = mapped_column(JSONB, nullable=False)
    import_result: Mapped[dict | None] = mapped_column(JSONB)


class ObservationRow(Base):
    __tablename__ = "market_observations"
    observation_id: Mapped[str] = mapped_column(String(160), primary_key=True)
    revision: Mapped[int] = mapped_column(Integer, primary_key=True)
    value: Mapped[object] = mapped_column(Numeric(20, 6), nullable=False)
    as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    record_id: Mapped[str] = mapped_column(String(160), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)


class BudgetRow(Base):
    __tablename__ = "budget_counters"
    day: Mapped[object] = mapped_column(Date, primary_key=True)
    bucket: Mapped[str] = mapped_column(String(160), primary_key=True)
    used: Mapped[int] = mapped_column(Integer, nullable=False)


class RuntimeHealthRow(Base):
    __tablename__ = "runtime_health"
    component: Mapped[str] = mapped_column(String(160), primary_key=True)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    detail: Mapped[str | None] = mapped_column(String(128))


class PermissionRow(Base):
    """One immutable nonsecret approval scope; changing settings cannot reset its budget."""

    __tablename__ = "permission_scopes"
    approval_id: Mapped[str] = mapped_column(String(160), primary_key=True)
    scope_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    blocked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class ProviderCallRow(Base):
    """Conservative reservation and optional reported usage; no prompt/credential content."""

    __tablename__ = "provider_calls"
    __table_args__ = (
        CheckConstraint("reserved_tokens >= 0", name="ck_call_reservation_nonnegative"),
    )
    reservation_id: Mapped[str] = mapped_column(String(160), primary_key=True)
    approval_id: Mapped[str] = mapped_column(
        ForeignKey("permission_scopes.approval_id"), nullable=False
    )
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reserved_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    input_tokens: Mapped[int | None] = mapped_column(Integer)
    output_tokens: Mapped[int | None] = mapped_column(Integer)
    usage_recorded: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
