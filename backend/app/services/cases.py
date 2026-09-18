from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.case import Case, CaseMember
from app.models.enums import CaseStatus
from app.models.enums import UserRole
from app.models.user import User


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
    creator: User,
) -> Case:
    case = Case(
        case_number=_generate_case_number(),
        title=title,
        description=description,
        status=status,
        created_by=creator.id,
    )
    session.add(case)
    session.flush()
    session.add(
        CaseMember(
            case_id=case.id,
            user_id=creator.id,
            assigned_role=creator.role.value,
        )
    )
    session.commit()
    session.refresh(case)
    return case


def update_case(
    session: Session,
    case_id: uuid.UUID,
    *,
    title: str | None = None,
    description: str | None = None,
    status: CaseStatus | None = None,
) -> Case:
    case = session.get(Case, case_id)
    if case is None:
        raise CaseNotFoundError(case_id)
    if title is not None:
        case.title = title
    if description is not None:
        case.description = description
    if status is not None:
        case.status = status
    session.commit()
    session.refresh(case)
    return case


def delete_case(
    session: Session,
    case_id: uuid.UUID,
) -> None:
    case = session.get(Case, case_id)
    if case is None:
        raise CaseNotFoundError(case_id)

    # Optional Neo4j graph cleanup for this case
    try:
        from app.graph.driver import get_driver
        driver = get_driver()
        with driver.session() as neo_session:
            neo_session.run(
                "MATCH ()-[r {case_id: $case_id}]->() DELETE r",
                case_id=str(case_id),
            )
            neo_session.run(
                "MATCH (c:Case {case_id: $case_id}) DETACH DELETE c",
                case_id=str(case_id),
            )
    except Exception:
        # Neo4j is derived cache layer; do not block deletion if offline
        pass

    session.delete(case)
    session.commit()


def list_cases(session: Session) -> list[Case]:
    stmt = select(Case).order_by(Case.created_at.desc(), Case.id.desc())
    return list(session.scalars(stmt).all())


def list_cases_for_user(session: Session, user: User) -> list[Case]:
    if user.role == UserRole.ADMIN:
        return list_cases(session)
    stmt = (
        select(Case)
        .join(CaseMember, CaseMember.case_id == Case.id)
        .where(CaseMember.user_id == user.id)
        .order_by(Case.created_at.desc(), Case.id.desc())
    )
    return list(session.scalars(stmt).all())


def get_case(session: Session, case_id: uuid.UUID) -> Case:
    case = session.get(Case, case_id)
    if case is None:
        raise CaseNotFoundError(case_id)
    return case
