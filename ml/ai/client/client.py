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
from dataclasses import replace as _dc_replace
from typing import Any, Optional

from ml.ai.errors import (
    AIAuthenticationError,
    AIConfigurationError,
    AIError,
    AIExecutionError,
    AIMalformedResponseError,
    AIProviderUnavailableError,
    AIQuotaExhaustedError,
    AIRateLimitError,
    AIRequestTooLargeError,
    AITimeoutError,
    AIUnsupportedInputError,
    redact_secrets,
)
from ml.ai.providers.base import ReasoningModelProvider
from ml.ai.types import ModelResponse, MultimodalInput

logger = logging.getLogger(__name__)

# Default budget for text sent to the AI overlay per request (~25k tokens).
# Well under typical provider payload limits (prevents HTTP 413) while
# preserving ample evidence context. The deterministic ML pipeline always
# receives the complete, unbounded document — only the optional AI overlay
# is bounded. Override via MLConfig.ai_max_input_chars / AI_MAX_INPUT_CHARS.
DEFAULT_MAX_INPUT_CHARS: int = 100_000

# Marker inserted where middle content was removed. Kept short so it
# consumes minimal budget. Never contains document content.
_TRUNCATION_MARKER_TEMPLATE = (
    "\n\n[... AI input truncated: showing first {head} and last {tail} "
    "of {total} chars; deterministic ML processed the complete document ...]\n\n"
)

# Errors considered transient and eligible for bounded retry with backoff.
# AIProviderUnavailableError covers 503/network-down conditions.
# AIRateLimitError covers brief 429 rate-limit windows.
# AITimeoutError covers per-request timeouts.
# NOTE: AIQuotaExhaustedError (subclass of AIRateLimitError) is explicitly
#       excluded below — retrying a quota-exhausted endpoint is wasteful.
TRANSIENT_ERRORS = (AITimeoutError, AIRateLimitError, AIProviderUnavailableError)

# Base retry delay in seconds; each attempt doubles (exponential backoff).
_BASE_BACKOFF_SECONDS: float = 0.5


class AIClient:
    """Isolated client boundary for interacting with AI reasoning providers."""

    def __init__(
        self,
        provider: ReasoningModelProvider,
        *,
        timeout_seconds: float = 30.0,
        max_retries: int = 2,
        max_input_bytes: int = 25_000_000,
        max_input_chars: int = DEFAULT_MAX_INPUT_CHARS,
    ) -> None:
        if provider is None:
            raise AIConfigurationError("A valid ReasoningModelProvider instance is required")
        if timeout_seconds <= 0:
            raise AIConfigurationError(f"timeout_seconds must be positive, got {timeout_seconds}")
        if max_retries < 0:
            raise AIConfigurationError(f"max_retries cannot be negative, got {max_retries}")
        if max_input_chars <= 0:
            raise AIConfigurationError(f"max_input_chars must be positive, got {max_input_chars}")

        self.provider = provider
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.max_input_bytes = max_input_bytes
        self.max_input_chars = max_input_chars
        self.last_error: Optional[AIError] = None
        self.last_input_truncated: bool = False

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

        # Bound the text sent to the AI overlay. Deterministic ML stages
        # operate on the original unbounded input; only provider-bound
        # text is truncated here (single choke point for all stages).
        self.last_input_truncated = False
        input_data = self._bound_input(input_data)

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

            except AIQuotaExhaustedError as exc:
                # Never retry quota exhaustion — quota won't reset in seconds.
                # Fall out of the retry loop immediately.
                self.last_error = exc
                logger.warning(
                    "AI quota exhausted on attempt %d/%d: %s; not retrying",
                    attempts,
                    total_attempts,
                    exc.sanitized_message,
                )
                raise

            except AIRequestTooLargeError as exc:
                # Never retry oversized payloads — resending the identical
                # request would fail again. Fall back to deterministic ML.
                self.last_error = exc
                logger.warning(
                    "AI request too large on attempt %d/%d: %s; not retrying",
                    attempts,
                    total_attempts,
                    exc.sanitized_message,
                )
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
                    "AI provider error on attempt %d/%d: %s",
                    attempts,
                    total_attempts,
                    exc.sanitized_message,
                )
                if attempts >= total_attempts:
                    raise exc
                # Exponential backoff: 0.5s, 1.0s, 2.0s … capped at 4 s.
                backoff = min(_BASE_BACKOFF_SECONDS * (2 ** (attempts - 1)), 4.0)
                logger.info("Retrying in %.1fs (attempt %d/%d)", backoff, attempts + 1, total_attempts)
                time.sleep(backoff)

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

    def _bound_input(self, input_data: MultimodalInput) -> MultimodalInput:
        """Return an input bounded to max_input_chars for provider dispatch.

        Preserves the head (~70%) and tail (~30%) of the effective text with
        a truncation marker, so beginning context and closing evidence-bearing
        content survive. Small inputs are returned unchanged.

        Only the text the provider will actually send is bounded
        (extracted_text first, then str content, else raw bytes).
        """
        budget = self.max_input_chars

        text: Optional[str] = None
        source = "extracted_text"
        if input_data.extracted_text is not None:
            text = input_data.extracted_text
        elif isinstance(input_data.content, str):
            text = input_data.content
            source = "content"

        if text is None:
            # Raw bytes without extracted text (e.g. unscanned binary):
            # bound by bytes; the provider decodes the same way.
            data = input_data.content
            assert isinstance(data, bytes)
            if len(data) <= budget:
                return input_data
            self.last_input_truncated = True
            logger.warning(
                "AI input truncated: %d bytes exceeds budget %d chars; sending head only",
                len(data),
                budget,
            )
            return _dc_replace(input_data, content=data[:budget])

        if len(text) <= budget:
            return input_data

        total = len(text)
        # Reserve room for the marker, then split ~70% head / ~30% tail.
        marker_probe = _TRUNCATION_MARKER_TEMPLATE.format(head=0, tail=0, total=total)
        content_budget = budget - len(marker_probe)
        if content_budget <= 0:
            bounded = text[:budget]
            marker = ""
        else:
            head_len = int(content_budget * 0.7)
            tail_len = content_budget - head_len
            tail_part = text[total - tail_len:] if tail_len > 0 else ""
            marker = _TRUNCATION_MARKER_TEMPLATE.format(head=head_len, tail=tail_len, total=total)
            bounded = text[:head_len] + marker + tail_part
            # Guard against digit-width drift between the probe marker and
            # the real one: shrink the HEAD side so the tail (closing
            # evidence) is preserved exactly and the budget always holds.
            overflow = len(bounded) - budget
            if overflow > 0:
                if overflow < head_len:
                    head_len -= overflow
                    marker = _TRUNCATION_MARKER_TEMPLATE.format(head=head_len, tail=tail_len, total=total)
                    bounded = text[:head_len] + marker + tail_part
                else:
                    bounded = bounded[:budget]

        self.last_input_truncated = True
        logger.warning(
            "AI input truncated: %d chars exceeds budget %d; sending bounded head+tail",
            total,
            budget,
        )
        if source == "extracted_text":
            return _dc_replace(input_data, extracted_text=bounded)
        return _dc_replace(input_data, content=bounded)

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
