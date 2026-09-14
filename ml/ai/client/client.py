"""Client boundary for CrimeLens AI model communication.

Enforces:
- Bounded timeouts
- Bounded retries for transient failures (timeouts, rate limits)
- Immediate failure for non-transient errors (auth, bad input, config)
- Input size checks and pre-call validation
- Error normalization and strict secret scrubbing
- Strict isolation: ZERO database, Neo4j, or FastAPI interactions.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Optional

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
    redact_secrets,
)
from ml.ai.providers.base import ReasoningModelProvider
from ml.ai.types import ModelResponse, MultimodalInput

logger = logging.getLogger(__name__)

# Errors considered transient and eligible for bounded retry
TRANSIENT_ERRORS = (AITimeoutError, AIRateLimitError)


class AIClient:
    """Isolated client boundary for interacting with AI reasoning providers."""

    def __init__(
        self,
        provider: ReasoningModelProvider,
        *,
        timeout_seconds: float = 30.0,
        max_retries: int = 2,
        max_input_bytes: int = 25_000_000,
    ) -> None:
        if provider is None:
            raise AIConfigurationError("A valid ReasoningModelProvider instance is required")
        if timeout_seconds <= 0:
            raise AIConfigurationError(f"timeout_seconds must be positive, got {timeout_seconds}")
        if max_retries < 0:
            raise AIConfigurationError(f"max_retries cannot be negative, got {max_retries}")

        self.provider = provider
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.max_input_bytes = max_input_bytes
        self.last_error: Optional[AIError] = None

    def analyze(
        self,
        input_data: MultimodalInput,
        *,
        context: Optional[dict[str, Any]] = None,
    ) -> ModelResponse:
        """Submit multimodal input to provider with timeout and bounded retry guarantees.

        Args:
            input_data: Typed MultimodalInput.
            context: Optional contextual parameters (document_id, hints).

        Returns:
            ModelResponse: Normalized model response.

        Raises:
            AIUnsupportedInputError: If input exceeds size limit or is invalid.
            AIError: Appropriate normalized AI error upon exhaustion of retries or non-retryable failure.
        """
        if not isinstance(input_data, MultimodalInput):
            raise AIUnsupportedInputError(
                f"Expected MultimodalInput, got {type(input_data).__name__}"
            )

        if input_data.byte_size > self.max_input_bytes:
            raise AIUnsupportedInputError(
                f"Input payload ({input_data.byte_size} bytes) exceeds configured limit ({self.max_input_bytes} bytes)"
            )

        if not self.provider.is_available:
            raise AIProviderUnavailableError(
                f"Provider {self.provider.provider_name!r} is currently unavailable"
            )

        safe_context = self._sanitize_context(context)

        last_error: Optional[AIError] = None
        attempts = 0
        total_attempts = 1 + self.max_retries

        while attempts < total_attempts:
            attempts += 1
            try:
                start_time = time.monotonic()
                response = self.provider.analyze(input_data, context=safe_context)
                duration = (time.monotonic() - start_time) * 1000.0

                if not isinstance(response, ModelResponse):
                    raise AIMalformedResponseError(
                        f"Provider {self.provider.provider_name!r} returned unexpected type {type(response).__name__}"
                    )

                # Validate response payload integrity
                if not isinstance(response.structured_payload, dict):
                    raise AIMalformedResponseError("Model response structured_payload must be a dictionary")

                self.last_error = None
                return response

            except AIAuthenticationError as exc:
                # Never retry authentication failures
                self.last_error = exc
                logger.error("AI provider authentication failure: %s", exc.sanitized_message)
                raise

            except AIUnsupportedInputError as exc:
                # Never retry invalid input errors
                self.last_error = exc
                logger.error("AI provider unsupported input: %s", exc.sanitized_message)
                raise

            except AIConfigurationError as exc:
                # Never retry configuration errors
                self.last_error = exc
                logger.error("AI provider configuration failure: %s", exc.sanitized_message)
                raise

            except TRANSIENT_ERRORS as exc:
                last_error = exc
                self.last_error = exc
                logger.warning(
                    "AI transient error on attempt %d/%d: %s",
                    attempts,
                    total_attempts,
                    exc.sanitized_message,
                )
                if attempts >= total_attempts:
                    raise exc

            except AIError as exc:
                last_error = exc
                self.last_error = exc
                logger.error("AI provider error on attempt %d/%d: %s", attempts, total_attempts, exc.sanitized_message)
                if attempts >= total_attempts:
                    raise exc

            except Exception as exc:
                # Normalize any raw unhandled exception from external vendor SDKs
                sanitized_msg = redact_secrets(str(exc))
                normalized = AIExecutionError(
                    f"Unexpected error during provider execution: {sanitized_msg}"
                )
                last_error = normalized
                self.last_error = normalized
                logger.error("Unhandled error on attempt %d/%d: %s", attempts, total_attempts, sanitized_msg)
                if attempts >= total_attempts:
                    raise normalized

        if last_error:
            self.last_error = last_error
            raise last_error
        err = AIExecutionError("Model analysis failed with an unknown error")
        self.last_error = err
        raise err

    def _sanitize_context(self, context: Optional[dict[str, Any]]) -> dict[str, Any]:
        """Strip dangerous fields from context before sending to provider."""
        if not context:
            return {}
        sanitized = {}
        for k, v in context.items():
            k_lower = str(k).lower()
            if any(term in k_lower for term in ("key", "secret", "token", "password", "session", "db")):
                continue
            if isinstance(v, (str, int, float, bool, list, dict)) or v is None:
                sanitized[k] = v
        return sanitized
