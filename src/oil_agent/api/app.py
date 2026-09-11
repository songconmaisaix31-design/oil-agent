"""FastAPI application factory with honest placeholders and no startup side effects.

Health proves process liveness only. Readiness additionally requires the expected
database migration. No business route returns fabricated data or performs sends.
"""

from typing import Annotated, NoReturn

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from oil_agent.api.auth import require_actor, require_admin
from oil_agent.contracts.dto import Ack, Actor, Feedback, Report, Revision, SourceRecord, StableId
from oil_agent.contracts.http import (
    AckRequest,
    ApiError,
    BusinessConfig,
    EventDetail,
    EventList,
    FeedbackRequest,
    HealthResponse,
    QuoteImportRequest,
    QuoteImportResult,
    QuotePreview,
    QuotePreviewRequest,
    ReportList,
    RuntimeStatus,
    SessionChallenge,
    SessionCreateRequest,
    SessionResponse,
)
from oil_agent.runtime.settings import Settings


def not_implemented() -> NoReturn:
    raise HTTPException(501, "Business capability is not implemented in the foundation")


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    app = FastAPI(title="Oil Agent API", version="0.2.0", separate_input_output_schemas=True)
    app.state.settings = settings

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException):
        codes = {401: "unauthorized", 403: "forbidden", 501: "not_implemented"}
        error = ApiError(code=codes.get(exc.status_code, "request_failed"), message=str(exc.detail))
        return JSONResponse(error.model_dump(), status_code=exc.status_code)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        # Never echo input values (login codes, raw uploads or external content).
        error = ApiError(code="invalid_input", message="Request validation failed")
        return JSONResponse(error.model_dump(), status_code=422)

    @app.get("/healthz", response_model=HealthResponse, tags=["health"])
    async def health():
        return HealthResponse(status="ok")

    @app.get(
        "/readyz",
        response_model=HealthResponse,
        tags=["health"],
        responses={503: {"model": HealthResponse}},
    )
    def ready():
        from oil_agent.storage.database import database_ready

        if not database_ready(settings):
            return JSONResponse(HealthResponse(status="not_ready").model_dump(), status_code=503)
        return HealthResponse(status="ok")

    errors = {code: {"model": ApiError} for code in (401, 403, 422, 501)}
    router = APIRouter(prefix="/api/v1", responses=errors)

    @router.get("/session/challenge", response_model=SessionChallenge, tags=["session"])
    async def session_challenge():
        not_implemented()

    @router.post("/callbacks/ack", response_model=Ack, tags=["callbacks"])
    async def callback_ack(request: Request):
        """D verifies signature; C checks identity, current recipient grant and replay."""
        not_implemented()

    @router.get(
        "/records/{record_id}/revisions/{revision}", response_model=SourceRecord, tags=["evidence"]
    )
    async def evidence_record(
        record_id: StableId, revision: Revision, actor: Actor = Depends(require_actor)
    ):
        """Resolve cited evidence only through an event/report authorized for this actor.

        C runtime must verify access and licensed excerpt rights; knowing an ID
        is never sufficient. The returned source URL identifies the original.
        """
        not_implemented()

    @router.get("/events", response_model=EventList, tags=["events"])
    async def events(
        cursor: Annotated[str | None, Query(max_length=1024)] = None,
        limit: Annotated[int, Query(ge=1, le=100)] = 20,
        actor: Actor = Depends(require_actor),
    ):
        not_implemented()

    @router.get("/events/{event_id}", response_model=EventDetail, tags=["events"])
    async def event_detail(event_id: StableId, actor: Actor = Depends(require_actor)):
        not_implemented()

    @router.post("/events/{event_id}/ack", response_model=Ack, tags=["events"])
    async def event_ack(
        event_id: StableId, body: AckRequest, actor: Actor = Depends(require_actor)
    ):
        not_implemented()

    @router.post("/events/{event_id}/feedback", response_model=Feedback, tags=["events"])
    async def event_feedback(
        event_id: StableId, body: FeedbackRequest, actor: Actor = Depends(require_actor)
    ):
        not_implemented()

    @router.get("/reports", response_model=ReportList, tags=["reports"])
    async def reports(
        cursor: Annotated[str | None, Query(max_length=1024)] = None,
        limit: Annotated[int, Query(ge=1, le=100)] = 20,
        actor: Actor = Depends(require_actor),
    ):
        not_implemented()

    @router.get("/reports/{report_id}", response_model=Report, tags=["reports"])
    async def report_detail(report_id: StableId, actor: Actor = Depends(require_actor)):
        not_implemented()

    @router.post("/quotes/preview", response_model=QuotePreview, tags=["quotes"])
    async def quote_preview(body: QuotePreviewRequest, actor: Actor = Depends(require_admin)):
        not_implemented()

    @router.post("/quotes/import", response_model=QuoteImportResult, tags=["quotes"])
    async def quote_import(body: QuoteImportRequest, actor: Actor = Depends(require_admin)):
        not_implemented()

    @router.get("/config", response_model=BusinessConfig, tags=["configuration"])
    async def get_config(actor: Actor = Depends(require_admin)):
        not_implemented()

    @router.put("/config", response_model=BusinessConfig, tags=["configuration"])
    async def update_config(body: BusinessConfig, actor: Actor = Depends(require_admin)):
        not_implemented()

    @router.get("/status", response_model=RuntimeStatus, tags=["configuration"])
    def status(actor: Actor = Depends(require_actor)):
        from oil_agent.storage.database import database_ready

        database = (
            "not_configured"
            if settings.database_url is None
            else ("available" if database_ready(settings) else "unavailable")
        )
        return RuntimeStatus(
            stage="foundation",
            database=database,
            outbound_mode=settings.outbound_mode,
            first_report_policy=settings.first_report_policy,
            reminders_enabled=settings.reminders_enabled,
            sms_enabled=settings.sms_enabled,
            phone_enabled=settings.phone_enabled,
            business_api_implemented=False,
            sources=(),
        )

    @router.get("/session", response_model=SessionResponse, tags=["session"])
    async def session(actor: Actor = Depends(require_actor)):
        return SessionResponse(actor=actor)

    @router.post("/session", response_model=SessionResponse, tags=["session"])
    async def create_session(body: SessionCreateRequest):
        not_implemented()

    @router.delete("/session", status_code=204, tags=["session"])
    async def delete_session(actor: Actor = Depends(require_actor)):
        not_implemented()

    app.include_router(router)
    return app
