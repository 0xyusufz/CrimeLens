from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.case import Case
from app.models.enums import CaseStatus


class CaseNotFoundError(Exception):
    def __init__(self, case_id: uuid.UUID):
        self.case_id = case_id
        super().__init__(f"Case not found: {case_id}")


def _generate_case_number() -> str:
    return f"CL-{uuid.uuid4().hex[:12].upper()}"


def create_case(
    session: Session,
    *,
    title: str,
    description: str | None,
    status: CaseStatus,
    creator_id: uuid.UUID,
) -> Case:
    case = Case(
        case_number=_generate_case_number(),
        title=title,
        description=description,
        status=status,
        created_by=creator_id,
    )
    session.add(case)
    session.commit()
    session.refresh(case)
    return case


def list_cases(session: Session) -> list[Case]:
    stmt = select(Case).order_by(Case.created_at.desc(), Case.id.desc())
    return list(session.scalars(stmt).all())


def get_case(session: Session, case_id: uuid.UUID) -> Case:
    case = session.get(Case, case_id)
    if case is None:
        raise CaseNotFoundError(case_id)
    return case
