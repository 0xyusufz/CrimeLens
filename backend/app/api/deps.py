from collections.abc import Generator
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.case import Case
from app.models.document import Document
from app.models.user import User
from app.services.access import user_can_access_case
from app.services.auth import InvalidTokenError_, TokenExpiredError, decode_access_token
from app.services.documents import DocumentNotFoundError, get_document

bearer_scheme = HTTPBearer(auto_error=False)


def get_db() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if creds is None or creds.scheme.lower() != "bearer" or not creds.credentials:
        raise _unauthorized()
    try:
        user_id = decode_access_token(creds.credentials)
    except (TokenExpiredError, InvalidTokenError_):
        raise _unauthorized() from None
    user = db.get(User, user_id)
    if user is None:
        raise _unauthorized()
    return user


def require_case_access(
    case_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Case:
    case = db.get(Case, case_id)
    if case is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")
    if not user_can_access_case(db, user, case_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    return case


def require_document_access(
    document_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Document:
    try:
        document = get_document(db, document_id)
    except DocumentNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        ) from None
    case = db.get(Case, document.case_id)
    if case is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    if not user_can_access_case(db, user, document.case_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    return document
