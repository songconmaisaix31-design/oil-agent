"""Shared short PostgreSQL transactions and safe repository errors."""

import hashlib
import json
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

from oil_agent.contracts.services import ErrorCode, ServiceError
from oil_agent.storage.models import AuditRow


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex}"


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def fingerprint(value: dict) -> str:
    return digest(json.dumps(value, sort_keys=True, separators=(",", ":")))


def reject(code: ErrorCode, message: str):
    raise ServiceError(code, message)


def lock_key(session, key: str):
    """Transaction-local advisory lock for an explicit identity, never fuzzy text."""
    number = int.from_bytes(hashlib.sha256(key.encode()).digest()[:8], signed=True)
    session.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": number})


class RepositoryBase:
    def __init__(self, engine, *, clock=None):
        self.engine = engine
        self.sessions = sessionmaker(engine, expire_on_commit=False)
        self.clock = clock or (lambda: datetime.now(UTC))
        self.production_gate = lambda: False

    def audit(self, session, action, object_id, *, actor_id=None, details=None):
        session.add(
            AuditRow(
                audit_id=new_id("audit"),
                actor_id=actor_id,
                action=action,
                object_id=object_id,
                created_at=self.clock(),
                details=details or {},
            )
        )
