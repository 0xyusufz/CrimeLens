"""Multimodal input and provider-neutral response representations for CrimeLens AI.

These types represent internal AI model communication data structures.
They do NOT replace shared CrimeLens schemas (EntityMention, Relationship, etc.)
and MUST NEVER generate database UUIDs, case_ids, or canonical persistence keys.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from ml.ai.errors import AIUnsupportedInputError


class InputType(str, Enum):
    """Supported multimodal input categories."""

    TEXT = "TEXT"
    IMAGE = "IMAGE"
    PDF = "PDF"
    STRUCTURED = "STRUCTURED"


_MIME_BY_EXTENSION = {
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".tiff": "image/tiff",
    ".tif": "image/tiff",
    ".csv": "text/csv",
    ".json": "application/json",
}


@dataclass(frozen=True)
class MultimodalInput:
    """Safe, typed container for multimodal content sent to model providers."""

    input_type: InputType
    content: bytes | str
    mime_type: str
    filename: Optional[str] = None
    extracted_text: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.content:
            raise AIUnsupportedInputError("MultimodalInput content cannot be empty")
        if isinstance(self.content, str) and not self.content.strip():
            raise AIUnsupportedInputError("MultimodalInput text content cannot be blank whitespace")
        if not isinstance(self.content, (bytes, str)):
            raise AIUnsupportedInputError(
                f"MultimodalInput content must be bytes or str, got {type(self.content).__name__}"
            )

    @property
    def byte_size(self) -> int:
        if isinstance(self.content, bytes):
            return len(self.content)
        return len(self.content.encode("utf-8"))

    @classmethod
    def from_text(
        cls,
        text: str,
        *,
        filename: Optional[str] = None,
        mime_type: str = "text/plain",
        metadata: Optional[dict[str, Any]] = None,
    ) -> MultimodalInput:
        if not isinstance(text, str):
            raise AIUnsupportedInputError(f"from_text requires str, got {type(text).__name__}")
        return cls(
            input_type=InputType.TEXT,
            content=text,
            mime_type=mime_type,
            filename=filename,
            extracted_text=text,
            metadata=metadata or {},
        )

    @classmethod
    def from_image(
        cls,
        data: bytes,
        *,
        mime_type: str = "image/png",
        filename: Optional[str] = None,
        extracted_text: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> MultimodalInput:
        if not isinstance(data, bytes):
            raise AIUnsupportedInputError(f"from_image requires bytes, got {type(data).__name__}")
        return cls(
            input_type=InputType.IMAGE,
            content=data,
            mime_type=mime_type,
            filename=filename,
            extracted_text=extracted_text,
            metadata=metadata or {},
        )

    @classmethod
    def from_pdf(
        cls,
        data: bytes,
        *,
        filename: Optional[str] = None,
        extracted_text: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> MultimodalInput:
        if not isinstance(data, bytes):
            raise AIUnsupportedInputError(f"from_pdf requires bytes, got {type(data).__name__}")
        return cls(
            input_type=InputType.PDF,
            content=data,
            mime_type="application/pdf",
            filename=filename,
            extracted_text=extracted_text,
            metadata=metadata or {},
        )

    @classmethod
    def from_structured(
        cls,
        records: list[dict[str, Any]] | dict[str, Any],
        *,
        filename: Optional[str] = None,
        mime_type: str = "application/json",
        metadata: Optional[dict[str, Any]] = None,
    ) -> MultimodalInput:
        if not isinstance(records, (list, dict)):
            raise AIUnsupportedInputError(
                f"from_structured requires list or dict, got {type(records).__name__}"
            )
        serialized = json.dumps(records, ensure_ascii=False)
        meta = dict(metadata or {})
        meta["record_count"] = len(records) if isinstance(records, list) else 1
        return cls(
            input_type=InputType.STRUCTURED,
            content=serialized,
            mime_type=mime_type,
            filename=filename,
            extracted_text=serialized,
            metadata=meta,
        )

    @classmethod
    def from_bytes(
        cls,
        data: bytes,
        input_type: InputType,
        *,
        mime_type: Optional[str] = None,
        filename: Optional[str] = None,
        extracted_text: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> MultimodalInput:
        if not isinstance(data, bytes):
            raise AIUnsupportedInputError(f"from_bytes requires bytes, got {type(data).__name__}")
        resolved_mime = mime_type
        if not resolved_mime and filename:
            ext = "." + filename.lower().split(".")[-1] if "." in filename else ""
            resolved_mime = _MIME_BY_EXTENSION.get(ext, "application/octet-stream")
        return cls(
            input_type=input_type,
            content=data,
            mime_type=resolved_mime or "application/octet-stream",
            filename=filename,
            extracted_text=extracted_text,
            metadata=metadata or {},
        )


@dataclass(frozen=True)
class ModelResponse:
    """Normalized, vendor-neutral model response container.

    External model responses are strictly UNTRUSTED. This object encapsulates
    raw model text and parsed candidate intelligence for subsequent deterministic
    validation by the CrimeLens pipeline.
    """

    provider_name: str
    model_name: str
    raw_content: Optional[str] = None
    structured_payload: dict[str, Any] = field(default_factory=dict)
    usage_tokens: Optional[dict[str, int]] = None
    latency_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def get_candidate_entities(self) -> list[dict[str, Any]]:
        """Return raw candidate entity mentions proposed by the model."""
        candidates = self.structured_payload.get("entities")
        if isinstance(candidates, list):
            return [c for c in candidates if isinstance(c, dict)]
        return []

    def get_candidate_relationships(self) -> list[dict[str, Any]]:
        """Return raw candidate relationships proposed by the model."""
        candidates = self.structured_payload.get("relationships")
        if isinstance(candidates, list):
            return [c for c in candidates if isinstance(c, dict)]
        return []

    def get_candidate_patterns(self) -> list[dict[str, Any]]:
        """Return raw candidate suspicious patterns proposed by the model."""
        candidates = self.structured_payload.get("patterns")
        if isinstance(candidates, list):
            return [c for c in candidates if isinstance(c, dict)]
        return []

    def get_candidate_leads(self) -> list[dict[str, Any]]:
        """Return raw candidate investigative leads proposed by the model."""
        candidates = self.structured_payload.get("leads")
        if isinstance(candidates, list):
            return [c for c in candidates if isinstance(c, dict)]
        return []
