"""Injected runtime HTTP API; live sessions, CSRF and explicit missing capabilities."""

from typing import Annotated, NoReturn
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Path, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from oil_agent.api.auth import require_actor, require_admin, require_csrf
from oil_agent.contracts.dto import Ack, AckPayload, Actor, Feedback, Report, SourceRecord, StableId
from oil_agent.contracts.http import (
    AckRequest,
    ApiError,
    BusinessConfig,
    CallbackResponse,
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
from oil_agent.contracts.services import ErrorCode, ServiceError
from oil_agent.runtime.settings import Settings


def not_implemented() -> NoReturn:
    raise HTTPException(501, "Business capability is not configured")


def create_app(settings: Settings | None = None, *, runtime=None) -> FastAPI:
    settings = settings or Settings()
    app = FastAPI(title="Oil Agent API", version="0.2.0", separate_input_output_schemas=True)
    app.state.settings, app.state.runtime = settings, runtime

    def get_runtime():
        if runtime is None:
            not_implemented()
        return runtime

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException):
        codes = {401: "unauthorized", 403: "forbidden", 501: "not_implemented"}
        return JSONResponse(
            ApiError(
                code=codes.get(exc.status_code, "request_failed"), message=str(exc.detail)
            ).model_dump(),
            status_code=exc.status_code,
        )

    @app.exception_handler(ServiceError)
    async def service_error(request: Request, exc: ServiceError):
        codes = {
            ErrorCode.UNAUTHORIZED: 401,
            ErrorCode.FORBIDDEN: 403,
            ErrorCode.NOT_IMPLEMENTED: 501,
            ErrorCode.REVISION_MISMATCH: 409,
            ErrorCode.REPLAY_REJECTED: 409,
            ErrorCode.RATE_LIMITED: 429,
            ErrorCode.QUOTA_EXHAUSTED: 429,
            ErrorCode.TIMEOUT: 503,
            ErrorCode.UNAVAILABLE: 503,
            ErrorCode.INVALID_INPUT: 422,
            ErrorCode.INVALID_OUTPUT: 502,
        }
        return JSONResponse(
            ApiError(
                code=exc.code.value,
                message="Operation could not be completed",
                retryable=exc.retryable,
            ).model_dump(),
            status_code=codes.get(exc.code, 500),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        return JSONResponse(
            ApiError(code="invalid_input", message="Request validation failed").model_dump(),
            status_code=422,
        )

    @app.exception_handler(Exception)
    async def unexpected_error(request: Request, exc: Exception):
        return JSONResponse(
            ApiError(code="internal_error", message="Operation failed safely").model_dump(),
            status_code=500,
        )

    @app.middleware("http")
    async def request_limits(request: Request, call_next):
        if request.method in {"POST", "PUT", "PATCH"}:
            limit = 262144 if request.url.path.endswith("/callbacks/ack") else 3_000_000
            body = bytearray()
            async for chunk in request.stream():
                body.extend(chunk)
                if len(body) > limit:
                    return JSONResponse(
                        ApiError(code="invalid_input", message="Request too large").model_dump(),
                        status_code=413,
                    )
            request._body = bytes(body)
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    @app.get("/healthz", response_model=HealthResponse, tags=["health"])
    def health():
        return HealthResponse(status="ok", stage="runtime" if runtime else "foundation")

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
        return HealthResponse(status="ok", stage="runtime" if runtime else "foundation")

    errors = {code: {"model": ApiError} for code in (401, 403, 409, 413, 422, 429, 501, 502, 503)}
    router = APIRouter(prefix="/api/v1", responses=errors)

    @router.get("/session/challenge", response_model=SessionChallenge, tags=["session"])
    async def challenge(response: Response):
        rt = get_runtime()
        if rt.services.identity is None or not rt.settings.identity_enabled:
            rt.missing("Verified identity")
        state, browser, expires = await rt.db(rt.repository.create_login_state)
        url = rt.services.identity.authorization_url(state)
        if urlsplit(url).scheme != "https" or not urlsplit(url).hostname:
            raise HTTPException(503, "Identity URL is not configured safely")
        response.set_cookie(
            "oil_login",
            browser,
            httponly=True,
            secure=settings.cookie_secure,
            samesite="lax",
            max_age=300,
            path="/api/v1/session",
        )
        return SessionChallenge(authorization_url=url, state=state, expires_at=expires)

    @router.post(
        "/callbacks/ack",
        response_model=CallbackResponse,
        response_model_exclude_none=True,
        tags=["callbacks"],
    )
    async def callback(request: Request):
        rt = get_runtime()
        return await rt.acknowledge_callback(
            AckPayload(
                body=await request.body(),
                headers=dict(request.headers),
                received_at=rt.repository.clock(),
            )
        )

    @router.get(
        "/records/{record_id}/revisions/{revision}", response_model=SourceRecord, tags=["evidence"]
    )
    def evidence(
        record_id: StableId,
        revision: Annotated[int, Path(ge=1)],
        actor: Actor = Depends(require_actor),
    ):
        return get_runtime().repository.evidence_record(actor, record_id, revision)

    @router.get("/events", response_model=EventList, tags=["events"])
    def events(
        cursor: Annotated[str | None, Query(max_length=1024)] = None,
        limit: Annotated[int, Query(ge=1, le=100)] = 20,
        actor: Actor = Depends(require_actor),
    ):
        return get_runtime().repository.events(actor, cursor=cursor, limit=limit)

    @router.get("/events/{event_id}", response_model=EventDetail, tags=["events"])
    def event_detail(event_id: StableId, actor: Actor = Depends(require_actor)):
        return get_runtime().repository.event_detail(actor, event_id)

    @router.post("/events/{event_id}/ack", response_model=Ack, tags=["events"])
    async def event_ack(event_id: StableId, body: AckRequest, actor: Actor = Depends(require_csrf)):
        return await get_runtime().acknowledge_web(actor, event_id, body)

    @router.post("/events/{event_id}/feedback", response_model=Feedback, tags=["events"])
    def feedback(event_id: StableId, body: FeedbackRequest, actor: Actor = Depends(require_csrf)):
        return get_runtime().repository.feedback(actor, event_id, body)

    @router.get("/reports", response_model=ReportList, tags=["reports"])
    def reports(
        cursor: Annotated[str | None, Query(max_length=1024)] = None,
        limit: Annotated[int, Query(ge=1, le=100)] = 20,
        actor: Actor = Depends(require_actor),
    ):
        return get_runtime().repository.reports(actor, cursor=cursor, limit=limit)

    @router.get("/reports/{report_id}", response_model=Report, tags=["reports"])
    def report_detail(report_id: StableId, actor: Actor = Depends(require_actor)):
        return get_runtime().repository.report_detail(actor, report_id)

    @router.post(
        "/quotes/preview",
        response_model=QuotePreview,
        tags=["quotes"],
        dependencies=[Depends(require_csrf)],
    )
    async def quote_preview(body: QuotePreviewRequest, actor: Actor = Depends(require_admin)):
        return await get_runtime().quote_preview(actor, body)

    @router.post(
        "/quotes/import",
        response_model=QuoteImportResult,
        tags=["quotes"],
        dependencies=[Depends(require_csrf)],
    )
    def quote_import(body: QuoteImportRequest, actor: Actor = Depends(require_admin)):
        return get_runtime().repository.import_preview(actor, body.preview_id)

    @router.get("/config", response_model=BusinessConfig, tags=["configuration"])
    def get_config(actor: Actor = Depends(require_admin)):
        return get_runtime().repository.get_config(actor)

    @router.put(
        "/config",
        response_model=BusinessConfig,
        tags=["configuration"],
        dependencies=[Depends(require_csrf)],
    )
    def update_config(body: BusinessConfig, actor: Actor = Depends(require_admin)):
        return get_runtime().repository.update_config(actor, body)

    @router.get("/status", response_model=RuntimeStatus, tags=["configuration"])
    def status(actor: Actor = Depends(require_actor)):
        from oil_agent.storage.database import database_ready

        config = runtime.repository.business_config() if runtime else BusinessConfig()
        counters, health_values = runtime.repository.runtime_metrics() if runtime else ({}, {})
        sources, capabilities = (), ()
        if runtime:
            sources = tuple(
                cp
                for source in runtime.services.sources
                if (cp := runtime.repository.checkpoint(source)) is not None
            )
            capabilities = tuple(
                name
                for name, value in vars(runtime.services).items()
                if value
                and name
                in {
                    "sources",
                    "assessment",
                    "reports",
                    "channels",
                    "ack_verifier",
                    "identity",
                    "quote_parser",
                }
            )
        return RuntimeStatus(
            stage="runtime" if runtime else "foundation",
            database="not_configured"
            if settings.database_url is None
            else "available"
            if database_ready(settings)
            else "unavailable",
            outbound_mode=config.outbound_mode,
            first_report_policy=config.first_report_policy,
            reminders_enabled=config.reminders_enabled,
            sms_enabled=False,
            phone_enabled=False,
            business_api_implemented=runtime is not None,
            sources=sources,
            counters=counters,
            health=health_values,
            capabilities=capabilities,
        )

    @router.get("/session", response_model=SessionResponse, tags=["session"])
    def session(actor: Actor = Depends(require_actor)):
        return SessionResponse(
            actor=actor, csrf_token=runtime.repository.session_csrf(actor) if runtime else None
        )

    @router.post("/session", response_model=SessionResponse, tags=["session"])
    async def login(body: SessionCreateRequest, request: Request, response: Response):
        if request.headers.get("origin") not in {None, settings.public_origin}:
            raise HTTPException(403, "Cross-origin login forbidden")
        token, csrf, actor = await get_runtime().login(body, request.cookies.get("oil_login"))
        response.set_cookie(
            "oil_session",
            token,
            httponly=True,
            secure=settings.cookie_secure,
            samesite="lax",
            max_age=settings.session_ttl_seconds,
            path="/",
        )
        response.delete_cookie("oil_login", path="/api/v1/session")
        return SessionResponse(actor=actor, csrf_token=csrf)

    @router.delete("/session", status_code=204, tags=["session"])
    def logout(response: Response, actor: Actor = Depends(require_csrf)):
        get_runtime().repository.logout(actor)
        response.delete_cookie("oil_session", path="/")

    app.include_router(router)
    return app
