"""Unified entity extraction coordinator for CrimeLens.

Combines deterministic regex/rule extraction with NER extraction,
deduplicates safe overlapping candidates, and assigns valid sequential ML mention IDs.
Does NOT create relationships, resolve entities, or perform database writes.
"""

from typing import Callable, Optional

from ml.extraction.candidate_classifier import CandidateDecision, classify_entity_candidates
from ml.extraction.ner import extract_named_entities
from ml.extraction.regex import extract_regex_entities
from shared.schemas.enums import EntityType
from shared.schemas.models import EntityMention


def extract_entities(
    text: str,
    document_id: str,
    min_confidence: float = 0.5,
    ner_runner: Optional[Callable[[str], list[EntityMention]]] = None,
    return_decisions: bool = False,
) -> list[EntityMention] | tuple[list[EntityMention], list[CandidateDecision]]:
    """Extract, deduplicate, and format all entity mentions from preprocessed text.

    Args:
        text: Normalized document text.
        document_id: Staging document identifier.
        min_confidence: Threshold below which candidates are excluded.
        ner_runner: Optional external NER runner function.

    Returns:
        list[EntityMention]: Schema-compliant EntityMention instances with unique mention IDs.
    """
    if not text or not text.strip():
        return []

    # 1. Collect candidates from regex (PHONE, BANK_ACCOUNT, VEHICLE)
    regex_candidates = extract_regex_entities(text, document_id)

    # 2. Collect candidates from NER (PERSON, ORGANIZATION, LOCATION, EVENT)
    ner_candidates = extract_named_entities(text, document_id, ner_runner=ner_runner)

    all_candidates = regex_candidates + ner_candidates

    # 3. Candidate-first type classification.  This retains role/generic phrase
    # decisions internally rather than coercing them into graph nodes.
    classified_candidates, decisions = classify_entity_candidates(
        all_candidates,
        text=text,
        min_confidence=min_confidence,
    )

    # 4. Deduplicate candidates by (type, normalized_name), keeping the highest confidence
    deduped: dict[tuple[EntityType, str], EntityMention] = {}
    for cand in classified_candidates:
        key = (cand.type, cand.name.lower())
        if key not in deduped or cand.confidence > deduped[key].confidence:
            deduped[key] = cand

    # 5. Assign sequential document-level mention IDs (mention_001, mention_002, ...)
    final_mentions: list[EntityMention] = []
    for idx, cand in enumerate(deduped.values(), start=1):
        mention_id = f"mention_{idx:03d}"
        final_mentions.append(
            EntityMention(
                id=mention_id,
                type=cand.type,
                name=cand.name,
                confidence=round(cand.confidence, 4),
            )
        )

    if return_decisions:
        return final_mentions, decisions
    return final_mentions
