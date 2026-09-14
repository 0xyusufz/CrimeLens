"""Configuration for the CrimeLens ML / Intelligence pipeline.

Contains ML-specific settings and thresholds.
Does NOT contain database, Neo4j, or server credentials.
"""

from dataclasses import dataclass
from typing import Optional


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

    # AI / Multimodal reasoning parameters (Phase 1)
    ai_enabled: bool = False
    ai_provider: str = "mock"
    ai_model: str = "mock-reasoner-v1"
    ai_api_key: Optional[str] = None
    ai_timeout_seconds: float = 30.0
    ai_max_retries: int = 2
    ai_max_input_bytes: int = 25_000_000

    def __repr__(self) -> str:
        masked_key = "***REDACTED***" if self.ai_api_key else None
        return (
            f"MLConfig("
            f"min_entity_confidence={self.min_entity_confidence}, "
            f"min_relationship_confidence={self.min_relationship_confidence}, "
            f"min_resolution_confidence={self.min_resolution_confidence}, "
            f"max_document_length_chars={self.max_document_length_chars}, "
            f"default_ocr_language={self.default_ocr_language!r}, "
            f"ai_enabled={self.ai_enabled}, "
            f"ai_provider={self.ai_provider!r}, "
            f"ai_model={self.ai_model!r}, "
            f"ai_api_key={masked_key!r}, "
            f"ai_timeout_seconds={self.ai_timeout_seconds}, "
            f"ai_max_retries={self.ai_max_retries}, "
            f"ai_max_input_bytes={self.ai_max_input_bytes})"
        )


default_config = MLConfig()

