"""Document upload, metadata, and ML processing endpoints.

Unauthenticated in this milestone. `uploaded_by` uses the same development
placeholder as case `created_by` until JWT exists. Files are stored locally
under UPLOAD_DIR named by document UUID. Processing validates Person B's
ExtractionEnvelope, persists PostgreSQL, then projects Neo4j.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.ml.adapter import get_ml_processor, MlContractError, MlDocumentProcessor, MlUnavailableError
from app.schemas.document import DocumentRead
from app.schemas.processing import DocumentProcessResult
from app.services.cases import CaseNotFoundError
from app.services.documents import (
    DocumentNotFoundError,
    EmptyUploadError,
    FileTooLargeError,
    StoredFileMissingError,
    UnsupportedFileTypeError,
    create_document,
    get_document,
    list_documents_for_case,
    read_upload_bytes,
)
from app.services.identity import get_request_creator_id
from app.services.processing import GraphProjectionError, process_uploaded_document

router = APIRouter()


def _database_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="A database error occurred.",
    )


@router.post(
    "/cases/{case_id}/documents",
    response_model=DocumentRead,
    status_code=status.HTTP_201_CREATED,
)
def upload_document(
    case_id: uuid.UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> DocumentRead:
    try:
        data = read_upload_bytes(file.file)
        uploader_id = get_request_creator_id(db)
        document = create_document(
            db,
            case_id=case_id,
            original_filename=file.filename,
            content_type=file.content_type,
            data=data,
            uploader_id=uploader_id,
        )
    except CaseNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found",
        ) from None
    except EmptyUploadError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc) or "Empty uploads are not allowed.",
        ) from None
    except UnsupportedFileTypeError as exc:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=str(exc) or "Unsupported file type.",
        ) from None
    except FileTooLargeError:
        raise HTTPException(
            status_code=413,
            detail="Upload exceeds the maximum allowed size.",
        ) from None
    except SQLAlchemyError:
        db.rollback()
        raise _database_error() from None
    return DocumentRead.model_validate(document)


@router.get("/cases/{case_id}/documents", response_model=list[DocumentRead])
def list_documents(case_id: uuid.UUID, db: Session = Depends(get_db)) -> list[DocumentRead]:
    try:
        rows = list_documents_for_case(db, case_id)
    except CaseNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found",
        ) from None
    except SQLAlchemyError:
        db.rollback()
        raise _database_error() from None
    return [DocumentRead.model_validate(row) for row in rows]


@router.get("/documents/{document_id}", response_model=DocumentRead)
def get_document_metadata(
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> DocumentRead:
    try:
        document = get_document(db, document_id)
    except DocumentNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        ) from None
    except SQLAlchemyError:
        db.rollback()
        raise _database_error() from None
    return DocumentRead.model_validate(document)


@router.post("/documents/{document_id}/process", response_model=DocumentProcessResult)
def process_document(
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
    processor: MlDocumentProcessor = Depends(get_ml_processor),
) -> DocumentProcessResult:
    try:
        return process_uploaded_document(db, document_id, processor)
    except DocumentNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        ) from None
    except StoredFileMissingError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="The stored document file is missing.",
        ) from None
    except MlUnavailableError:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="ML processing is not available yet.",
        ) from None
    except MlContractError:
        raise HTTPException(
            status_code=422,
            detail="ML output failed contract validation.",
        ) from None
    except GraphProjectionError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Graph projection failed.",
        ) from None
    except SQLAlchemyError:
        db.rollback()
        raise _database_error() from None
