"""Deterministic, evidence-driven rule-based relationship extraction for CrimeLens.

Extracts:
- CALLED
- SENT_MONEY_TO
- OWNS_VEHICLE
- USED_VEHICLE
- WORKS_FOR
- LOCATED_AT
- ASSOCIATED_WITH
- PART_OF_EVENT

Enforces:
- Evidence tracing (source snippets)
- Directionality preservation (source -> target)
- Negation detection (prevents false positive relations when negated)
- Provenance tracking (source_document_id / source_record_id)
- Deduplication of identical relationship occurrences
Does NOT perform entity resolution, pattern detection, or database writes.
"""

import re
from datetime import datetime, timezone
from typing import Any, Optional

from shared.schemas.enums import EntityType, RelationshipStatus, RelationshipType
from shared.schemas.models import EntityMention, Relationship

# Relational trigger patterns
RELATION_PATTERNS = [
    (
        RelationshipType.CALLED,
        re.compile(r"(?i)\b(?:called|telephoned|phoned|dialed|placed a call to)\b"),
        {(EntityType.PERSON, EntityType.PERSON), (EntityType.PERSON, EntityType.PHONE), (EntityType.PHONE, EntityType.PHONE)},
    ),
    (
        RelationshipType.SENT_MONEY_TO,
        re.compile(
            r"(?i)\b(?:sent(?:\s+(?:money|funds|[₹$€]?\s*\d[\d,]*(?:\.\d+)?))?\s+to|"
            r"transferred(?:\s+(?:money|funds|[₹$€]?\s*\d[\d,]*(?:\.\d+)?))?\s+to|"
            r"paid(?:\s+[₹$€]?\s*\d[\d,]*(?:\.\d+)?)?\s+to|"
            r"wired(?:\s+(?:money|funds|[₹$€]?\s*\d[\d,]*(?:\.\d+)?))?\s+to)\b"
        ),
        {(EntityType.PERSON, EntityType.PERSON), (EntityType.PERSON, EntityType.BANK_ACCOUNT), (EntityType.BANK_ACCOUNT, EntityType.BANK_ACCOUNT)},
    ),
    (
        RelationshipType.OWNS_VEHICLE,
        re.compile(r"(?i)\b(?:owns(?:\s+the)?(?:\s+vehicle)?|owner of(?:\s+the)?(?:\s+vehicle)?|purchased(?:\s+the)?(?:\s+vehicle)?|registered owner of)\b"),
        {(EntityType.PERSON, EntityType.VEHICLE), (EntityType.ORGANIZATION, EntityType.VEHICLE)},
    ),
    (
        RelationshipType.USED_VEHICLE,
        re.compile(r"(?i)\b(?:used(?:\s+the)?(?:\s+vehicle)?|drove(?:\s+the)?(?:\s+vehicle)?|fled in(?:\s+the)?(?:\s+vehicle)?|seen (?:driving|in)(?:\s+the)?(?:\s+vehicle)?|travelled in(?:\s+the)?(?:\s+vehicle)?)\b"),
        {(EntityType.PERSON, EntityType.VEHICLE)},
    ),
    (
        RelationshipType.WORKS_FOR,
        re.compile(r"(?i)\b(?:works for|employed at|employed by|employee of|working (?:at|for)|works at)\b"),
        {(EntityType.PERSON, EntityType.ORGANIZATION)},
    ),
    (
        RelationshipType.LOCATED_AT,
        re.compile(r"(?i)\b(?:is located (?:at|in)|located (?:at|in)|seen (?:at|in)|spotted (?:at|in)|residing (?:at|in)|present (?:at|in)|arrested (?:at|in)|meeting at)\b"),
        {(EntityType.PERSON, EntityType.LOCATION), (EntityType.ORGANIZATION, EntityType.LOCATION), (EntityType.VEHICLE, EntityType.LOCATION)},
    ),
    (
        RelationshipType.ASSOCIATED_WITH,
        re.compile(r"(?i)\b(?:is associated with|associated with|linked to|affiliated with|partnered with)\b"),
        {
            (EntityType.PERSON, EntityType.PERSON),
            (EntityType.PERSON, EntityType.ORGANIZATION),
            (EntityType.PERSON, EntityType.PHONE),
            (EntityType.ORGANIZATION, EntityType.ORGANIZATION),
        },
    ),
    (
        RelationshipType.PART_OF_EVENT,
        re.compile(r"(?i)\b(?:participated in|attended|involved in|present (?:during|at)|part of)\b"),
        {(EntityType.PERSON, EntityType.EVENT), (EntityType.ORGANIZATION, EntityType.EVENT)},
    ),
]

# Negation detection pattern
NEGATION_PATTERN = re.compile(
    r"(?i)\b(?:did not|didn't|does not|doesn't|never|not|was not|wasn't|failed to|denied)\b"
)


def _split_sentences(text: str) -> list[str]:
    """Split text into sentences or major lines."""
    raw_sentences = re.split(r"(?<=[.!?\n])\s+", text)
    return [s.strip() for s in raw_sentences if s.strip()]


def _is_negated_between(text_span: str) -> bool:
    """Check if negation exists within a text span."""
    return bool(NEGATION_PATTERN.search(text_span))


def extract_relationships(
    text: str,
    entities: list[EntityMention],
    document_id: str,
    structured_records: Optional[list[dict[str, Any]]] = None,
    min_confidence: float = 0.5,
) -> list[Relationship]:
    """Extract evidence-backed relationships between extracted entity mentions.

    Args:
        text: Normalized document text.
        entities: List of already-extracted EntityMention instances.
        document_id: Staging document identifier.
        structured_records: Optional CDR or transaction record dictionaries.
        min_confidence: Threshold below which relationships are excluded.

    Returns:
        list[Relationship]: Extracted and validated Relationship instances.
    """
    if not entities:
        return []

    relationships: list[Relationship] = []
    seen_keys: set[tuple[str, str, RelationshipType]] = set()
    rel_counter = 1

    # Map entities by lowercase name for fast lookup
    entity_by_name: dict[str, EntityMention] = {}
    for e in entities:
        entity_by_name[e.name.lower()] = e

    # -------------------------------------------------------------
    # 1. Unstructured text-based relationship extraction
    # -------------------------------------------------------------
    sentences = _split_sentences(text)
    for sent in sentences:
        # Find which entities appear in this sentence
        present_entities: list[tuple[EntityMention, int, int]] = []
        for e in entities:
            # Case-insensitive search for entity name in sentence
            pattern = re.compile(rf"\b{re.escape(e.name)}\b", re.IGNORECASE)
            for m in pattern.finditer(sent):
                present_entities.append((e, m.start(), m.end()))

        if len(present_entities) < 2:
            continue

        # Sort present entities by their position in the sentence
        present_entities.sort(key=lambda x: x[1])

        # Evaluate ordered pairs (source, target)
        for i in range(len(present_entities)):
            for j in range(len(present_entities)):
                if i == j:
                    continue
                src_ent, src_start, src_end = present_entities[i]
                tgt_ent, tgt_start, tgt_end = present_entities[j]

                # Directionality: src appears before tgt in the text
                if src_end > tgt_start:
                    continue

                span_between = sent[src_end:tgt_start]

                # Check if negated
                prefix = sent[max(0, src_start - 30):src_start]
                if _is_negated_between(span_between) or _is_negated_between(prefix):
                    continue

                for rel_type, pattern, valid_types in RELATION_PATTERNS:
                    if (src_ent.type, tgt_ent.type) not in valid_types:
                        continue

                    if pattern.search(span_between):
                        dedup_key = (src_ent.id, tgt_ent.id, rel_type)
                        if dedup_key not in seen_keys:
                            seen_keys.add(dedup_key)

                            rel_id = f"rel_{rel_counter:03d}"
                            rel_counter += 1

                            relationships.append(
                                Relationship(
                                    id=rel_id,
                                    source_entity_id=src_ent.id,
                                    relationship=rel_type,
                                    target_entity_id=tgt_ent.id,
                                    confidence=0.95,
                                    status=RelationshipStatus.CONFIRMED,
                                    source_document_id=document_id,
                                    evidence_snippet=sent.strip(),
                                    extracted_at=datetime.now(timezone.utc),
                                )
                            )

    # -------------------------------------------------------------
    # 2. Structured CDR & Transaction records processing
    # -------------------------------------------------------------
    if structured_records:
        for rec in structured_records:
            if hasattr(rec, "__dataclass_fields__"):
                caller_val = getattr(rec, "caller", None)
                callee_val = getattr(rec, "callee", None)
                sender_val = getattr(rec, "sender", None)
                recip_val = getattr(rec, "recipient", None)
                rec_id = str(getattr(rec, "record_id", None) or f"rec_{rel_counter:03d}")
                rec_type = "CDR" if caller_val and callee_val else ("TRANSACTION" if sender_val and recip_val else "")
            else:
                caller_val = rec.get("caller")
                callee_val = rec.get("callee")
                sender_val = rec.get("sender")
                recip_val = rec.get("recipient")
                rec_id = str(rec.get("record_id") or rec.get("id") or f"rec_{rel_counter:03d}")
                rec_type = rec.get("type", "")

            # CDR records: caller -> CALLED -> callee
            if rec_type == "CDR" or (caller_val is not None and callee_val is not None):
                caller_str = str(caller_val).strip().lower()
                callee_str = str(callee_val).strip().lower()

                src_ent = entity_by_name.get(caller_str)
                tgt_ent = entity_by_name.get(callee_str)

                if src_ent and tgt_ent:
                    dedup_key = (src_ent.id, tgt_ent.id, RelationshipType.CALLED)
                    if dedup_key not in seen_keys:
                        seen_keys.add(dedup_key)
                        rel_id = f"rel_{rel_counter:03d}"
                        rel_counter += 1
                        snippet = f"CDR {rec_id}: {src_ent.name} called {tgt_ent.name}"
                        relationships.append(
                            Relationship(
                                id=rel_id,
                                source_entity_id=src_ent.id,
                                relationship=RelationshipType.CALLED,
                                target_entity_id=tgt_ent.id,
                                confidence=0.98,
                                status=RelationshipStatus.CONFIRMED,
                                source_document_id=document_id,
                                source_record_id=rec_id,
                                evidence_snippet=snippet,
                                extracted_at=datetime.now(timezone.utc),
                            )
                        )

            # Transaction records: sender -> SENT_MONEY_TO -> recipient
            elif rec_type == "TRANSACTION" or (sender_val is not None and recip_val is not None):
                sender_str = str(sender_val).strip().lower()
                recip_str = str(recip_val).strip().lower()

                src_ent = entity_by_name.get(sender_str)
                tgt_ent = entity_by_name.get(recip_str)

                if src_ent and tgt_ent:
                    dedup_key = (src_ent.id, tgt_ent.id, RelationshipType.SENT_MONEY_TO)
                    if dedup_key not in seen_keys:
                        seen_keys.add(dedup_key)
                        rel_id = f"rel_{rel_counter:03d}"
                        rel_counter += 1
                        snippet = f"Transaction {rec_id}: {src_ent.name} sent money to {tgt_ent.name}"
                        relationships.append(
                            Relationship(
                                id=rel_id,
                                source_entity_id=src_ent.id,
                                relationship=RelationshipType.SENT_MONEY_TO,
                                target_entity_id=tgt_ent.id,
                                confidence=0.98,
                                status=RelationshipStatus.CONFIRMED,
                                source_document_id=document_id,
                                source_record_id=rec_id,
                                evidence_snippet=snippet,
                                extracted_at=datetime.now(timezone.utc),
                            )
                        )

    return [r for r in relationships if r.confidence >= min_confidence]
