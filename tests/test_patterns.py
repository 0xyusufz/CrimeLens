"""
Tests for the MVP pattern detector, idempotency, and Insights API integration.

Covers:
  1. Same pattern processed twice → exactly ONE persisted IntelligenceOutput row.
  2. Different evidence/entities → separate IntelligenceOutput rows.
  3. Insights API returns deduplicated patterns (never repeats same source_id).
  4. Lead persistence for CIRCULAR_TRANSACTION and LOCATION_TIME_OVERLAP.
  5. Case authorization (403 for non-members).
  6. Deterministic fingerprint = same source_id on repeat runs.
"""

from __future__ import annotations

import sys
import tempfile
import os
import unittest
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient
from sqlalchemy import select, func

from app.db.session import SessionLocal
from app.main import app
from app.models.document import Document, StructuredRecord
from app.models.enums import RecordType, UserRole, IntelligenceKind
from app.models.case import Case, CaseMember
from app.models.intelligence import IntelligenceOutput
from app.models.user import User
from app.services.auth import create_access_token
from app.services.processing import process_uploaded_document
from app.services.documents import stored_file_path
from app.ml.adapter import get_ml_processor
from backend.ml.process import detect_patterns
from tests.auth_support import create_test_user

client = TestClient(app)


class PatternDetectorTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        os.environ["UPLOAD_DIR"] = self._tmp.name
        self.session = SessionLocal()

        self.user, _ = create_test_user(self.session, role=UserRole.INVESTIGATOR, name="Pattern Tester")

        case_id = uuid.uuid4()
        self.case = Case(
            id=case_id,
            title="Pattern Test Case",
            status="OPEN",
            created_by=self.user.id,
            case_number=f"TEST-{case_id.hex[:6]}",
        )
        self.session.add(self.case)
        self.session.add(CaseMember(case_id=self.case.id, user_id=self.user.id, assigned_role="OWNER"))
        self.session.commit()

        doc_id = uuid.uuid4()
        self.doc = Document(
            id=doc_id,
            case_id=self.case.id,
            filename="test.json",
            sha256_hash="dummy",
            uploaded_by=self.user.id,
        )
        self.session.add(self.doc)
        self.session.commit()
        stored_file_path(self.doc.id).write_bytes(b"{}")

    def tearDown(self):
        try:
            self.session.rollback()
            stored_file_path(self.doc.id).unlink(missing_ok=True)
            for model in [Document, Case, User]:
                row = self.session.get(model, getattr(self, {Document: "doc", Case: "case", User: "user"}[model], None) and getattr(self, {Document: "doc", Case: "case", User: "user"}[model]).id)
                if row:
                    self.session.delete(row)
            self.session.commit()
        except Exception:
            self.session.rollback()
        finally:
            self.session.close()
            self._tmp.cleanup()

    def _add_transactions(self, session, triples, base_time):
        """Add A->B->C->... transaction records."""
        for i, (src, tgt, delta_hours) in enumerate(triples):
            session.add(StructuredRecord(
                case_id=self.case.id,
                document_id=self.doc.id,
                record_type=RecordType.TRANSACTION,
                raw_json={
                    "source": src,
                    "target": tgt,
                    "amount": 100,
                    "timestamp": (base_time + timedelta(hours=delta_hours)).isoformat(),
                },
            ))
        session.commit()

    def _trigger(self):
        processor = get_ml_processor()
        process_uploaded_document(self.session, self.doc.id, processor)

    def _io_count(self):
        return self.session.scalar(
            select(func.count()).select_from(IntelligenceOutput)
            .where(IntelligenceOutput.case_id == self.case.id)
        )

    def _io_by_kind(self, kind: IntelligenceKind):
        return list(self.session.scalars(
            select(IntelligenceOutput)
            .where(IntelligenceOutput.case_id == self.case.id, IntelligenceOutput.kind == kind)
        ).all())

    # ------------------------------------------------------------------
    # Detector unit tests
    # ------------------------------------------------------------------

    def test_circular_transaction_detection(self):
        base = datetime(2024, 4, 15, 12, 0, 0, tzinfo=timezone.utc)
        self._add_transactions(self.session, [("A", "B", 0), ("B", "C", 5*24), ("C", "A", 10*24)], base)

        result = detect_patterns(b"{}", "test.json", str(self.doc.id))

        self.assertEqual(len(result["patterns"]), 1)
        p = result["patterns"][0]
        self.assertEqual(p["type"], "CIRCULAR_TRANSACTION")
        self.assertEqual(p["status"], "INFERRED")
        self.assertEqual(len(p["evidence_ids"]), 3)
        self.assertEqual(set(p["entities"]), {"A", "B", "C"})
        # Lead generated
        self.assertEqual(len(result["leads"]), 1)
        self.assertEqual(result["leads"][0]["type"], "FINANCIAL_NETWORK")

    def test_rapid_transfer_chain_detection(self):
        base = datetime(2024, 4, 15, 12, 0, 0, tzinfo=timezone.utc)
        self._add_transactions(self.session, [("A", "B", 0), ("B", "C", 20)], base)

        result = detect_patterns(b"{}", "test.json", str(self.doc.id))

        self.assertEqual(len(result["patterns"]), 1)
        p = result["patterns"][0]
        self.assertEqual(p["type"], "RAPID_TRANSFER_CHAIN")
        self.assertEqual(p["status"], "INFERRED")
        self.assertEqual(len(p["evidence_ids"]), 2)
        # No lead for RAPID_TRANSFER_CHAIN
        self.assertEqual(len(result["leads"]), 0)

    def test_location_time_overlap_detection(self):
        base = datetime(2024, 4, 15, 12, 0, 0, tzinfo=timezone.utc)
        self.session.add(StructuredRecord(
            case_id=self.case.id, document_id=self.doc.id,
            record_type=RecordType.CDR,
            raw_json={"entity": "A", "location": "X", "timestamp": base.isoformat()},
        ))
        self.session.add(StructuredRecord(
            case_id=self.case.id, document_id=self.doc.id,
            record_type=RecordType.CDR,
            raw_json={"entity": "B", "location": "X", "timestamp": (base + timedelta(hours=1)).isoformat()},
        ))
        self.session.commit()

        result = detect_patterns(b"{}", "test.json", str(self.doc.id))

        self.assertEqual(len(result["patterns"]), 1)
        p = result["patterns"][0]
        self.assertEqual(p["type"], "LOCATION_TIME_OVERLAP")
        self.assertEqual(len(p["evidence_ids"]), 2)
        self.assertEqual(set(p["entities"]), {"A", "B"})
        # Lead generated
        self.assertEqual(len(result["leads"]), 1)
        self.assertEqual(result["leads"][0]["type"], "LOCATION_TIME_OVERLAP")

    def test_deterministic_fingerprint_same_data(self):
        """Same data → same id on two calls (fingerprint is deterministic)."""
        base = datetime(2024, 4, 15, 12, 0, 0, tzinfo=timezone.utc)
        self._add_transactions(self.session, [("A", "B", 0), ("B", "C", 20)], base)

        r1 = detect_patterns(b"{}", "test.json", str(self.doc.id))
        r2 = detect_patterns(b"{}", "test.json", str(self.doc.id))

        self.assertEqual(len(r1["patterns"]), 1)
        self.assertEqual(r1["patterns"][0]["id"], r2["patterns"][0]["id"],
                         "Pattern id must be deterministic across calls")

    def test_duplicate_data_produces_one_pattern(self):
        """If the same entity-set appears in multiple evidence combos,
        detector emits exactly ONE pattern (logical entity-set dedup)."""
        base = datetime(2024, 4, 15, 12, 0, 0, tzinfo=timezone.utc)
        # A->B, A->B again (duplicate route, same entities)
        self._add_transactions(self.session, [
            ("A", "B", 0), ("B", "C", 5*24), ("C", "A", 10*24),
            ("A", "B", 1), ("B", "C", 5*24+1), ("C", "A", 10*24+1),
        ], base)

        result = detect_patterns(b"{}", "test.json", str(self.doc.id))

        circulars = [p for p in result["patterns"] if p["type"] == "CIRCULAR_TRANSACTION"]
        self.assertEqual(len(circulars), 1, "Entity-set dedup must collapse to one circular pattern")

    def test_different_entities_produce_separate_patterns(self):
        """Two distinct rapid-transfer chains must produce two rows."""
        base = datetime(2024, 4, 15, 12, 0, 0, tzinfo=timezone.utc)
        # Chain 1: A->B->C
        # Chain 2: X->Y->Z
        self._add_transactions(self.session, [
            ("A", "B", 0), ("B", "C", 10),
            ("X", "Y", 0), ("Y", "Z", 10),
        ], base)

        result = detect_patterns(b"{}", "test.json", str(self.doc.id))
        rapids = [p for p in result["patterns"] if p["type"] == "RAPID_TRANSFER_CHAIN"]
        self.assertEqual(len(rapids), 2, "Distinct entity chains must remain as separate patterns")

    # ------------------------------------------------------------------
    # Persistence idempotency tests
    # ------------------------------------------------------------------

    def test_same_pattern_processed_twice_yields_one_db_row(self):
        """Processing the same document twice must NOT create a second IntelligenceOutput."""
        base = datetime(2024, 4, 15, 12, 0, 0, tzinfo=timezone.utc)
        self._add_transactions(self.session, [("A", "B", 0), ("B", "C", 10)], base)

        self._trigger()
        count_after_first = self._io_count()
        self.assertEqual(count_after_first, 1)

        self._trigger()
        count_after_second = self._io_count()
        self.assertEqual(count_after_second, 1, "Second processing must not create duplicate rows")

    def test_different_patterns_persist_as_separate_rows(self):
        """Distinct patterns must persist as distinct IntelligenceOutput rows."""
        base = datetime(2024, 4, 15, 12, 0, 0, tzinfo=timezone.utc)
        # Rapid chain: A->B->C
        self._add_transactions(self.session, [("A", "B", 0), ("B", "C", 10)], base)
        # CDR overlap: D and E
        self.session.add(StructuredRecord(
            case_id=self.case.id, document_id=self.doc.id,
            record_type=RecordType.CDR,
            raw_json={"entity": "D", "location": "Y", "timestamp": base.isoformat()},
        ))
        self.session.add(StructuredRecord(
            case_id=self.case.id, document_id=self.doc.id,
            record_type=RecordType.CDR,
            raw_json={"entity": "E", "location": "Y", "timestamp": (base + timedelta(minutes=30)).isoformat()},
        ))
        self.session.commit()

        self._trigger()
        patterns = self._io_by_kind(IntelligenceKind.PATTERN)
        # Should be: 1 RAPID_TRANSFER_CHAIN + 1 LOCATION_TIME_OVERLAP
        self.assertEqual(len(patterns), 2)
        types = {r.payload["type"] for r in patterns}
        self.assertIn("RAPID_TRANSFER_CHAIN", types)
        self.assertIn("LOCATION_TIME_OVERLAP", types)

    def test_lead_persistence(self):
        """Leads for CIRCULAR and LOCATION patterns must be persisted."""
        base = datetime(2024, 4, 15, 12, 0, 0, tzinfo=timezone.utc)
        self._add_transactions(self.session, [("A", "B", 0), ("B", "C", 5*24), ("C", "A", 10*24)], base)
        self.session.add(StructuredRecord(
            case_id=self.case.id, document_id=self.doc.id,
            record_type=RecordType.CDR,
            raw_json={"entity": "D", "location": "Z", "timestamp": base.isoformat()},
        ))
        self.session.add(StructuredRecord(
            case_id=self.case.id, document_id=self.doc.id,
            record_type=RecordType.CDR,
            raw_json={"entity": "E", "location": "Z", "timestamp": (base + timedelta(minutes=30)).isoformat()},
        ))
        self.session.commit()

        self._trigger()
        leads = self._io_by_kind(IntelligenceKind.LEAD)
        self.assertGreaterEqual(len(leads), 1, "At least one lead must be persisted")
        for r in leads:
            self.assertIn("title", r.payload)
            self.assertIn("explanation", r.payload)
            self.assertIn("evidence_ids", r.payload)
            # Status must be PREDICTED according to user instructions.
            self.assertEqual(r.payload.get("status"), "PREDICTED",
                             "Lead status must be PREDICTED")

    # ------------------------------------------------------------------
    # API integration tests
    # ------------------------------------------------------------------

    def test_insights_api_returns_generated_patterns(self):
        base = datetime(2024, 4, 15, 12, 0, 0, tzinfo=timezone.utc)
        self._add_transactions(self.session, [("A", "B", 0), ("B", "C", 10)], base)
        self._trigger()

        token = create_access_token(self.user)
        resp = client.get(
            f"/api/cases/{self.case.id}/insights",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(len(data["patterns"]), 1)
        self.assertEqual(data["patterns"][0]["type"], "RAPID_TRANSFER_CHAIN")
        self.assertEqual(data["patterns"][0]["status"], "INFERRED")

    def test_insights_api_no_duplicates(self):
        """Processing twice must NOT cause duplicates in the API response."""
        base = datetime(2024, 4, 15, 12, 0, 0, tzinfo=timezone.utc)
        self._add_transactions(self.session, [("A", "B", 0), ("B", "C", 10)], base)
        self._trigger()
        self._trigger()  # second time

        token = create_access_token(self.user)
        resp = client.get(
            f"/api/cases/{self.case.id}/insights",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        ids = [p["id"] for p in data["patterns"]]
        self.assertEqual(len(ids), len(set(ids)), "API response must not contain duplicate pattern ids")
        self.assertEqual(len(data["patterns"]), 1)

    def test_insights_api_case_authorization(self):
        """Non-member must receive 403."""
        user2, _ = create_test_user(self.session, role=UserRole.INVESTIGATOR, name="Outsider")
        token = create_access_token(user2)

        resp = client.get(
            f"/api/cases/{self.case.id}/insights",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(resp.status_code, 403)


if __name__ == "__main__":
    unittest.main()
