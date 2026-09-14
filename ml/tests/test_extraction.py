"""Phase 4 Entity Extraction unit tests.

Covers:
- TEST 1: Extraction module imports
- TEST 2: PERSON extraction
- TEST 3: PHONE extraction
- TEST 4: BANK_ACCOUNT extraction without misclassifying amounts/dates
- TEST 5: VEHICLE extraction
- TEST 6: ORGANIZATION extraction
- TEST 7: LOCATION extraction
- TEST 8: EVENT extraction
- TEST 9: Regex + NER combination and deduplication
- TEST 10: No false relationship creation
- TEST 11: No entity resolution / auto-merge
- TEST 12: Identifier preservation
- TEST 13: Confidence range [0, 1]
- TEST 14: Unicode / Multilingual name preservation
- TEST 15: Empty input handling (no fake entities)
- TEST 16: No fabricated evidence (mentions originate from text)
- TEST 17: Deterministic extraction
"""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ml.extraction import (
    extract_entities,
    extract_named_entities,
    extract_regex_entities,
)
from ml.pipeline import process_document
from shared.schemas.enums import EntityType
from shared.schemas.models import EntityMention, ExtractionResult


class TestEntityExtraction(unittest.TestCase):
    def test_1_extraction_module_imports(self):
        """TEST 1: Extraction module exports are callable and available."""
        self.assertTrue(callable(extract_entities))
        self.assertTrue(callable(extract_named_entities))
        self.assertTrue(callable(extract_regex_entities))

    def test_2_person_extraction(self):
        """TEST 2: PERSON extraction from labeled text and context."""
        text = "CASE FILE: Suspect: Rahul Kumar was seen at location."
        mentions = extract_entities(text, "doc_001")
        person_mentions = [m for m in mentions if m.type == EntityType.PERSON]

        self.assertTrue(len(person_mentions) >= 1)
        self.assertEqual(person_mentions[0].name, "Rahul Kumar")
        self.assertIsInstance(person_mentions[0], EntityMention)
        self.assertTrue(person_mentions[0].id.startswith("mention_"))

    def test_3_phone_extraction(self):
        """TEST 3: PHONE extraction preserves valid phone number formatting."""
        text = "Contact the officer at PHONE: +91-98765-43210 or 9876543210."
        mentions = extract_entities(text, "doc_002")
        phone_mentions = [m for m in mentions if m.type == EntityType.PHONE]

        self.assertTrue(len(phone_mentions) >= 1)
        phone_names = [m.name for m in phone_mentions]
        self.assertTrue(any("+91-98765-43210" in p or "9876543210" in p for p in phone_names))

    def test_4_bank_account_extraction(self):
        """TEST 4: BANK_ACCOUNT extraction without misclassifying amounts or dates."""
        text = (
            "Transferred ₹50,000 on 2026-01-15 to ACCOUNT: 123456789012."
        )
        mentions = extract_entities(text, "doc_003")
        acc_mentions = [m for m in mentions if m.type == EntityType.BANK_ACCOUNT]

        self.assertEqual(len(acc_mentions), 1)
        self.assertEqual(acc_mentions[0].name, "123456789012")
        # Ensure ₹50,000 or 2026-01-15 are NOT extracted as bank accounts
        self.assertNotIn("50000", [m.name for m in acc_mentions])
        self.assertNotIn("2026-01-15", [m.name for m in acc_mentions])

    def test_5_vehicle_extraction(self):
        """TEST 5: VEHICLE extraction matches registration format."""
        text = "Suspect fled in VEHICLE: DL 01 AB 1234 after the incident."
        mentions = extract_entities(text, "doc_004")
        vehicle_mentions = [m for m in mentions if m.type == EntityType.VEHICLE]

        self.assertEqual(len(vehicle_mentions), 1)
        self.assertEqual(vehicle_mentions[0].name, "DL 01 AB 1234")

    def test_6_organization_extraction(self):
        """TEST 6: ORGANIZATION extraction matches company and unit patterns."""
        text = "Registered employer: ORGANIZATION: ABC Logistics Pvt Ltd."
        mentions = extract_entities(text, "doc_005")
        org_mentions = [m for m in mentions if m.type == EntityType.ORGANIZATION]

        self.assertTrue(len(org_mentions) >= 1)
        self.assertIn("ABC Logistics Pvt Ltd", [m.name for m in org_mentions])

    def test_7_location_extraction(self):
        """TEST 7: LOCATION extraction identifies city names."""
        text = "Meeting scheduled at LOCATION: Bhubaneswar tomorrow."
        mentions = extract_entities(text, "doc_006")
        loc_mentions = [m for m in mentions if m.type == EntityType.LOCATION]

        self.assertTrue(len(loc_mentions) >= 1)
        self.assertIn("Bhubaneswar", [m.name for m in loc_mentions])

    def test_8_event_extraction(self):
        """TEST 8: EVENT extraction is conservative and schema-compatible."""
        text = "Investigation record: EVENT: Meeting on 2026-01-15 held at office."
        mentions = extract_entities(text, "doc_007")
        event_mentions = [m for m in mentions if m.type == EntityType.EVENT]

        self.assertTrue(len(event_mentions) >= 1)
        self.assertIn("Meeting on 2026-01-15", [m.name for m in event_mentions])

    def test_9_regex_and_ner_combination(self):
        """TEST 9: Combination deduplicates same entity candidates safely."""
        text = (
            "PHONE: +91-98765-43210\n"
            "Call from +91-98765-43210 logged."
        )
        mentions = extract_entities(text, "doc_008")
        phones = [m for m in mentions if m.type == EntityType.PHONE]
        # Should deduplicate repeated occurrences of identical phone
        self.assertEqual(len(phones), 1)

    def test_10_no_false_relationship_creation(self):
        """TEST 10: Extracted entities must NOT generate relationships in Phase 4."""
        text = "Rahul called Amit regarding the payment."
        result = process_document("doc_009", text)

        self.assertIsInstance(result, ExtractionResult)
        # Relationships MUST remain empty in Phase 4
        self.assertEqual(result.relationships, [])

    def test_11_no_entity_resolution(self):
        """TEST 11: Different name mentions must NOT be auto-merged in Phase 4."""
        text = "Suspects listed: Rahul Kumar and Rahul K. attended the meeting."
        mentions = extract_entities(text, "doc_010")
        persons = [m for m in mentions if m.type == EntityType.PERSON]

        names = [p.name for p in persons]
        self.assertIn("Rahul Kumar", names)
        self.assertIn("Rahul K", names)
        # They remain distinct mentions with separate IDs
        self.assertTrue(len(persons) >= 2)
        mention_ids = {p.id for p in persons}
        self.assertEqual(len(mention_ids), len(persons))

    def test_12_identifier_preservation(self):
        """TEST 12: Structured identifiers remain recoverable."""
        text = (
            "Suspect info:\n"
            "PHONE: +91-98765-43210\n"
            "ACCOUNT: 123456789012\n"
            "VEHICLE: DL 01 AB 1234\n"
        )
        mentions = extract_entities(text, "doc_011")
        extracted_names = {m.name for m in mentions}

        self.assertIn("+91-98765-43210", extracted_names)
        self.assertIn("123456789012", extracted_names)
        self.assertIn("DL 01 AB 1234", extracted_names)

    def test_13_confidence_range(self):
        """TEST 13: All emitted confidences satisfy 0 <= confidence <= 1."""
        text = (
            "Suspect: Amit Kumar, Phone: +91-98765-43210, "
            "Vehicle: KA 03 MH 9999, Location: Mumbai"
        )
        mentions = extract_entities(text, "doc_012")
        self.assertTrue(len(mentions) > 0)
        for m in mentions:
            self.assertGreaterEqual(m.confidence, 0.0)
            self.assertLessEqual(m.confidence, 1.0)

    def test_14_unicode_preservation(self):
        """TEST 14: Non-ASCII and Hindi names are preserved in EntityMention."""
        text = "संदिग्ध: PERSON: अमित कुमार उपस्थित थे।"
        mentions = extract_entities(text, "doc_013")
        persons = [m for m in mentions if m.type == EntityType.PERSON]

        self.assertTrue(len(persons) >= 1)
        self.assertIn("अमित कुमार", [p.name for p in persons])

    def test_15_empty_input(self):
        """TEST 15: Empty input returns empty list without fabricating entities."""
        self.assertEqual(extract_entities("", "doc_014"), [])
        self.assertEqual(extract_entities("   \n\t  ", "doc_014"), [])

        result = process_document("doc_014", "")
        self.assertEqual(result.entities, [])
        self.assertEqual(result.relationships, [])

    def test_16_no_fabricated_evidence(self):
        """TEST 16: Mentions originate from actual source text."""
        text = "Officer Insp. Vikram Roy recorded statement."
        mentions = extract_entities(text, "doc_015")

        for m in mentions:
            # The core characters of the mention must exist in the original text
            self.assertTrue(m.name in text or m.name.replace(" ", "") in text.replace(" ", ""))

    def test_17_determinism(self):
        """TEST 17: Repeated extraction on the same input produces identical output."""
        text = (
            "REPORT: Person: Suresh Verma, Phone: +91-98765-43210, "
            "Vehicle: DL 01 AB 1234, Location: Bhubaneswar."
        )
        mentions1 = extract_entities(text, "doc_016")
        mentions2 = extract_entities(text, "doc_016")

        self.assertEqual([m.model_dump() for m in mentions1], [m.model_dump() for m in mentions2])


if __name__ == "__main__":
    unittest.main()
