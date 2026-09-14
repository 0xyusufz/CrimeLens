"""CrimeLens AI / Multimodal & Reasoning Model Foundation.

Provides a vendor-neutral, isolated boundary for future multimodal and LLM integration.
Does NOT perform database persistence, Neo4j projections, or modify frozen contracts.
"""

from __future__ import annotations

from typing import Optional

from ml.ai.client.client import AIClient
from ml.ai.errors import (
    AIAuthenticationError,
    AIConfigurationError,
    AIError,
    AIExecutionError,
    AIMalformedResponseError,
    AIProviderUnavailableError,
    AIRateLimitError,
    AITimeoutError,
    AIUnsupportedInputError,
)
from ml.ai.providers.base import ReasoningModelProvider
from ml.ai.providers.mock import MockReasoningProvider
from ml.ai.types import InputType, ModelResponse, MultimodalInput


def create_ai_client(
    provider: Optional[ReasoningModelProvider] = None,
    *,
    timeout_seconds: float = 30.0,
    max_retries: int = 2,
    max_input_bytes: int = 25_000_000,
) -> AIClient:
    """Factory to instantiate an AIClient with a specified or default mock provider."""
    active_provider = provider or MockReasoningProvider()
    return AIClient(
        active_provider,
        timeout_seconds=timeout_seconds,
        max_retries=max_retries,
        max_input_bytes=max_input_bytes,
    )


__all__ = [
    # Types
    "InputType",
    "MultimodalInput",
    "ModelResponse",
    # Providers
    "ReasoningModelProvider",
    "MockReasoningProvider",
    # Client
    "AIClient",
    "create_ai_client",
    # Errors
    "AIError",
    "AIProviderUnavailableError",
    "AIConfigurationError",
    "AIAuthenticationError",
    "AITimeoutError",
    "AIRateLimitError",
    "AIMalformedResponseError",
    "AIUnsupportedInputError",
    "AIExecutionError",
]
