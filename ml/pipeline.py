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
from ml.extraction import extract_entities
from ml.ocr import extract_text_from_image
from ml.preprocessing import is_scanned_file, load_document, normalize_text
from ml.relationships import extract_relationships
from shared.schemas.models import ExtractionResult


def process_document(
    *args: Any,
    document_id: Optional[str] = None,
    text: Optional[str | bytes] = None,
    config: Optional[MLConfig] = None,
    **kwargs: Any,
) -> ExtractionResult:
    """Main entry point for document analysis in the CrimeLens ML pipeline.

    Supports:
    - process_document(document_id, text, ...)
    - process_document(document_bytes, filename, document_id) [backend adapter convention]

    Args:
        *args: Positional arguments matching either standard or backend convention.
        document_id: Staging document identifier (e.g., 'doc_001').
        text: Raw document text string, plain text file path, image file path, or image bytes.
        config: Optional ML configuration instance.
        **kwargs: Additional metadata, testing hooks, or structured records.

    Returns:
        ExtractionResult: Validated Pydantic model envelope containing
            extracted EntityMention and Relationship instances.

    Raises:
        ValueError: If document_id is empty.
        TypeError: If text is neither a string nor bytes.
        FileNotFoundError: If an image or document path does not exist.
        OCRError: If an OCR engine or image validation error occurs.
    """
    # Resolve calling conventions
    if len(args) == 3:
        # Backend adapter convention: (document_bytes, filename, document_id)
        doc_content, filename, doc_id = args
        document_id = str(doc_id)
        if isinstance(doc_content, bytes):
            if not is_scanned_file(str(filename)):
                try:
                    text = doc_content.decode("utf-8")
                except UnicodeDecodeError:
                    text = doc_content.decode("latin-1")
            else:
                text = doc_content
        else:
            text = doc_content
    elif len(args) == 2:
        first, second = args
        if isinstance(first, str) and (
            first.startswith("doc_")
            or len(first) == 36
            or not isinstance(second, str)
            or len(first) < len(second)
        ):
            document_id = str(first)
            text = second
        else:
            text = first
            document_id = str(second)
    elif len(args) == 1:
        if document_id is None:
            document_id = str(args[0])
        else:
            text = args[0]

    if document_id is None or not str(document_id).strip():
        raise ValueError("document_id must not be empty")

    if text is None:
        text = ""

    cfg = config or default_config
    ocr_runner = kwargs.get("ocr_engine_runner")
    ner_runner = kwargs.get("ner_runner")
    structured_records = kwargs.get("structured_records")

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

    # 3. Entity Extraction (Phase 4): Extract structured EntityMention candidates
    entities = extract_entities(
        clean_text,
        document_id=str(document_id).strip(),
        min_confidence=cfg.min_entity_confidence,
        ner_runner=ner_runner,
    )

    # 4. Relationship Extraction (Phase 5): Extract evidence-backed Relationship instances
    relationships = extract_relationships(
        clean_text,
        entities=entities,
        document_id=str(document_id).strip(),
        structured_records=structured_records,
        min_confidence=cfg.min_relationship_confidence,
    )

    # 5. Future stages (Phase 6 Resolution, Phase 7 Patterns)
    return ExtractionResult(
        document_id=str(document_id).strip(),
        entities=entities,
        relationships=relationships,
    )
