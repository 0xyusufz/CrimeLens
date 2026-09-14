"""Unit tests for Phase 9 — Investigative Lead Generation.

Tests:
1. CIRCULAR_TRANSACTION pattern -> Lead (priority HIGH, status REVIEW_REQUIRED)
2. RAPID_TRANSFER_CHAIN pattern -> Lead (priority HIGH, evidence traceability)
3. LOCATION_TIME_OVERLAP pattern -> Lead (priority MEDIUM, evidence traceability)
4. No pattern -> zero leads (no hallucinated leads)
5. Duplicate patterns -> deduplication produces exactly one lead
6. Invalid priority rejection (e.g. CRITICAL, SEVERE)
7. Invalid status rejection (e.g. DETECTED)
8. Absence of criminal/guilt assertions in titles and explanations
9. Absence of PostgreSQL database canonical UUIDs
10. Deterministic output under input reordering
11. Lead schema validation against shared contract (extra=forbid, no severity, no confidence)
12. Full Phase 8 Pattern -> Phase 9 Lead integration flow
"""

import re
import unittest

from pydantic import ValidationError

from ml.leads import generate_leads
from ml.patterns import (
    detect_circular_transactions,
    detect_location_time_overlaps,
    detect_rapid_transfers,
)
from shared.schemas.enums import (
    LeadPriority,
    LeadStatus,
    LeadType,
    PatternType,
    RelationshipStatus,
    Severity,
)
from shared.schemas.models import Lead, Pattern


class TestLeadGeneration(unittest.TestCase):
    """Test suite for Phase 9 lead generation."""

    def test_circular_transaction_lead(self):
        """TEST 1: CIRCULAR_TRANSACTION pattern maps to valid HIGH priority Lead."""
        pattern = Pattern(
            id="pattern_001",
            type=PatternType.CIRCULAR_TRANSACTION,
            severity=Severity.HIGH,
            status=RelationshipStatus.INFERRED,
            entities=["ACC_001", "ACC_002", "ACC_003"],
            explanation="Circular fund transfer detected: ACC_001 → ACC_002 → ACC_003 → ACC_001",
            evidence_ids=["tx_01", "tx_02", "tx_03"],
        )

        leads = generate_leads(patterns=[pattern])
        self.assertEqual(len(leads), 1)

        lead = leads[0]
        self.assertIsInstance(lead, Lead)
        self.assertEqual(lead.id, "lead_001")
        self.assertEqual(lead.type, LeadType.CIRCULAR_TRANSACTION)
        self.assertEqual(lead.priority, LeadPriority.HIGH)
        self.assertEqual(lead.status, LeadStatus.REVIEW_REQUIRED)
        self.assertEqual(lead.entity_ids, ["ACC_001", "ACC_002", "ACC_003"])
        self.assertEqual(lead.evidence_ids, ["tx_01", "tx_02", "tx_03"])
        self.assertTrue(len(lead.title) > 0)
        self.assertTrue(len(lead.explanation) > 0)

        # Confirm validation against Pydantic schema
        dumped = lead.model_dump()
        validated = Lead.model_validate(dumped)
        self.assertEqual(validated.id, lead.id)

    def test_rapid_transfer_lead(self):
        """TEST 2: RAPID_TRANSFER_CHAIN pattern maps to valid HIGH priority Lead with evidence traceability."""
        pattern = Pattern(
            id="pattern_002",
            type=PatternType.RAPID_TRANSFER_CHAIN,
            severity=Severity.HIGH,
            status=RelationshipStatus.INFERRED,
            entities=["ACC_A", "ACC_B", "ACC_C"],
            explanation="Rapid fund transfer chain detected: ACC_A → ACC_B → ACC_C",
            evidence_ids=["tx_rt_1", "tx_rt_2"],
        )

        leads = generate_leads(patterns=[pattern])
        self.assertEqual(len(leads), 1)

        lead = leads[0]
        self.assertEqual(lead.type, LeadType.RAPID_TRANSFER_CHAIN)
        self.assertEqual(lead.priority, LeadPriority.HIGH)
        self.assertEqual(lead.status, LeadStatus.REVIEW_REQUIRED)
        self.assertEqual(lead.evidence_ids, ["tx_rt_1", "tx_rt_2"])
        self.assertIn("ACC_A", lead.title)

    def test_location_time_overlap_lead(self):
        """TEST 3: LOCATION_TIME_OVERLAP pattern maps to valid MEDIUM priority Lead with evidence traceability."""
        pattern = Pattern(
            id="pattern_003",
            type=PatternType.LOCATION_TIME_OVERLAP,
            severity=Severity.MEDIUM,
            status=RelationshipStatus.INFERRED,
            entities=["Rahul Sharma", "Vikram Singh"],
            explanation="Location-time overlap detected at Sector 18, Noida",
            evidence_ids=["ev_loc_1", "ev_loc_2"],
        )

        leads = generate_leads(patterns=[pattern])
        self.assertEqual(len(leads), 1)

        lead = leads[0]
        self.assertEqual(lead.type, LeadType.LOCATION_TIME_OVERLAP)
        self.assertEqual(lead.priority, LeadPriority.MEDIUM)
        self.assertEqual(lead.status, LeadStatus.REVIEW_REQUIRED)
        self.assertEqual(lead.entity_ids, ["Rahul Sharma", "Vikram Singh"])
        self.assertEqual(lead.evidence_ids, ["ev_loc_1", "ev_loc_2"])

    def test_no_pattern_produces_no_leads(self):
        """TEST 4: Empty pattern list produces no leads (does not hallucinate leads)."""
        self.assertEqual(generate_leads([]), [])
        self.assertEqual(generate_leads(patterns=None), [])

    def test_duplicate_patterns_deduplicated(self):
        """TEST 5: Duplicate pattern inputs produce exactly one lead."""
        pattern = Pattern(
            id="pattern_001",
            type=PatternType.CIRCULAR_TRANSACTION,
            severity=Severity.HIGH,
            status=RelationshipStatus.INFERRED,
            entities=["ACC_001", "ACC_002", "ACC_003"],
            explanation="Circular transfer",
            evidence_ids=["tx_01", "tx_02", "tx_03"],
        )
        leads = generate_leads(patterns=[pattern, pattern, pattern])
        self.assertEqual(len(leads), 1)

    def test_invalid_priority_rejected(self):
        """TEST 6: Invalid priority values (e.g. CRITICAL, SEVERE) are rejected by schema."""
        payload = {
            "id": "lead_001",
            "type": "CIRCULAR_TRANSACTION",
            "priority": "CRITICAL",  # Invalid
            "status": "REVIEW_REQUIRED",
            "title": "Test Title",
            "explanation": "Test explanation",
            "entity_ids": ["E1"],
            "evidence_ids": ["EV1"],
        }
        with self.assertRaises(ValidationError):
            Lead.model_validate(payload)

    def test_invalid_status_rejected(self):
        """TEST 7: DETECTED or PREDICTED status is rejected by Lead schema."""
        payload = {
            "id": "lead_001",
            "type": "CIRCULAR_TRANSACTION",
            "priority": "HIGH",
            "status": "DETECTED",  # Invalid
            "title": "Test Title",
            "explanation": "Test explanation",
            "entity_ids": ["E1"],
            "evidence_ids": ["EV1"],
        }
        with self.assertRaises(ValidationError):
            Lead.model_validate(payload)

        # PREDICTED is in RelationshipStatus, but NOT in LeadStatus
        payload["status"] = "PREDICTED"
        with self.assertRaises(ValidationError):
            Lead.model_validate(payload)

    def test_no_criminality_claim(self):
        """TEST 8: Generated lead title and explanation do NOT make guilt or criminal claims."""
        patterns = [
            Pattern(
                id="p1",
                type=PatternType.CIRCULAR_TRANSACTION,
                severity=Severity.HIGH,
                status=RelationshipStatus.INFERRED,
                entities=["A", "B", "C"],
                explanation="Circular fund flow",
                evidence_ids=["tx1", "tx2", "tx3"],
            ),
            Pattern(
                id="p2",
                type=PatternType.RAPID_TRANSFER_CHAIN,
                severity=Severity.HIGH,
                status=RelationshipStatus.INFERRED,
                entities=["X", "Y", "Z"],
                explanation="Rapid fund chain",
                evidence_ids=["tx4", "tx5"],
            ),
            Pattern(
                id="p3",
                type=PatternType.LOCATION_TIME_OVERLAP,
                severity=Severity.MEDIUM,
                status=RelationshipStatus.INFERRED,
                entities=["P1", "P2"],
                explanation="Overlap",
                evidence_ids=["ev1", "ev2"],
            ),
        ]
        leads = generate_leads(patterns=patterns)
        forbidden_terms = ["criminal", "guilty", "guilt", "perpetrator", "illegal", "culprit", "accused"]

        for lead in leads:
            text = f"{lead.title} {lead.explanation}".lower()
            for term in forbidden_terms:
                self.assertNotIn(term, text, f"Forbidden accusatory term '{term}' found in lead text")

    def test_no_database_id_generation(self):
        """TEST 9: ML output uses staging identifiers (lead_001), never PostgreSQL canonical UUIDs."""
        pattern = Pattern(
            id="p1",
            type=PatternType.CIRCULAR_TRANSACTION,
            severity=Severity.HIGH,
            status=RelationshipStatus.INFERRED,
            entities=["ACC_1", "ACC_2", "ACC_3"],
            explanation="Circular",
            evidence_ids=["t1", "t2", "t3"],
        )
        leads = generate_leads(patterns=[pattern])
        lead = leads[0]
        self.assertTrue(lead.id.startswith("lead_"))
        uuid_regex = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
        self.assertFalse(re.match(uuid_regex, lead.id, re.IGNORECASE))
        self.assertFalse(hasattr(lead, "case_id"))

    def test_determinism_under_permutation(self):
        """TEST 10: Input reordering produces identical lead content and ordering."""
        p1 = Pattern(
            id="p1",
            type=PatternType.CIRCULAR_TRANSACTION,
            severity=Severity.HIGH,
            status=RelationshipStatus.INFERRED,
            entities=["A", "B", "C"],
            explanation="Circular",
            evidence_ids=["t1", "t2", "t3"],
        )
        p2 = Pattern(
            id="p2",
            type=PatternType.LOCATION_TIME_OVERLAP,
            severity=Severity.MEDIUM,
            status=RelationshipStatus.INFERRED,
            entities=["P1", "P2"],
            explanation="Overlap",
            evidence_ids=["e1", "e2"],
        )

        leads_order_1 = generate_leads(patterns=[p1, p2])
        leads_order_2 = generate_leads(patterns=[p2, p1])

        self.assertEqual(len(leads_order_1), len(leads_order_2))
        for l1, l2 in zip(leads_order_1, leads_order_2):
            self.assertEqual(l1.id, l2.id)
            self.assertEqual(l1.type, l2.type)
            self.assertEqual(l1.priority, l2.priority)
            self.assertEqual(l1.title, l2.title)
            self.assertEqual(l1.entity_ids, l2.entity_ids)
            self.assertEqual(l1.evidence_ids, l2.evidence_ids)

    def test_schema_rejects_severity_and_confidence(self):
        """Confirm extra forbidden fields like severity and confidence raise ValidationError."""
        payload = {
            "id": "lead_001",
            "type": "CIRCULAR_TRANSACTION",
            "priority": "HIGH",
            "status": "REVIEW_REQUIRED",
            "title": "Test",
            "explanation": "Test",
            "entity_ids": ["E1"],
            "evidence_ids": ["EV1"],
            "severity": "HIGH",  # Forbidden on Lead
        }
        with self.assertRaises(ValidationError):
            Lead.model_validate(payload)

        payload.pop("severity")
        payload["confidence"] = 0.95  # Forbidden on Lead
        with self.assertRaises(ValidationError):
            Lead.model_validate(payload)

    def test_phase8_to_phase9_flow(self):
        """End-to-end integration: structured data -> Phase 8 patterns -> Phase 9 leads."""
        tx_records = [
            {
                "sender": "ACC_1",
                "recipient": "ACC_2",
                "amount": 100000.0,
                "currency": "INR",
                "transaction_time": "2026-01-01T10:00:00",
                "record_id": "tx_1",
            },
            {
                "sender": "ACC_2",
                "recipient": "ACC_3",
                "amount": 95000.0,
                "currency": "INR",
                "transaction_time": "2026-01-02T10:00:00",
                "record_id": "tx_2",
            },
            {
                "sender": "ACC_3",
                "recipient": "ACC_1",
                "amount": 90000.0,
                "currency": "INR",
                "transaction_time": "2026-01-10T10:00:00",
                "record_id": "tx_3",
            },
        ]
        circular_patterns = detect_circular_transactions(tx_records)
        rapid_patterns = detect_rapid_transfers(tx_records[:2])
        all_patterns = circular_patterns + rapid_patterns
        self.assertEqual(len(all_patterns), 2)

        leads = generate_leads(patterns=all_patterns)
        self.assertEqual(len(leads), 2)

        types = [lead.type for lead in leads]
        self.assertIn(LeadType.CIRCULAR_TRANSACTION, types)
        self.assertIn(LeadType.RAPID_TRANSFER_CHAIN, types)
        for lead in leads:
            self.assertEqual(lead.priority, LeadPriority.HIGH)
            self.assertEqual(lead.status, LeadStatus.REVIEW_REQUIRED)


if __name__ == "__main__":
    unittest.main()
