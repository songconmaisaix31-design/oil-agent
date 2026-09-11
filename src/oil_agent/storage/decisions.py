"""Stable explicit families, immutable versions and transactional outbox decisions."""

from datetime import timedelta

from sqlalchemy import select

from oil_agent.contracts.dto import EventAssessment, Report, SourceRecord
from oil_agent.contracts.services import ErrorCode
from oil_agent.storage.base import digest, fingerprint, lock_key, new_id, reject
from oil_agent.storage.models import EvidenceRow, SourceRecordRow, SubjectRow, VersionRow


class DecisionRepository:
    def validate_evidence(self, session, item):
        for ref in item.evidence:
            row = session.get(SourceRecordRow, (ref.record_id, ref.revision))
            if not row:
                reject(ErrorCode.INVALID_OUTPUT, "Evidence record revision does not exist")
            record = SourceRecord.model_validate(row.payload)
            if (record.provenance, record.fixture_dataset) != (
                item.provenance,
                item.fixture_dataset,
            ):
                reject(ErrorCode.INVALID_OUTPUT, "Mixed evidence provenance is forbidden")
            if ref.field not in {"title", "content_excerpt"} or ref.excerpt not in getattr(
                record, ref.field, ""
            ):
                reject(ErrorCode.INVALID_OUTPUT, "Evidence excerpt is unsupported")
            if isinstance(item, EventAssessment):
                groups = [
                    g.origin_publisher for g in item.origin_groups if ref.record_id in g.record_ids
                ]
                if groups != [record.origin_publisher]:
                    reject(ErrorCode.INVALID_OUTPUT, "Evidence original publisher is inconsistent")
            if isinstance(item, Report) and record.discovered_at > item.cutoff_at:
                reject(ErrorCode.INVALID_OUTPUT, "Evidence was unavailable at report cutoff")

    def _store_version(self, session, subject, item, decision_hash, *, kind):
        payload = item.model_dump(mode="json")
        session.add(
            VersionRow(
                subject_id=subject.subject_id,
                revision=item.revision,
                payload=payload,
                decision_hash=decision_hash,
                created_at=self.clock(),
            )
        )
        subject.current_revision = item.revision
        session.flush()
        for record_id, revision in {(r.record_id, r.revision) for r in item.evidence}:
            session.add(
                EvidenceRow(
                    subject_id=subject.subject_id,
                    revision=item.revision,
                    record_id=record_id,
                    record_revision=revision,
                )
            )
        self.create_notifications(session, subject, item, kind=kind)
        self.audit(
            session,
            "version_committed",
            subject.subject_id,
            details={"revision": item.revision, "kind": kind},
        )

    def commit_assessments(
        self, claims, candidates: tuple[EventAssessment, ...], *, namespace="assessment-v1"
    ):
        with self.sessions.begin() as session:
            records = self.lock_claims(session, claims)
            input_refs = {(c.record.record_id, c.record.revision) for c in claims}
            output = []
            ordered = sorted(candidates, key=lambda c: c.event_id)
            if len({c.event_id for c in ordered}) != len(ordered):
                reject(ErrorCode.INVALID_OUTPUT, "Candidate family repeated in one assessment")
            for candidate in ordered:
                if not {(r.record_id, r.revision) for r in candidate.evidence} <= input_refs:
                    reject(
                        ErrorCode.INVALID_OUTPUT, "Assessment referenced records outside its input"
                    )
                self.validate_evidence(session, candidate)
                identity = fingerprint(
                    {
                        "namespace": namespace,
                        "family": candidate.event_id,
                        "provenance": candidate.provenance.value,
                        "fixture_dataset": candidate.fixture_dataset,
                    }
                )
                lock_key(session, "event:" + identity)
                subject = session.scalar(
                    select(SubjectRow).where(SubjectRow.identity_key == identity)
                )
                if subject is None:
                    subject = SubjectRow(
                        subject_id=new_id("event"),
                        identity_key=identity,
                        kind="event",
                        current_revision=0,
                    )
                    session.add(subject)
                    session.flush()
                decision = candidate.model_dump(
                    mode="json",
                    exclude={
                        "event_id",
                        "revision",
                        "assessed_at",
                        "supersedes_revision",
                        "change_summary",
                    },
                )
                decision_hash = fingerprint(decision)
                previous = session.get(VersionRow, (subject.subject_id, subject.current_revision))
                if previous and previous.decision_hash == decision_hash:
                    output.append(EventAssessment.model_validate(previous.payload))
                    continue
                revision = subject.current_revision + 1
                item = EventAssessment.model_validate(
                    candidate.model_dump()
                    | {
                        "event_id": subject.subject_id,
                        "revision": revision,
                        "supersedes_revision": revision - 1 if revision > 1 else None,
                    }
                )
                kind = "first_report" if revision == 1 else "update"
                if item.evidence_status in {"corrected", "conflicting"}:
                    kind = "correction"
                elif item.evidence_status == "withdrawn":
                    kind = "withdrawal"
                elif (
                    previous
                    and previous.payload["assertion_status"] == "occurred"
                    and (item.assertion_status != "occurred")
                ):
                    kind = "correction"
                self._store_version(session, subject, item, decision_hash, kind=kind)
                output.append(item)
            for row in records:
                row.processing_state = "done"
                row.lease_token = None
                row.lease_until = None
            return tuple(output)

    def reserve_report(self, day, timezone, provenance, fixture_dataset):
        identity = digest(f"report:{day}:{timezone}:{provenance}:{fixture_dataset}")
        with self.sessions.begin() as session:
            lock_key(session, identity)
            row = session.scalar(select(SubjectRow).where(SubjectRow.identity_key == identity))
            if row and (
                row.current_revision > 0 or (row.build_until and row.build_until > self.clock())
            ):
                return None
            if row is None:
                row = SubjectRow(
                    subject_id=new_id("report"),
                    identity_key=identity,
                    kind="report",
                    current_revision=0,
                    report_date=day,
                    timezone=timezone,
                )
                session.add(row)
            row.build_token = new_id("build")
            row.build_until = self.clock() + timedelta(seconds=90)
            return row.subject_id, row.build_token

    def commit_report(self, report: Report, token):
        with self.sessions.begin() as session:
            row = session.get(SubjectRow, report.report_id, with_for_update=True)
            if (
                not row
                or row.kind != "report"
                or row.build_token != token
                or (row.build_until <= self.clock() or row.current_revision != 0)
            ):
                reject(ErrorCode.REVISION_MISMATCH, "Report build lease is stale")
            if (
                report.report_date != row.report_date
                or report.timezone != row.timezone
                or report.revision != 1
            ):
                reject(ErrorCode.INVALID_OUTPUT, "Report identity/date/revision mismatch")
            self.validate_evidence(session, report)
            for metric in report.computed_metrics:
                if metric.value is not None and not metric.evidence:
                    reject(ErrorCode.INVALID_OUTPUT, "Numeric metrics require evidence")
            self._store_version(
                session,
                row,
                report,
                fingerprint(report.model_dump(mode="json")),
                kind="daily_report",
            )
            row.build_token = None
            row.build_until = None
            return report
