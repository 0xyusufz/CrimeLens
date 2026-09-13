"""Case management HTTP endpoints. Authenticated; created_by comes from the JWT user."""

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
from app.schemas.audit import AuditRead
from app.schemas.case import CaseCreate, CaseListItem, CaseRead
from app.schemas.entity import CaseGraphResult
from app.schemas.insights import CaseInsights
from app.schemas.ledger import EvidenceBlockRead
from app.services.audit import AuditWriteError, list_audit_for_case, record_audit
from app.services.case_graph import (
    DEFAULT_GRAPH_LIMIT,
    MAX_GRAPH_LIMIT,
    EntityNotInCaseError,
    InvalidGraphLimitError,
    get_case_graph,
)
from app.services.cases import create_case as create_case_row
from app.services.cases import list_cases_for_user
from app.services.insights import list_case_insights
from app.services.ledger import list_case_ledger

router = APIRouter()


def _database_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="A database error occurred.",
    )


@router.post("", response_model=CaseRead, status_code=status.HTTP_201_CREATED)
def create_case(
    payload: CaseCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CaseRead:
    try:
        case = create_case_row(
            db,
            title=payload.title,
            description=payload.description,
            status=payload.status,
            creator=user,
        )
    except SQLAlchemyError:
        db.rollback()
        raise _database_error() from None
    try:
        record_audit(
            db,
            action=AuditAction.CASE_CREATED,
            result=AuditResult.SUCCESS,
            user_id=user.id,
            case_id=case.id,
            resource_type="case",
            resource_id=case.id,
        )
    except AuditWriteError:
        raise _database_error() from None
    return CaseRead.model_validate(case)


@router.get("", response_model=list[CaseListItem])
def list_cases(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[CaseListItem]:
    try:
        rows = list_cases_for_user(db, user)
    except SQLAlchemyError:
        db.rollback()
        raise _database_error() from None
    return [CaseListItem.model_validate(row) for row in rows]


@router.get("/{case_id}", response_model=CaseRead)
def get_case(case: Case = Depends(require_case_access)) -> CaseRead:
    return CaseRead.model_validate(case)


@router.get("/{case_id}/audit", response_model=list[AuditRead])
def list_case_audit(
    case: Case = Depends(require_case_access),
    db: Session = Depends(get_db),
) -> list[AuditRead]:
    try:
        rows = list_audit_for_case(db, case.id)
    except SQLAlchemyError:
        db.rollback()
        raise _database_error() from None
    return [AuditRead.model_validate(row) for row in rows]


@router.get("/{case_id}/ledger", response_model=list[EvidenceBlockRead])
def list_case_ledger_blocks(
    case: Case = Depends(require_case_access),
    db: Session = Depends(get_db),
) -> list[EvidenceBlockRead]:
    """Case ledger blocks, newest block_index first."""
    try:
        rows = list_case_ledger(db, case.id)
    except SQLAlchemyError:
        db.rollback()
        raise _database_error() from None
    return [EvidenceBlockRead.model_validate(row) for row in rows]


@router.get("/{case_id}/graph", response_model=CaseGraphResult)
def get_case_subgraph(
    case: Case = Depends(require_case_access),
    entity_id: UUID | None = None,
    limit: int = Query(default=DEFAULT_GRAPH_LIMIT, ge=1, le=MAX_GRAPH_LIMIT),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CaseGraphResult:
    try:
        result = get_case_graph(db, case.id, entity_id=entity_id, limit=limit)
        record_audit(
            db,
            action=AuditAction.CASE_GRAPH_VIEWED,
            result=AuditResult.SUCCESS,
            user_id=user.id,
            case_id=case.id,
            resource_type="case",
            resource_id=case.id,
            details={
                "limit": limit,
                "node_count": len(result.nodes),
                "relationship_count": len(result.relationships),
                "truncated": result.truncated,
            },
        )
    except InvalidGraphLimitError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"limit must be between 1 and {MAX_GRAPH_LIMIT}.",
        ) from None
    except EntityNotInCaseError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Entity not found"
        ) from None
    except AuditWriteError:
        raise _database_error() from None
    except (SQLAlchemyError, Neo4jError):
        db.rollback()
        raise _database_error() from None
    return result


@router.get("/{case_id}/insights", response_model=CaseInsights)
def get_case_insights(
    case: Case = Depends(require_case_access),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CaseInsights:
    try:
        result = list_case_insights(db, case.id)
        record_audit(
            db,
            action=AuditAction.CASE_INSIGHTS_VIEWED,
            result=AuditResult.SUCCESS,
            user_id=user.id,
            case_id=case.id,
            resource_type="case",
            resource_id=case.id,
            details={
                "pattern_count": len(result.patterns),
                "lead_count": len(result.leads),
            },
        )
    except AuditWriteError:
        raise _database_error() from None
    except SQLAlchemyError:
        db.rollback()
        raise _database_error() from None
    return result
