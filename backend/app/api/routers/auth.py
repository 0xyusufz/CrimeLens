"""Authentication endpoints. Passwords are verified against users.password_hash."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.enums import AuditAction, AuditResult
from app.models.user import User
from app.schemas.auth import AuthUser, LoginRequest, LoginResponse
from app.services.audit import AuditWriteError, record_audit
from app.services.auth import authenticate_user, create_access_token

router = APIRouter()


def _database_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="A database error occurred.",
    )


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> LoginResponse:
    attempted_email = payload.email.strip().lower()
    try:
        user = authenticate_user(db, payload.email, payload.password)
    except SQLAlchemyError:
        db.rollback()
        raise _database_error() from None
    if user is None:
        known = db.scalar(select(User).where(func.lower(User.email) == attempted_email))
        try:
            record_audit(
                db,
                action=AuditAction.LOGIN_FAILURE,
                result=AuditResult.FAILURE,
                user_id=known.id if known is not None else None,
                details={"email": attempted_email},
            )
        except AuditWriteError:
            raise _database_error() from None
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    try:
        record_audit(
            db,
            action=AuditAction.LOGIN_SUCCESS,
            result=AuditResult.SUCCESS,
            user_id=user.id,
            details={"email": user.email},
        )
    except AuditWriteError:
        raise _database_error() from None
    token = create_access_token(user)
    return LoginResponse(
        access_token=token,
        token_type="bearer",
        user=AuthUser.model_validate(user),
    )
