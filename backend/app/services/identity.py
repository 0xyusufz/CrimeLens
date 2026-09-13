"""Request identity helpers.

JWT/RBAC is not implemented. Case writes currently attribute `created_by` to a
development-only placeholder user. Replace `get_request_creator_id` with the
authenticated JWT subject when auth lands. Never accept creator identity or
credentials from the case API client.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import dev_case_creator_email
from app.models.enums import UserRole
from app.models.user import User

# Sentinel only so the NOT NULL password_hash column can be satisfied.
# This is not a password, not a hash, and must never be used for login.
DEV_CREATOR_PASSWORD_PLACEHOLDER = "DEV_ONLY_NO_AUTH_NOT_A_PASSWORD_HASH"


def get_request_creator_id(session: Session) -> uuid.UUID:
    """Return the user id that should be stored as `cases.created_by`.

    DEVELOPMENT ONLY: looks up (or inserts) the configured placeholder user.
    Future JWT path: return the authenticated user's id instead of calling this.
    """
    email = dev_case_creator_email()
    user = session.scalar(select(User).where(User.email == email))
    if user is not None:
        return user.id

    user = User(
        name="Development Case Creator",
        email=email,
        password_hash=DEV_CREATOR_PASSWORD_PLACEHOLDER,
        role=UserRole.INVESTIGATOR,
    )
    session.add(user)
    session.flush()
    return user.id
