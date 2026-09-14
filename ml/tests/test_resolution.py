"""Phase 6 Entity Resolution unit tests.

Covers all 18 required scenarios:
- TEST 1: Resolution module import
- TEST 2: Exact phone matching
- TEST 3: Exact bank account matching
- TEST 4: Vehicle matching
- TEST 5: Exact normalized name
- TEST 6: Fuzzy name does NOT auto-merge
- TEST 7: Conflicting strong identifiers
- TEST 8: Multiple signals
- TEST 9: Type safety
- TEST 10: Cross-document matching
- TEST 11: No canonical UUID generation
- TEST 12: No case_id generation
- TEST 13: Confidence range [0, 1]
- TEST 14: Proposal schema validation
- TEST 15: Evidence/reason preservation
- TEST 16: Determinism
- TEST 17: No database access
- TEST 18: No relationship mutation
"""

from datetime import datetime, timezone
from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ml.resolution import compare_mentions, propose_resolutions
from shared.schemas.enums import EntityType, RelationshipStatus, RelationshipType, ResolutionSignal
from shared.schemas.models import EntityMention, Relationship, ResolutionProposal


class TestEntityResolution(unittest.TestCase):
    def test_1_resolution_module_import(self):
        """TEST 1: Verify resolver functions import cleanly and are callable."""
        self.assertTrue(callable(propose_resolutions))
        self.assertTrue(callable(compare_mentions))

    def test_2_exact_phone_matching(self):
        """TEST 2: Exact normalized phone number creates strong resolution proposal."""
        mA = EntityMention(id="mention_001", type=EntityType.PHONE, name="+91-98765-43210", confidence=0.95)
        mB = EntityMention(id="mention_002", type=EntityType.PHONE, name="+91 98765 43210", confidence=0.95)

        proposals = propose_resolutions([mA, mB])

        self.assertEqual(len(proposals), 2)
        # Both mentions belong to the same canonical grouping
        self.assertEqual(proposals[0].canonical_entity_id, proposals[1].canonical_entity_id)
        mention_ids = {p.mention_id for p in proposals}
        self.assertEqual(mention_ids, {"mention_001", "mention_002"})
        # Signal is PHONE_MATCH and confidence is high
        for p in proposals:
            self.assertIn(ResolutionSignal.PHONE_MATCH, p.signals)
            self.assertGreaterEqual(p.confidence, 0.90)

    def test_3_exact_bank_account_matching(self):
        """TEST 3: Exact normalized account creates proposal; different accounts do not."""
        mA = EntityMention(id="mention_003", type=EntityType.BANK_ACCOUNT, name="123456789012", confidence=0.95)
        mB = EntityMention(id="mention_004", type=EntityType.BANK_ACCOUNT, name="1234-5678-9012", confidence=0.95)

        proposals = propose_resolutions([mA, mB])
        self.assertEqual(len(proposals), 2)
        for p in proposals:
            self.assertIn(ResolutionSignal.ACCOUNT_MATCH, p.signals)
            self.assertGreaterEqual(p.confidence, 0.90)

        # Different accounts must NOT match
        mC = EntityMention(id="mention_005", type=EntityType.BANK_ACCOUNT, name="123456789000", confidence=0.95)
        diff_proposals = propose_resolutions([mA, mC])
        self.assertEqual(diff_proposals, [])

    def test_4_vehicle_matching(self):
        """TEST 4: Exact normalized vehicle registration matching."""
        mA = EntityMention(id="mention_006", type=EntityType.VEHICLE, name="DL 01 AB 1234", confidence=0.95)
        mB = EntityMention(id="mention_007", type=EntityType.VEHICLE, name="DL-01-AB-1234", confidence=0.95)

        proposals = propose_resolutions([mA, mB])
        self.assertEqual(len(proposals), 2)
        for p in proposals:
            self.assertIn(ResolutionSignal.VEHICLE_MATCH, p.signals)
            self.assertGreaterEqual(p.confidence, 0.90)

    def test_5_exact_normalized_name(self):
        """TEST 5: Exact normalized person name produces proposal according to project rules."""
        mA = EntityMention(id="mention_008", type=EntityType.PERSON, name="Rahul Kumar", confidence=0.90)
        mB = EntityMention(id="mention_009", type=EntityType.PERSON, name="rahul kumar", confidence=0.90)

        proposals = propose_resolutions([mA, mB])
        self.assertEqual(len(proposals), 2)
        for p in proposals:
            self.assertIn(ResolutionSignal.NAME_SIMILARITY, p.signals)
            self.assertGreaterEqual(p.confidence, 0.70)

    def test_6_fuzzy_name_does_not_auto_merge(self):
        """TEST 6: Name-only fuzzy matching NEVER auto-merges; review-only with lower confidence."""
        mA = EntityMention(id="mention_010", type=EntityType.PERSON, name="Rahul Kumar", confidence=0.90)
        mB = EntityMention(id="mention_011", type=EntityType.PERSON, name="Rahul K.", confidence=0.90)

        # Under default threshold (0.70), fuzzy name match is NOT auto-proposed
        default_proposals = propose_resolutions([mA, mB], min_confidence=0.70)
        self.assertEqual(default_proposals, [])

        # In review mode (min_confidence <= 0.60), proposal is returned as a suggestion
        review_proposals = propose_resolutions([mA, mB], min_confidence=0.50)
        self.assertEqual(len(review_proposals), 2)
        for p in review_proposals:
            # Confidence strictly below auto-merge threshold (0.70)
            self.assertLess(p.confidence, 0.70)
            self.assertIn(ResolutionSignal.NAME_SIMILARITY, p.signals)

    def test_7_conflicting_strong_identifiers(self):
        """TEST 7: Conflicting strong identifiers prevent resolution proposal despite matching name."""
        mA = EntityMention(id="mention_012", type=EntityType.PERSON, name="Rahul Kumar", confidence=0.90)
        mB = EntityMention(id="mention_013", type=EntityType.PERSON, name="Rahul Kumar", confidence=0.90)

        context = {
            "mention_012": {"phone": "1111111111"},
            "mention_013": {"phone": "9999999999"},
        }
        proposals = propose_resolutions([mA, mB], context=context)
        self.assertEqual(proposals, [])

    def test_8_multiple_signals(self):
        """TEST 8: Multiple independent signals strengthen proposal confidence."""
        mA = EntityMention(id="mention_014", type=EntityType.PERSON, name="Rahul Kumar", confidence=0.90)
        mB = EntityMention(id="mention_015", type=EntityType.PERSON, name="Rahul Kumar", confidence=0.90)

        # Name-only
        name_only_proposals = propose_resolutions([mA, mB])
        self.assertEqual(len(name_only_proposals), 2)
        name_only_conf = name_only_proposals[0].confidence

        # Name + Phone
        context = {
            "mention_014": {"phone": "+91-98765-43210"},
            "mention_015": {"phone": "+91 98765 43210"},
        }
        multi_proposals = propose_resolutions([mA, mB], context=context)
        self.assertEqual(len(multi_proposals), 2)
        multi_conf = multi_proposals[0].confidence

        self.assertGreater(multi_conf, name_only_conf)
        self.assertIn(ResolutionSignal.NAME_SIMILARITY, multi_proposals[0].signals)
        self.assertIn(ResolutionSignal.PHONE_MATCH, multi_proposals[0].signals)

    def test_9_type_safety(self):
        """TEST 9: Incompatible entity types are never resolved together."""
        mA = EntityMention(id="mention_016", type=EntityType.PERSON, name="123456789", confidence=0.90)
        mB = EntityMention(id="mention_017", type=EntityType.BANK_ACCOUNT, name="123456789", confidence=0.90)

        proposals = propose_resolutions([mA, mB])
        self.assertEqual(proposals, [])

    def test_10_cross_document_matching(self):
        """TEST 10: Compatible mentions from different documents produce unified proposal."""
        mA = EntityMention(id="mention_docA_001", type=EntityType.PERSON, name="Rahul Kumar", confidence=0.90)
        mB = EntityMention(id="mention_docB_014", type=EntityType.PERSON, name="Rahul Kumar", confidence=0.90)

        context = {
            "document_ids": {
                "mention_docA_001": "doc_A",
                "mention_docB_014": "doc_B",
            }
        }
        proposals = propose_resolutions([mA, mB], context=context)
        self.assertEqual(len(proposals), 2)
        self.assertEqual(proposals[0].canonical_entity_id, proposals[1].canonical_entity_id)

    def test_11_no_canonical_uuid_generation(self):
        """TEST 11: Resolver produces ML staging grouping keys, NEVER database UUIDs."""
        mA = EntityMention(id="mention_018", type=EntityType.PERSON, name="Rahul Kumar", confidence=0.90)
        mB = EntityMention(id="mention_019", type=EntityType.PERSON, name="Rahul Kumar", confidence=0.90)

        proposals = propose_resolutions([mA, mB])
        self.assertTrue(len(proposals) >= 1)

        uuid_pattern = re.compile(
            r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
            re.IGNORECASE,
        )
        for p in proposals:
            self.assertFalse(uuid_pattern.match(p.canonical_entity_id))
            self.assertTrue(p.canonical_entity_id.startswith("entity_"))

    def test_12_no_case_id_generation(self):
        """TEST 12: ResolutionProposal does NOT contain or generate case_id."""
        mA = EntityMention(id="mention_020", type=EntityType.PERSON, name="Rahul Kumar", confidence=0.90)
        mB = EntityMention(id="mention_021", type=EntityType.PERSON, name="Rahul Kumar", confidence=0.90)

        proposals = propose_resolutions([mA, mB])
        for p in proposals:
            data = p.model_dump()
            self.assertNotIn("case_id", data)

    def test_13_confidence_range(self):
        """TEST 13: All emitted confidences satisfy 0 <= confidence <= 1."""
        mA = EntityMention(id="mention_022", type=EntityType.PERSON, name="Rahul Kumar", confidence=0.90)
        mB = EntityMention(id="mention_023", type=EntityType.PERSON, name="Rahul Kumar", confidence=0.90)

        proposals = propose_resolutions([mA, mB], min_confidence=0.50)
        for p in proposals:
            self.assertGreaterEqual(p.confidence, 0.0)
            self.assertLessEqual(p.confidence, 1.0)

    def test_14_proposal_schema_validation(self):
        """TEST 14: Emitted ResolutionProposal objects conform strictly to frozen schema."""
        mA = EntityMention(id="mention_024", type=EntityType.PHONE, name="+91-98765-43210", confidence=0.95)
        mB = EntityMention(id="mention_025", type=EntityType.PHONE, name="9876543210", confidence=0.95)

        proposals = propose_resolutions([mA, mB])
        for p in proposals:
            validated = ResolutionProposal.model_validate(p.model_dump())
            self.assertIsInstance(validated, ResolutionProposal)
            self.assertTrue(len(validated.signals) >= 1)

    def test_15_evidence_reason_preservation(self):
        """TEST 15: Emitted signals originate strictly from matched inputs, no fabricated evidence."""
        mA = EntityMention(id="mention_026", type=EntityType.PHONE, name="+91-98765-43210", confidence=0.95)
        mB = EntityMention(id="mention_027", type=EntityType.PHONE, name="9876543210", confidence=0.95)

        proposals = propose_resolutions([mA, mB])
        for p in proposals:
            self.assertEqual(p.signals, [ResolutionSignal.PHONE_MATCH])

    def test_16_determinism(self):
        """TEST 16: Identical inputs produce identical resolution proposals."""
        mA = EntityMention(id="mention_028", type=EntityType.PERSON, name="Amit Kumar", confidence=0.90)
        mB = EntityMention(id="mention_029", type=EntityType.PERSON, name="Amit Kumar", confidence=0.90)

        run1 = propose_resolutions([mA, mB])
        run2 = propose_resolutions([mA, mB])

        self.assertEqual(len(run1), len(run2))
        for p1, p2 in zip(run1, run2):
            self.assertEqual(p1.canonical_entity_id, p2.canonical_entity_id)
            self.assertEqual(p1.mention_id, p2.mention_id)
            self.assertEqual(p1.confidence, p2.confidence)
            self.assertEqual(p1.signals, p2.signals)

    def test_17_no_database_access(self):
        """TEST 17: Resolution module contains zero database imports."""
        import ml.resolution.resolver as resolver_module

        module_src = Path(resolver_module.__file__).read_text(encoding="utf-8")
        forbidden = ["psycopg", "asyncpg", "sqlalchemy", "neo4j", "sqlite3"]
        for term in forbidden:
            self.assertNotIn(f"import {term}", module_src)
            self.assertNotIn(f"from {term}", module_src)

    def test_18_no_relationship_mutation(self):
        """TEST 18: Resolver does not mutate Phase 5 relationship instances."""
        mA = EntityMention(id="mention_030", type=EntityType.PERSON, name="Rahul Kumar", confidence=0.90)
        mB = EntityMention(id="mention_031", type=EntityType.PHONE, name="+91-98765-43210", confidence=0.95)
        mC = EntityMention(id="mention_032", type=EntityType.PERSON, name="Rahul Kumar", confidence=0.90)

        rel = Relationship(
            id="rel_001",
            source_entity_id="mention_030",
            relationship=RelationshipType.CALLED,
            target_entity_id="mention_031",
            confidence=0.95,
            status=RelationshipStatus.CONFIRMED,
            source_document_id="doc_001",
            evidence_snippet="Rahul called 9876543210",
            extracted_at=datetime.now(timezone.utc),
        )

        orig_dict = rel.model_dump()
        proposals = propose_resolutions([mA, mC], relationships=[rel])
        self.assertEqual(rel.model_dump(), orig_dict)


if __name__ == "__main__":
    unittest.main()
