"""Case-authorized multi-hop investigation path API."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from neo4j.exceptions import Neo4jError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_case_access
from app.models.case import Case
from app.models.enums import AuditAction, AuditResult
from app.models.user import User
from app.schemas.investigation import InvestigationPathResult
from app.services.audit import AuditWriteError, record_audit
from app.services.investigation import (
    DEFAULT_HOPS,
    MAX_HOPS,
    EntityNotInCaseError,
    InvalidHopLimitError,
    find_shortest_path,
)

router = APIRouter()


def _database_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="A database error occurred.",
    )


@router.get("/path", response_model=InvestigationPathResult)
def get_investigation_path(
    source_entity_id: UUID = Query(...),
    target_entity_id: UUID = Query(...),
    case: Case = Depends(require_case_access),
    max_hops: int = Query(default=DEFAULT_HOPS, ge=1, le=MAX_HOPS),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> InvestigationPathResult:
    try:
        result = find_shortest_path(
            db,
            case_id=case.id,
            source_entity_id=source_entity_id,
            target_entity_id=target_entity_id,
            max_hops=max_hops,
        )
        record_audit(
            db,
            action=AuditAction.INVESTIGATION_PATH_QUERIED,
            result=AuditResult.SUCCESS,
            user_id=user.id,
            case_id=case.id,
            resource_type="investigation",
            resource_id=case.id,
            details={
                "source_entity_id": str(source_entity_id),
                "target_entity_id": str(target_entity_id),
                "max_hops": max_hops,
                "found": result.found,
            },
        )
    except InvalidHopLimitError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"max_hops must be between 1 and {MAX_HOPS}.",
        ) from None
    except EntityNotInCaseError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Entity not found",
        ) from None
    except AuditWriteError:
        raise _database_error() from None
    except (SQLAlchemyError, Neo4jError):
        db.rollback()
        raise _database_error() from None
    return result
