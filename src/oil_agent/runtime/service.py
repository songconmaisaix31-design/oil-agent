"""Injected business orchestration, with bounded calls outside PostgreSQL transactions.

Integration supplies RuntimeServices explicitly. This module imports no AB/D
implementations, creates no scheduler, performs no speculative network requests,
and never turns missing services into mock success. All sync repository work is
run in threads so HTTP/event loops remain available during database operations.
"""

import asyncio
import base64
import binascii
import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from oil_agent.contracts.dto import AckPayload, Delivery, ReportBuildRequest, VerifiedAck
from oil_agent.contracts.http import CallbackResponse, QuoteParseRequest
from oil_agent.contracts.services import (
    AckVerifier,
    AssessmentService,
    CallContext,
    ErrorCode,
    IdentityAdapter,
    NotificationChannel,
    QuoteParser,
    ReportService,
    ServiceError,
    SourceAdapter,
)
from oil_agent.runtime.authorization import RuntimeAuthorization
from oil_agent.runtime.c1 import C1Runtime, C1TenantLookup
from oil_agent.runtime.settings import Settings
from oil_agent.storage.base import new_id


@dataclass
class RuntimeServices:
    c1_tenant_lookup: C1TenantLookup | None = None
    sources: dict[str, SourceAdapter] = field(default_factory=dict)
    assessment: AssessmentService | None = None
    reports: ReportService | None = None
    channels: dict[str, NotificationChannel] = field(default_factory=dict)
    ack_verifier: AckVerifier | None = None
    identity: IdentityAdapter | None = None
    quote_parser: QuoteParser | None = None
    external_sources: frozenset[str] = frozenset()
    assessment_uses_model: bool = False
    reports_use_model: bool = False
    source_poll_seconds: dict[str, int] = field(default_factory=dict)


class Runtime(C1Runtime, RuntimeAuthorization):
    async def latest_source_record(self, source_id: str, external_id: str):
        """AB receives committed immutable history in this runtime's exact data scope."""
        record = await self.db(self.repository.latest_source_record, source_id, external_id)
        if record and (record.provenance, record.fixture_dataset) != (
            self.settings.data_provenance,
            self.settings.fixture_dataset,
        ):
            raise ServiceError(ErrorCode.FORBIDDEN, "Source history belongs to another data scope")
        return record

    async def authorize_recipient(self, scope):
        return await self.db(self.repository.authorize_recipient, scope)

    async def authorize_intent(self, intent):
        return await self.db(self.repository.authorize_intent, intent)

    async def verify_delivery_message(self, delivery_id, platform_message_id):
        return await self.db(
            self.repository.verify_delivery_message, delivery_id, platform_message_id
        )

    async def resolve_identity(self, identity):
        approved = None if self.local_test_identity() else self.approved_identity(identity)
        result = await self.db(self.repository.resolve_identity, identity)
        if approved and result != (approved.actor_id, approved.recipient_id):
            raise ServiceError(ErrorCode.FORBIDDEN, "Identity mapping differs from approved scope")
        return result

    def __init__(
        self,
        repository,
        services: RuntimeServices | None = None,
        *,
        settings: Settings | None = None,
    ):
        self.repository = repository
        self.services = services or RuntimeServices()
        self.settings = settings or Settings()
        # A transport constructed for one scope must not authorize a replacement.
        self._c1_constructed_app_permission = self.settings.c1_app_request_permission
        self._c1_constructed_permission = self.settings.c1_permission
        self._c1_constructed_lookup_only = self.settings.c1_tenant_lookup_only
        self.repository.production_gate = lambda: self.settings.production_ready
        self.repository.trial_config_gate = self.trial_config_allowed
        self.repository.trial_item_gate = self.trial_item_allowed
        self.repository.recipient_scope_gate = self.recipient_allowed
        self.repository.data_scope = lambda: (
            self.settings.data_provenance,
            self.settings.fixture_dataset,
        )
        self.repository.actor_scope_gate = self.actor_allowed

        def current_or_none(method):
            try:
                return method()
            except ServiceError:
                return None

        self.repository.c1_permission_provider = lambda: current_or_none(self.current_c1_permission)
        self.repository.c1_app_permission_provider = lambda: current_or_none(
            self.current_c1_app_request_permission
        )
        self.repository.c1_lookup_permission_provider = lambda: current_or_none(
            self._current_c1_lookup_permission
        )
        self.repository.local_provisioning_allowed = lambda: (
            self.settings.data_provenance == "fixture"
            and not self.settings.c1_display_only
            and not self.settings.c1_tenant_lookup_only
            and self.settings.identity_permission is None
            and self.settings.outbound_mode == "dry_run"
        )

    async def db(self, method, *args, **kwargs):
        return await asyncio.to_thread(method, *args, **kwargs)

    def context(self, *, seconds=20, attempt=1):
        return CallContext(
            request_id=new_id("call"),
            deadline_at=self.repository.clock() + timedelta(seconds=seconds),
            timeout_seconds=seconds,
            attempt=attempt,
        )

    async def bounded(self, operation, *, context):
        remaining = min(
            context.timeout_seconds, (context.deadline_at - self.repository.clock()).total_seconds()
        )
        if remaining <= 0:
            raise ServiceError(ErrorCode.TIMEOUT, "Service deadline expired")
        try:
            async with asyncio.timeout(remaining):
                return await operation(context)
        except TimeoutError:
            raise ServiceError(ErrorCode.TIMEOUT, "Service deadline exceeded") from None

    def missing(self, name):
        raise ServiceError(ErrorCode.NOT_IMPLEMENTED, f"{name} service is not configured")

    async def ingest(self, source_id):
        source = self.services.sources.get(source_id)
        if source is None:
            self.missing("Source")
        permission = None
        if source_id in self.services.external_sources:
            permission = self.source_permission(source_id)
        else:
            await self.db(
                self.repository.charge_budget,
                "source:" + source_id,
                self.settings.daily_source_requests,
            )
        checkpoint = await self.db(self.repository.checkpoint, source_id)
        try:
            batch = await self.bounded(
                lambda ctx: source.fetch(checkpoint, context=ctx), context=self.context()
            )
            if batch.checkpoint.source_id != source_id:
                raise ServiceError(
                    ErrorCode.INVALID_OUTPUT, "Source returned another source identity"
                )
            if any(
                (r.provenance, r.fixture_dataset)
                != (self.settings.data_provenance, self.settings.fixture_dataset)
                or (permission is not None and r.rights_ref != permission.rights_ref)
                for r in batch.records
            ):
                raise ServiceError(
                    ErrorCode.INVALID_OUTPUT, "Source changed its authorized data scope or rights"
                )
            count = await self.db(self.repository.persist_batch, batch, expected=checkpoint)
            await self.db(
                self.repository.health,
                "source:" + source_id,
                "ok" if batch.checkpoint.gap_state == "none" else "degraded",
            )
            return count
        except ServiceError as error:
            await self.db(
                self.repository.health, "source:" + source_id, "degraded", error.code.value
            )
            raise

    async def _processing_budget(self, *, urgent, uses_model):
        if uses_model:
            self.model_permission()
        await self.db(
            self.repository.charge_budget,
            "processing",
            self.settings.daily_processing_calls,
            reserve=self.settings.urgent_processing_reserve,
            urgent=urgent,
        )
        # Actual provider requests/tokens are reserved by the injected per-request hook.

    async def assess_pending(self):
        if self.services.assessment is None:
            self.missing("Assessment")
        scope = dict(
            provenance=self.settings.data_provenance, fixture_dataset=self.settings.fixture_dataset
        )
        if not await self.db(self.repository.pending_record_exists, **scope):
            return ()
        await self._processing_budget(urgent=True, uses_model=self.services.assessment_uses_model)
        claims = await self.db(self.repository.claim_records, lease_seconds=90, **scope)
        if not claims:
            return ()
        try:
            context = self.context(seconds=50, attempt=max(c.attempt for c in claims))
            candidates = await self.bounded(
                lambda ctx: self.services.assessment.assess(
                    tuple(c.record for c in claims), context=ctx
                ),
                context=context,
            )
            snapshot = await self.db(self.repository.prepare_assessment, claims, candidates)
            if len(snapshot.records) > len(claims):
                await self._processing_budget(
                    urgent=True, uses_model=self.services.assessment_uses_model
                )
                candidates = await self.bounded(
                    lambda ctx: self.services.assessment.assess(snapshot.records, context=ctx),
                    context=context,
                )
            result = await self.db(
                self.repository.commit_assessments, claims, candidates, snapshot=snapshot
            )
            await self.db(self.repository.health, "assessment")
            return result
        except Exception as error:
            code = error.code if isinstance(error, ServiceError) else ErrorCode.INVALID_OUTPUT
            try:
                if code == ErrorCode.QUOTA_EXHAUSTED:
                    await self.db(self.repository.defer_records_for_budget, claims)
                else:
                    await self.db(
                        self.repository.fail_records,
                        claims,
                        code,
                        retryable=code
                        in {ErrorCode.TIMEOUT, ErrorCode.UNAVAILABLE, ErrorCode.REVISION_MISMATCH},
                    )
            except ServiceError:
                pass  # A newer attempt owns the row; never overwrite its result.
            await self.db(self.repository.health, "assessment", "degraded", code.value)
            if isinstance(error, ServiceError):
                raise
            raise ServiceError(code, "Assessment failed output validation") from None

    async def send_pending(self, *, subject_type="event"):
        if self.settings.c1_tenant_lookup_only:
            raise ServiceError(ErrorCode.FORBIDDEN, "C1 tenant lookup cannot deliver messages")
        c1 = self.settings.c1_display_only
        if c1 != (subject_type == "exercise"):
            raise ServiceError(ErrorCode.FORBIDDEN, "Delivery lane does not match C1 mode")
        c1_permission = self.current_c1_permission() if c1 else None
        config = (
            SimpleNamespace(notification_channel="feishu", outbound_mode="c1")
            if c1
            else await self.db(self.repository.business_config)
        )
        if config.notification_channel not in self.services.channels:
            self.missing("Configured notification channel")
        if config.notification_channel != "dry_run" and not (
            c1
            or self.trial_config_allowed(config)
            or (config.outbound_mode == "production" and self.settings.production_ready)
        ):
            raise ServiceError(ErrorCode.FORBIDDEN, "Sending permission is not valid")
        claims = await self.db(
            self.repository.claim_deliveries,
            limit=1,
            subject_type=subject_type,
            provenance=self.settings.data_provenance,
            fixture_dataset=self.settings.fixture_dataset,
            max_attempts=c1_permission.max_send_attempts if c1 else 3,
        )
        completed = []
        for claim in claims:
            if not await self.authorize_intent(claim.intent):
                result = Delivery(
                    delivery_id=claim.intent.delivery_id,
                    intent_id=claim.intent.intent_id,
                    recipient_id=claim.intent.recipient_scope.recipient_id,
                    revision=claim.intent.revision,
                    attempt=claim.attempt,
                    state="failed_final",
                    updated_at=self.repository.clock(),
                    error_code="authorization_revoked",
                )
                completed.append(await self.db(self.repository.finish_delivery, claim, result))
                continue
            try:
                if claim.intent.channel == "feishu" and not c1:
                    if config.outbound_mode == "trial":
                        permission = self.settings.trial_send_permission
                        await self.db(
                            self.repository.reserve_provider_call,
                            permission,
                            "trial_send",
                            daily_limit=permission.max_requests,
                        )
                    else:
                        await self.db(
                            self.repository.charge_budget,
                            "delivery",
                            self.settings.production_budget_units,
                        )
                result = await self.bounded(
                    lambda ctx, claim=claim: (
                        self.c1_channel_send(claim, context=ctx)
                        if c1
                        else self.services.channels[claim.intent.channel].send(
                            claim.intent, context=ctx
                        )
                    ),
                    context=self.context(seconds=20, attempt=claim.attempt),
                )
            except Exception as error:
                # Only explicit pre-send rejection codes are safe to classify as known failures.
                code = error.code if isinstance(error, ServiceError) else ErrorCode.UNAVAILABLE
                state = "unknown"
                if code == ErrorCode.RATE_LIMITED:
                    state = "failed_retryable"
                elif code in {
                    ErrorCode.UNAUTHORIZED,
                    ErrorCode.FORBIDDEN,
                    ErrorCode.INVALID_INPUT,
                    ErrorCode.NOT_IMPLEMENTED,
                    ErrorCode.QUOTA_EXHAUSTED,
                }:
                    state = "failed_final"
                result = Delivery(
                    delivery_id=claim.intent.delivery_id,
                    intent_id=claim.intent.intent_id,
                    recipient_id=claim.intent.recipient_scope.recipient_id,
                    revision=claim.intent.revision,
                    attempt=claim.attempt,
                    state=state,
                    updated_at=self.repository.clock(),
                    error_code=code.value,
                )
            if (
                c1
                and result.state == "failed_retryable"
                and claim.attempt >= c1_permission.max_send_attempts
            ):
                result = Delivery.model_validate(result.model_dump() | {"state": "failed_final"})
            completed.append(await self.db(self.repository.finish_delivery, claim, result))
        await self.db(self.repository.health, "delivery:" + subject_type)
        return tuple(completed)

    async def acknowledge_callback(self, payload: AckPayload):
        if self.services.ack_verifier is None:
            self.missing("Acknowledgement verifier")
        context = self.context(seconds=2)
        challenge_handler = getattr(self.services.ack_verifier, "challenge", None)
        if challenge_handler:
            challenge = await self.bounded(
                lambda ctx: challenge_handler(payload, context=ctx), context=context
            )
            if challenge is not None:
                return CallbackResponse(challenge=challenge)
        verified = await self.bounded(
            lambda ctx: self.services.ack_verifier.verify(payload, context=ctx),
            context=context,
        )
        await self.db(self.repository.acknowledge, verified)
        return CallbackResponse()

    async def acknowledge_web(self, actor, event_id, request):
        verified = VerifiedAck(
            delivery_id=request.delivery_id,
            subject_id=event_id,
            revision=request.revision,
            recipient_id=actor.recipient_id,
            actor_id=actor.actor_id,
            callback_id="web:"
            + hashlib.sha256(f"{actor.actor_id}:{request.delivery_id}".encode()).hexdigest(),
            verified_at=self.repository.clock(),
        )
        return await self.db(self.repository.acknowledge, verified, actor=actor)

    async def login(self, request, browser_cookie):
        if self.services.identity is None or not self.settings.identity_enabled:
            self.missing("Verified identity")
        permission = None if self.local_test_identity() else self.identity_permission()
        await self.db(self.repository.consume_login_state, request.state, browser_cookie)
        if permission:
            await self.db(
                self.repository.reserve_provider_call,
                permission,
                "identity_exchange",
                daily_limit=permission.max_requests,
            )
        identity = await self.bounded(
            lambda ctx: self.services.identity.authenticate(request.code, context=ctx),
            context=self.context(seconds=10),
        )
        if permission:
            approved = self.approved_identity(identity)
            actual = await self.db(self.repository.resolve_identity, identity)
            if actual != (approved.actor_id, approved.recipient_id):
                raise ServiceError(
                    ErrorCode.FORBIDDEN, "Identity mapping differs from approved scope"
                )
        return await self.db(
            self.repository.issue_session,
            identity,
            duration_seconds=self.settings.session_ttl_seconds,
            authentication_scope=permission.approval_id if permission else None,
        )

    async def quote_preview(self, actor, request):
        if self.services.quote_parser is None:
            self.missing("Quote parser")
        is_fixture = self.settings.data_provenance == "fixture"
        publisher = (
            "Authorized local quote upload" if is_fixture else self.settings.quote_origin_publisher
        )
        if not is_fixture and (
            not publisher
            or not self.settings.quote_upload_rights_ref
            or request.rights_ref != self.settings.quote_upload_rights_ref
        ):
            raise ServiceError(
                ErrorCode.FORBIDDEN, "Real upload publisher and rights require server approval"
            )
        try:
            raw = base64.b64decode(request.content_base64, validate=True)
        except (binascii.Error, ValueError):
            raise ServiceError(ErrorCode.INVALID_INPUT, "Invalid base64 upload") from None
        if not raw or len(raw) > 2_000_000:
            raise ServiceError(ErrorCode.INVALID_INPUT, "Upload exceeds the local size limit")
        parsed = await self.bounded(
            lambda ctx: self.services.quote_parser.preview(
                QuoteParseRequest(
                    upload=request,
                    origin_publisher=publisher,
                    discovered_at=self.repository.clock(),
                    is_fixture=is_fixture,
                    provenance=self.settings.data_provenance,
                    fixture_dataset=self.settings.fixture_dataset,
                ),
                context=ctx,
            ),
            context=self.context(seconds=20),
        )
        if parsed.file_hash != hashlib.sha256(raw).hexdigest() or any(
            (record.provenance, record.fixture_dataset, record.origin_publisher)
            != (self.settings.data_provenance, self.settings.fixture_dataset, publisher)
            for record in parsed.records
        ):
            raise ServiceError(
                ErrorCode.INVALID_OUTPUT, "Parser changed upload provenance or digest"
            )
        return await self.db(self.repository.save_preview, actor, parsed)

    async def build_daily(self):
        if self.services.reports is None:
            self.missing("Report")
        config = await self.db(self.repository.business_config)
        now = self.repository.clock()
        local = now.astimezone(ZoneInfo(config.report_timezone))
        scheduled = datetime.combine(
            local.date(), config.report_time, ZoneInfo(config.report_timezone)
        )
        if local < scheduled:
            return None
        reserved = await self.db(
            self.repository.reserve_report,
            local.date(),
            config.report_timezone,
            self.settings.data_provenance,
            self.settings.fixture_dataset,
        )
        if reserved is None:
            return None
        await self._processing_budget(urgent=False, uses_model=self.services.reports_use_model)
        report_id, token = reserved
        records, events, observations = await self.db(
            self.repository.report_snapshot,
            now,
            self.settings.data_provenance,
            self.settings.fixture_dataset,
        )
        request = ReportBuildRequest(
            report_id=report_id,
            report_date=local.date(),
            timezone=config.report_timezone,
            cutoff_at=now,
            revision=1,
            records=records,
            events=events,
            observations=observations,
            is_fixture=self.settings.data_provenance == "fixture",
            provenance=self.settings.data_provenance,
            fixture_dataset=self.settings.fixture_dataset,
        )
        report = await self.bounded(
            lambda ctx: self.services.reports.build(request, context=ctx),
            context=self.context(seconds=60),
        )
        if (report.report_id, report.cutoff_at, report.provenance, report.fixture_dataset) != (
            request.report_id,
            request.cutoff_at,
            request.provenance,
            request.fixture_dataset,
        ):
            raise ServiceError(
                ErrorCode.INVALID_OUTPUT, "Report changed its input snapshot identity"
            )
        gaps = await self.db(self.repository.coverage_gaps)
        report = report.model_copy(
            update={
                "delayed": local > scheduled + timedelta(minutes=5),
                "gaps": tuple(sorted(set(report.gaps) | set(gaps))),
            }
        )
        result = await self.db(self.repository.commit_report, report, token)
        await self.db(self.repository.health, "report")
        return result

    async def recover(self):
        records = await self.db(self.repository.recover_records)
        unknown = await self.db(self.repository.recover_deliveries)
        reminders = await self.db(self.repository.create_due_reminders)
        await self.db(self.repository.health, "recovery")
        return {
            "records_recovered": records,
            "deliveries_unknown": unknown,
            "reminders_created": reminders,
        }
