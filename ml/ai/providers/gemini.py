"""Gemini reasoning provider implementation for CrimeLens.

Transport: Subprocess + curl (due to macOS Python 3.13 TLS hang issues).
No external AI SDK required. The API key is NEVER included in exception messages,
log output, or error strings.
"""

from __future__ import annotations

import json
import subprocess
import time
from typing import Any, Optional
from urllib.parse import urlencode

from ml.ai.errors import (
    AIAuthenticationError,
    AIExecutionError,
    AIMalformedResponseError,
    AIProviderUnavailableError,
    AIQuotaExhaustedError,
    AIRateLimitError,
    AITimeoutError,
)
from ml.ai.providers.base import ReasoningModelProvider
from ml.ai.types import ModelResponse, MultimodalInput

# Endpoint template — key injected at call time, never stored in strings.
_GEMINI_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

_SYSTEM_INSTRUCTION = (
    "You are an intelligence extractor for the CrimeLens investigation platform. "
    "Return ONLY valid JSON with the following keys: "
    "entities (list), relationships (list), patterns (list), leads (list). "
    "Do NOT include markdown fences, commentary, or explanation."
)


class GeminiReasoningProvider(ReasoningModelProvider):
    """Gemini provider using curl via subprocess.

    This bypasses local Python SSL hang issues on certain macOS environments.

    Security contract:
    - The API key is stored as a private instance attribute (_api_key).
    - It is NEVER placed into exception messages, log strings, or any
      serialisable output.
    - The request URL (which contains the key as a query parameter) is
      never included in raised exceptions.
    - The subprocess call uses a list of arguments (no shell interpolation).
    """

    def __init__(self, api_key: str, model_name: str = "gemini-1.5-flash") -> None:
        if not api_key:
            raise AIAuthenticationError("Gemini API key must not be empty")
        self._api_key = api_key
        self._model_name = model_name

    @property
    def provider_name(self) -> str:
        return "gemini"

    @property
    def is_available(self) -> bool:
        return bool(self._api_key)

    # ------------------------------------------------------------------
    # Public API (ReasoningModelProvider contract)
    # ------------------------------------------------------------------

    def analyze(
        self,
        input_data: MultimodalInput,
        *,
        context: Optional[dict[str, Any]] = None,
    ) -> ModelResponse:
        """Submit input to Gemini and return a normalised ModelResponse.

        Raises the appropriate AIError subclass on any failure.
        The API key is never included in any raised exception message.
        """
        url = _GEMINI_ENDPOINT.format(model=self._model_name) + "?" + urlencode({"key": self._api_key})

        # Prefer extracted_text (pre-populated by MultimodalInput.from_text())
        content = input_data.extracted_text or (
            input_data.content
            if isinstance(input_data.content, str)
            else input_data.content.decode("utf-8", errors="replace")
        )

        prompt_parts: list[str] = []
        if context:
            prompt_parts.append(f"Context: {json.dumps(context, ensure_ascii=False)}")
        prompt_parts.append(f"Input:\n{content}")
        prompt = "\n".join(prompt_parts)

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "systemInstruction": {"parts": [{"text": _SYSTEM_INSTRUCTION}]},
            "generationConfig": {"responseMimeType": "application/json"},
        }
        payload_str = json.dumps(payload, ensure_ascii=False)

        # Build curl command securely (no shell string)
        cmd = [
            "curl",
            "-s",                  # Silent
            "--max-time", "15",    # Hard timeout of 15 seconds
            "-w", "\n%{http_code}", # Append HTTP code to stdout
            "-X", "POST",
            "-H", "Content-Type: application/json",
            "-d", payload_str,
            url,
        ]

        start = time.monotonic()
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=16.0)
            latency_ms = (time.monotonic() - start) * 1000.0
        except subprocess.TimeoutExpired:
            raise AITimeoutError("Gemini request timed out (curl subprocess)") from None
        except Exception as exc:
            raise AIExecutionError(f"Unexpected error executing curl: {type(exc).__name__}") from None

        if res.returncode != 0:
            raise AIProviderUnavailableError(f"Network error reaching Gemini (curl code {res.returncode})")

        # Parse output: body + status code
        lines = res.stdout.strip().rsplit("\n", 1)
        if len(lines) == 2 and lines[-1].isdigit():
            body, code_str = lines[0], lines[1]
            code = int(code_str)
        else:
            # Fallback if the output doesn't match expected pattern
            body = res.stdout
            code = 200

        # --- Map HTTP status codes — never include URL/key in messages ---
        if code in (401, 403):
            raise AIAuthenticationError(
                "Gemini authentication failed — check GEMINI_API_KEY"
            )
        if code == 404:
            raise AIExecutionError(
                f"Gemini model not found: {self._model_name!r} — check GEMINI_MODEL in .env"
            )
        if code == 429:
            # 429 may be a brief rate-limit or permanent quota exhaustion.
            # Inspect the body for quota-exhaustion signals so the client
            # can skip retries immediately instead of waiting 15 s × 3 times.
            body_lower = body.lower()
            if any(kw in body_lower for kw in ("quota", "exhausted", "daily", "monthly", "billing")):
                raise AIQuotaExhaustedError(
                    "Gemini quota exhausted (429) — no point retrying until quota resets"
                )
            raise AIRateLimitError("Gemini rate limit exceeded (429)")
        if code >= 500:
            raise AIProviderUnavailableError(f"Gemini server error ({code})")
        if code != 200:
            raise AIExecutionError(f"Gemini API HTTP error ({code})")

        # --- Parse response body ---
        try:
            resp_data = json.loads(body)
            text_content = resp_data["candidates"][0]["content"]["parts"][0]["text"]
            # Strip accidental markdown fences
            if text_content.startswith("```json"):
                text_content = text_content[7:].rsplit("```", 1)[0].strip()
            elif text_content.startswith("```"):
                text_content = text_content[3:].rsplit("```", 1)[0].strip()
            structured = json.loads(text_content)
        except (KeyError, IndexError, json.JSONDecodeError, ValueError) as exc:
            raise AIMalformedResponseError(
                f"Failed to parse Gemini response structure: {type(exc).__name__}"
            ) from None

        usage = resp_data.get("usageMetadata", {})
        tokens = {
            "prompt_tokens": usage.get("promptTokenCount", 0),
            "completion_tokens": usage.get("candidatesTokenCount", 0),
            "total_tokens": usage.get("totalTokenCount", 0),
        }
        finish_reason = resp_data["candidates"][0].get("finishReason")

        return ModelResponse(
            provider_name=self.provider_name,
            model_name=self._model_name,
            raw_content=body,
            structured_payload=structured,
            usage_tokens=tokens,
            latency_ms=latency_ms,
            metadata={"gemini_finish_reason": finish_reason},
        )

    def health_check(self) -> bool:
        return self.is_available
