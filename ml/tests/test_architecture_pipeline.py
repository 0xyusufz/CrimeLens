"""Regression guards for the precision-first architecture layers."""

from datetime import datetime, timezone

from ml.evaluation.metrics import score_prediction
from ml.ocr.confidence import apply_ocr_confidence_to_entities
from ml.pipeline import process_document
from ml.resolution.case_memory import propose_case_memory_links
from shared.schemas.enums import EntityType, RelationshipStatus, RelationshipType
from shared.schemas.models import EntityMention, Relationship


def test_generic_role_is_not_promoted_to_a_person_node():
    result = process_document(
        document_id="role_guard_001",
        text="Rajesh Kumar, an English lecturer at XYZ College, called Amit Sharma.",
        return_full_analysis=True,
    )
    persons = {entity.name for entity in result["entities"] if entity.type == EntityType.PERSON}
    assert "English lecturer" not in persons
    assert "Rajesh Kumar" in persons
    assert any(
        item["proposed_type"] == "ROLE" and item["text"] == "english lecturer"
        for item in result["entity_candidate_decisions"]
    )


def test_ai_relationship_is_quarantined_from_the_accepted_graph():
    def document_reader(_: str, __: str):
        return {
            "entities": [],
            "relationships": [
                {
                    "source": "Priya Verma",
                    "target": "Nikhil Rao",
                    "type": "CALLED",
                    "evidence": "Priya Verma called Nikhil Rao.",
                    "confidence": 0.9,
                }
            ],
        }

    result = process_document(
        document_id="candidate_guard_001",
        text="Priya Verma called Nikhil Rao.",
        return_full_analysis=True,
        document_understanding_runner=document_reader,
    )
    assert all(item.status != RelationshipStatus.PREDICTED for item in result["relationships"])
    assert len(result["candidate_relationships"]) == 1
    assert result["candidate_relationships"][0].status == RelationshipStatus.PREDICTED


def test_low_ocr_confidence_reduces_entity_confidence():
    entity = EntityMention(
        id="mention_001", type=EntityType.PERSON, name="Amit Kumar", confidence=0.95
    )
    adjusted = apply_ocr_confidence_to_entities(
        [entity],
        [{"text": "Amit Kumar", "confidence": 0.54}],
    )
    assert 0.5 < adjusted[0].confidence < entity.confidence


def test_case_memory_exact_phone_is_proposed_as_strong_link():
    new_mention = EntityMention(
        id="mention_001", type=EntityType.PHONE, name="+91 98765 43210", confidence=0.9
    )
    proposals = propose_case_memory_links(
        [new_mention],
        [
            {
                "canonical_entity_id": "entity_existing",
                "id": "memory_001",
                "type": "PHONE",
                "name": "9876543210",
            }
        ],
    )
    assert proposals[0].canonical_entity_id == "entity_existing"
    assert proposals[0].requires_review is False


def test_metric_scoring_reports_entity_and_relationship_f1_separately():
    entities = [
        EntityMention(id="a", type=EntityType.PERSON, name="Priya Verma", confidence=0.9),
        EntityMention(id="b", type=EntityType.PERSON, name="Nikhil Rao", confidence=0.9),
    ]
    relationship = Relationship(
        id="rel_001",
        source_entity_id="a",
        relationship=RelationshipType.CALLED,
        target_entity_id="b",
        confidence=0.9,
        status=RelationshipStatus.CONFIRMED,
        source_document_id="metric_001",
        evidence_snippet="Priya Verma called Nikhil Rao.",
        extracted_at=datetime.now(timezone.utc),
    )
    entity_score, relationship_score = score_prediction(
        {"entities": entities, "relationships": [relationship]},
        {
            "entities": [
                {"type": "PERSON", "name": "Priya Verma"},
                {"type": "PERSON", "name": "Nikhil Rao"},
            ],
            "relationships": [
                {"source": "Priya Verma", "relationship": "CALLED", "target": "Nikhil Rao"}
            ],
        },
    )
    assert entity_score.f1 == 1.0
    assert relationship_score.f1 == 1.0
