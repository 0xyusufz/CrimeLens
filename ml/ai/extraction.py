"""AI-assisted Entity and Information Extraction for CrimeLens (Phase 3).

Consumes Phase 2 DocumentUnderstanding context to propose candidate entity mentions
across the 7 frozen CrimeLens entity categories:
- PERSON, ORGANIZATION, PHONE, BANK_ACCOUNT, VEHICLE, LOCATION, EVENT

CRITICAL SAFETY & CONTRACT RULES:
1. AI output is strictly UNTRUSTED candidate intelligence.
2. Grounded: Validates candidates against source context to defend against hallucinations.
3. Strict Schema: Rejects unsupported types (e.g. CRIMINAL, SUSPECT, THREAT_LEVEL).
4. Bounded Confidence: Enforces 0.0 <= confidence <= 1.0 (no risk scoring).
5. Isolated: ZERO database UUIDs, zero case IDs, zero database/Neo4j access.
6. Non-Destructive: Complements, never blindly overwrites, deterministic extraction.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Optional

from ml.ai.client.client import AIClient
from ml.ai.document_understanding import DocumentUnderstanding
from ml.ai.errors import AIError
from ml.ai.types import MultimodalInput
from ml.config import MLConfig, default_config
from ml.extraction.ner import clean_entity_name
from ml.resolution.resolver import normalize_account, normalize_phone, normalize_vehicle
from shared.schemas.enums import EntityType
from shared.schemas.models import EntityMention

SUPPORTED_ENTITY_TYPES = {et.value: et for et in EntityType}


@dataclass(frozen=True)
class AIEntityCandidate:
    """Intermediate candidate entity proposed by AI or deterministic extraction."""

    type: EntityType
    name: str
    confidence: float
    raw_value: Optional[str] = None
    page_number: Optional[int] = None
    section_title: Optional[str] = None
    evidence_snippet: Optional[str] = None
    extraction_method: str = "ai"
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.name or not self.name.strip():
            raise ValueError("Candidate entity name cannot be empty")
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(f"Confidence must be between 0.0 and 1.0, got {self.confidence}")


class AIEntityExtractor:
    """Extracts candidate entities using Phase 1 AIClient and Phase 2 DocumentUnderstanding."""

    def __init__(
        self,
        client: Optional[AIClient] = None,
        config: Optional[MLConfig] = None,
    ) -> None:
        self.client = client
        self.config = config or default_config

    def get_raw_candidates(
        self,
        doc_understanding: DocumentUnderstanding,
        *,
        context: Optional[dict[str, Any]] = None,
    ) -> list[dict[str, Any]]:
        """Fetch raw unvalidated candidate dictionaries directly from provider response."""
        if not self.config.ai_enabled or self.client is None or not self.client.provider.is_available:
            return []

        meta = {
            **(context or {}),
            "document_id": doc_understanding.document_id,
            "filename": doc_understanding.filename,
            "document_type": doc_understanding.document_type,
            "page_count": doc_understanding.page_count,
            "task": "entity_extraction",
        }

        m_input = MultimodalInput.from_text(
            doc_understanding.full_text or "Empty document",
            filename=doc_understanding.filename,
            metadata=meta,
        )

        try:
            response = self.client.analyze(m_input, context=meta)
        except AIError:
            return []

        from ml.ai.response_parser import AIResponseParser

        parsed_candidates = AIResponseParser.extract_candidates(
            response.raw_content or response.structured_payload
        )
        return parsed_candidates.get("entities") or response.get_candidate_entities()

    def extract_candidates(
        self,
        doc_understanding: DocumentUnderstanding,
        *,
        context: Optional[dict[str, Any]] = None,
    ) -> list[AIEntityCandidate]:
        """Propose candidate entity mentions from document understanding context.

        Args:
            doc_understanding: Phase 2 DocumentUnderstanding object.
            context: Optional contextual parameters.

        Returns:
            list[AIEntityCandidate]: Verified candidate entity mentions.
        """
        raw_candidates = self.get_raw_candidates(doc_understanding, context=context)
        return self._parse_and_validate_candidates(raw_candidates, doc_understanding)

    def _parse_and_validate_candidates(
        self,
        raw_candidates: list[dict[str, Any]],
        doc: DocumentUnderstanding,
    ) -> list[AIEntityCandidate]:
        valid_candidates: list[AIEntityCandidate] = []
        full_text_lower = doc.full_text.lower()

        for raw in raw_candidates:
            if not isinstance(raw, dict):
                continue

            raw_type = str(raw.get("type", "")).strip().upper()
            raw_name = str(raw.get("name", "")).strip()

            # 1. Type validation: Strictly enforce CrimeLens 7-entity taxonomy
            if raw_type not in SUPPORTED_ENTITY_TYPES:
                # Reject unsupported types (e.g. CRIMINAL, SUSPECT, GANG)
                continue

            entity_type = SUPPORTED_ENTITY_TYPES[raw_type]

            # 2. Name validation
            if not raw_name or len(raw_name) > 255:
                continue

            # 3. Confidence parsing and bounding
            try:
                conf = float(raw.get("confidence", 0.8))
                if conf < 0.0 or conf > 1.0:
                    continue
            except (ValueError, TypeError):
                continue

            # 4. Hallucination defense: Grounding check
            # The candidate name or its significant tokens must exist in the source document
            if not self._is_grounded_in_source(raw_name, full_text_lower, entity_type):
                continue

            # 5. Page number preservation
            page_num = raw.get("page_number")
            if isinstance(page_num, int) and 1 <= page_num <= doc.page_count:
                valid_page = page_num
            else:
                # Infer page from text match if possible
                valid_page = self._find_page_for_entity(raw_name, doc)

            # 6. Evidence snippet preservation
            snippet = raw.get("evidence_snippet")
            if not snippet or not isinstance(snippet, str):
                snippet = self._extract_snippet_from_doc(raw_name, doc)

            valid_candidates.append(
                AIEntityCandidate(
                    type=entity_type,
                    name=raw_name,
                    confidence=round(conf, 4),
                    raw_value=raw_name,
                    page_number=valid_page,
                    section_title=raw.get("section_title"),
                    evidence_snippet=snippet,
                    extraction_method="ai",
                    metadata=raw.get("metadata", {}),
                )
            )

        return valid_candidates

    def _is_grounded_in_source(self, name: str, source_text_lower: str, entity_type: EntityType) -> bool:
        """Verify candidate text exists in source material to protect against hallucination."""
        name_lower = name.lower().strip()
        if name_lower in source_text_lower:
            return True

        # Normalized identifier checks
        if entity_type == EntityType.PHONE:
            digits = "".join(ch for ch in name if ch.isdigit())
            if len(digits) >= 10 and digits[-10:] in "".join(ch for ch in source_text_lower if ch.isdigit()):
                return True
        elif entity_type in (EntityType.BANK_ACCOUNT, EntityType.VEHICLE):
            compact = "".join(name_lower.split())
            if compact in "".join(source_text_lower.split()):
                return True

        # Multi-word name token overlap (for persons/orgs: at least 70% of non-trivial words present)
        tokens = [t for t in name_lower.split() if len(t) > 2]
        if tokens:
            matches = sum(1 for t in tokens if t in source_text_lower)
            if matches / len(tokens) >= 0.7:
                return True

        return False

    def _find_page_for_entity(self, name: str, doc: DocumentUnderstanding) -> Optional[int]:
        name_lower = name.lower()
        for page in doc.pages:
            if name_lower in page.text.lower():
                return page.page_number
        return None

    def _extract_snippet_from_doc(self, name: str, doc: DocumentUnderstanding) -> Optional[str]:
        name_lower = name.lower()
        idx = doc.full_text.lower().find(name_lower)
        if idx != -1:
            start = max(0, idx - 40)
            end = min(len(doc.full_text), idx + len(name) + 40)
            snippet = doc.full_text[start:end].strip()
            if start > 0:
                snippet = "..." + snippet
            if end < len(doc.full_text):
                snippet = snippet + "..."
            return snippet
        return None


class EntityReconciler:
    """Reconciles deterministic and AI candidate entities into standard EntityMention objects."""

    def reconcile(
        self,
        deterministic_mentions: list[EntityMention],
        ai_candidates: list[AIEntityCandidate],
        *,
        min_confidence: float = 0.5,
    ) -> list[EntityMention]:
        """Merge, deduplicate, and assign sequential mention IDs to reconciled candidates.

        Args:
            deterministic_mentions: Mentions extracted by regex and rule-based NER.
            ai_candidates: Candidate mentions proposed by AI.
            min_confidence: Minimum threshold for inclusion.

        Returns:
            list[EntityMention]: Final deduplicated, sequentially indexed EntityMention list.
        """
        reconciled: dict[tuple[EntityType, str], dict[str, Any]] = {}

        # 1. Ingest deterministic candidates (established baseline)
        for m in deterministic_mentions:
            if m.confidence < min_confidence:
                continue
            norm_name = self._normalize_candidate_name(m.type, m.name)
            key = (m.type, norm_name)
            reconciled[key] = {
                "type": m.type,
                "name": m.name,
                "confidence": m.confidence,
                "method": "deterministic",
            }

        # 2. Ingest AI candidates (supplementary)
        for cand in ai_candidates:
            if cand.confidence < min_confidence:
                continue
            norm_name = self._normalize_candidate_name(cand.type, cand.name)
            key = (cand.type, norm_name)

            if key in reconciled:
                # Reconcile existing candidate: reinforce confidence
                existing = reconciled[key]
                combined_conf = max(existing["confidence"], cand.confidence)
                # If both agreed, increase confidence slightly
                combined_conf = min(1.0, combined_conf + 0.02)
                existing["confidence"] = round(combined_conf, 4)
                existing["method"] = "reconciled"
            else:
                # Add new contextual candidate proposed by AI
                reconciled[key] = {
                    "type": cand.type,
                    "name": cand.name,
                    "confidence": cand.confidence,
                    "method": "ai",
                }

        # 3. Format as schema-compliant EntityMention objects with sequential staging IDs
        final_mentions: list[EntityMention] = []
        for idx, item in enumerate(reconciled.values(), start=1):
            mention_id = f"mention_{idx:03d}"
            final_mentions.append(
                EntityMention(
                    id=mention_id,
                    type=item["type"],
                    name=item["name"],
                    confidence=item["confidence"],
                )
            )

        return final_mentions

    def _normalize_candidate_name(self, entity_type: EntityType, name: str) -> str:
        trimmed = clean_entity_name(name)
        if entity_type == EntityType.PHONE:
            return normalize_phone(trimmed)
        if entity_type == EntityType.BANK_ACCOUNT:
            return normalize_account(trimmed)
        if entity_type == EntityType.VEHICLE:
            return normalize_vehicle(trimmed)
        return trimmed.lower()
