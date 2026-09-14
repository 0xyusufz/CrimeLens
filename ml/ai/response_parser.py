"""Phase 7 — Safe AI Response Parser.

Parses raw, untrusted model outputs into structured candidate dictionaries while
enforcing strict safety constraints:
1. Untrusted Input: Raw provider output is treated as completely untrusted.
2. Resilience: Safely handles empty strings, nulls, lists, dicts, truncated JSON,
   markdown codeblocks, unexpected nested structures, and type mismatches without
   crashing the pipeline.
3. Chain-of-Thought Firewall: Strips hidden thinking blocks (<thought>, <reasoning>,
   `thought`, `reasoning_content`, `chain_of_thought`) so internal model deliberation
   is never persisted or exposed.
4. Structured Payload Normalization: Normalizes extracted candidate lists for entities,
   relationships, patterns, and leads.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Patterns identifying internal model reasoning/chain-of-thought blocks
_COT_TAG_PATTERNS = [
    re.compile(r"<thought>.*?</thought>", re.DOTALL | re.IGNORECASE),
    re.compile(r"<reasoning>.*?</reasoning>", re.DOTALL | re.IGNORECASE),
    re.compile(r"<scratchpad>.*?</scratchpad>", re.DOTALL | re.IGNORECASE),
    re.compile(r"```thinking.*?```", re.DOTALL | re.IGNORECASE),
]

# Keys in structured JSON that represent internal chain-of-thought
_COT_KEYS = {
    "thought",
    "thoughts",
    "reasoning",
    "reasoning_content",
    "chain_of_thought",
    "internal_thoughts",
    "scratchpad",
    "thinking",
}


class AIResponseParser:
    """Safely extracts candidate intelligence from raw, untrusted AI provider outputs."""

    @classmethod
    def sanitize_raw_content(cls, raw_content: Optional[str]) -> str:
        """Strip hidden thinking tags and normalize raw text."""
        if not raw_content or not isinstance(raw_content, str):
            return ""

        cleaned = raw_content
        for pattern in _COT_TAG_PATTERNS:
            cleaned = pattern.sub("", cleaned)

        return cleaned.strip()

    @classmethod
    def parse_json_safely(cls, content: Any) -> dict[str, Any]:
        """Safely parse content into a dictionary, handling JSON strings, codeblocks, or existing dicts.

        Never raises exceptions; returns empty dict on invalid or unparseable input.
        """
        if content is None:
            return {}

        if isinstance(content, dict):
            return cls._sanitize_payload_dict(content)

        if not isinstance(content, str):
            return {}

        cleaned = cls.sanitize_raw_content(content)
        if not cleaned:
            return {}

        # Strip markdown json code block fences if present
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r"\s*```$", "", cleaned)
            cleaned = cleaned.strip()

        # Attempt direct JSON parsing
        try:
            parsed = json.loads(cleaned)
            if isinstance(parsed, dict):
                return cls._sanitize_payload_dict(parsed)
            # If parsed into a list, wrap in dict if elements are candidates
            if isinstance(parsed, list):
                return cls._handle_list_payload(parsed)
            return {}
        except json.JSONDecodeError:
            pass

        # Attempt to extract outermost JSON object via regex heuristic
        match = re.search(r"(\{.*\})", cleaned, re.DOTALL)
        if match:
            try:
                candidate_json = match.group(1)
                parsed = json.loads(candidate_json)
                if isinstance(parsed, dict):
                    return cls._sanitize_payload_dict(parsed)
            except json.JSONDecodeError:
                pass

        # If completely unparseable, log warning and return empty dictionary
        logger.warning("Failed to parse raw AI response as JSON: %s", cleaned[:120])
        return {}

    @classmethod
    def _handle_list_payload(cls, items: list[Any]) -> dict[str, Any]:
        """Convert a list payload into categorized dictionary if applicable."""
        dict_items = [item for item in items if isinstance(item, dict)]
        if not dict_items:
            return {}

        # Check if items look like entities or relationships
        if any("relationship" in it or "source_entity_id" in it or "target_entity_id" in it for it in dict_items):
            return {"relationships": dict_items}
        if any("type" in it and "name" in it for it in dict_items):
            return {"entities": dict_items}

        return {"items": dict_items}

    @classmethod
    def _sanitize_payload_dict(cls, payload: dict[str, Any]) -> dict[str, Any]:
        """Recursively sanitize dictionary to remove internal chain-of-thought keys."""
        sanitized: dict[str, Any] = {}
        for k, v in payload.items():
            k_lower = str(k).lower().strip()
            # Drop private chain-of-thought keys from top level
            if k_lower in _COT_KEYS:
                continue

            if isinstance(v, dict):
                sanitized[k] = cls._sanitize_payload_dict(v)
            elif isinstance(v, list):
                sanitized[k] = [
                    cls._sanitize_payload_dict(item) if isinstance(item, dict) else item
                    for item in v
                ]
            else:
                sanitized[k] = v

        return sanitized

    @classmethod
    def extract_candidates(cls, payload: Any) -> dict[str, list[dict[str, Any]]]:
        """Extract and structure candidate entities, relationships, patterns, and leads.

        Guarantees returned dict contains lists of dictionaries only.
        """
        parsed = cls.parse_json_safely(payload)

        def _safe_list(key: str) -> list[dict[str, Any]]:
            val = parsed.get(key)
            if isinstance(val, list):
                return [item for item in val if isinstance(item, dict)]
            if isinstance(val, dict):
                # Single candidate wrapped in dict
                return [val]
            return []

        return {
            "entities": _safe_list("entities"),
            "relationships": _safe_list("relationships"),
            "patterns": _safe_list("patterns"),
            "leads": _safe_list("leads"),
        }
