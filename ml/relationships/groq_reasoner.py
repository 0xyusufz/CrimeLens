"""Evidence-constrained Groq relationship candidate adapter.

Groq receives an explicitly closed world: accepted mention IDs, the frozen
relationship vocabulary, and source evidence blocks.  It returns candidates
only; the graph-quality firewall remains the authority that decides whether an
edge reaches the contract envelope.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Callable, Iterable

from shared.schemas.enums import RelationshipType
from shared.schemas.models import EntityMention


_ALLOWED_RELATIONSHIPS = [item.value for item in RelationshipType]


def build_reasoning_context(
    entities: Iterable[EntityMention],
    evidence_blocks: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "entities": [
            {"id": entity.id, "name": entity.name, "type": entity.type.value}
            for entity in entities
        ],
        "evidence_blocks": [
            {
                "id": str(block.get("id") or block.get("block_id") or ""),
                "text": str(block.get("text") or ""),
                "page": block.get("page") or block.get("page_number") or 1,
            }
            for block in evidence_blocks
            if str(block.get("text") or "").strip()
        ],
        "allowed_relationships": _ALLOWED_RELATIONSHIPS,
    }


def _parse_response(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, dict):
        return list(value.get("relationships") or [])
    if isinstance(value, list):
        return list(value)
    if not isinstance(value, str):
        return []
    raw = value.strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
    if fenced:
        raw = fenced.group(1)
    try:
        return _parse_response(json.loads(raw))
    except json.JSONDecodeError:
        return []


def generate_relationship_candidates(
    reasoner: Any,
    *,
    entities: Iterable[EntityMention],
    evidence_blocks: Iterable[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Call an injected reasoner and normalize only closed-world candidates."""
    entity_list = list(entities)
    by_id = {item.id: item for item in entity_list}
    by_name = {item.name.casefold(): item for item in entity_list}
    context = build_reasoning_context(entity_list, evidence_blocks)
    telemetry = {"seen": 0, "accepted": 0, "rejected": 0}

    try:
        if hasattr(reasoner, "reason"):
            raw_response = reasoner.reason(context)
        else:
            raw_response = reasoner(context)
    except Exception:
        return [], {"seen": 0, "accepted": 0, "rejected": 1, "reasoner_error": 1}

    normalized: list[dict[str, Any]] = []
    for raw in _parse_response(raw_response):
        telemetry["seen"] += 1
        if not isinstance(raw, dict):
            telemetry["rejected"] += 1
            continue
        source_key = str(raw.get("source_entity_id") or raw.get("source") or "").strip()
        target_key = str(raw.get("target_entity_id") or raw.get("target") or "").strip()
        source = by_id.get(source_key) or by_name.get(source_key.casefold())
        target = by_id.get(target_key) or by_name.get(target_key.casefold())
        rel_type = str(raw.get("relationship") or raw.get("type") or "").upper()
        evidence = str(raw.get("evidence_snippet") or raw.get("evidence") or "").strip()
        if source is None or target is None or source.id == target.id or rel_type not in _ALLOWED_RELATIONSHIPS or not evidence:
            telemetry["rejected"] += 1
            continue
        normalized.append(
            {
                "source": source.name,
                "target": target.name,
                "type": rel_type,
                "evidence": evidence,
                "confidence": raw.get("confidence", 0.65),
            }
        )
        telemetry["accepted"] += 1
    return normalized, telemetry


class GroqRelationshipReasoner:
    """Optional remote reasoner; it is never constructed or invoked by default."""

    def __init__(self, api_key: str | None = None, model: str = "openai/gpt-oss-20b"):
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        self.model = model
        self._client = None
        if self.api_key:
            try:
                from groq import Groq

                self._client = Groq(api_key=self.api_key)
            except ImportError:
                self._client = None

    def is_available(self) -> bool:
        return self._client is not None

    def reason(self, context: dict[str, Any]) -> dict[str, Any]:
        if self._client is None:
            return {"relationships": []}
        prompt = (
            "Return JSON only: {\"relationships\":[...]}. Use only entity IDs in the supplied "
            "context and only allowed relationship values. Every relationship requires an exact "
            "verbatim evidence snippet copied from one supplied block. If evidence is insufficient, "
            "return an empty list. Never infer a relation merely from co-occurrence.\n\n"
            + json.dumps(context, ensure_ascii=False)
        )
        response = self._client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_completion_tokens=2048,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content if response.choices else ""
        return {"relationships": _parse_response(content or "")}


__all__ = ["GroqRelationshipReasoner", "build_reasoning_context", "generate_relationship_candidates"]
