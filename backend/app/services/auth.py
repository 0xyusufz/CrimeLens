"""Password hashing and JWT helpers. Never log passwords or the signing secret."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import jwt_algorithm, jwt_expire_minutes, jwt_secret
from app.models.user import User


class AuthError(Exception):
    pass


class TokenExpiredError(AuthError):
    pass


class InvalidTokenError_(AuthError):
    pass


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    if not password_hash.startswith("$2"):
        return False
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(
    user: User,
    *,
    expires_delta: timedelta | None = None,
) -> str:
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(minutes=jwt_expire_minutes()))
    payload = {
        "sub": str(user.id),
        "iat": int(now.timestamp()),
        "exp": expire,
    }
    return jwt.encode(payload, jwt_secret(), algorithm=jwt_algorithm())


def decode_access_token(token: str) -> uuid.UUID:
    try:
        payload = jwt.decode(token, jwt_secret(), algorithms=[jwt_algorithm()])
    except ExpiredSignatureError as exc:
        raise TokenExpiredError("Token expired") from exc
    except InvalidTokenError as exc:
        raise InvalidTokenError_("Invalid token") from exc
    sub = payload.get("sub")
    if not sub:
        raise InvalidTokenError_("Invalid token")
    try:
        return uuid.UUID(str(sub))
    except ValueError as exc:
        raise InvalidTokenError_("Invalid token") from exc


def authenticate_user(session: Session, email: str, password: str) -> User | None:
    normalized = email.strip().lower()
    user = session.scalar(select(User).where(func.lower(User.email) == normalized))
    if user is None:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user
