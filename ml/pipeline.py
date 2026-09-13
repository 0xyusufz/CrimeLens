"""CrimeLens ML Pipeline Entry Interface.

Orchestrates the analysis flow:
Document Text -> Preprocessing (Phase 2) -> OCR (Phase 3) -> Entity Extraction (Phase 4)
-> Relationship Extraction -> Resolution Proposals -> Pattern Detection -> Validation
-> Structured JSON (ExtractionResult)

ML produces structured contract JSON. It NEVER writes to PostgreSQL or Neo4j.
"""

from typing import Any, Optional

from ml.config import MLConfig, default_config
from ml.preprocessing import load_document, normalize_text
from shared.schemas.models import ExtractionResult


def process_document(
    document_id: str,
    text: str,
    config: Optional[MLConfig] = None,
    **kwargs: Any,
) -> ExtractionResult:
    """Main entry point for document analysis in the CrimeLens ML pipeline.

    Args:
        document_id: Staging document identifier (e.g., 'doc_001').
        text: Raw document text or text file path to analyze.
        config: Optional ML configuration instance.
        **kwargs: Additional metadata parameters (e.g., structured records).

    Returns:
        ExtractionResult: Validated Pydantic model envelope containing
            extracted EntityMention and Relationship instances.

    Raises:
        ValueError: If document_id is empty or if input points to a scanned file needing OCR.
        TypeError: If text is not a string.
    """
    if not document_id or not document_id.strip():
        raise ValueError("document_id must not be empty")

    cfg = config or default_config

    # Phase 2 Preprocessing: Load and normalize document content
    raw_text = load_document(text)
    clean_text = normalize_text(raw_text)

    # Downstream extraction stages (Phases 3-6) will consume clean_text.
    # In Phase 2, extraction components are stubs returning empty collections.
    return ExtractionResult(
        document_id=document_id.strip(),
        entities=[],
        relationships=[],
    )
