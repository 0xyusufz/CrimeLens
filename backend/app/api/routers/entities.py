"""Entity details and 1-hop connection endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from neo4j.exceptions import Neo4jError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.case import Case
from app.models.enums import AuditAction, AuditResult
from app.models.user import User
from app.schemas.entity import EntityConnectionsResult, EntityRead
from app.services.access import user_can_access_case
from app.services.audit import AuditWriteError, record_audit
from app.services.entities import (
    DEFAULT_CONNECTION_LIMIT,
    MAX_CONNECTION_LIMIT,
    EntityForbiddenError,
    EntityNotFoundError,
    EntityNotInCaseError,
    InvalidConnectionLimitError,
    get_entity_for_user,
    list_entity_connections,
)

router = APIRouter()


def _database_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="A database error occurred.",
    )


def _entity_not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entity not found")


@router.get("/entities/{entity_id}", response_model=EntityRead)
def get_entity(
    entity_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> EntityRead:
    try:
        result = get_entity_for_user(db, user, entity_id)
        record_audit(
            db,
            action=AuditAction.ENTITY_VIEWED,
            result=AuditResult.SUCCESS,
            user_id=user.id,
            resource_type="entity",
            resource_id=entity_id,
            details={"case_count": len(result.cases)},
        )
    except EntityNotFoundError:
        raise _entity_not_found() from None
    except EntityForbiddenError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized"
        ) from None
    except AuditWriteError:
        raise _database_error() from None
    except SQLAlchemyError:
        db.rollback()
        raise _database_error() from None
    return result


@router.get("/entities/{entity_id}/connections", response_model=EntityConnectionsResult)
def get_entity_connections(
    entity_id: UUID,
    case_id: UUID | None = None,
    limit: int = Query(default=DEFAULT_CONNECTION_LIMIT, ge=1, le=MAX_CONNECTION_LIMIT),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> EntityConnectionsResult:
    if case_id is not None:
        case = db.get(Case, case_id)
        if case is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Case not found"
            )
        if not user_can_access_case(db, user, case_id):
            try:
                record_audit(
                    db,
                    action=AuditAction.CASE_ACCESS_DENIED,
                    result=AuditResult.FAILURE,
                    user_id=user.id,
                    case_id=case_id,
                    resource_type="entity",
                    resource_id=entity_id,
                )
            except AuditWriteError:
                raise _database_error() from None
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized"
            )
    try:
        result = list_entity_connections(
            db, user, entity_id, case_id=case_id, limit=limit
        )
        record_audit(
            db,
            action=AuditAction.ENTITY_CONNECTIONS_QUERIED,
            result=AuditResult.SUCCESS,
            user_id=user.id,
            case_id=case_id,
            resource_type="entity",
            resource_id=entity_id,
            details={
                "limit": limit,
                "result_count": len(result.connections),
            },
        )
    except InvalidConnectionLimitError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"limit must be between 1 and {MAX_CONNECTION_LIMIT}.",
        ) from None
    except EntityNotInCaseError:
        raise _entity_not_found() from None
    except EntityNotFoundError:
        raise _entity_not_found() from None
    except EntityForbiddenError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized"
        ) from None
    except AuditWriteError:
        raise _database_error() from None
    except (SQLAlchemyError, Neo4jError):
        db.rollback()
        raise _database_error() from None
    return result
