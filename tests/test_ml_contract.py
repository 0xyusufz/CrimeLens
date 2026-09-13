"""Validate frozen CrimeLens ML JSON examples. No database or API calls."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pydantic import ValidationError

from shared.schemas import (
    EntityMention,
    ExtractionResult,
    Lead,
    Pattern,
    Relationship,
    ResolutionProposal,
)


ENTITY_JSON = {
    "id": "mention_001",
    "type": "PERSON",
    "name": "Rahul Sharma",
    "confidence": 0.96,
}

RELATIONSHIP_JSON = {
    "id": "rel_001",
    "source_entity_id": "mention_001",
    "relationship": "CALLED",
    "target_entity_id": "mention_002",
    "confidence": 0.98,
    "status": "CONFIRMED",
    "source_document_id": "doc_001",
    "evidence_snippet": "Rahul called Amit Kumar.",
    "extracted_at": "2026-09-13T10:30:00",
}

EXTRACTION_JSON = {
    "document_id": "doc_001",
    "entities": [
        {
            "id": "mention_001",
            "type": "PERSON",
            "name": "Rahul Sharma",
            "confidence": 0.96,
        },
        {
            "id": "mention_002",
            "type": "PERSON",
            "name": "Amit Kumar",
            "confidence": 0.94,
        },
        {
            "id": "mention_003",
            "type": "LOCATION",
            "name": "Bhubaneswar",
            "confidence": 0.91,
        },
    ],
    "relationships": [
        {
            "id": "rel_001",
            "source_entity_id": "mention_001",
            "relationship": "CALLED",
            "target_entity_id": "mention_002",
            "confidence": 0.98,
            "status": "CONFIRMED",
            "source_document_id": "doc_001",
            "evidence_snippet": "Rahul called Amit Kumar.",
            "extracted_at": "2026-09-13T10:30:00",
        }
    ],
}

RESOLUTION_JSON = {
    "canonical_entity_id": "entity_001",
    "mention_id": "mention_023",
    "confidence": 0.97,
    "signals": ["phone_match", "name_similarity"],
}

PATTERN_JSON = {
    "id": "pattern_001",
    "type": "CIRCULAR_TRANSACTION",
    "severity": "HIGH",
    "entities": ["entity_001", "entity_002", "entity_003"],
    "explanation": "A → B → C → A",
    "evidence_ids": ["txn_001", "txn_002", "txn_003"],
}

LEAD_JSON = {
    "id": "lead_001",
    "type": "FINANCIAL_NETWORK",
    "priority": "HIGH",
    "title": "Potential circular transaction network",
    "explanation": "Funds move from A → B → C → A within a short period.",
    "entity_ids": ["entity_001", "entity_002", "entity_003"],
    "evidence_ids": ["txn_001", "txn_002", "txn_003"],
}


class ContractValidationTests(unittest.TestCase):
    def test_valid_entity_mention(self):
        mention = EntityMention.model_validate(ENTITY_JSON)
        self.assertEqual(mention.id, "mention_001")
        self.assertEqual(mention.confidence, 0.96)

    def test_valid_relationship(self):
        rel = Relationship.model_validate(RELATIONSHIP_JSON)
        self.assertEqual(rel.status.value, "CONFIRMED")
        self.assertEqual(rel.source_document_id, "doc_001")

    def test_valid_extraction_envelope(self):
        result = ExtractionResult.model_validate(EXTRACTION_JSON)
        self.assertEqual(result.document_id, "doc_001")
        self.assertEqual(len(result.entities), 3)
        self.assertEqual(len(result.relationships), 1)

    def test_valid_resolution_proposal(self):
        proposal = ResolutionProposal.model_validate(RESOLUTION_JSON)
        self.assertEqual(proposal.canonical_entity_id, "entity_001")
        self.assertEqual(proposal.mention_id, "mention_023")

    def test_valid_pattern(self):
        pattern = Pattern.model_validate(PATTERN_JSON)
        self.assertEqual(pattern.severity.value, "HIGH")
        self.assertEqual(pattern.status.value, "DETECTED")
        self.assertNotEqual(pattern.status.value, pattern.severity.value)

    def test_valid_lead(self):
        lead = Lead.model_validate(LEAD_JSON)
        self.assertEqual(lead.priority.value, "HIGH")
        self.assertEqual(lead.status.value, "REVIEW_REQUIRED")
        self.assertNotEqual(lead.status.value, lead.priority.value)

    def test_invalid_confidence_percentage_fails(self):
        payload = dict(ENTITY_JSON)
        payload["confidence"] = 95
        with self.assertRaises(ValidationError):
            EntityMention.model_validate(payload)

    def test_invalid_entity_type_fails(self):
        payload = dict(ENTITY_JSON)
        payload["type"] = "HUMAN"
        with self.assertRaises(ValidationError):
            EntityMention.model_validate(payload)

    def test_inferred_status_is_not_confirmed(self):
        payload = dict(RELATIONSHIP_JSON)
        payload["status"] = "INFERRED"
        rel = Relationship.model_validate(payload)
        self.assertEqual(rel.status.value, "INFERRED")
        self.assertNotEqual(rel.status.value, "CONFIRMED")


if __name__ == "__main__":
    unittest.main()
