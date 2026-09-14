"""Phase 7 Structured CDR and Transaction Handling unit tests.

Covers:
- TEST 1: CDR module import
- TEST 2: Valid CDR
- TEST 3: Caller preservation
- TEST 4: Callee preservation
- TEST 5: Direction (caller -> CALLED -> callee)
- TEST 6: Call time preservation
- TEST 7: Duration preservation
- TEST 8: Phone normalization
- TEST 9: Missing caller
- TEST 10: Missing callee
- TEST 11: Invalid timestamp
- TEST 12: Invalid duration
- TEST 13: Transaction module import
- TEST 14: Valid transaction
- TEST 15: Sender preservation
- TEST 16: Recipient preservation
- TEST 17: Direction (sender -> SENT_MONEY_TO -> recipient)
- TEST 18: Amount preservation
- TEST 19: Currency preservation
- TEST 20: Transaction time
- TEST 21: Missing sender
- TEST 22: Missing recipient
- TEST 23: Invalid amount
- TEST 24: Invalid currency
- TEST 25: Invalid transaction time
- TEST 26: Same sender/recipient
- TEST 27: Rapid transfer readiness (data preserved for Phase 8)
- TEST 28: Circular transaction readiness (data preserved for Phase 8)
- TEST 29: Location/time readiness (location and cell_id preserved)
- TEST 30: No pattern side effect
- TEST 31: No lead generation
- TEST 32: No resolution side effect
"""

from datetime import datetime, timezone
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ml.structured import (
    CDRRecord,
    TransactionRecord,
    cdr_to_relationship,
    parse_cdr,
    parse_cdrs,
    parse_transaction,
    parse_transactions,
    transaction_to_relationship,
)
from shared.schemas.enums import RelationshipStatus, RelationshipType
from shared.schemas.models import Pattern, Relationship


class TestStructuredCDRAndTransactions(unittest.TestCase):
    # =========================================================================
    # CDR TESTS (TESTS 1 - 12)
    # =========================================================================

    def test_1_cdr_module_import(self):
        """TEST 1: Verify CDR handler imports successfully and exports required callables."""
        self.assertTrue(callable(parse_cdr))
        self.assertTrue(callable(parse_cdrs))
        self.assertTrue(callable(cdr_to_relationship))

    def test_2_valid_cdr(self):
        """TEST 2: Verify valid CDR record is accepted and parsed."""
        raw = {
            "caller": "+91-98765-43210",
            "callee": "+91-91234-56789",
            "call_time": "2026-01-15T14:30:00",
            "duration": 120,
            "record_id": "cdr_001",
        }
        rec = parse_cdr(raw)
        self.assertIsInstance(rec, CDRRecord)
        self.assertEqual(rec.record_id, "cdr_001")
        self.assertEqual(rec.duration, 120)

    def test_3_caller_preservation(self):
        """TEST 3: Verify caller remains correct and uncorrupted."""
        raw = {
            "caller": "+91-98765-43210",
            "callee": "+91-91234-56789",
            "call_time": "2026-01-15T14:30:00",
        }
        rec = parse_cdr(raw)
        self.assertEqual(rec.caller, "+91-98765-43210")

    def test_4_callee_preservation(self):
        """TEST 4: Verify callee remains correct and uncorrupted."""
        raw = {
            "caller": "+91-98765-43210",
            "callee": "+91-91234-56789",
            "call_time": "2026-01-15T14:30:00",
        }
        rec = parse_cdr(raw)
        self.assertEqual(rec.callee, "+91-91234-56789")

    def test_5_cdr_direction(self):
        """TEST 5: Verify caller -> CALLED -> callee direction is strictly enforced."""
        rec = parse_cdr({
            "caller": "+91-98765-43210",
            "callee": "+91-91234-56789",
            "call_time": "2026-01-15T14:30:00",
            "record_id": "cdr_002",
        })
        rel = cdr_to_relationship(rec, "doc_001", "mention_001", "mention_002", "rel_001")

        self.assertIsInstance(rel, Relationship)
        self.assertEqual(rel.relationship, RelationshipType.CALLED)
        # Source must be caller mention, target must be callee mention
        self.assertEqual(rel.source_entity_id, "mention_001")
        self.assertEqual(rel.target_entity_id, "mention_002")

    def test_6_call_time_preservation(self):
        """TEST 6: Verify timestamp is preserved accurately without truncation."""
        raw = {
            "caller": "+91-98765-43210",
            "callee": "+91-91234-56789",
            "call_time": "2026-01-15T14:30:45.123456",
        }
        rec = parse_cdr(raw)
        self.assertEqual(rec.call_time, "2026-01-15T14:30:45.123456")
        self.assertEqual(rec.call_datetime.second, 45)
        self.assertEqual(rec.call_datetime.microsecond, 123456)

    def test_7_duration_preservation(self):
        """TEST 7: Verify duration remains accurate for integer, float, and missing."""
        rec1 = parse_cdr({
            "caller": "+91-98765-43210",
            "callee": "+91-91234-56789",
            "call_time": "2026-01-15T14:30:00",
            "duration": 60,
        })
        self.assertEqual(rec1.duration, 60)

        rec2 = parse_cdr({
            "caller": "+91-98765-43210",
            "callee": "+91-91234-56789",
            "call_time": "2026-01-15T14:30:00",
            "duration": 45.5,
        })
        self.assertEqual(rec2.duration, 45.5)

        rec3 = parse_cdr({
            "caller": "+91-98765-43210",
            "callee": "+91-91234-56789",
            "call_time": "2026-01-15T14:30:00",
        })
        self.assertIsNone(rec3.duration)

    def test_8_phone_normalization(self):
        """TEST 8: Verify equivalent phone formats normalize consistently via existing logic."""
        rec1 = parse_cdr({
            "caller": "+91-98765-43210",
            "callee": "9123456789",
            "call_time": "2026-01-15T14:30:00",
        })
        rec2 = parse_cdr({
            "caller": "+91 98765 43210",
            "callee": "+91-91234-56789",
            "call_time": "2026-01-15T14:30:00",
        })

        self.assertEqual(rec1.normalized_caller, "9876543210")
        self.assertEqual(rec2.normalized_caller, "9876543210")
        self.assertEqual(rec1.normalized_callee, "9123456789")
        self.assertEqual(rec2.normalized_callee, "9123456789")

    def test_9_missing_caller(self):
        """TEST 9: Missing or empty caller raises ValueError."""
        with self.assertRaises(ValueError):
            parse_cdr({
                "caller": "",
                "callee": "+91-91234-56789",
                "call_time": "2026-01-15T14:30:00",
            })
        with self.assertRaises(ValueError):
            parse_cdr({
                "callee": "+91-91234-56789",
                "call_time": "2026-01-15T14:30:00",
            })

    def test_10_missing_callee(self):
        """TEST 10: Missing or empty callee raises ValueError."""
        with self.assertRaises(ValueError):
            parse_cdr({
                "caller": "+91-98765-43210",
                "callee": "",
                "call_time": "2026-01-15T14:30:00",
            })
        with self.assertRaises(ValueError):
            parse_cdr({
                "caller": "+91-98765-43210",
                "call_time": "2026-01-15T14:30:00",
            })

    def test_11_invalid_timestamp(self):
        """TEST 11: Invalid timestamp format raises ValueError."""
        with self.assertRaises(ValueError):
            parse_cdr({
                "caller": "+91-98765-43210",
                "callee": "+91-91234-56789",
                "call_time": "invalid-time",
            })
        with self.assertRaises(ValueError):
            parse_cdr({
                "caller": "+91-98765-43210",
                "callee": "+91-91234-56789",
                "call_time": "",
            })

    def test_12_invalid_duration(self):
        """TEST 12: Negative or non-numeric duration raises ValueError."""
        with self.assertRaises(ValueError):
            parse_cdr({
                "caller": "+91-98765-43210",
                "callee": "+91-91234-56789",
                "call_time": "2026-01-15T14:30:00",
                "duration": -10,
            })
        with self.assertRaises(ValueError):
            parse_cdr({
                "caller": "+91-98765-43210",
                "callee": "+91-91234-56789",
                "call_time": "2026-01-15T14:30:00",
                "duration": "not-a-number",
            })

    # =========================================================================
    # TRANSACTION TESTS (TESTS 13 - 26)
    # =========================================================================

    def test_13_transaction_module_import(self):
        """TEST 13: Verify transaction handler imports successfully and exports required callables."""
        self.assertTrue(callable(parse_transaction))
        self.assertTrue(callable(parse_transactions))
        self.assertTrue(callable(transaction_to_relationship))

    def test_14_valid_transaction(self):
        """TEST 14: Verify valid transaction is accepted and parsed."""
        raw = {
            "sender": "123456789012",
            "recipient": "987654321098",
            "amount": 50000,
            "currency": "INR",
            "transaction_time": "2026-01-15T15:00:00",
            "record_id": "txn_001",
        }
        rec = parse_transaction(raw)
        self.assertIsInstance(rec, TransactionRecord)
        self.assertEqual(rec.record_id, "txn_001")
        self.assertEqual(rec.amount, 50000.0)
        self.assertEqual(rec.currency, "INR")

    def test_15_sender_preservation(self):
        """TEST 15: Verify sender identifier is preserved."""
        raw = {
            "sender": "123456789012",
            "recipient": "987654321098",
            "amount": 50000,
            "currency": "INR",
            "transaction_time": "2026-01-15T15:00:00",
        }
        rec = parse_transaction(raw)
        self.assertEqual(rec.sender, "123456789012")

    def test_16_recipient_preservation(self):
        """TEST 16: Verify recipient identifier is preserved."""
        raw = {
            "sender": "123456789012",
            "recipient": "987654321098",
            "amount": 50000,
            "currency": "INR",
            "transaction_time": "2026-01-15T15:00:00",
        }
        rec = parse_transaction(raw)
        self.assertEqual(rec.recipient, "987654321098")

    def test_17_transaction_direction(self):
        """TEST 17: Verify sender -> SENT_MONEY_TO -> recipient direction is enforced."""
        rec = parse_transaction({
            "sender": "123456789012",
            "recipient": "987654321098",
            "amount": 50000,
            "currency": "INR",
            "transaction_time": "2026-01-15T15:00:00",
            "record_id": "txn_002",
        })
        rel = transaction_to_relationship(rec, "doc_002", "mention_src", "mention_tgt", "rel_002")

        self.assertIsInstance(rel, Relationship)
        self.assertEqual(rel.relationship, RelationshipType.SENT_MONEY_TO)
        self.assertEqual(rel.source_entity_id, "mention_src")
        self.assertEqual(rel.target_entity_id, "mention_tgt")

    def test_18_amount_preservation(self):
        """TEST 18: Verify amount preserves decimal precision without rounding."""
        raw = {
            "sender": "123456789012",
            "recipient": "987654321098",
            "amount": 50000.75,
            "currency": "INR",
            "transaction_time": "2026-01-15T15:00:00",
        }
        rec = parse_transaction(raw)
        self.assertEqual(rec.amount, 50000.75)

    def test_19_currency_preservation(self):
        """TEST 19: Verify source currency remains unchanged without conversion."""
        raw = {
            "sender": "123456789012",
            "recipient": "987654321098",
            "amount": 1000,
            "currency": "USD",
            "transaction_time": "2026-01-15T15:00:00",
        }
        rec = parse_transaction(raw)
        self.assertEqual(rec.currency, "USD")

    def test_20_transaction_time(self):
        """TEST 20: Verify transaction timestamp is preserved accurately."""
        raw = {
            "sender": "123456789012",
            "recipient": "987654321098",
            "amount": 50000,
            "currency": "INR",
            "transaction_time": "2026-01-15T15:30:12.654321",
        }
        rec = parse_transaction(raw)
        self.assertEqual(rec.transaction_time, "2026-01-15T15:30:12.654321")
        self.assertEqual(rec.transaction_datetime.second, 12)
        self.assertEqual(rec.transaction_datetime.microsecond, 654321)

    def test_21_missing_sender(self):
        """TEST 21: Missing or empty sender raises ValueError."""
        with self.assertRaises(ValueError):
            parse_transaction({
                "sender": "",
                "recipient": "987654321098",
                "amount": 50000,
                "currency": "INR",
                "transaction_time": "2026-01-15T15:00:00",
            })

    def test_22_missing_recipient(self):
        """TEST 22: Missing or empty recipient raises ValueError."""
        with self.assertRaises(ValueError):
            parse_transaction({
                "sender": "123456789012",
                "recipient": "",
                "amount": 50000,
                "currency": "INR",
                "transaction_time": "2026-01-15T15:00:00",
            })

    def test_23_invalid_amount(self):
        """TEST 23: Non-numeric or non-positive amount raises ValueError."""
        with self.assertRaises(ValueError):
            parse_transaction({
                "sender": "123456789012",
                "recipient": "987654321098",
                "amount": -500,
                "currency": "INR",
                "transaction_time": "2026-01-15T15:00:00",
            })
        with self.assertRaises(ValueError):
            parse_transaction({
                "sender": "123456789012",
                "recipient": "987654321098",
                "amount": 0,
                "currency": "INR",
                "transaction_time": "2026-01-15T15:00:00",
            })
        with self.assertRaises(ValueError):
            parse_transaction({
                "sender": "123456789012",
                "recipient": "987654321098",
                "amount": "abc",
                "currency": "INR",
                "transaction_time": "2026-01-15T15:00:00",
            })

    def test_24_invalid_currency(self):
        """TEST 24: Malformed currency raises ValueError."""
        with self.assertRaises(ValueError):
            parse_transaction({
                "sender": "123456789012",
                "recipient": "987654321098",
                "amount": 50000,
                "currency": "INVALID",
                "transaction_time": "2026-01-15T15:00:00",
            })
        with self.assertRaises(ValueError):
            parse_transaction({
                "sender": "123456789012",
                "recipient": "987654321098",
                "amount": 50000,
                "currency": "12",
                "transaction_time": "2026-01-15T15:00:00",
            })

    def test_25_invalid_transaction_time(self):
        """TEST 25: Malformed transaction timestamp raises ValueError."""
        with self.assertRaises(ValueError):
            parse_transaction({
                "sender": "123456789012",
                "recipient": "987654321098",
                "amount": 50000,
                "currency": "INR",
                "transaction_time": "bad-date",
            })

    def test_26_same_sender_and_recipient(self):
        """TEST 26: Same sender and recipient is rejected clearly."""
        with self.assertRaises(ValueError):
            parse_transaction({
                "sender": "123456789012",
                "recipient": "123456789012",
                "amount": 50000,
                "currency": "INR",
                "transaction_time": "2026-01-15T15:00:00",
            })
        # Even with spacing/hyphen variations
        with self.assertRaises(ValueError):
            parse_transaction({
                "sender": "1234-5678-9012",
                "recipient": "123456789012",
                "amount": 50000,
                "currency": "INR",
                "transaction_time": "2026-01-15T15:00:00",
            })

    # =========================================================================
    # PATTERN-READINESS & BOUNDARY TESTS (TESTS 27 - 32)
    # =========================================================================

    def test_27_rapid_transfer_readiness(self):
        """TEST 27: Verify sender, recipient, and timestamps survive for Phase 8 48-hour rule evaluation."""
        tx1 = parse_transaction({
            "sender": "ACC_A",
            "recipient": "ACC_B",
            "amount": 100000,
            "currency": "INR",
            "transaction_time": "2026-01-15T10:00:00",
            "record_id": "tx_1",
        })
        tx2 = parse_transaction({
            "sender": "ACC_B",
            "recipient": "ACC_C",
            "amount": 95000,
            "currency": "INR",
            "transaction_time": "2026-01-16T08:30:00",
            "record_id": "tx_2",
        })

        self.assertEqual(tx1.recipient, tx2.sender)
        delta_hours = (tx2.transaction_datetime - tx1.transaction_datetime).total_seconds() / 3600
        self.assertTrue(0 < delta_hours <= 48)

    def test_28_circular_transaction_readiness(self):
        """TEST 28: Verify circular transfers preserve sender, recipient, and amount without detecting pattern."""
        chain = parse_transactions([
            {"sender": "ACC_A", "recipient": "ACC_B", "amount": 50000, "currency": "INR", "transaction_time": "2026-01-15T10:00:00"},
            {"sender": "ACC_B", "recipient": "ACC_C", "amount": 50000, "currency": "INR", "transaction_time": "2026-01-15T11:00:00"},
            {"sender": "ACC_C", "recipient": "ACC_A", "amount": 50000, "currency": "INR", "transaction_time": "2026-01-15T12:00:00"},
        ])
        self.assertEqual(len(chain), 3)
        self.assertEqual(chain[0].recipient, chain[1].sender)
        self.assertEqual(chain[1].recipient, chain[2].sender)
        self.assertEqual(chain[2].recipient, chain[0].sender)

    def test_29_location_time_readiness(self):
        """TEST 29: Location and cell_id fields are preserved for spatio-temporal analysis."""
        cdr = parse_cdr({
            "caller": "+91-98765-43210",
            "callee": "+91-91234-56789",
            "call_time": "2026-01-15T14:30:00",
            "location": "Bhubaneswar",
            "cell_id": "CELL_OD_001",
        })
        self.assertEqual(cdr.location, "Bhubaneswar")
        self.assertEqual(cdr.cell_id, "CELL_OD_001")

        tx = parse_transaction({
            "sender": "ACC_A",
            "recipient": "ACC_B",
            "amount": 50000,
            "currency": "INR",
            "transaction_time": "2026-01-15T14:30:00",
            "location": "Bhubaneswar",
        })
        self.assertEqual(tx.location, "Bhubaneswar")

    def test_30_no_pattern_side_effect(self):
        """TEST 30: Phase 7 produces ZERO Pattern objects."""
        tx = parse_transaction({
            "sender": "ACC_A",
            "recipient": "ACC_B",
            "amount": 50000,
            "currency": "INR",
            "transaction_time": "2026-01-15T14:30:00",
        })
        self.assertNotIsInstance(tx, Pattern)

    def test_31_no_lead_generation(self):
        """TEST 31: Phase 7 generates ZERO Lead objects."""
        from shared.schemas.models import Lead

        cdr = parse_cdr({
            "caller": "+91-98765-43210",
            "callee": "+91-91234-56789",
            "call_time": "2026-01-15T14:30:00",
        })
        self.assertNotIsInstance(cdr, Lead)

    def test_32_no_resolution_side_effect(self):
        """TEST 32: Phase 7 does NOT generate canonical UUIDs or merge entities."""
        tx = parse_transaction({
            "sender": "123456789012",
            "recipient": "987654321098",
            "amount": 50000,
            "currency": "INR",
            "transaction_time": "2026-01-15T14:30:00",
        })
        self.assertFalse(hasattr(tx, "canonical_entity_id"))
        self.assertFalse(hasattr(tx, "case_id"))


if __name__ == "__main__":
    unittest.main()
