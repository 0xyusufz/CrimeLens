"""Groq reasoning provider implementation for CrimeLens.

Transport: Subprocess + curl (same approach as Gemini for consistency).
No external SDK required. The API key is NEVER included in exception messages,
log output, or error strings.
"""

from __future__ import annotations

import json
import subprocess
import time
from typing import Any, Optional

from ml.ai.errors import (
    AIAuthenticationError,
    AIExecutionError,
    AIMalformedResponseError,
    AIProviderUnavailableError,
    AIQuotaExhaustedError,
    AIRateLimitError,
    AIRequestTooLargeError,
    AITimeoutError,
)
from ml.ai.providers.base import ReasoningModelProvider
from ml.ai.types import ModelResponse, MultimodalInput

_GROQ_ENDPOINT = "https://api.groq.com/openai/v1/chat/completions"

_SYSTEM_INSTRUCTION = (
    "You are an intelligence extractor for the CrimeLens investigation platform. "
    "Return ONLY valid JSON with the following keys: "
    "entities (list), relationships (list), patterns (list), leads (list). "
    "Do NOT include markdown fences, commentary, or explanation."
)


class GroqReasoningProvider(ReasoningModelProvider):
    """Groq provider using curl via subprocess.

    Groq exposes an OpenAI-compatible chat completions endpoint.
    Uses Bearer-token auth (not query-param like Gemini).

    Security contract:
    - The API key is stored as a private instance attribute (_api_key).
    - It is NEVER placed into exception messages, log strings, or any
      serialisable output.
    - The subprocess call uses a list of arguments (no shell interpolation).
    """

    def __init__(self, api_key: str, model_name: str = "llama-3.3-70b-versatile") -> None:
        if not api_key:
            raise AIAuthenticationError("Groq API key must not be empty")
        self._api_key = api_key
        self._model_name = model_name

    @property
    def provider_name(self) -> str:
        return "groq"

    @property
    def is_available(self) -> bool:
        return bool(self._api_key)

    def analyze(
        self,
        input_data: MultimodalInput,
        *,
        context: Optional[dict[str, Any]] = None,
    ) -> ModelResponse:
        """Submit input to Groq and return a normalised ModelResponse.

        Raises the appropriate AIError subclass on any failure.
        The API key is never included in any raised exception message.
        """
        # Build the prompt content
        content = input_data.extracted_text or (
            input_data.content
            if isinstance(input_data.content, str)
            else input_data.content.decode("utf-8", errors="replace")
        )

        prompt_parts: list[str] = []
        if context:
            prompt_parts.append(f"Context: {json.dumps(context, ensure_ascii=False)}")
        prompt_parts.append(f"Input:\n{content}")
        full_prompt = "\n".join(prompt_parts)

        # Groq uses OpenAI-compatible chat completions format
        payload = {
            "model": self._model_name,
            "messages": [
                {"role": "system", "content": _SYSTEM_INSTRUCTION},
                {"role": "user", "content": full_prompt},
            ],
            "temperature": 0.1,
            "max_tokens": 4096,
            "response_format": {"type": "json_object"},
        }
        payload_str = json.dumps(payload, ensure_ascii=False)

        # Build curl command securely (no shell string)
        cmd = [
            "curl",
            "-s",
            "--max-time", "15",
            "-w", "\n%{http_code}",
            "-X", "POST",
            "-H", "Content-Type: application/json",
            "-H", f"Authorization: Bearer {self._api_key}",
            "-d", payload_str,
            _GROQ_ENDPOINT,
        ]

        start = time.monotonic()
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=16.0)
            latency_ms = (time.monotonic() - start) * 1000.0
        except subprocess.TimeoutExpired:
            raise AITimeoutError("Groq request timed out (curl subprocess)") from None
        except Exception as exc:
            raise AIExecutionError(f"Unexpected error executing curl: {type(exc).__name__}") from None

        if res.returncode != 0:
            raise AIProviderUnavailableError(f"Network error reaching Groq (curl code {res.returncode})")

        # Parse output: body + status code
        lines = res.stdout.strip().rsplit("\n", 1)
        if len(lines) == 2 and lines[-1].isdigit():
            body, code_str = lines[0], lines[1]
            code = int(code_str)
        else:
            body = res.stdout
            code = 200

        # --- Map HTTP status codes — never include URL/key in messages ---
        if code in (401, 403):
            raise AIAuthenticationError(
                "Groq authentication failed — check GROQ_API_KEY"
            )
        if code == 404:
            raise AIExecutionError(
                f"Groq model not found: {self._model_name!r} — check GROQ_MODEL in .env"
            )
        if code == 413:
            raise AIRequestTooLargeError(
                "Groq rejected the request as too large (413) — input exceeds provider payload limits"
            )
        if code == 429:
            body_lower = body.lower()
            if any(kw in body_lower for kw in ("quota", "exhausted", "daily", "monthly", "billing", "rate limit")):
                raise AIQuotaExhaustedError(
                    "Groq quota exhausted (429) — no point retrying until quota resets"
                )
            raise AIRateLimitError("Groq rate limit exceeded (429)")
        if code >= 500:
            raise AIProviderUnavailableError(f"Groq server error ({code})")
        if code != 200:
            raise AIExecutionError(f"Groq API HTTP error ({code})")

        # --- Parse response body ---
        try:
            resp_data = json.loads(body)
            choices = resp_data.get("choices", [])
            text_content = choices[0]["message"]["content"]
            # Strip accidental markdown fences
            if text_content.startswith("```json"):
                text_content = text_content[7:].rsplit("```", 1)[0].strip()
            elif text_content.startswith("```"):
                text_content = text_content[3:].rsplit("```", 1)[0].strip()
            structured = json.loads(text_content)
        except (KeyError, IndexError, json.JSONDecodeError, ValueError) as exc:
            raise AIMalformedResponseError(
                f"Failed to parse Groq response structure: {type(exc).__name__}"
            ) from None

        usage = resp_data.get("usage", {})
        tokens = {
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0),
        }
        finish_reason = choices[0].get("finish_reason") if choices else None

        return ModelResponse(
            provider_name=self.provider_name,
            model_name=self._model_name,
            raw_content=body,
            structured_payload=structured,
            usage_tokens=tokens,
            latency_ms=latency_ms,
            metadata={"groq_finish_reason": finish_reason},
        )

    def health_check(self) -> bool:
        return self.is_available
