"""Case management HTTP endpoints. Authenticated; created_by comes from the JWT user."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_case_access
from app.models.case import Case
from app.models.user import User
from app.schemas.case import CaseCreate, CaseListItem, CaseRead
from app.services.cases import create_case as create_case_row
from app.services.cases import list_cases_for_user

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
