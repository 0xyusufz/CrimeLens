"""Vendor-neutral reasoning model provider abstraction for CrimeLens AI.

This abstraction enables swapping model providers (Gemini, OpenAI, Claude, local models)
without altering the downstream deterministic CrimeLens pipeline.
The provider knows NOTHING about PostgreSQL, Neo4j, FastAPI, case authorization,
or persistent database UUIDs.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional

from ml.ai.types import ModelResponse, MultimodalInput


class ReasoningModelProvider(ABC):
    """Abstract base class for all CrimeLens multimodal & reasoning AI providers."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Unique identifier name for this provider (e.g., 'mock', 'gemini', 'openai')."""

    @property
    def is_available(self) -> bool:
        """Indicates whether this provider is currently configured and operational."""
        return True

    @abstractmethod
    def analyze(
        self,
        input_data: MultimodalInput,
        *,
        context: Optional[dict[str, Any]] = None,
    ) -> ModelResponse:
        """Execute multimodal analysis or reasoning on the provided input.

        Args:
            input_data: The typed MultimodalInput container.
            context: Optional contextual dictionary (e.g. document_id, case context, domain hints).
                     Must NOT contain database connections or raw auth tokens.

        Returns:
            ModelResponse: Normalized model response containing candidate proposals.

        Raises:
            AIProviderUnavailableError: If provider cannot be contacted.
            AITimeoutError: If provider request timed out.
            AIRateLimitError: If rate limit exceeded.
            AIMalformedResponseError: If response parsing failed.
            AIExecutionError: For other execution failures.
        """

    def health_check(self) -> bool:
        """Optional provider liveness/health probe. Defaults to returning is_available."""
        return self.is_available
