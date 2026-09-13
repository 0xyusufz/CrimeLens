"""CrimeLens ML Pipeline Entry Interface.

Orchestrates the analysis flow:
Document Text -> Preprocessing -> OCR (if needed) -> Entity Extraction
-> Relationship Extraction -> Resolution Proposals -> Pattern Detection -> Validation
-> Structured JSON (ExtractionResult)

ML produces structured contract JSON. It NEVER writes to PostgreSQL or Neo4j.
"""

from typing import Any, Optional

from ml.config import MLConfig, default_config
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
        text: Raw or preprocessed document text to analyze.
        config: Optional ML configuration instance.
        **kwargs: Additional metadata parameters (e.g., structured records).

    Returns:
        ExtractionResult: Validated Pydantic model envelope containing
            extracted EntityMention and Relationship instances.

    Raises:
        ValueError: If document_id is empty.
    """
    if not document_id or not document_id.strip():
        raise ValueError("document_id must not be empty")

    cfg = config or default_config

    # In Phase 1 (Foundation), returns a validated, schema-compliant ExtractionResult envelope.
    # Future phases will plug in preprocessing, extraction, and validation stages.
    return ExtractionResult(
        document_id=document_id.strip(),
        entities=[],
        relationships=[],
    )
