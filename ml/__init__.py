"""CrimeLens ML & Intelligence Pipeline (Person B)."""

from ml.ai import (
    AIClient,
    AIEntityCandidate,
    AIEntityExtractor,
    AIError,
    DocumentModality,
    DocumentPage,
    DocumentRouter,
    DocumentSection,
    DocumentTable,
    DocumentUnderstanding,
    DocumentUnderstandingEngine,
    EntityReconciler,
    InputType,
    MockReasoningProvider,
    ModelResponse,
    MultimodalInput,
    ReasoningModelProvider,
    RoutedDocument,
    create_ai_client,
)
from ml.config import MLConfig, default_config
from ml.pipeline import process_document

__all__ = [
    "MLConfig",
    "default_config",
    "process_document",
    "AIClient",
    "create_ai_client",
    "ReasoningModelProvider",
    "MockReasoningProvider",
    "MultimodalInput",
    "ModelResponse",
    "InputType",
    "AIError",
    "DocumentRouter",
    "DocumentModality",
    "RoutedDocument",
    "DocumentUnderstanding",
    "DocumentUnderstandingEngine",
    "DocumentPage",
    "DocumentSection",
    "DocumentTable",
    "AIEntityCandidate",
    "AIEntityExtractor",
    "EntityReconciler",
]


