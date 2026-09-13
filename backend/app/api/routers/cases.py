"""Case management HTTP endpoints. Authenticated; created_by comes from the JWT user."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_case_access
from app.models.case import Case
from app.models.enums import AuditAction, AuditResult
from app.models.user import User
from app.schemas.audit import AuditRead
from app.schemas.case import CaseCreate, CaseListItem, CaseRead
from app.schemas.ledger import EvidenceBlockRead
from app.services.audit import AuditWriteError, list_audit_for_case, record_audit
from app.services.cases import create_case as create_case_row
from app.services.cases import list_cases_for_user
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
