"""Unit tests for Phase 8 — Suspicious Pattern Detection.

Tests:
1. CIRCULAR_TRANSACTION:
   - positive: 3-node cycle within 30 days
   - positive boundary: exactly 30 days apart
   - negative: > 30 days
   - negative: 2-node cycle (A -> B -> A)
   - negative: disconnected chain (A -> B, C -> D, D -> A)
   - negative: non-cycle chain (A -> B, B -> C, D -> A)
   - negative: non-distinct nodes
   - deduplication of duplicate inputs

2. RAPID_TRANSFER_CHAIN:
   - positive: 3-node forward chain within 48 hours
   - positive boundary: exactly 48 hours
   - negative: > 48 hours
   - negative: disconnected edges (A -> B, C -> D)
   - negative: reverse/convergent edges (A -> B, C -> B)
   - negative: 2-node back-and-forth (A -> B, B -> A)
   - negative: same transaction reused as both edges
   - negative: reverse chronological order (t2 < t1)

3. LOCATION_TIME_OVERLAP:
   - positive: co-presence within 2 hours
   - positive boundary: exactly 2 hours apart
   - negative: > 2 hours apart
   - negative: different locations
   - negative: missing timestamp
   - negative: missing location
   - negative: same entity (A and A)
   - multi-source: CDRRecord and TransactionRecord overlap

4. SCHEMA VALIDATION:
   - Pydantic contract compliance
   - Status semantics: INFERRED (never DETECTED)
   - Extra fields forbidden check

5. DETERMINISM:
   - Shuffled input produces identical results
"""

from datetime import datetime, timedelta
import unittest

from ml.patterns import (
    detect_circular_transactions,
    detect_location_time_overlaps,
    detect_rapid_transfer_chains,
    detect_rapid_transfers,
)
from ml.structured import CDRRecord, TransactionRecord
from shared.schemas.enums import PatternType, RelationshipStatus, Severity
from shared.schemas.models import Pattern


class TestCircularTransactionDetection(unittest.TestCase):
    """Tests for CIRCULAR_TRANSACTION detector (3-node directed cycle <= 30 days)."""

    def test_positive_circular_transaction(self):
        """A -> B -> C -> A completed within 20 days qualifies."""
        records = [
            {
                "sender": "ACC_001",
                "recipient": "ACC_002",
                "amount": 100000.0,
                "currency": "INR",
                "transaction_time": "2026-01-01T10:00:00",
                "record_id": "txn_001",
            },
            {
                "sender": "ACC_002",
                "recipient": "ACC_003",
                "amount": 95000.0,
                "currency": "INR",
                "transaction_time": "2026-01-10T12:00:00",
                "record_id": "txn_002",
            },
            {
                "sender": "ACC_003",
                "recipient": "ACC_001",
                "amount": 90000.0,
                "currency": "INR",
                "transaction_time": "2026-01-20T15:00:00",
                "record_id": "txn_003",
            },
        ]
        patterns = detect_circular_transactions(records)
        self.assertEqual(len(patterns), 1)
        p = patterns[0]
        self.assertEqual(p.type, PatternType.CIRCULAR_TRANSACTION)
        self.assertEqual(p.severity, Severity.HIGH)
        self.assertEqual(p.status, RelationshipStatus.INFERRED)
        self.assertEqual(sorted(p.entities), ["ACC_001", "ACC_002", "ACC_003"])
        self.assertEqual(p.evidence_ids, ["txn_001", "txn_002", "txn_003"])
        self.assertIn("Circular fund transfer detected", p.explanation)

    def test_positive_boundary_exactly_30_days(self):
        """Earliest to latest transaction exactly 30 days qualifies."""
        t1 = datetime(2026, 1, 1, 0, 0, 0)
        t2 = t1 + timedelta(days=15)
        t3 = t1 + timedelta(days=30)  # Exactly 30 days
        records = [
            {
                "sender": "ACC_A",
                "recipient": "ACC_B",
                "amount": 50000.0,
                "currency": "INR",
                "transaction_time": t1.isoformat(),
                "record_id": "tx_bound_1",
            },
            {
                "sender": "ACC_B",
                "recipient": "ACC_C",
                "amount": 50000.0,
                "currency": "INR",
                "transaction_time": t2.isoformat(),
                "record_id": "tx_bound_2",
            },
            {
                "sender": "ACC_C",
                "recipient": "ACC_A",
                "amount": 50000.0,
                "currency": "INR",
                "transaction_time": t3.isoformat(),
                "record_id": "tx_bound_3",
            },
        ]
        patterns = detect_circular_transactions(records)
        self.assertEqual(len(patterns), 1)
        self.assertEqual(patterns[0].type, PatternType.CIRCULAR_TRANSACTION)

    def test_negative_exceeds_30_days(self):
        """Earliest to latest transaction > 30 days (e.g. 30 days + 1 second) does not qualify."""
        t1 = datetime(2026, 1, 1, 0, 0, 0)
        t2 = t1 + timedelta(days=15)
        t3 = t1 + timedelta(days=30, seconds=1)  # 30 days and 1 second
        records = [
            {
                "sender": "ACC_A",
                "recipient": "ACC_B",
                "amount": 50000.0,
                "currency": "INR",
                "transaction_time": t1.isoformat(),
                "record_id": "tx_late_1",
            },
            {
                "sender": "ACC_B",
                "recipient": "ACC_C",
                "amount": 50000.0,
                "currency": "INR",
                "transaction_time": t2.isoformat(),
                "record_id": "tx_late_2",
            },
            {
                "sender": "ACC_C",
                "recipient": "ACC_A",
                "amount": 50000.0,
                "currency": "INR",
                "transaction_time": t3.isoformat(),
                "record_id": "tx_late_3",
            },
        ]
        patterns = detect_circular_transactions(records)
        self.assertEqual(len(patterns), 0)

    def test_negative_two_node_cycle(self):
        """A -> B and B -> A is a 2-node cycle, NOT a 3-node CIRCULAR_TRANSACTION."""
        records = [
            {
                "sender": "ACC_A",
                "recipient": "ACC_B",
                "amount": 50000.0,
                "currency": "INR",
                "transaction_time": "2026-01-01T10:00:00",
                "record_id": "tx_2node_1",
            },
            {
                "sender": "ACC_B",
                "recipient": "ACC_A",
                "amount": 50000.0,
                "currency": "INR",
                "transaction_time": "2026-01-05T10:00:00",
                "record_id": "tx_2node_2",
            },
        ]
        patterns = detect_circular_transactions(records)
        self.assertEqual(len(patterns), 0)

    def test_negative_disconnected_chain(self):
        """A -> B, C -> D, D -> A is not a continuous A -> B -> C -> A chain."""
        records = [
            {
                "sender": "ACC_A",
                "recipient": "ACC_B",
                "amount": 10000.0,
                "currency": "INR",
                "transaction_time": "2026-01-01T10:00:00",
                "record_id": "tx_disc_1",
            },
            {
                "sender": "ACC_C",
                "recipient": "ACC_D",
                "amount": 10000.0,
                "currency": "INR",
                "transaction_time": "2026-01-05T10:00:00",
                "record_id": "tx_disc_2",
            },
            {
                "sender": "ACC_D",
                "recipient": "ACC_A",
                "amount": 10000.0,
                "currency": "INR",
                "transaction_time": "2026-01-10T10:00:00",
                "record_id": "tx_disc_3",
            },
        ]
        patterns = detect_circular_transactions(records)
        self.assertEqual(len(patterns), 0)

    def test_negative_non_cycle_chain(self):
        """A -> B, B -> C, D -> A is not a cycle (C does not send to D or A)."""
        records = [
            {
                "sender": "ACC_A",
                "recipient": "ACC_B",
                "amount": 10000.0,
                "currency": "INR",
                "transaction_time": "2026-01-01T10:00:00",
                "record_id": "tx_noncyc_1",
            },
            {
                "sender": "ACC_B",
                "recipient": "ACC_C",
                "amount": 10000.0,
                "currency": "INR",
                "transaction_time": "2026-01-05T10:00:00",
                "record_id": "tx_noncyc_2",
            },
            {
                "sender": "ACC_D",
                "recipient": "ACC_A",
                "amount": 10000.0,
                "currency": "INR",
                "transaction_time": "2026-01-10T10:00:00",
                "record_id": "tx_noncyc_3",
            },
        ]
        patterns = detect_circular_transactions(records)
        self.assertEqual(len(patterns), 0)

    def test_negative_duplicate_nodes(self):
        """A -> B, B -> B (invalid), B -> A does not qualify."""
        records = [
            {
                "sender": "ACC_A",
                "recipient": "ACC_B",
                "amount": 10000.0,
                "currency": "INR",
                "transaction_time": "2026-01-01T10:00:00",
                "record_id": "tx_dup_1",
            },
            {
                "sender": "ACC_B",
                "recipient": "ACC_B",
                "amount": 10000.0,
                "currency": "INR",
                "transaction_time": "2026-01-05T10:00:00",
                "record_id": "tx_dup_2",
            },
            {
                "sender": "ACC_B",
                "recipient": "ACC_A",
                "amount": 10000.0,
                "currency": "INR",
                "transaction_time": "2026-01-10T10:00:00",
                "record_id": "tx_dup_3",
            },
        ]
        patterns = detect_circular_transactions(records)
        self.assertEqual(len(patterns), 0)

    def test_duplicate_records_do_not_produce_duplicate_patterns(self):
        """Passing identical transaction records multiple times produces exactly 1 pattern."""
        rec1 = {
            "sender": "ACC_X",
            "recipient": "ACC_Y",
            "amount": 25000.0,
            "currency": "INR",
            "transaction_time": "2026-01-01T10:00:00",
            "record_id": "tx_dedup_1",
        }
        rec2 = {
            "sender": "ACC_Y",
            "recipient": "ACC_Z",
            "amount": 25000.0,
            "currency": "INR",
            "transaction_time": "2026-01-05T10:00:00",
            "record_id": "tx_dedup_2",
        }
        rec3 = {
            "sender": "ACC_Z",
            "recipient": "ACC_X",
            "amount": 25000.0,
            "currency": "INR",
            "transaction_time": "2026-01-10T10:00:00",
            "record_id": "tx_dedup_3",
        }
        # Pass each record twice
        patterns = detect_circular_transactions([rec1, rec2, rec3, rec1, rec2, rec3])
        self.assertEqual(len(patterns), 1)


class TestRapidTransferChainDetection(unittest.TestCase):
    """Tests for RAPID_TRANSFER_CHAIN detector (A -> B -> C within 48 hours)."""

    def test_positive_rapid_transfer(self):
        """A -> B at 10:00, B -> C at 30:00 (difference 20 hours) qualifies."""
        records = [
            {
                "sender": "ACC_A",
                "recipient": "ACC_B",
                "amount": 200000.0,
                "currency": "INR",
                "transaction_time": "2026-02-01T10:00:00",
                "record_id": "rt_001",
            },
            {
                "sender": "ACC_B",
                "recipient": "ACC_C",
                "amount": 190000.0,
                "currency": "INR",
                "transaction_time": "2026-02-02T06:00:00",  # 20 hours later
                "record_id": "rt_002",
            },
        ]
        patterns = detect_rapid_transfers(records)
        self.assertEqual(len(patterns), 1)
        p = patterns[0]
        self.assertEqual(p.type, PatternType.RAPID_TRANSFER_CHAIN)
        self.assertEqual(p.severity, Severity.HIGH)
        self.assertEqual(p.status, RelationshipStatus.INFERRED)
        self.assertEqual(p.entities, ["ACC_A", "ACC_B", "ACC_C"])
        self.assertEqual(p.evidence_ids, ["rt_001", "rt_002"])
        self.assertIn("Rapid fund transfer chain detected", p.explanation)

    def test_positive_boundary_exactly_48_hours(self):
        """A -> B at T, B -> C at T + 48 hours exactly qualifies."""
        t1 = datetime(2026, 2, 1, 0, 0, 0)
        t2 = t1 + timedelta(hours=48)
        records = [
            {
                "sender": "ACC_A",
                "recipient": "ACC_B",
                "amount": 50000.0,
                "currency": "INR",
                "transaction_time": t1.isoformat(),
                "record_id": "rt_bound_1",
            },
            {
                "sender": "ACC_B",
                "recipient": "ACC_C",
                "amount": 50000.0,
                "currency": "INR",
                "transaction_time": t2.isoformat(),
                "record_id": "rt_bound_2",
            },
        ]
        patterns = detect_rapid_transfers(records)
        self.assertEqual(len(patterns), 1)
        self.assertEqual(patterns[0].type, PatternType.RAPID_TRANSFER_CHAIN)

    def test_negative_exceeds_48_hours(self):
        """A -> B at T, B -> C at T + 48 hours + 1 minute does not qualify."""
        t1 = datetime(2026, 2, 1, 0, 0, 0)
        t2 = t1 + timedelta(hours=48, minutes=1)
        records = [
            {
                "sender": "ACC_A",
                "recipient": "ACC_B",
                "amount": 50000.0,
                "currency": "INR",
                "transaction_time": t1.isoformat(),
                "record_id": "rt_late_1",
            },
            {
                "sender": "ACC_B",
                "recipient": "ACC_C",
                "amount": 50000.0,
                "currency": "INR",
                "transaction_time": t2.isoformat(),
                "record_id": "rt_late_2",
            },
        ]
        patterns = detect_rapid_transfers(records)
        self.assertEqual(len(patterns), 0)

    def test_negative_disconnected_transfers(self):
        """A -> B and C -> D have no linking node, no chain."""
        records = [
            {
                "sender": "ACC_A",
                "recipient": "ACC_B",
                "amount": 10000.0,
                "currency": "INR",
                "transaction_time": "2026-02-01T10:00:00",
                "record_id": "rt_disc_1",
            },
            {
                "sender": "ACC_C",
                "recipient": "ACC_D",
                "amount": 10000.0,
                "currency": "INR",
                "transaction_time": "2026-02-01T12:00:00",
                "record_id": "rt_disc_2",
            },
        ]
        patterns = detect_rapid_transfers(records)
        self.assertEqual(len(patterns), 0)

    def test_negative_convergent_transfers(self):
        """A -> B and C -> B both send to B (convergent, not a forward A -> B -> C chain)."""
        records = [
            {
                "sender": "ACC_A",
                "recipient": "ACC_B",
                "amount": 10000.0,
                "currency": "INR",
                "transaction_time": "2026-02-01T10:00:00",
                "record_id": "rt_conv_1",
            },
            {
                "sender": "ACC_C",
                "recipient": "ACC_B",
                "amount": 10000.0,
                "currency": "INR",
                "transaction_time": "2026-02-01T12:00:00",
                "record_id": "rt_conv_2",
            },
        ]
        patterns = detect_rapid_transfers(records)
        self.assertEqual(len(patterns), 0)

    def test_negative_back_and_forth(self):
        """A -> B and B -> A is a 2-node loop, not a 3-node forward chain (A != C required)."""
        records = [
            {
                "sender": "ACC_A",
                "recipient": "ACC_B",
                "amount": 10000.0,
                "currency": "INR",
                "transaction_time": "2026-02-01T10:00:00",
                "record_id": "rt_bf_1",
            },
            {
                "sender": "ACC_B",
                "recipient": "ACC_A",
                "amount": 10000.0,
                "currency": "INR",
                "transaction_time": "2026-02-01T12:00:00",
                "record_id": "rt_bf_2",
            },
        ]
        patterns = detect_rapid_transfers(records)
        self.assertEqual(len(patterns), 0)

    def test_negative_same_transaction_reuse(self):
        """A single transaction record cannot be reused as both edges."""
        records = [
            {
                "sender": "ACC_A",
                "recipient": "ACC_B",
                "amount": 10000.0,
                "currency": "INR",
                "transaction_time": "2026-02-01T10:00:00",
                "record_id": "rt_single_1",
            }
        ]
        patterns = detect_rapid_transfers(records)
        self.assertEqual(len(patterns), 0)

    def test_negative_reverse_time_order(self):
        """If B -> C occurs before A -> B (t2 < t1), it is not a forward chain."""
        records = [
            {
                "sender": "ACC_A",
                "recipient": "ACC_B",
                "amount": 10000.0,
                "currency": "INR",
                "transaction_time": "2026-02-02T12:00:00",  # Later
                "record_id": "rt_rev_1",
            },
            {
                "sender": "ACC_B",
                "recipient": "ACC_C",
                "amount": 10000.0,
                "currency": "INR",
                "transaction_time": "2026-02-01T10:00:00",  # Earlier
                "record_id": "rt_rev_2",
            },
        ]
        patterns = detect_rapid_transfers(records)
        self.assertEqual(len(patterns), 0)

    def test_alias_function(self):
        """detect_rapid_transfer_chains is an exact functional alias of detect_rapid_transfers."""
        records = [
            {
                "sender": "A",
                "recipient": "B",
                "amount": 10.0,
                "currency": "INR",
                "transaction_time": "2026-01-01T10:00:00",
                "record_id": "r1",
            },
            {
                "sender": "B",
                "recipient": "C",
                "amount": 10.0,
                "currency": "INR",
                "transaction_time": "2026-01-01T12:00:00",
                "record_id": "r2",
            },
        ]
        p1 = detect_rapid_transfers(records)
        p2 = detect_rapid_transfer_chains(records)
        self.assertEqual(len(p1), 1)
        self.assertEqual(len(p2), 1)
        self.assertEqual(p1[0].id, p2[0].id)


class TestLocationTimeOverlapDetection(unittest.TestCase):
    """Tests for LOCATION_TIME_OVERLAP detector (co-presence at same location <= 2 hours)."""

    def test_positive_location_time_overlap(self):
        """Entity A at Loc X at 10:00, Entity B at Loc X at 11:30 (90 min <= 2h) qualifies."""
        records = [
            {
                "entity": "Rahul Sharma",
                "location": "Sector 18, Noida",
                "timestamp": "2026-03-01T10:00:00",
                "record_id": "ev_001",
            },
            {
                "entity": "Vikram Singh",
                "location": "Sector 18, Noida",
                "timestamp": "2026-03-01T11:30:00",
                "record_id": "ev_002",
            },
        ]
        patterns = detect_location_time_overlaps(records)
        self.assertEqual(len(patterns), 1)
        p = patterns[0]
        self.assertEqual(p.type, PatternType.LOCATION_TIME_OVERLAP)
        self.assertEqual(p.severity, Severity.MEDIUM)
        self.assertEqual(p.status, RelationshipStatus.INFERRED)
        self.assertEqual(p.entities, ["Rahul Sharma", "Vikram Singh"])
        self.assertEqual(p.evidence_ids, ["ev_001", "ev_002"])
        self.assertIn("Location-time overlap detected", p.explanation)

    def test_positive_boundary_exactly_2_hours(self):
        """Co-presence separated by exactly 2 hours qualifies."""
        t1 = datetime(2026, 3, 1, 10, 0, 0)
        t2 = t1 + timedelta(hours=2)
        records = [
            {
                "entity": "Suspect_1",
                "location": "MG Road, Bengaluru",
                "timestamp": t1.isoformat(),
                "record_id": "loc_bound_1",
            },
            {
                "entity": "Suspect_2",
                "location": "MG Road, Bengaluru",
                "timestamp": t2.isoformat(),
                "record_id": "loc_bound_2",
            },
        ]
        patterns = detect_location_time_overlaps(records)
        self.assertEqual(len(patterns), 1)
        self.assertEqual(patterns[0].type, PatternType.LOCATION_TIME_OVERLAP)

    def test_negative_exceeds_2_hours(self):
        """Co-presence separated by > 2 hours (e.g. 2 hours + 1 minute) does not qualify."""
        t1 = datetime(2026, 3, 1, 10, 0, 0)
        t2 = t1 + timedelta(hours=2, minutes=1)
        records = [
            {
                "entity": "Suspect_1",
                "location": "MG Road, Bengaluru",
                "timestamp": t1.isoformat(),
                "record_id": "loc_late_1",
            },
            {
                "entity": "Suspect_2",
                "location": "MG Road, Bengaluru",
                "timestamp": t2.isoformat(),
                "record_id": "loc_late_2",
            },
        ]
        patterns = detect_location_time_overlaps(records)
        self.assertEqual(len(patterns), 0)

    def test_negative_different_locations(self):
        """Events within 10 minutes but at completely different locations do not qualify."""
        records = [
            {
                "entity": "Person A",
                "location": "Mumbai Airport",
                "timestamp": "2026-03-01T10:00:00",
                "record_id": "loc_diff_1",
            },
            {
                "entity": "Person B",
                "location": "Delhi Airport",
                "timestamp": "2026-03-01T10:10:00",
                "record_id": "loc_diff_2",
            },
        ]
        patterns = detect_location_time_overlaps(records)
        self.assertEqual(len(patterns), 0)

    def test_negative_missing_timestamp(self):
        """Record with missing timestamp is ignored and does not create a pattern."""
        records = [
            {
                "entity": "Person A",
                "location": "Chandni Chowk",
                "record_id": "loc_notime_1",
            },
            {
                "entity": "Person B",
                "location": "Chandni Chowk",
                "timestamp": "2026-03-01T10:00:00",
                "record_id": "loc_notime_2",
            },
        ]
        patterns = detect_location_time_overlaps(records)
        self.assertEqual(len(patterns), 0)

    def test_negative_missing_location(self):
        """Record with missing location is ignored and does not create a pattern."""
        records = [
            {
                "entity": "Person A",
                "timestamp": "2026-03-01T10:00:00",
                "record_id": "loc_noloc_1",
            },
            {
                "entity": "Person B",
                "location": "Chandni Chowk",
                "timestamp": "2026-03-01T10:30:00",
                "record_id": "loc_noloc_2",
            },
        ]
        patterns = detect_location_time_overlaps(records)
        self.assertEqual(len(patterns), 0)

    def test_negative_same_entity(self):
        """Same entity appearing twice at the same location does not trigger an overlap."""
        records = [
            {
                "entity": "Rahul Sharma",
                "location": "Sector 18, Noida",
                "timestamp": "2026-03-01T10:00:00",
                "record_id": "loc_same_1",
            },
            {
                "entity": "Rahul Sharma",
                "location": "Sector 18, Noida",
                "timestamp": "2026-03-01T11:00:00",
                "record_id": "loc_same_2",
            },
        ]
        patterns = detect_location_time_overlaps(records)
        self.assertEqual(len(patterns), 0)

    def test_multi_source_cdr_and_transaction(self):
        """CDRRecord and TransactionRecord overlapping at the same location within 1 hour."""
        cdr = CDRRecord(
            caller="+919876543210",
            callee="+919123456789",
            call_time="2026-03-01T14:00:00",
            call_datetime=datetime(2026, 3, 1, 14, 0, 0),
            location="Connaught Place, New Delhi",
            record_id="cdr_cp_01",
        )
        tx = TransactionRecord(
            sender="ACC_DELHI_101",
            recipient="ACC_DELHI_202",
            amount=50000.0,
            currency="INR",
            transaction_time="2026-03-01T14:45:00",
            transaction_datetime=datetime(2026, 3, 1, 14, 45, 0),
            location="Connaught Place, New Delhi",
            record_id="tx_cp_01",
        )
        patterns = detect_location_time_overlaps([cdr, tx])
        self.assertEqual(len(patterns), 1)
        p = patterns[0]
        self.assertEqual(p.type, PatternType.LOCATION_TIME_OVERLAP)
        self.assertEqual(p.severity, Severity.MEDIUM)
        self.assertEqual(p.evidence_ids, ["cdr_cp_01", "tx_cp_01"])


class TestPatternSchemaValidation(unittest.TestCase):
    """Confirm all pattern detectors emit valid Pattern instances conforming to shared schema."""

    def test_pattern_schema_compliance(self):
        """Ensure emitted patterns pass strict Pydantic model validation."""
        tx_records = [
            {
                "sender": "A",
                "recipient": "B",
                "amount": 1000.0,
                "currency": "INR",
                "transaction_time": "2026-01-01T10:00:00",
                "record_id": "tx1",
            },
            {
                "sender": "B",
                "recipient": "C",
                "amount": 1000.0,
                "currency": "INR",
                "transaction_time": "2026-01-02T10:00:00",
                "record_id": "tx2",
            },
            {
                "sender": "C",
                "recipient": "A",
                "amount": 1000.0,
                "currency": "INR",
                "transaction_time": "2026-01-03T10:00:00",
                "record_id": "tx3",
            },
        ]
        circular = detect_circular_transactions(tx_records)
        rapid = detect_rapid_transfers(tx_records[:2])
        overlap = detect_location_time_overlaps(
            [
                {"entity": "P1", "location": "Loc1", "timestamp": "2026-01-01T10:00:00", "record_id": "e1"},
                {"entity": "P2", "location": "Loc1", "timestamp": "2026-01-01T11:00:00", "record_id": "e2"},
            ]
        )

        all_patterns = circular + rapid + overlap
        self.assertEqual(len(all_patterns), 3)

        for p in all_patterns:
            self.assertIsInstance(p, Pattern)
            # Validate through Pydantic serialization/deserialization
            dumped = p.model_dump()
            validated = Pattern.model_validate(dumped)
            self.assertEqual(validated.id, p.id)
            self.assertEqual(validated.type, p.type)
            self.assertEqual(validated.status, RelationshipStatus.INFERRED)
            self.assertNotEqual(validated.status.value, "DETECTED")
            self.assertFalse(hasattr(p, "confidence"))  # Pattern must NOT have confidence field


class TestPatternDeterminism(unittest.TestCase):
    """Ensure pattern detection is 100% deterministic regardless of input permutation."""

    def test_determinism_under_permutation(self):
        records = [
            {
                "sender": "X",
                "recipient": "Y",
                "amount": 500.0,
                "currency": "INR",
                "transaction_time": "2026-01-01T10:00:00",
                "record_id": "t1",
            },
            {
                "sender": "Y",
                "recipient": "Z",
                "amount": 500.0,
                "currency": "INR",
                "transaction_time": "2026-01-02T10:00:00",
                "record_id": "t2",
            },
            {
                "sender": "Z",
                "recipient": "X",
                "amount": 500.0,
                "currency": "INR",
                "transaction_time": "2026-01-03T10:00:00",
                "record_id": "t3",
            },
        ]
        # Order 1
        res1 = detect_circular_transactions(records)
        # Order 2 (reversed)
        res2 = detect_circular_transactions(list(reversed(records)))

        self.assertEqual(len(res1), len(res2))
        self.assertEqual(res1[0].entities, res2[0].entities)
        self.assertEqual(res1[0].evidence_ids, res2[0].evidence_ids)
        self.assertEqual(res1[0].explanation, res2[0].explanation)


if __name__ == "__main__":
    unittest.main()
