"""Actor-filtered views, audited configuration and durable quote previews/imports."""

from datetime import timedelta

from sqlalchemy import select, update

from oil_agent.contracts.dto import (
    EventAssessment,
    Feedback,
    MarketObservation,
    NotificationIntent,
    Report,
    SourceRecord,
)
from oil_agent.contracts.http import (
    BusinessConfig,
    EventDetail,
    EventList,
    QuoteImportResult,
    QuotePreview,
    ReportList,
)
from oil_agent.contracts.services import ErrorCode
from oil_agent.storage.base import new_id, reject
from oil_agent.storage.models import (
    AckRow,
    AuthorizationRow,
    BusinessConfigRow,
    DeliveryRow,
    EvidenceRow,
    FeedbackRow,
    IntentRow,
    ObservationRow,
    PreviewRow,
    SourceCheckpointRow,
    SourceRecordRow,
    SubjectRow,
    UserRow,
    VersionRow,
)


class QueryRepository:
    def business_config(self):
        with self.sessions() as session:
            return BusinessConfig.model_validate(session.get(BusinessConfigRow, 1).payload)

    def get_config(self, actor):
        with self.sessions() as session:
            self.check_actor(session, actor, admin=True)
            return BusinessConfig.model_validate(session.get(BusinessConfigRow, 1).payload)

    def update_config(self, actor, config):
        if config.sms_enabled or config.phone_enabled:
            reject(ErrorCode.FORBIDDEN, "Production, SMS and phone gates are not satisfied")
        if config.outbound_mode == "production" and (
            not self.production_gate()
            or not config.first_report_policy
            or not config.recipient_ids
            or config.notification_channel != "feishu"
        ):
            reject(ErrorCode.FORBIDDEN, "Production readiness gates are not satisfied")
        if config.outbound_mode == "dry_run" and config.notification_channel != "dry_run":
            reject(ErrorCode.FORBIDDEN, "Dry-run configuration cannot select a live channel")
        if config.outbound_mode == "trial" and not self.trial_config_gate(config):
            reject(ErrorCode.FORBIDDEN, "Trial configuration exceeds its approved scope")
        with self.sessions.begin() as session:
            self.check_actor(session, actor, admin=True)
            row = session.get(BusinessConfigRow, 1, with_for_update=True)
            valid = set(
                session.scalars(select(UserRow.recipient_id).where(UserRow.active.is_(True)))
            )
            if not set(config.recipient_ids) <= valid:
                reject(ErrorCode.INVALID_INPUT, "Recipients must be active provisioned users")
            removed = set(row.payload["recipient_ids"]) - set(config.recipient_ids)
            session.execute(
                update(AuthorizationRow)
                .where(AuthorizationRow.recipient_id.in_(removed))
                .values(active=False)
            )
            # Disabling reminders stops existing grants as well as future grants.
            if not config.reminders_enabled:
                session.execute(update(AuthorizationRow).values(reminders_enabled=False))
            row.payload = config.model_dump(mode="json")
            row.revision += 1
            self.audit(
                session,
                "config_updated",
                "business_config",
                actor_id=actor.actor_id,
                details={"revision": row.revision, "recipients_removed": len(removed)},
            )
            return config

    def _visible_versions(self, session, actor, kind, *, cursor=None, limit=20):
        self.check_actor(session, actor)
        statement = (
            select(VersionRow)
            .join(SubjectRow)
            .join(
                AuthorizationRow,
                (
                    (AuthorizationRow.subject_id == VersionRow.subject_id)
                    & (AuthorizationRow.revision == VersionRow.revision)
                ),
            )
            .where(
                SubjectRow.kind == kind,
                *self.payload_scope(VersionRow.payload),
                AuthorizationRow.recipient_id == actor.recipient_id,
                AuthorizationRow.active.is_(True),
            )
        )
        if cursor:
            statement = statement.where(VersionRow.subject_id > cursor)
        rows = session.scalars(
            statement.distinct(VersionRow.subject_id)
            .order_by(VersionRow.subject_id, VersionRow.revision.desc())
            .limit(limit + 1)
        ).all()
        return rows[:limit], rows[limit - 1].subject_id if len(rows) > limit else None

    def events(self, actor, *, cursor=None, limit=20):
        with self.sessions() as session:
            rows, next_cursor = self._visible_versions(
                session, actor, "event", cursor=cursor, limit=limit
            )
            items = tuple(EventAssessment.model_validate(row.payload) for row in rows)
            cutoff = max((item.assessed_at for item in items), default=None)
            return EventList(items=items, next_cursor=next_cursor, data_cutoff_at=cutoff)

    def event_detail(self, actor, event_id):
        with self.sessions() as session:
            self.check_actor(session, actor)
            subject = session.get(SubjectRow, event_id)
            if not subject or subject.kind != "event":
                reject(ErrorCode.FORBIDDEN, "Event is not authorized")
            self.require_data_scope(
                EventAssessment.model_validate(
                    session.get(VersionRow, (event_id, subject.current_revision)).payload
                )
            )
            grants = session.scalars(
                select(AuthorizationRow)
                .where(
                    AuthorizationRow.subject_id == event_id,
                    AuthorizationRow.recipient_id == actor.recipient_id,
                    AuthorizationRow.active.is_(True),
                )
                .order_by(AuthorizationRow.revision)
            ).all()
            if not grants:
                reject(ErrorCode.FORBIDDEN, "Event is not authorized")
            revisions = [grant.revision for grant in grants]
            timeline = tuple(
                EventAssessment.model_validate(
                    session.get(VersionRow, (event_id, revision)).payload
                )
                for revision in revisions
            )
            pairs = session.execute(
                select(DeliveryRow, IntentRow)
                .join(IntentRow)
                .where(
                    IntentRow.subject_id == event_id,
                    IntentRow.revision.in_(revisions),
                    IntentRow.recipient_id == actor.recipient_id,
                )
            ).all()
            deliveries = tuple(
                self.delivery_dto(row, NotificationIntent.model_validate(intent.payload))
                for row, intent in pairs
            )
            ack_rows = session.scalars(
                select(AckRow).where(
                    AckRow.delivery_id.in_([d.delivery_id for d in deliveries]),
                    AckRow.actor_id == actor.actor_id,
                )
            ).all()
            acknowledged = max((ack.payload["revision"] for ack in ack_rows), default=None)
            current = timeline[-1]
            return EventDetail(
                current=current,
                timeline=timeline,
                deliveries=deliveries,
                acknowledged_revision=acknowledged,
                can_ack=acknowledged != current.revision
                and any(
                    d.revision == current.revision and d.state in {"accepted", "dry_run"}
                    for d in deliveries
                ),
            )

    def reports(self, actor, *, cursor=None, limit=20):
        with self.sessions() as session:
            rows, next_cursor = self._visible_versions(
                session, actor, "report", cursor=cursor, limit=limit
            )
            return ReportList(
                items=tuple(Report.model_validate(row.payload) for row in rows),
                next_cursor=next_cursor,
            )

    def report_detail(self, actor, report_id):
        with self.sessions() as session:
            row = session.get(SubjectRow, report_id)
            if not row or row.kind != "report":
                reject(ErrorCode.FORBIDDEN, "Report is not authorized")
            self.require_access(session, actor, report_id, row.current_revision)
            return Report.model_validate(
                session.get(VersionRow, (report_id, row.current_revision)).payload
            )

    def evidence_record(self, actor, record_id, revision):
        with self.sessions() as session:
            self.check_actor(session, actor)
            permitted = session.scalar(
                select(EvidenceRow)
                .join(
                    AuthorizationRow,
                    (
                        (EvidenceRow.subject_id == AuthorizationRow.subject_id)
                        & (EvidenceRow.revision == AuthorizationRow.revision)
                    ),
                )
                .where(
                    EvidenceRow.record_id == record_id,
                    EvidenceRow.record_revision == revision,
                    AuthorizationRow.recipient_id == actor.recipient_id,
                    AuthorizationRow.active.is_(True),
                )
                .limit(1)
            )
            if not permitted:
                reject(ErrorCode.FORBIDDEN, "Evidence is not authorized")
            record = SourceRecord.model_validate(
                session.get(SourceRecordRow, (record_id, revision)).payload
            )
            self.require_data_scope(record)
            return record

    def feedback(self, actor, event_id, request):
        with self.sessions.begin() as session:
            self.require_access(session, actor, event_id, request.revision)
            if session.get(SubjectRow, event_id).kind != "event":
                reject(ErrorCode.INVALID_INPUT, "Feedback target is not an event")
            item = Feedback(
                feedback_id=new_id("feedback"),
                event_id=event_id,
                revision=request.revision,
                actor_id=actor.actor_id,
                kind=request.kind,
                comment=request.comment,
                created_at=self.clock(),
            )
            session.add(
                FeedbackRow(
                    feedback_id=item.feedback_id,
                    actor_id=actor.actor_id,
                    subject_id=event_id,
                    revision=item.revision,
                    payload=item.model_dump(mode="json"),
                )
            )
            self.audit(
                session,
                "feedback",
                event_id,
                actor_id=actor.actor_id,
                details={"kind": item.kind.value, "revision": item.revision},
            )
            return item

    def save_preview(self, actor, parsed):
        for record in parsed.records:
            self.require_data_scope(record)
        refs = {(record.record_id, record.revision): record for record in parsed.records}
        if len(refs) != len(parsed.records):
            reject(ErrorCode.INVALID_OUTPUT, "Quote source records must be unique")
        for observation in parsed.observations:
            source = refs.get((observation.evidence.record_id, observation.evidence.revision))
            if (
                not source
                or (source.provenance, source.fixture_dataset)
                != (observation.provenance, observation.fixture_dataset)
                or observation.evidence.field not in {"title", "content_excerpt"}
                or (
                    observation.evidence.excerpt
                    not in getattr(source, observation.evidence.field, "")
                )
            ):
                reject(ErrorCode.INVALID_OUTPUT, "Quote observation has invalid source evidence")
        preview = QuotePreview(
            preview_id=new_id("preview"),
            file_hash=parsed.file_hash,
            observations=parsed.observations,
            issues=parsed.issues,
            duplicate_rows=parsed.duplicate_rows,
            expires_at=self.clock() + timedelta(minutes=15),
            can_import=bool(parsed.observations) and not parsed.issues,
        )
        with self.sessions.begin() as session:
            self.check_actor(session, actor, admin=True)
            session.add(
                PreviewRow(
                    preview_id=preview.preview_id,
                    actor_id=actor.actor_id,
                    file_hash=preview.file_hash,
                    expires_at=preview.expires_at,
                    payload=preview.model_dump(mode="json"),
                    source_records=[r.model_dump(mode="json") for r in parsed.records],
                )
            )
            self.audit(session, "quote_preview", preview.preview_id, actor_id=actor.actor_id)
        return preview

    def import_preview(self, actor, preview_id):
        with self.sessions.begin() as session:
            self.check_actor(session, actor, admin=True)
            row = session.get(PreviewRow, preview_id, with_for_update=True)
            if not row or row.actor_id != actor.actor_id:
                reject(ErrorCode.FORBIDDEN, "Preview is not authorized")
            if row.import_result:
                return QuoteImportResult.model_validate(row.import_result)
            preview = QuotePreview.model_validate(row.payload)
            if preview.expires_at <= self.clock() or not preview.can_import:
                reject(ErrorCode.INVALID_INPUT, "Preview expired or contains invalid rows")
            records = [SourceRecord.model_validate(r) for r in row.source_records]
            for record in records:
                self.require_data_scope(record)
            # Serialize shared quote identities across actor-specific preview imports.
            from oil_agent.storage.base import lock_key

            for source_id in sorted({r.source_id for r in records}):
                lock_key(session, "source:" + source_id)
            for record in records:
                self._insert_record(session, record, state="done", rediscovered=True)
            inserted = duplicates = 0
            for observation in preview.observations:
                current = session.get(
                    ObservationRow, (observation.observation_id, observation.revision)
                )
                if current:
                    if current.payload != observation.model_dump(mode="json"):
                        reject(ErrorCode.INVALID_INPUT, "Observation revision is immutable")
                    duplicates += 1
                    continue
                session.add(
                    ObservationRow(
                        observation_id=observation.observation_id,
                        revision=observation.revision,
                        value=observation.value,
                        as_of=observation.as_of,
                        record_id=observation.source_record_id,
                        payload=observation.model_dump(mode="json"),
                    )
                )
                inserted += 1
            result = QuoteImportResult(
                import_id=new_id("import"),
                imported_count=inserted,
                duplicate_count=duplicates + len(preview.duplicate_rows),
            )
            row.import_result = result.model_dump(mode="json")
            self.audit(
                session,
                "quote_import",
                preview_id,
                actor_id=actor.actor_id,
                details={"imported": inserted, "duplicates": result.duplicate_count},
            )
            return result

    def report_snapshot(self, cutoff, provenance, fixture_dataset):
        with self.sessions() as session:
            records = session.scalars(
                select(SourceRecordRow)
                .where(
                    SourceRecordRow.discovered_at <= cutoff,
                    SourceRecordRow.processing_state.not_in(["quarantined", "failed"]),
                    SourceRecordRow.payload["provenance"].astext == str(provenance),
                    SourceRecordRow.payload["fixture_dataset"].astext == fixture_dataset,
                )
                .order_by(SourceRecordRow.record_id, SourceRecordRow.revision.desc())
                .limit(5001)
            ).all()
            available = {}
            for row in records:
                record = SourceRecord.model_validate(row.payload)
                available[(record.record_id, record.revision)] = record
            if len(available) > 5000:
                reject(ErrorCode.QUOTA_EXHAUSTED, "Report snapshot exceeds configured local bound")
            events = []
            for row in session.scalars(
                select(VersionRow)
                .join(SubjectRow)
                .where(
                    SubjectRow.kind == "event",
                    VersionRow.created_at <= cutoff,
                    VersionRow.payload["provenance"].astext == str(provenance),
                    VersionRow.payload["fixture_dataset"].astext == fixture_dataset,
                )
                .distinct(VersionRow.subject_id)
                .order_by(VersionRow.subject_id, VersionRow.revision.desc())
                .limit(1001)
            ):
                event = EventAssessment.model_validate(row.payload)
                if (event.provenance, event.fixture_dataset) == (provenance, fixture_dataset):
                    events.append(event)
            observations = tuple(
                MarketObservation.model_validate(row.payload)
                for row in session.scalars(
                    select(ObservationRow)
                    .where(
                        ObservationRow.as_of <= cutoff,
                        ObservationRow.payload["provenance"].astext == str(provenance),
                        ObservationRow.payload["fixture_dataset"].astext == fixture_dataset,
                    )
                    .limit(5001)
                )
            )
            if len(events) > 1000 or len(observations) > 5000:
                reject(ErrorCode.QUOTA_EXHAUSTED, "Report snapshot exceeds configured local bound")
            return tuple(available.values()), tuple(events), observations

    def coverage_gaps(self):
        with self.sessions() as session:
            scope = self.data_scope()
            allowed_sources = select(SourceRecordRow.source_id).where(
                *self.payload_scope(SourceRecordRow.payload)
            )
            return tuple(
                f"Source {row.source_id} coverage gap: {row.gap_state}"
                for row in session.scalars(
                    select(SourceCheckpointRow)
                    .where(SourceCheckpointRow.gap_state != "none")
                    .where(SourceCheckpointRow.source_id.in_(allowed_sources) if scope else True)
                    .limit(100)
                )
            )
