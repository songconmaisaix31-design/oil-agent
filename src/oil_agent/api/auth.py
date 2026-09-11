"""Fail-closed session seam for D identity verification and C authorization.

Runtime must replace resolve_session with database-backed, revocable session
resolution. No token, header, actor ID or fixture credential is trusted here.
Tests may override require_actor explicitly through FastAPI dependencies.
"""

from datetime import UTC, datetime

from fastapi import Depends, HTTPException
from fastapi.security import APIKeyCookie

from oil_agent.contracts.dto import Actor, Role

session_cookie = APIKeyCookie(name="oil_session", auto_error=False)


async def resolve_session(cookie: str | None = Depends(session_cookie)) -> Actor | None:
    return None


async def require_actor(actor: Actor | None = Depends(resolve_session)) -> Actor:
    if actor is None or actor.expires_at <= datetime.now(UTC):
        raise HTTPException(status_code=401, detail="Authentication required")
    return actor


async def require_admin(actor: Actor = Depends(require_actor)) -> Actor:
    if actor.role != Role.ADMIN:
        raise HTTPException(status_code=403, detail="Administrator role required")
    return actor
