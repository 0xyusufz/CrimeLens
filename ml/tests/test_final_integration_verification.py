"""Phase 9 — Final ML Handoff & Integration Verification Test Suite.

Verifies:
1. Backend adapter discovery across all candidates:
   ("ml.process", "process_document"), ("ml.pipeline", "process_document"), ("ml.extract", "process_document").
2. Full calling conventions (A: bytes+filename+id, B: id+text, C: full intelligence bundle).
3. Complete end-to-end orchestration using real ML pipeline logic (not simulated).
4. Frozen schema adherence, Pydantic validation, and lossless JSON serialization.
5. Deterministic baseline authority, pattern detection, and explainable lead generation.
6. Cold-start import and execution with zero API keys or external network connections.
7. Strict boundaries: zero database connections, zero Neo4j writes, zero arbitrary code execution.
"""

from __future__ import annotations

import importlib
import json
import os
import unittest
from typing import Any

from ml.ai.client.client import AIClient
from ml.ai.providers.mock import MockReasoningProvider
from ml.config import MLConfig
from ml.pipeline import process_document
from ml.validation.output_validator import validate_extraction_result, validate_json_serializability
from shared.schemas.enums import (
    EntityType,
    LeadPriority,
    LeadStatus,
    RelationshipStatus,
    RelationshipType,
    Severity,
)
from shared.schemas.models import (
    EntityMention,
    ExtractionResult,
    Lead,
    Pattern,
    Relationship,
    ResolutionProposal,
)


class TestBackendDiscoveryAndInvocation(unittest.TestCase):
    """Verifies that Person A's backend adapter discovers and invokes ML cleanly."""

    def test_discovery_all_three_candidate_modules(self) -> None:
        """Verify all three candidates in Person A's adapter tuple resolve successfully."""
        candidates = (
            ("ml.process", "process_document"),
            ("ml.pipeline", "process_document"),
            ("ml.extract", "process_document"),
        )
        resolved_count = 0
        for mod_name, func_name in candidates:
            mod = importlib.import_module(mod_name)
            self.assertTrue(hasattr(mod, func_name), f"{mod_name} must have {func_name}")
            fn = getattr(mod, func_name)
            self.assertTrue(callable(fn), f"{mod_name}.{func_name} must be callable")
            resolved_count += 1

        self.assertEqual(resolved_count, 3)

    def test_top_level_ml_package_export(self) -> None:
        """Verify `from ml import process_document` works as expected."""
        import ml
        self.assertTrue(hasattr(ml, "process_document"))
        self.assertTrue(callable(ml.process_document))

    def test_calling_convention_a_bytes_filename_doc_id(self) -> None:
        """Convention A: process_document(document_bytes, filename, document_id) - adapter preferred."""
        doc_bytes = b"Suspect Anand Verma (+919876543210) transferred funds to Axis Bank account 987654321098."
        filename = "investigation_memo.txt"
        doc_id = "doc_conv_a_001"

        result = process_document(doc_bytes, filename, doc_id)
        self.assertIsInstance(result, ExtractionResult)
        self.assertEqual(result.document_id, doc_id)
        self.assertGreaterEqual(len(result.entities), 1)
        validate_extraction_result(result)

    def test_calling_convention_b_named_kwargs(self) -> None:
        """Convention B: process_document(document_id=..., text=...)."""
        doc_id = "doc_conv_b_002"
        text = "Vikram Malhotra called callee 9123456780 on 2024-05-01."

        result = process_document(document_id=doc_id, text=text)
        self.assertIsInstance(result, ExtractionResult)
        self.assertEqual(result.document_id, doc_id)
        validate_extraction_result(result)

    def test_calling_convention_c_full_intelligence_bundle(self) -> None:
        """Convention C: process_document(..., return_full_analysis=True) returning full dictionary."""
        doc_id = "doc_conv_c_003"
        text = "Anand Verma sent funds to Vikram Malhotra."
        transactions = [
            {"sender": "ACC_A", "recipient": "ACC_B", "amount": 50000.0, "currency": "INR", "transaction_time": "2024-05-01T10:00:00Z"},
            {"sender": "ACC_B", "recipient": "ACC_C", "amount": 48000.0, "currency": "INR", "transaction_time": "2024-05-01T14:00:00Z"},
            {"sender": "ACC_C", "recipient": "ACC_A", "amount": 45000.0, "currency": "INR", "transaction_time": "2024-05-02T09:00:00Z"},
        ]
        cdrs = [
            {"caller": "9876543210", "callee": "9123456780", "call_time": "2024-05-01T10:30:00Z", "duration": 120},
        ]

        bundle = process_document(
            doc_id,
            text,
            transactions=transactions,
            cdrs=cdrs,
            return_full_analysis=True,
        )
        self.assertIsInstance(bundle, dict)
        self.assertIn("extraction_result", bundle)
        self.assertIn("resolution_proposals", bundle)
        self.assertIn("patterns", bundle)
        self.assertIn("leads", bundle)

        # ExtractionResult contract verification
        validate_extraction_result(bundle["extraction_result"])

        # Resolution proposals
        for prop in bundle["resolution_proposals"]:
            self.assertIsInstance(prop, ResolutionProposal)

        # Deterministic circular pattern detection
        self.assertGreaterEqual(len(bundle["patterns"]), 1)
        for p in bundle["patterns"]:
            self.assertIsInstance(p, Pattern)
            self.assertEqual(p.status, RelationshipStatus.INFERRED)

        # Deterministic lead generation
        self.assertGreaterEqual(len(bundle["leads"]), 1)
        for lead in bundle["leads"]:
            self.assertIsInstance(lead, Lead)
            self.assertEqual(lead.status, LeadStatus.REVIEW_REQUIRED)


class TestEndToEndInvestigationPipeline(unittest.TestCase):
    """Exercises real ML pipeline end-to-end with synthetic case file and mocked multimodal AI."""

    def setUp(self) -> None:
        fixture_path = os.path.join(os.path.dirname(__file__), "..", "fixtures", "synthetic_large_document.json")
        with open(fixture_path, "r", encoding="utf-8") as f:
            self.fixture = json.load(f)

    def test_full_synthetic_investigation_flow(self) -> None:
        """Run complete document understanding, AI reasoning, reconciliation, patterns, and leads."""
        doc_id = self.fixture.get("fixture_id", "doc_syn_001")
        doc_text = "\n\n".join(f"Page {p['page_number']}:\n{p['text']}" for p in self.fixture["pages"])
        transactions = [
            {"sender": "ACC_A", "recipient": "ACC_B", "amount": 50000.0, "currency": "INR", "transaction_time": "2024-01-15T10:00:00Z"},
            {"sender": "ACC_B", "recipient": "ACC_C", "amount": 48000.0, "currency": "INR", "transaction_time": "2024-01-15T14:00:00Z"},
            {"sender": "ACC_C", "recipient": "ACC_A", "amount": 45000.0, "currency": "INR", "transaction_time": "2024-01-16T09:00:00Z"},
        ]
        cdrs = [
            {"caller": "9876543210", "callee": "9123456780", "call_time": "2024-01-14T18:30:00Z", "duration": 180},
        ]

        # Configure AI client with mock reasoning provider
        client = AIClient(MockReasoningProvider())
        cfg = MLConfig(ai_enabled=True)

        bundle = process_document(
            doc_id,
            doc_text,
            transactions=transactions,
            cdrs=cdrs,
            config=cfg,
            ai_client=client,
            return_full_analysis=True,
        )

        # 1. Output structure
        self.assertIsInstance(bundle, dict)
        self.assertIn("extraction_result", bundle)
        ext_res = bundle["extraction_result"]
        self.assertEqual(ext_res.document_id, doc_id)

        # 2. Schema compliance & serializability
        validate_extraction_result(ext_res)
        validate_json_serializability(ext_res)

        # 3. Deterministic + AI candidate reconciliation
        self.assertGreaterEqual(len(ext_res.entities), 4)
        entity_types = {e.type for e in ext_res.entities}
        self.assertIn(EntityType.PHONE, entity_types)
        self.assertIn(EntityType.BANK_ACCOUNT, entity_types)

        # 4. Pattern detection: Circular transaction detected deterministically
        circular_patterns = [p for p in bundle["patterns"] if p.type.value == "CIRCULAR_TRANSACTION"]
        self.assertGreaterEqual(len(circular_patterns), 1)
        self.assertEqual(circular_patterns[0].severity, Severity.HIGH)
        self.assertEqual(circular_patterns[0].status, RelationshipStatus.INFERRED)

        # 5. Lead generation: Investigative leads generated deterministically
        high_priority_leads = [l for l in bundle["leads"] if l.priority == LeadPriority.HIGH]
        self.assertGreaterEqual(len(high_priority_leads), 1)
        self.assertEqual(high_priority_leads[0].status, LeadStatus.REVIEW_REQUIRED)
        lead_types = {l.type.value for l in bundle["leads"]}
        self.assertTrue("CIRCULAR_TRANSACTION" in lead_types or "RAPID_TRANSFER_CHAIN" in lead_types)

        # 6. Traceability metrics present
        metrics = bundle["ai_traceability"]
        self.assertTrue(metrics["ai_enabled"])
        self.assertTrue(metrics["ai_attempted"])
        self.assertFalse(metrics["ai_fallback_occurred"])


class TestColdStartAndIsolation(unittest.TestCase):
    """Verifies that ML runs offline without database, credentials, or network connections."""

    def test_clean_import_without_api_keys(self) -> None:
        """ML package imports cleanly without AI_API_KEY or any provider secrets."""
        orig_key = os.environ.pop("AI_API_KEY", None)
        try:
            import ml
            import ml.config
            import ml.pipeline

            cfg = ml.config.MLConfig()
            self.assertFalse(cfg.ai_enabled)
            self.assertIsNone(cfg.ai_api_key)
        finally:
            if orig_key is not None:
                os.environ["AI_API_KEY"] = orig_key

    def test_ai_disabled_deterministic_independence(self) -> None:
        """Deterministic ML runs 100% independently without requiring any AI provider."""
        doc_text = "Suspect Amit (+919876543210) opened account ACC123456789 at Mumbai."
        result = process_document("doc_offline_001", doc_text, config=MLConfig(ai_enabled=False))

        self.assertIsInstance(result, ExtractionResult)
        self.assertGreaterEqual(len(result.entities), 1)
        validate_extraction_result(result)

    def test_zero_database_access_in_ml(self) -> None:
        """ML codebase contains zero database connection initialization or write calls."""
        ml_dir = os.path.dirname(os.path.dirname(__file__))
        this_file = os.path.basename(__file__)
        forbidden_terms = ["create_engine(", "psycopg2.connect(", "neo4j.GraphDatabase", "alembic"]

        for root, _, files in os.walk(ml_dir):
            for file in files:
                if file.endswith(".py") and file != this_file:
                    filepath = os.path.join(root, file)
                    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                        for term in forbidden_terms:
                            self.assertNotIn(
                                term,
                                content,
                                f"Forbidden database connection term {term!r} found in {filepath}",
                            )

    def test_no_arbitrary_code_execution(self) -> None:
        """Verify that AI response parsing uses strict json loading, never eval() on model output."""
        from ml.ai.response_parser import AIResponseParser

        parser = AIResponseParser()
        malicious_input = "__import__('os').system('echo hacked')"
        parsed = parser.parse_json_safely(malicious_input)
        # Should return safe empty structure, never execute
        self.assertIsInstance(parsed, dict)
        self.assertEqual(parsed, {})


if __name__ == "__main__":
    unittest.main()
