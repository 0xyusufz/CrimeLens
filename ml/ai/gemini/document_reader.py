"""Multimodal document understanding adapter for Gemini.

Gemini is treated as an interpreter.  Its output is restricted to candidate
document facts and remains subject to local candidate classification and the
relationship firewall.  The adapter is opt-in and supports a test/injected
runner, so evidence processing remains usable without a cloud key.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Callable


_ALLOWED_ENTITY_TYPES = {
    "PERSON",
    "ORGANIZATION",
    "LOCATION",
    "PHONE",
    "BANK_ACCOUNT",
    "VEHICLE",
    "EVENT",
    "ROLE",
}
_MIME_TYPES = {
    "PDF": "application/pdf",
    "IMAGE": "image/png",
}
_MAX_INLINE_DOCUMENT_BYTES = 20 * 1024 * 1024


class GeminiDocumentReader:
    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        runner: Callable[[dict[str, Any]], Any] | None = None,
    ):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model = model or os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        self.runner = runner
        self._client = None
        if self.api_key and runner is None:
            try:
                from google import genai

                self._client = genai.Client(api_key=self.api_key)
            except ImportError:
                self._client = None

    def is_available(self) -> bool:
        return self.runner is not None or self._client is not None

    def _prompt(self, package: dict[str, Any]) -> str:
        public_package = {key: value for key, value in package.items() if key != "document_bytes"}
        return (
            "You are a document-understanding assistant for evidence analysis. "
            "Return JSON only with fields document_type, sections, entities, and relationships. "
            "Entities are candidates only. Use ROLE for job titles/generic roles, never PERSON. "
            "Relationships must use only the supplied evidence text verbatim and may only use: "
            "CALLED, SENT_MONEY_TO, OWNS_VEHICLE, USED_VEHICLE, WORKS_FOR, LOCATED_AT, "
            "ASSOCIATED_WITH, PART_OF_EVENT. If unsupported, omit the relation.\n\n"
            + json.dumps(public_package, ensure_ascii=False)
        )

    def read(self, package: dict[str, Any]) -> dict[str, Any]:
        if self.runner is not None:
            return self._normalize(self.runner(package))
        if self._client is None:
            return {"document_type": "UNKNOWN", "sections": [], "entities": [], "relationships": []}
        contents: list[Any] = [self._prompt(package)]
        document_bytes = package.get("document_bytes")
        file_kind = str(package.get("file_kind") or "").upper()
        if (
            isinstance(document_bytes, bytes)
            and document_bytes
            and len(document_bytes) <= _MAX_INLINE_DOCUMENT_BYTES
            and file_kind in _MIME_TYPES
        ):
            try:
                from google.genai import types

                contents.append(
                    types.Part.from_bytes(data=document_bytes, mime_type=_MIME_TYPES[file_kind])
                )
            except (AttributeError, ImportError):
                # Text/page metadata remains an evidence-preserving fallback.
                pass
        response = self._client.models.generate_content(
            model=self.model,
            contents=contents,
            config={"response_mime_type": "application/json"},
        )
        return self._normalize(response.text or "")

    def extract(self, text: str, document_id: str) -> dict[str, Any]:
        """Compatibility hook used by the existing candidate-first pipeline."""
        return self.read(
            {
                "document_id": document_id,
                "text": text,
                "pages": [{"page": 1, "text": text}],
            }
        )

    @staticmethod
    def _normalize(value: Any) -> dict[str, Any]:
        if isinstance(value, str):
            raw = value.strip()
            fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
            if fenced:
                raw = fenced.group(1)
            try:
                value = json.loads(raw)
            except json.JSONDecodeError:
                value = {}
        if not isinstance(value, dict):
            value = {}
        entities = []
        for item in value.get("entities") or []:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or item.get("text") or "").strip()
            entity_type = str(item.get("type") or item.get("candidate_type") or "").upper()
            if name and entity_type in _ALLOWED_ENTITY_TYPES:
                entities.append(
                    {
                        "name": name,
                        "type": entity_type,
                        "confidence": item.get("confidence", 0.7),
                    }
                )
        return {
            "document_type": str(value.get("document_type") or "UNKNOWN"),
            "sections": list(value.get("sections") or value.get("pages") or []),
            "entities": entities,
            "relationships": list(value.get("relationships") or []),
        }


__all__ = ["GeminiDocumentReader"]
