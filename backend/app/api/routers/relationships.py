"""Relationship evidence / provenance endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.enums import AuditAction, AuditResult
from app.models.user import User
from app.schemas.relationship import RelationshipEvidenceRead
from app.services.audit import AuditWriteError, record_audit
from app.services.relationships import (
    RelationshipForbiddenError,
    RelationshipNotFoundError,
    get_relationship_evidence,
)

router = APIRouter()


def _database_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="A database error occurred.",
    )


@router.get(
    "/relationships/{relationship_id}/evidence",
    response_model=RelationshipEvidenceRead,
)
def get_evidence(
    relationship_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> RelationshipEvidenceRead:
    try:
        result = get_relationship_evidence(db, user, relationship_id)
        record_audit(
            db,
            action=AuditAction.RELATIONSHIP_EVIDENCE_VIEWED,
            result=AuditResult.SUCCESS,
            user_id=user.id,
            case_id=result.case_id,
            resource_type="relationship",
            resource_id=relationship_id,
        )
    except RelationshipNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Relationship not found",
        ) from None
    except RelationshipForbiddenError as exc:
        try:
            record_audit(
                db,
                action=AuditAction.CASE_ACCESS_DENIED,
                result=AuditResult.FAILURE,
                user_id=user.id,
                case_id=exc.case_id,
                resource_type="relationship",
                resource_id=relationship_id,
            )
        except AuditWriteError:
            raise _database_error() from None
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized",
        ) from None
    except AuditWriteError:
        raise _database_error() from None
    except SQLAlchemyError:
        db.rollback()
        raise _database_error() from None
    return result
