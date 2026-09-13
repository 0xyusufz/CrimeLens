"""Append-only audit trail.

Audit inserts are committed before the corresponding HTTP response is returned
for access-control and login events. If the insert fails, the API returns 500
and does not return a protected resource. Mutations that already committed
(e.g. processing) are not rolled back; a later audit failure still returns 500
so the client does not treat the operation as fully recorded.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.audit import AuditLog
from app.models.enums import AuditAction, AuditResult

_BLOCKED_DETAIL_KEYS = frozenset(
    {
        "password",
        "password_hash",
        "token",
        "access_token",
        "refresh_token",
        "jwt",
        "secret",
        "authorization",
        "content",
        "bytes",
        "file",
    }
)


class AuditWriteError(Exception):
    pass


def _safe_details(details: dict[str, Any] | None) -> dict[str, Any]:
    if not details:
        return {}
    cleaned: dict[str, Any] = {}
    for key, value in details.items():
        lowered = str(key).lower()
        if lowered in _BLOCKED_DETAIL_KEYS:
            continue
        if isinstance(value, (str, int, float, bool)) or value is None:
            cleaned[str(key)] = value
    return cleaned


def record_audit(
    session: Session,
    *,
    action: AuditAction,
    result: AuditResult,
    user_id: uuid.UUID | None = None,
    case_id: uuid.UUID | None = None,
    resource_type: str | None = None,
    resource_id: uuid.UUID | None = None,
    details: dict[str, Any] | None = None,
) -> AuditLog:
    row = AuditLog(
        user_id=user_id,
        action=action.value,
        case_id=case_id,
        resource_type=resource_type,
        resource_id=resource_id,
        result=result.value,
        details=_safe_details(details),
    )
    session.add(row)
    try:
        session.commit()
        session.refresh(row)
    except SQLAlchemyError as exc:
        session.rollback()
        raise AuditWriteError("Audit event could not be recorded.") from exc
    return row


def list_audit_for_case(session: Session, case_id: uuid.UUID) -> list[AuditLog]:
    stmt = (
        select(AuditLog)
        .where(AuditLog.case_id == case_id)
        .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
    )
    return list(session.scalars(stmt).all())
