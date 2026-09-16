from datetime import datetime, timezone

from ml.intelligence.candidates import integrate_ai_candidates
from ml.intelligence.document_understanding import understand_document
from ml.intelligence.quality import apply_graph_quality_firewall
from ml.intelligence.sos import assess_sos
from shared.schemas.enums import EntityType, RelationshipStatus, RelationshipType
from shared.schemas.models import EntityMention, Pattern, Relationship


def _entities():
    return [
        EntityMention(id="mention_001", type=EntityType.PERSON, name="Rahul Sharma", confidence=0.95),
        EntityMention(id="mention_002", type=EntityType.PERSON, name="Amit Kumar", confidence=0.95),
    ]


def _relationship(status=RelationshipStatus.CONFIRMED, rel_id="rel_001"):
    return Relationship(
        id=rel_id,
        source_entity_id="mention_001",
        relationship=RelationshipType.CALLED,
        target_entity_id="mention_002",
        confidence=0.9,
        status=status,
        source_document_id="doc_001",
        evidence_snippet="Rahul Sharma called Amit Kumar.",
        extracted_at=datetime.now(timezone.utc),
    )


def test_document_understanding_creates_stable_provenance_blocks():
    text = "First Information Report\n\nRahul Sharma called Amit Kumar."
    result = understand_document(text, "doc_001")
    assert result.document_type == "FIR"
    assert result.block_count == 2
    assert text[result.blocks[0].start_char:result.blocks[0].end_char] == result.blocks[0].text
    assert [block.block_id for block in result.blocks] == ["block_001", "block_002"]


def test_candidate_integration_rejects_ungrounded_ai_edge():
    text = "Rahul Sharma called Amit Kumar."
    entities, relationships, telemetry = integrate_ai_candidates(
        _entities(),
        {
            "entities": [],
            "relationships": [
                {
                    "source": "Rahul Sharma",
                    "target": "Amit Kumar",
                    "type": "CALLED",
                    "evidence": "The model inferred a call.",
                }
            ],
        },
        document_id="doc_001",
        source_text=text,
    )
    assert len(entities) == 2
    assert relationships == []
    assert telemetry["relationships_rejected"] == 1


def test_quality_firewall_deduplicates_and_records_status_conflict():
    accepted, report = apply_graph_quality_firewall(
        [_relationship(RelationshipStatus.PREDICTED), _relationship(RelationshipStatus.CONFIRMED, "rel_002")],
        _entities(),
        source_text="Rahul Sharma called Amit Kumar.",
    )
    assert len(accepted) == 1
    assert accepted[0].status == RelationshipStatus.CONFIRMED
    assert report.duplicate_groups == 1
    assert report.contradictions == 1


def test_sos_is_case_signal_with_reason_codes_not_person_score():
    pattern = Pattern(
        id="pattern_001",
        type="RAPID_TRANSFER_CHAIN",
        severity="HIGH",
        status="INFERRED",
        entities=["entity_001", "entity_002", "entity_003"],
        explanation="A rapid transfer chain needs review.",
        evidence_ids=["txn_001", "txn_002"],
    )
    assessment = assess_sos([pattern], [_relationship()])
    assert assessment.level == "HIGH"
    assert assessment.score <= 1.0
    assert "RAPID_TRANSFER_CHAIN" in assessment.reason_codes
    assert "entity_001" not in assessment.as_dict()
