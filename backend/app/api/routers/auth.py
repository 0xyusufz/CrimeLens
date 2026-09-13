"""Authentication endpoints. Passwords are verified against users.password_hash."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.auth import AuthUser, LoginRequest, LoginResponse
from app.services.auth import authenticate_user, create_access_token

router = APIRouter()


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> LoginResponse:
    try:
        user = authenticate_user(db, payload.email, payload.password)
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="A database error occurred.",
        ) from None
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    token = create_access_token(user)
    return LoginResponse(
        access_token=token,
        token_type="bearer",
        user=AuthUser.model_validate(user),
    )
