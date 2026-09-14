"""Integration tests for Phase 10 — Final ML Pipeline Integration.

Tests:
1. TEST 1 — BASIC DOCUMENT (Preprocessing -> NER -> ExtractionResult)
2. TEST 2 — RELATIONSHIP DOCUMENT (NER + Relationship Extraction)
3. TEST 3 — TRANSACTION FLOW (Structured Transaction parsing -> Pattern detection)
4. TEST 4 — CIRCULAR TRANSACTION (3-node cycle within 30 days generated through pipeline)
5. TEST 5 — RAPID TRANSFER (3-node forward chain within 48 hours generated through pipeline)
6. TEST 6 — LOCATION TIME OVERLAP (Co-presence within 2 hours generated through pipeline)
7. TEST 7 — LEAD GENERATION (Pattern -> Lead generation conforms to schema)
8. TEST 8 — EMPTY DOCUMENT (Safe handling of non-informative input, no crash)
9. TEST 9 — INSUFFICIENT PATTERN DATA (No fabricated patterns without valid timestamps)
10. TEST 10 — INVALID INPUT (Controlled ValueError / TypeError on invalid input)
11. TEST 11 — DETERMINISM (Identical inputs produce identical logical outputs)
12. TEST 12 — SERIALIZATION (Complete pipeline output serializable to valid JSON)
13. TEST 13 — REGRESSION (Phase 1–9 capabilities remain intact)
14. TEST 14 — NO DATABASE ACCESS (Zero dependency on PostgreSQL or Neo4j)
15. TEST 15 — NO BACKEND DEPENDENCY (Zero dependency on FastAPI server runtime)
"""

import json
from pathlib import Path
import unittest

from ml.pipeline import process_document
from ml.structured import TransactionRecord
from shared.schemas.enums import (
    EntityType,
    LeadPriority,
    LeadStatus,
    LeadType,
    PatternType,
    RelationshipStatus,
    RelationshipType,
    Severity,
)
from shared.schemas.models import (
    ExtractionResult,
    Lead,
    Pattern,
    Relationship,
    ResolutionProposal,
)


class TestPipelineIntegration(unittest.TestCase):
    """Phase 10 ML Pipeline integration test suite."""

    def test_01_basic_document(self):
        """TEST 1: Document loads, normalizes text, extracts entities, and yields ExtractionResult."""
        text = "Vikram Sharma (+919876543210) works at Apex Logistics in Mumbai."
        result = process_document("doc_basic_001", text)

        self.assertIsInstance(result, ExtractionResult)
        self.assertEqual(result.document_id, "doc_basic_001")
        self.assertTrue(len(result.entities) >= 3)

        entity_types = {e.type for e in result.entities}
        self.assertIn(EntityType.PERSON, entity_types)
        self.assertIn(EntityType.PHONE, entity_types)
        self.assertIn(EntityType.LOCATION, entity_types)

        # Validate Pydantic serialization
        dumped = result.model_dump()
        revalidated = ExtractionResult.model_validate(dumped)
        self.assertEqual(revalidated.document_id, "doc_basic_001")

    def test_02_relationship_document(self):
        """TEST 2: Entity extraction and relationship extraction work together in the pipeline."""
        text = "Inspector Rahul Verma called Vikram Sharma regarding case investigation."
        result = process_document("doc_rel_002", text)

        self.assertIsInstance(result, ExtractionResult)
        self.assertTrue(len(result.entities) >= 2)
        self.assertTrue(len(result.relationships) >= 1)

        rel = result.relationships[0]
        self.assertEqual(rel.relationship, RelationshipType.CALLED)
        self.assertEqual(rel.source_document_id, "doc_rel_002")
        self.assertIn(rel.source_entity_id, {e.id for e in result.entities})
        self.assertIn(rel.target_entity_id, {e.id for e in result.entities})

    def test_03_transaction_flow(self):
        """TEST 3: Transaction records parse, normalize, and generate patterns through pipeline."""
        tx_data = [
            {
                "sender": "ACC_ALPHA",
                "recipient": "ACC_BETA",
                "amount": 75000.0,
                "currency": "INR",
                "transaction_time": "2026-04-01T10:00:00",
                "record_id": "tx_pipe_01",
            },
            {
                "sender": "ACC_BETA",
                "recipient": "ACC_GAMMA",
                "amount": 70000.0,
                "currency": "INR",
                "transaction_time": "2026-04-01T16:00:00",
                "record_id": "tx_pipe_02",
            },
        ]
        analysis = process_document(
            "doc_tx_003",
            "",
            transactions=tx_data,
            return_full_analysis=True,
        )
        self.assertIsInstance(analysis, dict)
        self.assertIn("extraction_result", analysis)
        self.assertIn("patterns", analysis)

        patterns = analysis["patterns"]
        self.assertTrue(len(patterns) >= 1)
        self.assertIsInstance(patterns[0], Pattern)

    def test_04_circular_transaction(self):
        """TEST 4: A -> B -> C -> A within 30 days generates CIRCULAR_TRANSACTION through pipeline."""
        cycle_txs = [
            {
                "sender": "ACC_A",
                "recipient": "ACC_B",
                "amount": 50000.0,
                "currency": "INR",
                "transaction_time": "2026-05-01T10:00:00",
                "record_id": "c_tx_1",
            },
            {
                "sender": "ACC_B",
                "recipient": "ACC_C",
                "amount": 50000.0,
                "currency": "INR",
                "transaction_time": "2026-05-10T12:00:00",
                "record_id": "c_tx_2",
            },
            {
                "sender": "ACC_C",
                "recipient": "ACC_A",
                "amount": 50000.0,
                "currency": "INR",
                "transaction_time": "2026-05-20T14:00:00",
                "record_id": "c_tx_3",
            },
        ]
        analysis = process_document(
            "doc_circ_004",
            "",
            transactions=cycle_txs,
            return_full_analysis=True,
        )
        patterns = analysis["patterns"]
        pattern_types = [p.type for p in patterns]
        self.assertIn(PatternType.CIRCULAR_TRANSACTION, pattern_types)

        circ_pattern = next(p for p in patterns if p.type == PatternType.CIRCULAR_TRANSACTION)
        self.assertEqual(circ_pattern.severity, Severity.HIGH)
        self.assertEqual(circ_pattern.status, RelationshipStatus.INFERRED)
        self.assertEqual(sorted(circ_pattern.entities), ["ACC_A", "ACC_B", "ACC_C"])

    def test_05_rapid_transfer(self):
        """TEST 5: A -> B -> C within 48 hours generates RAPID_TRANSFER_CHAIN through pipeline."""
        rapid_txs = [
            {
                "sender": "ACC_SRC",
                "recipient": "ACC_MID",
                "amount": 100000.0,
                "currency": "INR",
                "transaction_time": "2026-06-01T10:00:00",
                "record_id": "rt_tx_1",
            },
            {
                "sender": "ACC_MID",
                "recipient": "ACC_DST",
                "amount": 98000.0,
                "currency": "INR",
                "transaction_time": "2026-06-02T14:00:00",  # 28 hours later
                "record_id": "rt_tx_2",
            },
        ]
        analysis = process_document(
            "doc_rapid_005",
            "",
            transactions=rapid_txs,
            return_full_analysis=True,
        )
        patterns = analysis["patterns"]
        pattern_types = [p.type for p in patterns]
        self.assertIn(PatternType.RAPID_TRANSFER_CHAIN, pattern_types)

        rapid_pattern = next(p for p in patterns if p.type == PatternType.RAPID_TRANSFER_CHAIN)
        self.assertEqual(rapid_pattern.severity, Severity.HIGH)
        self.assertEqual(rapid_pattern.entities, ["ACC_SRC", "ACC_MID", "ACC_DST"])

    def test_06_location_time_overlap(self):
        """TEST 6: Two events at same location within 2 hours generate LOCATION_TIME_OVERLAP."""
        overlap_events = [
            {
                "caller": "+919876543210",
                "callee": "+919111111111",
                "call_time": "2026-07-01T10:00:00",
                "location": "Connaught Place, New Delhi",
                "record_id": "cdr_ov_1",
            },
            {
                "caller": "+919999999999",
                "callee": "+919222222222",
                "call_time": "2026-07-01T11:30:00",  # 90 min later
                "location": "Connaught Place, New Delhi",
                "record_id": "cdr_ov_2",
            },
        ]
        analysis = process_document(
            "doc_loc_006",
            "",
            cdrs=overlap_events,
            return_full_analysis=True,
        )
        patterns = analysis["patterns"]
        pattern_types = [p.type for p in patterns]
        self.assertIn(PatternType.LOCATION_TIME_OVERLAP, pattern_types)

    def test_07_lead_generation(self):
        """TEST 7: Detected patterns trigger Phase 9 lead generation conforming to frozen schema."""
        rapid_txs = [
            {
                "sender": "ACC_1",
                "recipient": "ACC_2",
                "amount": 20000.0,
                "currency": "INR",
                "transaction_time": "2026-08-01T10:00:00",
                "record_id": "tx_lead_1",
            },
            {
                "sender": "ACC_2",
                "recipient": "ACC_3",
                "amount": 19500.0,
                "currency": "INR",
                "transaction_time": "2026-08-01T14:00:00",
                "record_id": "tx_lead_2",
            },
        ]
        analysis = process_document(
            "doc_lead_007",
            "",
            transactions=rapid_txs,
            return_full_analysis=True,
        )
        leads = analysis["leads"]
        self.assertTrue(len(leads) >= 1)

        lead = leads[0]
        self.assertIsInstance(lead, Lead)
        self.assertEqual(lead.type, LeadType.RAPID_TRANSFER_CHAIN)
        self.assertEqual(lead.priority, LeadPriority.HIGH)
        self.assertEqual(lead.status, LeadStatus.REVIEW_REQUIRED)
        self.assertFalse(hasattr(lead, "severity"))

    def test_08_empty_document(self):
        """TEST 8: Document with no detectable entities/relationships yields empty collections without crashing."""
        result = process_document("doc_empty_008", "Meeting scheduled for Tuesday.")
        self.assertIsInstance(result, ExtractionResult)
        self.assertEqual(result.document_id, "doc_empty_008")
        self.assertEqual(len(result.entities), 0)
        self.assertEqual(len(result.relationships), 0)

    def test_09_insufficient_pattern_data(self):
        """TEST 9: Missing timestamps or exceeding thresholds produces no fabricated patterns."""
        # Gap > 48 hours
        stale_txs = [
            {
                "sender": "ACC_1",
                "recipient": "ACC_2",
                "amount": 1000.0,
                "currency": "INR",
                "transaction_time": "2026-01-01T10:00:00",
                "record_id": "t1",
            },
            {
                "sender": "ACC_2",
                "recipient": "ACC_3",
                "amount": 1000.0,
                "currency": "INR",
                "transaction_time": "2026-01-10T10:00:00",  # 9 days later (> 48 hours)
                "record_id": "t2",
            },
        ]
        analysis = process_document(
            "doc_stale_009",
            "",
            transactions=stale_txs,
            return_full_analysis=True,
        )
        # Should NOT produce RAPID_TRANSFER_CHAIN
        rapid_patterns = [p for p in analysis["patterns"] if p.type == PatternType.RAPID_TRANSFER_CHAIN]
        self.assertEqual(len(rapid_patterns), 0)

    def test_10_invalid_input(self):
        """TEST 10: Invalid input raises controlled ValueError or TypeError."""
        # Empty document_id
        with self.assertRaises(ValueError):
            process_document("", "Valid text")

        with self.assertRaises(ValueError):
            process_document(None, "Valid text")

        # Invalid text type
        with self.assertRaises(TypeError):
            process_document("doc_010", 12345)

    def test_11_determinism(self):
        """TEST 11: Exact same input processed twice produces identical logical output."""
        text = "Vikram Sharma (+919876543210) called Amit Kumar in Delhi."
        res1 = process_document("doc_det_011", text)
        res2 = process_document("doc_det_011", text)

        self.assertEqual(len(res1.entities), len(res2.entities))
        self.assertEqual(len(res1.relationships), len(res2.relationships))
        self.assertEqual([e.id for e in res1.entities], [e.id for e in res2.entities])
        self.assertEqual([r.id for r in res1.relationships], [r.id for r in res2.relationships])

    def test_12_serialization(self):
        """TEST 12: Pipeline output serializes to JSON and validates cleanly."""
        text = "Inspector Rahul called Amit Kumar."
        analysis = process_document("doc_ser_012", text, return_full_analysis=True)

        envelope = analysis["extraction_result"]
        json_str = json.dumps(envelope.model_dump(mode="json"))
        self.assertIsInstance(json_str, str)

        deserialized = ExtractionResult.model_validate_json(json_str)
        self.assertEqual(deserialized.document_id, "doc_ser_012")

    def test_13_regression_checks(self):
        """TEST 13: Core components continue to function in isolated unit modes."""
        from ml.extraction import extract_entities
        from ml.preprocessing import normalize_text
        from ml.relationships import extract_relationships

        cleaned = normalize_text("  Rahul  Kumar   ")
        self.assertEqual(cleaned, "Rahul Kumar")

        entities = extract_entities("Rahul Kumar called Amit", "doc_reg")
        self.assertTrue(len(entities) >= 1)

    def test_14_no_database_access(self):
        """TEST 14: ML pipeline runs without PostgreSQL or Neo4j drivers or credentials."""
        import subprocess
        import sys

        # Verify no database connection modules are imported or required by pipeline.
        # We run this in a subprocess to ensure clean sys.modules, preventing order-dependent
        # failures when this test runs after backend tests in a combined test suite.
        script = (
            "import sys\n"
            "import ml.pipeline\n"
            "assert 'psycopg2' not in sys.modules, 'psycopg2 loaded by ML'\n"
            "assert 'asyncpg' not in sys.modules, 'asyncpg loaded by ML'\n"
            "assert 'neo4j' not in sys.modules, 'neo4j loaded by ML'\n"
        )

        result = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True,
            text=True
        )
        self.assertEqual(
            result.returncode, 0,
            f"ML pipeline isolation test failed: {result.stderr}"
        )

    def test_15_no_backend_dependency(self):
        """TEST 15: ML pipeline executes without running FastAPI or any HTTP server."""
        result = process_document("doc_standalone", "Standalone document text without server.")
        self.assertIsInstance(result, ExtractionResult)


if __name__ == "__main__":
    unittest.main()
