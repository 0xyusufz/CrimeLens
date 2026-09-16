"""Local file router with hash, type detection, and native-text extraction.

The router owns no persistence.  It returns enough metadata for the pipeline
to make an evidence-preserving choice between native text, OCR, or structured
record processing.  PDF extraction uses ``pypdf`` only when it is installed;
scanned PDFs are deliberately marked for OCR rather than decoded as bytes.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import io
from pathlib import Path
import re
from typing import Optional
import zipfile
from xml.etree import ElementTree


class DocumentKind(str, Enum):
    TEXT = "TEXT"
    IMAGE = "IMAGE"
    PDF = "PDF"
    DOCX = "DOCX"
    CSV = "CSV"
    JSON = "JSON"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class PageContent:
    page_number: int
    text: str
    source: str
    confidence: float | None = None


@dataclass(frozen=True)
class IngestedDocument:
    document_id: str
    filename: str | None
    kind: DocumentKind
    sha256: str | None
    raw_bytes: bytes | None
    text: str
    pages: tuple[PageContent, ...]
    needs_ocr: bool


_IMAGE_MAGIC = (b"\x89PNG\r\n\x1a\n", b"\xff\xd8\xff", b"BM", b"II*\x00", b"MM\x00*", b"GIF87a", b"GIF89a")
_EXTENSION_KIND = {
    ".txt": DocumentKind.TEXT,
    ".md": DocumentKind.TEXT,
    ".log": DocumentKind.TEXT,
    ".pdf": DocumentKind.PDF,
    ".docx": DocumentKind.DOCX,
    ".csv": DocumentKind.CSV,
    ".json": DocumentKind.JSON,
    ".png": DocumentKind.IMAGE,
    ".jpg": DocumentKind.IMAGE,
    ".jpeg": DocumentKind.IMAGE,
    ".tif": DocumentKind.IMAGE,
    ".tiff": DocumentKind.IMAGE,
    ".bmp": DocumentKind.IMAGE,
    ".gif": DocumentKind.IMAGE,
}


def _decode_text(value: bytes) -> str:
    try:
        return value.decode("utf-8")
    except UnicodeDecodeError:
        return value.decode("latin-1", errors="replace")


def _detect_kind(data: bytes | None, filename: str | None) -> DocumentKind:
    suffix = Path(filename or "").suffix.lower()
    by_extension = _EXTENSION_KIND.get(suffix)
    if data:
        if data.startswith(b"%PDF-"):
            return DocumentKind.PDF
        if any(data.startswith(signature) for signature in _IMAGE_MAGIC):
            return DocumentKind.IMAGE
        if data.startswith(b"PK\x03\x04") and suffix == ".docx":
            return DocumentKind.DOCX
    return by_extension or DocumentKind.TEXT


def _extract_docx(data: bytes) -> str:
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            xml = archive.read("word/document.xml")
    except (KeyError, zipfile.BadZipFile) as exc:
        raise ValueError("Invalid DOCX document") from exc
    root = ElementTree.fromstring(xml)
    namespace = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    paragraphs = []
    for paragraph in root.iter(f"{namespace}p"):
        content = "".join(node.text or "" for node in paragraph.iter(f"{namespace}t"))
        if content.strip():
            paragraphs.append(content)
    return "\n".join(paragraphs)


def _extract_pdf(data: bytes) -> tuple[tuple[PageContent, ...], bool]:
    try:
        from pypdf import PdfReader
    except ImportError:
        return (), True

    try:
        reader = PdfReader(io.BytesIO(data))
    except Exception as exc:
        raise ValueError("Invalid PDF document") from exc
    pages = tuple(
        PageContent(
            page_number=index,
            text=(page.extract_text() or "").strip(),
            source="native_pdf",
            confidence=1.0,
        )
        for index, page in enumerate(reader.pages, start=1)
    )
    needs_ocr = not any(page.text for page in pages)
    return pages, needs_ocr


def _read_path_or_text(value: str) -> tuple[bytes | None, str | None, str]:
    # Multiline/long evidence is text, not a filesystem probe. This avoids
    # platform path-length errors for large reports passed directly as strings.
    if "\n" in value or "\r" in value or len(value) > 240:
        return None, None, value
    try:
        potential_path = Path(value)
        if potential_path.exists() and potential_path.is_file():
            data = potential_path.read_bytes()
            return data, potential_path.name, ""
    except OSError:
        return None, None, value
    return None, None, value


def ingest_document(
    document_id: str,
    content: str | bytes,
    *,
    filename: Optional[str] = None,
) -> IngestedDocument:
    """Classify evidence and extract native text when safely available."""
    if isinstance(content, str):
        raw_bytes, path_filename, raw_text = _read_path_or_text(content)
        filename = filename or path_filename
    elif isinstance(content, bytes):
        raw_bytes, raw_text = content, ""
    else:
        raise TypeError("content must be text or bytes")

    kind = _detect_kind(raw_bytes, filename)
    sha256 = hashlib.sha256(raw_bytes).hexdigest() if raw_bytes is not None else None
    pages: tuple[PageContent, ...] = ()
    needs_ocr = False

    if kind == DocumentKind.PDF and raw_bytes is not None:
        pages, needs_ocr = _extract_pdf(raw_bytes)
        raw_text = "\n\n".join(page.text for page in pages if page.text)
    elif kind == DocumentKind.DOCX and raw_bytes is not None:
        raw_text = _extract_docx(raw_bytes)
        pages = (PageContent(1, raw_text, "native_docx", 1.0),) if raw_text else ()
    elif kind in {DocumentKind.TEXT, DocumentKind.CSV, DocumentKind.JSON} and raw_bytes is not None:
        raw_text = _decode_text(raw_bytes)
        pages = (PageContent(1, raw_text, "native_text", 1.0),) if raw_text else ()
    elif kind == DocumentKind.IMAGE:
        needs_ocr = True
    elif raw_bytes is not None:
        raw_text = _decode_text(raw_bytes)
        pages = (PageContent(1, raw_text, "decoded_text", 0.8),) if raw_text else ()

    return IngestedDocument(
        document_id=str(document_id),
        filename=filename,
        kind=kind,
        sha256=sha256,
        raw_bytes=raw_bytes,
        text=raw_text,
        pages=pages,
        needs_ocr=needs_ocr,
    )


__all__ = ["DocumentKind", "IngestedDocument", "PageContent", "ingest_document"]
