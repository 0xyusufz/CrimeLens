"""Legacy development identity. Authenticated APIs use JWT user ids instead.

`get_request_creator_id` is unused by HTTP routes after JWT. It is kept only so
existing database rows attributed to the old placeholder remain explainable.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import dev_case_creator_email
from app.models.user import User


def get_request_creator_id(session: Session) -> uuid.UUID:
    """Look up the old development placeholder user if it exists.

    Do not create users here. Do not use this for authenticated requests.
    """
    email = dev_case_creator_email()
    user = session.scalar(select(User).where(User.email == email))
    if user is None:
        raise RuntimeError("Development placeholder identity is not used after JWT.")
    return user.id
