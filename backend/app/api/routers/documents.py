"""Document upload, metadata, and ML processing endpoints.

Authenticated. Case-level access is required. uploaded_by comes from the JWT user.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_case_access, require_document_access
from app.ml.adapter import MlContractError, MlDocumentProcessor, MlUnavailableError, get_ml_processor
from app.models.case import Case
from app.models.document import Document
from app.models.enums import AuditAction, AuditResult
from app.models.user import User
from app.schemas.document import DocumentRead
from app.schemas.processing import DocumentProcessResult
from app.services.audit import AuditWriteError, record_audit
from app.services.documents import (
    EmptyUploadError,
    FileTooLargeError,
    StoredFileMissingError,
    UnsupportedFileTypeError,
    create_document,
    list_documents_for_case,
    read_upload_bytes,
)
from app.services.csv_ingest import CsvParseError
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
    file: UploadFile = File(...),
    case: Case = Depends(require_case_access),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DocumentRead:
    try:
        data = read_upload_bytes(file.file)
        document = create_document(
            db,
            case_id=case.id,
            original_filename=file.filename,
            content_type=file.content_type,
            data=data,
            uploader_id=user.id,
        )
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
    try:
        record_audit(
            db,
            action=AuditAction.DOCUMENT_UPLOADED,
            result=AuditResult.SUCCESS,
            user_id=user.id,
            case_id=case.id,
            resource_type="document",
            resource_id=document.id,
            details={"filename": document.filename},
        )
    except AuditWriteError:
        raise _database_error() from None
    return DocumentRead.model_validate(document)


@router.post(
    "/cases/{case_id}/documents/batch",
    response_model=list[DocumentRead],
    status_code=status.HTTP_201_CREATED,
)
def upload_documents_batch(
    files: list[UploadFile] = File(...),
    case: Case = Depends(require_case_access),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[DocumentRead]:
    if not files:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No files provided.")
    if len(files) > 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 5 files can be uploaded at once.",
        )
    created_docs = []
    for file in files:
        try:
            data = read_upload_bytes(file.file)
            document = create_document(
                db,
                case_id=case.id,
                original_filename=file.filename,
                content_type=file.content_type,
                data=data,
                uploader_id=user.id,
            )
            created_docs.append(document)
            try:
                record_audit(
                    db,
                    action=AuditAction.DOCUMENT_UPLOADED,
                    result=AuditResult.SUCCESS,
                    user_id=user.id,
                    case_id=case.id,
                    resource_type="document",
                    resource_id=document.id,
                    details={"filename": document.filename, "batch": True},
                )
            except AuditWriteError:
                pass
        except EmptyUploadError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"File {file.filename} is empty.") from None
        except UnsupportedFileTypeError as exc:
            raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail=f"File {file.filename}: {str(exc)}") from None
        except FileTooLargeError:
            raise HTTPException(status_code=413, detail=f"File {file.filename} exceeds maximum size.") from None
        except SQLAlchemyError:
            db.rollback()
            raise _database_error() from None

    return [DocumentRead.model_validate(doc) for doc in created_docs]


@router.get("/cases/{case_id}/documents", response_model=list[DocumentRead])
def list_documents(
    case: Case = Depends(require_case_access),
    db: Session = Depends(get_db),
) -> list[DocumentRead]:
    try:
        rows = list_documents_for_case(db, case.id)
    except SQLAlchemyError:
        db.rollback()
        raise _database_error() from None
    return [DocumentRead.model_validate(row) for row in rows]


@router.get("/documents/{document_id}", response_model=DocumentRead)
def get_document_metadata(
    document: Document = Depends(require_document_access),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DocumentRead:
    try:
        record_audit(
            db,
            action=AuditAction.DOCUMENT_VIEWED,
            result=AuditResult.SUCCESS,
            user_id=user.id,
            case_id=document.case_id,
            resource_type="document",
            resource_id=document.id,
            details={"filename": document.filename},
        )
    except AuditWriteError:
        raise _database_error() from None
    return DocumentRead.model_validate(document)


@router.post("/documents/{document_id}/process", response_model=DocumentProcessResult)
def process_document(
    document: Document = Depends(require_document_access),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    processor: MlDocumentProcessor = Depends(get_ml_processor),
) -> DocumentProcessResult:
    def _failed(reason: str) -> None:
        record_audit(
            db,
            action=AuditAction.DOCUMENT_PROCESS_FAILED,
            result=AuditResult.FAILURE,
            user_id=user.id,
            case_id=document.case_id,
            resource_type="document",
            resource_id=document.id,
            details={"reason": reason},
        )

    try:
        result = process_uploaded_document(db, document.id, processor)
    except CsvParseError as exc:
        try:
            _failed("csv_parse_error")
        except AuditWriteError:
            raise _database_error() from None
        raise HTTPException(
            status_code=422,
            detail=str(exc) or "CSV parsing failed.",
        ) from None
    except StoredFileMissingError:
        try:
            _failed("stored_file_missing")
        except AuditWriteError:
            raise _database_error() from None
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="The stored document file is missing.",
        ) from None
    except MlUnavailableError:
        try:
            _failed("ml_unavailable")
        except AuditWriteError:
            raise _database_error() from None
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="ML processing is not available yet.",
        ) from None
    except MlContractError:
        try:
            _failed("contract_validation")
        except AuditWriteError:
            raise _database_error() from None
        raise HTTPException(
            status_code=422,
            detail="ML output failed contract validation.",
        ) from None
    except GraphProjectionError:
        try:
            _failed("graph_projection")
        except AuditWriteError:
            raise _database_error() from None
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Graph projection failed.",
        ) from None
    except SQLAlchemyError:
        db.rollback()
        try:
            _failed("database")
        except AuditWriteError:
            raise _database_error() from None
        raise _database_error() from None
    try:
        record_audit(
            db,
            action=AuditAction.DOCUMENT_PROCESSED,
            result=AuditResult.SUCCESS,
            user_id=user.id,
            case_id=document.case_id,
            resource_type="document",
            resource_id=document.id,
        )
    except AuditWriteError:
        raise _database_error() from None
    return result
