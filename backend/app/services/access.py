from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.case import Case, CaseMember
from app.models.enums import UserRole
from app.models.user import User


def user_can_access_case(session: Session, user: User, case_id: uuid.UUID) -> bool:
    if user.role == UserRole.ADMIN:
        return True
    member = session.scalar(
        select(CaseMember).where(
            CaseMember.case_id == case_id,
            CaseMember.user_id == user.id,
        )
    )
    return member is not None
