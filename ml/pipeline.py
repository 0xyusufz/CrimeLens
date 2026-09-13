"""CrimeLens ML Pipeline Entry Interface.

Orchestrates the analysis flow:
Document Text / Image -> Preprocessing (Phase 2) / OCR (Phase 3)
-> Entity Extraction (Phase 4) -> Relationship Extraction (Phase 5)
-> Resolution Proposals (Phase 6) -> Pattern Detection (Phase 7)
-> Validation -> Structured JSON (ExtractionResult)

ML produces structured contract JSON. It NEVER writes to PostgreSQL or Neo4j.
"""

from typing import Any, Optional

from ml.config import MLConfig, default_config
from ml.ocr import extract_text_from_image
from ml.preprocessing import is_scanned_file, load_document, normalize_text
from shared.schemas.models import ExtractionResult


def process_document(
    document_id: str,
    text: str | bytes,
    config: Optional[MLConfig] = None,
    **kwargs: Any,
) -> ExtractionResult:
    """Main entry point for document analysis in the CrimeLens ML pipeline.

    Supports both plain text documents and image/scanned documents via OCR.

    Args:
        document_id: Staging document identifier (e.g., 'doc_001').
        text: Raw document text string, plain text file path, image file path, or image bytes.
        config: Optional ML configuration instance.
        **kwargs: Additional metadata or testing hooks (e.g., ocr_engine_runner).

    Returns:
        ExtractionResult: Validated Pydantic model envelope containing
            extracted EntityMention and Relationship instances.

    Raises:
        ValueError: If document_id is empty.
        TypeError: If text is neither a string nor bytes.
        FileNotFoundError: If an image or document path does not exist.
        OCRError: If an OCR engine or image validation error occurs.
    """
    if not document_id or not document_id.strip():
        raise ValueError("document_id must not be empty")

    cfg = config or default_config
    ocr_runner = kwargs.get("ocr_engine_runner")

    # 1. Document Ingestion: Plain text vs. Scanned/Image via Phase 3 OCR
    if isinstance(text, bytes):
        raw_text = extract_text_from_image(text, lang=cfg.default_ocr_language, engine_runner=ocr_runner)
    elif isinstance(text, str):
        if is_scanned_file(text):
            raw_text = extract_text_from_image(text, lang=cfg.default_ocr_language, engine_runner=ocr_runner)
        else:
            raw_text = load_document(text)
    else:
        raise TypeError("text must be a string or bytes")

    # 2. Preprocessing Normalization (Phase 2): Flow OCR or loaded text through normalizer
    clean_text = normalize_text(raw_text)

    # 3. Future extraction stages (Phases 4-6) will consume clean_text.
    # In Phase 3, extraction components are stubs returning empty collections.
    return ExtractionResult(
        document_id=document_id.strip(),
        entities=[],
        relationships=[],
    )
