"""Case management HTTP endpoints.

These routes are unauthenticated. `created_by` is filled by
`get_request_creator_id` (development placeholder) until JWT exists.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.case import CaseCreate, CaseListItem, CaseRead
from app.services.cases import CaseNotFoundError
from app.services.cases import create_case as create_case_row
from app.services.cases import get_case as get_case_row
from app.services.cases import list_cases as list_case_rows
from app.services.identity import get_request_creator_id

router = APIRouter()


def _database_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="A database error occurred.",
    )


@router.post("", response_model=CaseRead, status_code=status.HTTP_201_CREATED)
def create_case(payload: CaseCreate, db: Session = Depends(get_db)) -> CaseRead:
    try:
        creator_id = get_request_creator_id(db)
        case = create_case_row(
            db,
            title=payload.title,
            description=payload.description,
            status=payload.status,
            creator_id=creator_id,
        )
    except SQLAlchemyError:
        db.rollback()
        raise _database_error() from None
    return CaseRead.model_validate(case)


@router.get("", response_model=list[CaseListItem])
def list_cases(db: Session = Depends(get_db)) -> list[CaseListItem]:
    try:
        rows = list_case_rows(db)
    except SQLAlchemyError:
        db.rollback()
        raise _database_error() from None
    return [CaseListItem.model_validate(row) for row in rows]


@router.get("/{case_id}", response_model=CaseRead)
def get_case(case_id: uuid.UUID, db: Session = Depends(get_db)) -> CaseRead:
    try:
        case = get_case_row(db, case_id)
    except CaseNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found",
        ) from None
    except SQLAlchemyError:
        db.rollback()
        raise _database_error() from None
    return CaseRead.model_validate(case)
