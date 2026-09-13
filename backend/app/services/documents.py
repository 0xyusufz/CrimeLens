from __future__ import annotations

import hashlib
import uuid
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import max_upload_bytes, upload_dir
from app.models.document import Document
from app.services.cases import CaseNotFoundError, get_case

ALLOWED_EXTENSIONS = {".pdf", ".csv", ".txt"}
ALLOWED_CONTENT_TYPES = {
    ".pdf": {"application/pdf", "application/x-pdf"},
    ".csv": {"text/csv", "application/csv", "text/plain", "application/vnd.ms-excel"},
    ".txt": {"text/plain"},
}
GENERIC_BINARY_TYPES = {"", "application/octet-stream", "binary/octet-stream"}


class DocumentNotFoundError(Exception):
    def __init__(self, document_id: uuid.UUID):
        self.document_id = document_id
        super().__init__(f"Document not found: {document_id}")


class EmptyUploadError(Exception):
    pass


class UnsupportedFileTypeError(Exception):
    pass


class FileTooLargeError(Exception):
    def __init__(self, max_bytes: int):
        self.max_bytes = max_bytes
        super().__init__("Upload exceeds the maximum allowed size.")


def stored_file_path(document_id: uuid.UUID) -> Path:
    base = upload_dir()
    base.mkdir(parents=True, exist_ok=True)
    path = (base / str(document_id)).resolve()
    if path.parent != base.resolve():
        raise RuntimeError("Refusing to write outside the upload directory.")
    return path


def display_filename(raw: str | None) -> str:
    """Keep the original name as metadata only; never use it as a filesystem path."""
    if raw is None or not str(raw).strip():
        raise EmptyUploadError("A filename is required.")
    name = Path(str(raw).replace("\\", "/")).name.strip()
    if not name or name in {".", ".."}:
        raise EmptyUploadError("A filename is required.")
    if len(name) > 255:
        name = name[:255]
    return name


def _normalized_content_type(content_type: str | None) -> str:
    if not content_type:
        return ""
    return content_type.split(";", 1)[0].strip().lower()


def validate_upload(filename: str, content_type: str | None, data: bytes) -> None:
    if not data:
        raise EmptyUploadError("Empty uploads are not allowed.")
    limit = max_upload_bytes()
    if len(data) > limit:
        raise FileTooLargeError(limit)

    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise UnsupportedFileTypeError("Only PDF, CSV, and TXT files are allowed.")

    if ext == ".pdf" and not data.startswith(b"%PDF"):
        raise UnsupportedFileTypeError("File content does not match a PDF.")
    if ext in {".csv", ".txt"} and data.startswith(b"%PDF"):
        raise UnsupportedFileTypeError("File content does not match the declared type.")

    ct = _normalized_content_type(content_type)
    if ct and ct not in GENERIC_BINARY_TYPES and ct not in ALLOWED_CONTENT_TYPES[ext]:
        raise UnsupportedFileTypeError("Content type is not allowed for this file.")


def read_upload_bytes(file_obj, *, max_bytes: int | None = None) -> bytes:
    limit = max_bytes if max_bytes is not None else max_upload_bytes()
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = file_obj.read(64 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > limit:
            raise FileTooLargeError(limit)
        chunks.append(chunk)
    return b"".join(chunks)


def create_document(
    session: Session,
    *,
    case_id: uuid.UUID,
    original_filename: str | None,
    content_type: str | None,
    data: bytes,
    uploader_id: uuid.UUID,
) -> Document:
    get_case(session, case_id)
    filename = display_filename(original_filename)
    validate_upload(filename, content_type, data)

    document_id = uuid.uuid4()
    digest = hashlib.sha256(data).hexdigest()
    path = stored_file_path(document_id)
    path.write_bytes(data)
    document = Document(
        id=document_id,
        case_id=case_id,
        filename=filename,
        sha256_hash=digest,
        uploaded_by=uploader_id,
    )
    session.add(document)
    try:
        session.commit()
        session.refresh(document)
    except Exception:
        session.rollback()
        path.unlink(missing_ok=True)
        raise
    return document


def list_documents_for_case(session: Session, case_id: uuid.UUID) -> list[Document]:
    get_case(session, case_id)
    stmt = (
        select(Document)
        .where(Document.case_id == case_id)
        .order_by(Document.uploaded_at.desc(), Document.id.desc())
    )
    return list(session.scalars(stmt).all())


def get_document(session: Session, document_id: uuid.UUID) -> Document:
    document = session.get(Document, document_id)
    if document is None:
        raise DocumentNotFoundError(document_id)
    return document
