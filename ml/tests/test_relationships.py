"""Phase 5 Relationship Extraction unit tests.

Covers:
- TEST 1: Relationship module import
- TEST 2: CALLED extraction
- TEST 3: SENT_MONEY_TO extraction
- TEST 4: OWNS_VEHICLE extraction
- TEST 5: USED_VEHICLE extraction
- TEST 6: WORKS_FOR extraction
- TEST 7: LOCATED_AT extraction
- TEST 8: ASSOCIATED_WITH extraction
- TEST 9: PART_OF_EVENT extraction
- TEST 10: No co-occurrence false relationships
- TEST 11: Negation handling (no false positive relations)
- TEST 12: Directionality enforcement
- TEST 13: Duplicate relationship deduplication
- TEST 14: Multiple relationship types (owns and uses)
- TEST 15: Confidence bounds [0, 1]
- TEST 16: Evidence snippet fidelity
- TEST 17: No entity resolution / auto-merge
- TEST 18: No pattern generation (CIRCULAR_TRANSACTION etc.)
- TEST 19: Structured CDR record processing
- TEST 20: Structured transaction record processing
"""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ml.extraction import extract_entities
from ml.pipeline import process_document
from ml.relationships import extract_relationships
from shared.schemas.enums import EntityType, RelationshipStatus, RelationshipType
from shared.schemas.models import EntityMention, ExtractionResult, Relationship


class TestRelationshipExtraction(unittest.TestCase):
    def test_1_relationship_module_import(self):
        """TEST 1: Relationship module exports are callable and available."""
        self.assertTrue(callable(extract_relationships))

    def test_2_called_extraction(self):
        """TEST 2: CALLED extraction between persons with evidence snippet."""
        text = "Rahul Kumar called Amit Kumar at 14:30."
        entities = extract_entities(text, "doc_001")
        relationships = extract_relationships(text, entities, "doc_001")

        self.assertEqual(len(relationships), 1)
        rel = relationships[0]
        self.assertEqual(rel.relationship, RelationshipType.CALLED)
        self.assertEqual(rel.status, RelationshipStatus.CONFIRMED)
        self.assertIn("called", rel.evidence_snippet.lower())
        self.assertEqual(rel.source_document_id, "doc_001")

        # Verify source is Rahul Kumar and target is Amit Kumar
        mention_map = {e.id: e.name for e in entities}
        self.assertEqual(mention_map[rel.source_entity_id], "Rahul Kumar")
        self.assertEqual(mention_map[rel.target_entity_id], "Amit Kumar")

    def test_3_sent_money_to_extraction(self):
        """TEST 3: SENT_MONEY_TO extraction preserving sender and recipient direction."""
        text = "Suresh Verma sent ₹5000 to Amit Kumar yesterday."
        entities = extract_entities(text, "doc_002")
        relationships = extract_relationships(text, entities, "doc_002")

        self.assertEqual(len(relationships), 1)
        rel = relationships[0]
        self.assertEqual(rel.relationship, RelationshipType.SENT_MONEY_TO)

        mention_map = {e.id: e.name for e in entities}
        self.assertEqual(mention_map[rel.source_entity_id], "Suresh Verma")
        self.assertEqual(mention_map[rel.target_entity_id], "Amit Kumar")

    def test_4_owns_vehicle(self):
        """TEST 4: OWNS_VEHICLE extraction only when ownership is explicit."""
        text = "Rahul Kumar owns vehicle DL 01 AB 1234 according to registry."
        entities = extract_entities(text, "doc_003")
        relationships = extract_relationships(text, entities, "doc_003")

        self.assertEqual(len(relationships), 1)
        rel = relationships[0]
        self.assertEqual(rel.relationship, RelationshipType.OWNS_VEHICLE)

        mention_map = {e.id: e.name for e in entities}
        self.assertEqual(mention_map[rel.source_entity_id], "Rahul Kumar")
        self.assertEqual(mention_map[rel.target_entity_id], "DL 01 AB 1234")

    def test_5_used_vehicle(self):
        """TEST 5: USED_VEHICLE extraction only when usage is explicit."""
        text = "Suspect Rahul Kumar fled in vehicle DL 01 AB 1234."
        entities = extract_entities(text, "doc_004")
        relationships = extract_relationships(text, entities, "doc_004")

        self.assertEqual(len(relationships), 1)
        rel = relationships[0]
        self.assertEqual(rel.relationship, RelationshipType.USED_VEHICLE)

        mention_map = {e.id: e.name for e in entities}
        self.assertEqual(mention_map[rel.source_entity_id], "Rahul Kumar")
        self.assertEqual(mention_map[rel.target_entity_id], "DL 01 AB 1234")

    def test_6_works_for(self):
        """TEST 6: WORKS_FOR extraction between person and organization."""
        text = "Rahul Kumar works for ABC Logistics Pvt Ltd in operations."
        entities = extract_entities(text, "doc_005")
        relationships = extract_relationships(text, entities, "doc_005")

        self.assertEqual(len(relationships), 1)
        rel = relationships[0]
        self.assertEqual(rel.relationship, RelationshipType.WORKS_FOR)

        mention_map = {e.id: e.name for e in entities}
        self.assertEqual(mention_map[rel.source_entity_id], "Rahul Kumar")
        self.assertEqual(mention_map[rel.target_entity_id], "ABC Logistics Pvt Ltd")

    def test_7_located_at(self):
        """TEST 7: LOCATED_AT extraction between entity and location."""
        text = "Suspect Amit Kumar is located at Bhubaneswar."
        entities = extract_entities(text, "doc_006")
        relationships = extract_relationships(text, entities, "doc_006")

        self.assertEqual(len(relationships), 1)
        rel = relationships[0]
        self.assertEqual(rel.relationship, RelationshipType.LOCATED_AT)

        mention_map = {e.id: e.name for e in entities}
        self.assertEqual(mention_map[rel.source_entity_id], "Amit Kumar")
        self.assertEqual(mention_map[rel.target_entity_id], "Bhubaneswar")

    def test_8_associated_with(self):
        """TEST 8: ASSOCIATED_WITH extraction from explicit association phrasing."""
        text = "Amit Kumar is associated with ABC Logistics Pvt Ltd."
        entities = extract_entities(text, "doc_007")
        relationships = extract_relationships(text, entities, "doc_007")

        self.assertEqual(len(relationships), 1)
        rel = relationships[0]
        self.assertEqual(rel.relationship, RelationshipType.ASSOCIATED_WITH)

        mention_map = {e.id: e.name for e in entities}
        self.assertEqual(mention_map[rel.source_entity_id], "Amit Kumar")
        self.assertEqual(mention_map[rel.target_entity_id], "ABC Logistics Pvt Ltd")

    def test_9_part_of_event(self):
        """TEST 9: PART_OF_EVENT extraction between entity and event."""
        text = "Rahul Kumar participated in Meeting on 2026-01-15."
        entities = extract_entities(text, "doc_008")
        relationships = extract_relationships(text, entities, "doc_008")

        self.assertEqual(len(relationships), 1)
        rel = relationships[0]
        self.assertEqual(rel.relationship, RelationshipType.PART_OF_EVENT)

        mention_map = {e.id: e.name for e in entities}
        self.assertEqual(mention_map[rel.source_entity_id], "Rahul Kumar")
        self.assertEqual(mention_map[rel.target_entity_id], "Meeting on 2026-01-15")

    def test_10_no_co_occurrence_relationship(self):
        """TEST 10: Simple co-occurrence without relational context creates NO relationships."""
        text = (
            "CASE SUMMARY:\n"
            "Rahul Kumar\n"
            "ABC Logistics Pvt Ltd\n"
            "Bhubaneswar\n"
        )
        entities = extract_entities(text, "doc_009")
        relationships = extract_relationships(text, entities, "doc_009")

        self.assertEqual(relationships, [])

    def test_11_negation(self):
        """TEST 11: Negated interaction must not create a relationship."""
        text = "Rahul Kumar did not call Amit Kumar yesterday."
        entities = extract_entities(text, "doc_010")
        relationships = extract_relationships(text, entities, "doc_010")

        self.assertEqual(relationships, [])

        text2 = "Rahul Kumar does not work for ABC Logistics Pvt Ltd."
        entities2 = extract_entities(text2, "doc_010")
        relationships2 = extract_relationships(text2, entities2, "doc_010")

        self.assertEqual(relationships2, [])

    def test_12_directionality(self):
        """TEST 12: Direction must never be reversed."""
        text = "Rahul Kumar sent money to Amit Kumar."
        entities = extract_entities(text, "doc_011")
        relationships = extract_relationships(text, entities, "doc_011")

        self.assertEqual(len(relationships), 1)
        rel = relationships[0]

        mention_map = {e.id: e.name for e in entities}
        self.assertEqual(mention_map[rel.source_entity_id], "Rahul Kumar")
        self.assertEqual(mention_map[rel.target_entity_id], "Amit Kumar")
        self.assertNotEqual(mention_map[rel.source_entity_id], "Amit Kumar")

    def test_13_duplicate_relationship_handling(self):
        """TEST 13: Identical relational evidence deduplicates cleanly."""
        text = (
            "Rahul Kumar called Amit Kumar.\n"
            "Rahul Kumar called Amit Kumar."
        )
        entities = extract_entities(text, "doc_012")
        relationships = extract_relationships(text, entities, "doc_012")

        # Deduplicates identical relation occurrences
        self.assertEqual(len(relationships), 1)

    def test_14_multiple_relationship_types(self):
        """TEST 14: Distinct supported relationship types on same entity pair are preserved."""
        text = "Rahul Kumar owns and used vehicle DL 01 AB 1234."
        entities = extract_entities(text, "doc_013")
        relationships = extract_relationships(text, entities, "doc_013")

        rel_types = {r.relationship for r in relationships}
        self.assertIn(RelationshipType.OWNS_VEHICLE, rel_types)
        self.assertIn(RelationshipType.USED_VEHICLE, rel_types)
        self.assertEqual(len(relationships), 2)

    def test_15_confidence_bounds(self):
        """TEST 15: All relationship confidences are within [0, 1]."""
        text = "Rahul Kumar called Amit Kumar."
        result = process_document("doc_014", text)

        self.assertTrue(len(result.relationships) > 0)
        for r in result.relationships:
            self.assertGreaterEqual(r.confidence, 0.0)
            self.assertLessEqual(r.confidence, 1.0)

    def test_16_evidence_fidelity(self):
        """TEST 16: Evidence snippet originates from actual source text."""
        snippet = "Rahul Kumar called Amit Kumar"
        text = f"POLICE LOG: {snippet} regarding case 42."
        entities = extract_entities(text, "doc_015")
        relationships = extract_relationships(text, entities, "doc_015")

        self.assertEqual(len(relationships), 1)
        self.assertIn(snippet, relationships[0].evidence_snippet)

    def test_17_no_resolution(self):
        """TEST 17: Relationship extraction does not auto-merge or resolve entities."""
        text = "Rahul Kumar called Amit Kumar. Rahul K sent money to Amit."
        result = process_document("doc_016", text)

        # Entity mentions remain distinct
        mention_names = [e.name for e in result.entities]
        self.assertIn("Rahul Kumar", mention_names)
        self.assertIn("Rahul K", mention_names)

    def test_18_no_pattern_generation(self):
        """TEST 18: Relationship extraction must NOT emit patterns or leads."""
        text = "A sent money to B. B sent money to C. C sent money to A."
        result = process_document("doc_017", text)

        # ExtractionResult has only entities and relationships
        self.assertTrue(hasattr(result, "relationships"))
        self.assertFalse(hasattr(result, "patterns"))
        self.assertFalse(hasattr(result, "leads"))

    def test_19_structured_cdr(self):
        """TEST 19: Structured CDR records generate CALLED with source_record_id."""
        entities = [
            EntityMention(id="mention_001", type=EntityType.PERSON, name="Rahul Kumar", confidence=0.95),
            EntityMention(id="mention_002", type=EntityType.PERSON, name="Amit Kumar", confidence=0.95),
        ]
        structured_records = [
            {
                "type": "CDR",
                "record_id": "cdr_000101",
                "caller": "Rahul Kumar",
                "callee": "Amit Kumar",
                "duration": 120,
            }
        ]
        relationships = extract_relationships(
            "",
            entities=entities,
            document_id="doc_018",
            structured_records=structured_records,
        )

        self.assertEqual(len(relationships), 1)
        rel = relationships[0]
        self.assertEqual(rel.relationship, RelationshipType.CALLED)
        self.assertEqual(rel.source_entity_id, "mention_001")
        self.assertEqual(rel.target_entity_id, "mention_002")
        self.assertEqual(rel.source_record_id, "cdr_000101")
        self.assertEqual(rel.source_document_id, "doc_018")

    def test_20_structured_transaction(self):
        """TEST 20: Structured transaction records generate SENT_MONEY_TO with source_record_id."""
        entities = [
            EntityMention(id="mention_001", type=EntityType.PERSON, name="Rahul Kumar", confidence=0.95),
            EntityMention(id="mention_002", type=EntityType.PERSON, name="Amit Kumar", confidence=0.95),
        ]
        structured_records = [
            {
                "type": "TRANSACTION",
                "record_id": "txn_000202",
                "sender": "Rahul Kumar",
                "recipient": "Amit Kumar",
                "amount": 25000,
            }
        ]
        relationships = extract_relationships(
            "",
            entities=entities,
            document_id="doc_019",
            structured_records=structured_records,
        )

        self.assertEqual(len(relationships), 1)
        rel = relationships[0]
        self.assertEqual(rel.relationship, RelationshipType.SENT_MONEY_TO)
        self.assertEqual(rel.source_entity_id, "mention_001")
        self.assertEqual(rel.target_entity_id, "mention_002")
        self.assertEqual(rel.source_record_id, "txn_000202")
        self.assertEqual(rel.source_document_id, "doc_019")


if __name__ == "__main__":
    unittest.main()
