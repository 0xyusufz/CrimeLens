"""Document modality detection and internal input routing for CrimeLens AI.

Directs incoming documents across supported modalities:
- Plain Text / Text Files
- Native & Scanned PDFs
- Images (PNG, JPEG, TIFF, BMP)
- Structured Files (JSON, CSV, CDRs, Transactions)

Strictly decoupled from PostgreSQL, Neo4j, and FastAPI.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from ml.ai.errors import AIUnsupportedInputError
from ml.ai.types import InputType, MultimodalInput
from ml.preprocessing.document_loader import SCANNED_FILE_EXTENSIONS, is_scanned_file


class DocumentModality(str, Enum):
    """Modalities recognized by the CrimeLens input router."""

    TEXT = "TEXT"
    IMAGE = "IMAGE"
    PDF = "PDF"
    STRUCTURED = "STRUCTURED"


IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp"}
TEXT_EXTENSIONS = {".txt", ".text", ".md", ".log"}
STRUCTURED_EXTENSIONS = {".csv", ".json"}


@dataclass(frozen=True)
class RoutedDocument:
    """Safe, typed container holding a classified document ready for processing."""

    modality: DocumentModality
    multimodal_input: MultimodalInput
    raw_content: bytes | str
    filename: Optional[str] = None
    is_scanned: bool = False
    requires_ocr: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


class DocumentRouter:
    """Classifies input data and builds a RoutedDocument container."""

    def route(
        self,
        content_or_path: str | bytes | MultimodalInput,
        *,
        filename: Optional[str] = None,
        mime_type: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> RoutedDocument:
        """Route input content to appropriate modality container.

        Args:
            content_or_path: String text, filesystem path, raw bytes, or existing MultimodalInput.
            filename: Optional source filename (used for extension detection).
            mime_type: Optional MIME type hint.
            metadata: Optional caller metadata.

        Returns:
            RoutedDocument: Typed routed document container.

        Raises:
            AIUnsupportedInputError: If input is empty, unsupported, or unreadable.
        """
        meta = dict(metadata or {})

        # 1. Already a MultimodalInput
        if isinstance(content_or_path, MultimodalInput):
            return self._from_multimodal_input(content_or_path, meta)

        # 2. Raw Bytes
        if isinstance(content_or_path, bytes):
            return self._route_bytes(
                content_or_path,
                filename=filename,
                mime_type=mime_type,
                metadata=meta,
            )

        # 3. String Content or File Path
        if isinstance(content_or_path, str):
            return self._route_string(
                content_or_path,
                filename=filename,
                mime_type=mime_type,
                metadata=meta,
            )

        raise AIUnsupportedInputError(
            f"Unsupported input type '{type(content_or_path).__name__}'. Expected str, bytes, or MultimodalInput."
        )

    def _from_multimodal_input(
        self,
        m_input: MultimodalInput,
        metadata: dict[str, Any],
    ) -> RoutedDocument:
        combined_meta = {**m_input.metadata, **metadata}
        is_scanned = bool(combined_meta.get("is_scanned", False))
        requires_ocr = is_scanned or m_input.input_type == InputType.IMAGE

        modality_map = {
            InputType.TEXT: DocumentModality.TEXT,
            InputType.IMAGE: DocumentModality.IMAGE,
            InputType.PDF: DocumentModality.PDF,
            InputType.STRUCTURED: DocumentModality.STRUCTURED,
        }
        modality = modality_map.get(m_input.input_type, DocumentModality.TEXT)

        return RoutedDocument(
            modality=modality,
            multimodal_input=m_input,
            raw_content=m_input.content,
            filename=m_input.filename,
            is_scanned=is_scanned,
            requires_ocr=requires_ocr,
            metadata=combined_meta,
        )

    def _route_bytes(
        self,
        data: bytes,
        *,
        filename: Optional[str],
        mime_type: Optional[str],
        metadata: dict[str, Any],
    ) -> RoutedDocument:
        if not data:
            raise AIUnsupportedInputError("Byte content cannot be empty")

        ext = Path(filename).suffix.lower() if filename else ""

        # PDF detection (magic bytes %PDF- or .pdf extension)
        if data.startswith(b"%PDF-") or ext == ".pdf" or mime_type == "application/pdf":
            # Detect whether PDF has text or is scanned
            has_text_markers = b"/Text" in data or b"/Font" in data or b"BT" in data
            is_scanned = not has_text_markers
            m_input = MultimodalInput.from_pdf(
                data,
                filename=filename,
                metadata={**metadata, "is_scanned": is_scanned},
            )
            return RoutedDocument(
                modality=DocumentModality.PDF,
                multimodal_input=m_input,
                raw_content=data,
                filename=filename,
                is_scanned=is_scanned,
                requires_ocr=is_scanned,
                metadata={**metadata, "is_scanned": is_scanned},
            )

        # Image detection
        if ext in IMAGE_EXTENSIONS or (mime_type and mime_type.startswith("image/")):
            resolved_mime = mime_type or f"image/{ext.lstrip('.') or 'png'}"
            m_input = MultimodalInput.from_image(
                data,
                mime_type=resolved_mime,
                filename=filename,
                metadata=metadata,
            )
            return RoutedDocument(
                modality=DocumentModality.IMAGE,
                multimodal_input=m_input,
                raw_content=data,
                filename=filename,
                is_scanned=True,
                requires_ocr=True,
                metadata=metadata,
            )

        # Attempt decoding as text or structured data
        try:
            text_str = data.decode("utf-8")
        except UnicodeDecodeError:
            try:
                text_str = data.decode("latin-1")
            except Exception as exc:
                raise AIUnsupportedInputError(
                    f"Binary data with extension '{ext}' could not be decoded and is not a supported image or PDF format."
                ) from exc

        return self._route_text_content(
            text_str,
            filename=filename,
            mime_type=mime_type,
            metadata=metadata,
            original_bytes=data,
        )

    def _route_string(
        self,
        content_or_path: str,
        *,
        filename: Optional[str],
        mime_type: Optional[str],
        metadata: dict[str, Any],
    ) -> RoutedDocument:
        if not content_or_path.strip():
            raise AIUnsupportedInputError("String content cannot be empty or whitespace-only")

        # Check if content is a valid local file path
        potential_path = Path(content_or_path)
        if len(content_or_path) < 512 and potential_path.suffix:
            if potential_path.is_file() and potential_path.exists():
                file_bytes = potential_path.read_bytes()
                return self._route_bytes(
                    file_bytes,
                    filename=filename or potential_path.name,
                    mime_type=mime_type,
                    metadata={**metadata, "file_path": str(potential_path)},
                )

        return self._route_text_content(
            content_or_path,
            filename=filename,
            mime_type=mime_type,
            metadata=metadata,
            original_bytes=None,
        )

    def _route_text_content(
        self,
        text: str,
        *,
        filename: Optional[str],
        mime_type: Optional[str],
        metadata: dict[str, Any],
        original_bytes: Optional[bytes] = None,
    ) -> RoutedDocument:
        ext = Path(filename).suffix.lower() if filename else ""

        # Structured detection (JSON or CSV)
        trimmed = text.strip()
        if (
            ext == ".json"
            or mime_type == "application/json"
            or (trimmed.startswith(("{", "[")) and trimmed.endswith(("}", "]")))
        ):
            try:
                parsed = json.loads(trimmed)
                if isinstance(parsed, (dict, list)):
                    m_input = MultimodalInput.from_structured(
                        parsed,
                        filename=filename,
                        metadata=metadata,
                    )
                    return RoutedDocument(
                        modality=DocumentModality.STRUCTURED,
                        multimodal_input=m_input,
                        raw_content=original_bytes if original_bytes is not None else text,
                        filename=filename,
                        is_scanned=False,
                        requires_ocr=False,
                        metadata={**metadata, "structured_format": "json"},
                    )
            except Exception:
                pass  # Fall through to plain text if JSON parsing fails

        if ext == ".csv" or mime_type == "text/csv" or self._is_csv_like(trimmed):
            m_input = MultimodalInput.from_text(
                text,
                filename=filename,
                mime_type="text/csv",
                metadata={**metadata, "structured_format": "csv"},
            )
            return RoutedDocument(
                modality=DocumentModality.STRUCTURED,
                multimodal_input=m_input,
                raw_content=original_bytes if original_bytes is not None else text,
                filename=filename,
                is_scanned=False,
                requires_ocr=False,
                metadata={**metadata, "structured_format": "csv"},
            )

        # Standard plain text
        m_input = MultimodalInput.from_text(
            text,
            filename=filename,
            mime_type=mime_type or "text/plain",
            metadata=metadata,
        )
        return RoutedDocument(
            modality=DocumentModality.TEXT,
            multimodal_input=m_input,
            raw_content=original_bytes if original_bytes is not None else text,
            filename=filename,
            is_scanned=False,
            requires_ocr=False,
            metadata=metadata,
        )

    def _is_csv_like(self, text: str) -> bool:
        """Heuristic check for CSV content (header row with commas/tabs and uniform delimiters)."""
        lines = [line for line in text.splitlines() if line.strip()]
        if len(lines) < 2:
            return False
        first_line = lines[0]
        if "," in first_line:
            col_count = len(first_line.split(","))
            if col_count >= 3:
                second_line_cols = len(lines[1].split(","))
                return col_count == second_line_cols
        return False
