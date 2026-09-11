"""Fail-closed session seam for D identity verification and C authorization.

Runtime resolves opaque cookies through database-backed, revocable sessions.
No arbitrary token, header, actor ID or fixture credential is trusted here.
Tests may override require_actor explicitly through FastAPI dependencies.
"""

from datetime import UTC, datetime

from fastapi import Depends, HTTPException, Request
from fastapi.security import APIKeyCookie

from oil_agent.contracts.dto import Actor, Role

session_cookie = APIKeyCookie(name="oil_session", auto_error=False)


def resolve_session(request: Request, cookie: str | None = Depends(session_cookie)) -> Actor | None:
    runtime = request.app.state.runtime
    return runtime.repository.resolve_session(cookie) if runtime else None


async def require_actor(actor: Actor | None = Depends(resolve_session)) -> Actor:
    if actor is None or actor.expires_at <= datetime.now(UTC):
        raise HTTPException(status_code=401, detail="Authentication required")
    return actor


async def require_admin(actor: Actor = Depends(require_actor)) -> Actor:
    if actor.role != Role.ADMIN:
        raise HTTPException(status_code=403, detail="Administrator role required")
    return actor


def require_csrf(request: Request, actor: Actor = Depends(require_actor)) -> Actor:
    runtime = request.app.state.runtime
    if runtime is None:
        return actor
    origin = request.headers.get("origin")
    if origin and origin != request.app.state.settings.public_origin:
        raise HTTPException(403, "Cross-origin mutation forbidden")
    if request.headers.get("sec-fetch-site") == "cross-site":
        raise HTTPException(403, "Cross-site mutation forbidden")
    runtime.repository.verify_csrf(actor, request.headers.get("x-csrf-token"))
    return actor
