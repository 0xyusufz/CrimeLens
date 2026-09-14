"""Deterministic mock reasoning provider for testing CrimeLens AI foundations.

Requires NO network access, NO vendor SDKs, and NO API keys.
Produces deterministic, repeatable candidate outputs based on input content hashing.
Supports controlled error simulation for testing timeouts, rate limits, and failure paths.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Optional

from ml.ai.errors import (
    AIAuthenticationError,
    AIExecutionError,
    AIMalformedResponseError,
    AIProviderUnavailableError,
    AIRateLimitError,
    AITimeoutError,
)
from ml.ai.providers.base import ReasoningModelProvider
from ml.ai.types import InputType, ModelResponse, MultimodalInput


class MockReasoningProvider(ReasoningModelProvider):
    """Deterministic, offline reasoning model provider for testing and validation."""

    def __init__(
        self,
        *,
        model_name: str = "mock-reasoner-v1",
        simulate_timeout: bool = False,
        simulate_rate_limit: bool = False,
        simulate_malformed: bool = False,
        simulate_auth_failure: bool = False,
        simulate_unavailable: bool = False,
        simulate_execution_error: bool = False,
        custom_payload: Optional[dict[str, Any]] = None,
        latency_ms: float = 5.0,
    ) -> None:
        self._model_name = model_name
        self.simulate_timeout = simulate_timeout
        self.simulate_rate_limit = simulate_rate_limit
        self.simulate_malformed = simulate_malformed
        self.simulate_auth_failure = simulate_auth_failure
        self.simulate_unavailable = simulate_unavailable
        self.simulate_execution_error = simulate_execution_error
        self.custom_payload = custom_payload
        self.latency_ms = latency_ms

    @property
    def provider_name(self) -> str:
        return "mock"

    @property
    def is_available(self) -> bool:
        return not self.simulate_unavailable

    def analyze(
        self,
        input_data: MultimodalInput,
        *,
        context: Optional[dict[str, Any]] = None,
    ) -> ModelResponse:
        # Controlled failure simulations
        if self.simulate_unavailable:
            raise AIProviderUnavailableError("Mock provider is configured as unavailable")
        if self.simulate_auth_failure:
            raise AIAuthenticationError("Mock provider simulated authentication failure (401)")
        if self.simulate_timeout:
            raise AITimeoutError("Mock provider simulated bounded timeout exceeded")
        if self.simulate_rate_limit:
            raise AIRateLimitError("Mock provider simulated rate limit quota exceeded (429)")
        if self.simulate_execution_error:
            raise AIExecutionError("Mock provider simulated remote execution error")
        if self.simulate_malformed:
            raise AIMalformedResponseError("Mock provider simulated unparseable or corrupt response")

        if self.custom_payload is not None:
            raw_str = json.dumps(self.custom_payload, ensure_ascii=False)
            return ModelResponse(
                provider_name=self.provider_name,
                model_name=self._model_name,
                raw_content=raw_str,
                structured_payload=self.custom_payload,
                usage_tokens={"prompt_tokens": 12, "completion_tokens": 24, "total_tokens": 36},
                latency_ms=self.latency_ms,
                metadata={"deterministic": True, "custom": True},
            )

        # Deterministic generation from input hash
        content_bytes = (
            input_data.content
            if isinstance(input_data.content, bytes)
            else input_data.content.encode("utf-8")
        )
        digest = hashlib.sha256(content_bytes).hexdigest()[:8]

        # Staging mentions only (never database UUIDs)
        candidates: dict[str, Any] = {
            "entities": [
                {
                    "id": f"mention_mock_{digest}_1",
                    "type": "PERSON",
                    "name": "Subject Alpha",
                    "confidence": 0.95,
                },
                {
                    "id": f"mention_mock_{digest}_2",
                    "type": "PHONE",
                    "name": "+919876543210",
                    "confidence": 0.99,
                },
            ],
            "relationships": [
                {
                    "id": f"rel_mock_{digest}_1",
                    "source_entity_id": f"mention_mock_{digest}_1",
                    "target_entity_id": f"mention_mock_{digest}_2",
                    "relationship": "ASSOCIATED_WITH",
                    "confidence": 0.92,
                    "status": "INFERRED",
                    "evidence_snippet": f"Associated via mock analysis (hash {digest}).",
                }
            ],
            "patterns": [],
            "leads": [],
        }

        # Add multimodal-specific mock metadata
        if input_data.input_type == InputType.IMAGE:
            candidates["metadata"] = {"visual_elements": ["document_scan", "signature"]}
        elif input_data.input_type == InputType.PDF:
            candidates["metadata"] = {"document_structure": "multi_section"}
        elif input_data.input_type == InputType.STRUCTURED:
            candidates["metadata"] = {"tabular_rows": input_data.metadata.get("record_count", 0)}

        raw_content = json.dumps(candidates, ensure_ascii=False)
        return ModelResponse(
            provider_name=self.provider_name,
            model_name=self._model_name,
            raw_content=raw_content,
            structured_payload=candidates,
            usage_tokens={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
            latency_ms=self.latency_ms,
            metadata={"deterministic": True, "input_digest": digest, "input_type": input_data.input_type.value},
        )
