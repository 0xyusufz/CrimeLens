"""Normalized error hierarchy for CrimeLens AI / Multimodal foundation.

All exceptions in this module guarantee that sensitive values such as API keys
and credentials are never included in exception messages or string representations.
"""

from __future__ import annotations

import re
from typing import Any, Optional

_KEY_VALUE_PATTERN = re.compile(
    r"(?i)(api[_-]?key|secret|token|password|bearer|auth)\s*[:=]\s*['\"]?([a-zA-Z0-9_\-\.]{8,})['\"]?"
)
_TOKEN_PATTERNS = [
    re.compile(r"(?i)\bsk-[a-zA-Z0-9]{20,}\b"),
    re.compile(r"(?i)\bAIza[0-9A-Za-z\-_]{35}\b"),
]


def redact_secrets(text: str) -> str:
    """Strip potential API keys, tokens, or credentials from error text."""
    if not text:
        return text
    sanitized = _KEY_VALUE_PATTERN.sub(r"\1=***REDACTED***", text)
    for pattern in _TOKEN_PATTERNS:
        sanitized = pattern.sub("***REDACTED***", sanitized)
    return sanitized



class AIError(Exception):
    """Base exception for all CrimeLens AI operations."""

    def __init__(self, message: str, *, details: Optional[dict[str, Any]] = None) -> None:
        self.raw_message = message
        self.sanitized_message = redact_secrets(message)
        self.details = self._sanitize_details(details or {})
        super().__init__(self.sanitized_message)

    def _sanitize_details(self, details: dict[str, Any]) -> dict[str, Any]:
        sanitized = {}
        for k, v in details.items():
            k_str = str(k).lower()
            if any(term in k_str for term in ("key", "secret", "token", "password", "auth", "credential")):
                sanitized[k] = "***REDACTED***"
            elif isinstance(v, str):
                sanitized[k] = redact_secrets(v)
            else:
                sanitized[k] = v
        return sanitized

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.sanitized_message!r})"


class AIProviderUnavailableError(AIError):
    """Raised when a requested model provider is unavailable, offline, or unregistered."""


class AIConfigurationError(AIError):
    """Raised when AI configuration is invalid, missing required options, or misconfigured."""


class AIAuthenticationError(AIError):
    """Raised when model provider rejects authentication or API credentials."""


class AITimeoutError(AIError):
    """Raised when an external model request exceeds the configured bounded timeout."""


class AIRateLimitError(AIError):
    """Raised when provider rate limit is exceeded (may succeed after brief back-off)."""


class AIQuotaExhaustedError(AIRateLimitError):
    """Raised when the provider quota is fully exhausted (e.g. daily/monthly limit).

    Subclasses AIRateLimitError so that catch-all handlers still catch it,
    but the client treats it as non-retrying: retrying won't help until quota resets.
    """


class AIMalformedResponseError(AIError):
    """Raised when model response is corrupt, unparseable, or missing required payload structure."""


class AIUnsupportedInputError(AIError):
    """Raised when input format, MIME type, or data payload is unsupported or exceeds safe limits."""


class AIExecutionError(AIError):
    """Raised when provider execution fails due to remote server error or unhandled model fault."""
