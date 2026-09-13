"""Evidence integrity ledger endpoints. Append-only; does not store file bytes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_document_access
from app.models.document import Document
from app.models.enums import AuditAction, AuditResult
from app.models.user import User
from app.schemas.ledger import EvidenceBlockRead, EvidenceVerifyResult
from app.services.audit import AuditWriteError, record_audit
from app.services.documents import StoredFileMissingError
from app.services.ledger import (
    EvidenceHashMismatchError,
    anchor_document,
    verify_document,
)

router = APIRouter()


def _database_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="A database error occurred.",
    )


@router.post("/evidence/{document_id}/anchor", response_model=EvidenceBlockRead)
def anchor_evidence(
    document: Document = Depends(require_document_access),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> EvidenceBlockRead:
    try:
        block, created = anchor_document(db, document, user)
        if created:
            record_audit(
                db,
                action=AuditAction.EVIDENCE_ANCHORED,
                result=AuditResult.SUCCESS,
                user_id=user.id,
                case_id=document.case_id,
                resource_type="document",
                resource_id=document.id,
                details={"block_index": block.block_index},
            )
        else:
            db.commit()
    except StoredFileMissingError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="The stored document file is missing.",
        ) from None
    except EvidenceHashMismatchError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Stored evidence hash does not match the document record.",
        ) from None
    except AuditWriteError:
        raise _database_error() from None
    except SQLAlchemyError:
        db.rollback()
        raise _database_error() from None
    return EvidenceBlockRead.model_validate(block)


@router.get("/evidence/{document_id}/verify", response_model=EvidenceVerifyResult)
def verify_evidence(
    document: Document = Depends(require_document_access),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> EvidenceVerifyResult:
    try:
        result = verify_document(db, document)
        record_audit(
            db,
            action=AuditAction.EVIDENCE_VERIFIED,
            result=AuditResult.SUCCESS if result["verified"] else AuditResult.FAILURE,
            user_id=user.id,
            case_id=document.case_id,
            resource_type="document",
            resource_id=document.id,
            details={"anchored": result["anchored"], "verified": result["verified"]},
        )
    except AuditWriteError:
        raise _database_error() from None
    except SQLAlchemyError:
        db.rollback()
        raise _database_error() from None
    return EvidenceVerifyResult.model_validate(result)
