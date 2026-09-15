"""Configuration for the CrimeLens ML / Intelligence pipeline.

Contains ML-specific settings and thresholds.
Does NOT contain database, Neo4j, or server credentials.
"""

import os as _os
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
    ai_max_input_chars: int = 100_000

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
            f"ai_max_input_bytes={self.ai_max_input_bytes}, "
            f"ai_max_input_chars={self.ai_max_input_chars})"
        )


# ---------------------------------------------------------------------------
# Default config: built from environment at import time.
# Secrets are read from env; never hard-coded here.
# ---------------------------------------------------------------------------
_gemini_key: Optional[str] = _os.environ.get("GEMINI_API_KEY") or None
_groq_key: Optional[str] = _os.environ.get("GROQ_API_KEY") or None
_provider_env: str = (_os.environ.get("AI_PROVIDER") or "").lower()
_model_env: str = _os.environ.get("GEMINI_MODEL") or _os.environ.get("GROQ_MODEL") or ""

# Provider precedence:
#   1. AI_PROVIDER env var (explicit override)
#   2. GEMINI_API_KEY present → "gemini"
#   3. GROQ_API_KEY present → "groq"
#   4. fallback → "mock" (no key required, no network needed)
if _provider_env:
    _active_provider = _provider_env
elif _gemini_key:
    _active_provider = "gemini"
elif _groq_key:
    _active_provider = "groq"
else:
    _active_provider = "mock"

# Resolve key and model for the active provider
if _active_provider == "gemini":
    _active_key = _gemini_key
    _active_model = _model_env or "gemini-1.5-flash"
elif _active_provider == "groq":
    _active_key = _groq_key
    _active_model = _model_env or "llama-3.3-70b-versatile"
else:
    _active_key = None
    _active_model = "mock-reasoner-v1"


def _parse_int_env(name: str, default: int) -> int:
    """Parse a positive-int env knob; fall back to default on any invalid value."""
    try:
        value = int((_os.environ.get(name) or "").strip() or default)
    except (ValueError, TypeError):
        return default
    return value if value > 0 else default


_max_input_chars: int = _parse_int_env("AI_MAX_INPUT_CHARS", 100_000)

default_config = MLConfig(
    ai_enabled=bool(_active_key),
    ai_provider=_active_provider,
    ai_model=_active_model,
    ai_api_key=_active_key,
    ai_max_input_chars=_max_input_chars,
)
