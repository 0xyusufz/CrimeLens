"""Configuration for the CrimeLens ML / Intelligence pipeline.

Contains ML-specific settings and thresholds.
Does NOT contain database, Neo4j, or server credentials.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class MLConfig:
    """Configuration parameters for ML extraction and analysis."""

    # Confidence thresholds for entity and relationship extraction
    min_entity_confidence: float = 0.5
    min_relationship_confidence: float = 0.5
    min_resolution_confidence: float = 0.7

    # Pipeline processing parameters
    max_document_length_chars: int = 1_000_000
    default_ocr_language: str = "eng"


default_config = MLConfig()
