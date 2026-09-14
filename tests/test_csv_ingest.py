"""CSV ingestion tests: parse + StructuredRecord persistence.

Tests are split into two classes:
  CsvParseTests   – pure unit tests, no DB, no Neo4j
  CsvIngestTests  – integration tests against real PostgreSQL (same pattern as
                    test_documents_processing.py)

No ml/ code is touched. Uses FixtureDocumentProcessor to satisfy the
existing adapter's signature during process endpoint calls.
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
import uuid
from io import BytesIO
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.db.session import SessionLocal
from app.main import app
from app.ml.adapter import FixtureDocumentProcessor, get_ml_processor
from app.models.document import StructuredRecord
from app.models.enums import RecordType, UserRole
from app.services.csv_ingest import (
    CsvParseError,
    EmptyCsvError,
    MissingRequiredColumnsError,
    UnrecognisedCsvSchemaError,
    parse_csv_bytes,
    upsert_structured_records,
)
from tests.auth_support import create_test_user, login_headers

client = TestClient(app)


# ── Pure parsing unit tests (no DB) ──────────────────────────────────────────

class CsvParseTests(unittest.TestCase):
    """Unit tests for parse_csv_bytes. No DB required."""

    def test_transaction_standard_headers(self):
        csv = b"source,target,amount,timestamp\nA,B,100,2026-01-01T10:00:00\n"
        schema, records = parse_csv_bytes(csv)
        self.assertEqual(schema, RecordType.TRANSACTION)
        self.assertEqual(len(records), 1)
        r = records[0]
        self.assertEqual(r["sender"], "A")
        self.assertEqual(r["recipient"], "B")
        self.assertEqual(r["amount"], 100.0)
        self.assertEqual(r["transaction_time"], "2026-01-01T10:00:00")
        self.assertEqual(r["currency"], "INR")  # default

    def test_transaction_alias_headers(self):
        """sender/recipient headers also accepted."""
        csv = b"sender,recipient,amount,transaction_time,currency,record_id\nX,Y,500.5,2026-02-01,USD,T99\n"
        schema, records = parse_csv_bytes(csv)
        self.assertEqual(schema, RecordType.TRANSACTION)
        r = records[0]
        self.assertEqual(r["sender"], "X")
        self.assertEqual(r["recipient"], "Y")
        self.assertEqual(r["amount"], 500.5)
        self.assertEqual(r["currency"], "USD")
        self.assertEqual(r["record_id"], "T99")

    def test_transaction_multiple_rows(self):
        csv = (
            b"source,target,amount,timestamp\n"
            b"A,B,100,2026-01-01T10:00:00\n"
            b"B,C,50,2026-01-02T10:00:00\n"
            b"C,A,90,2026-01-20T14:00:00\n"
        )
        schema, records = parse_csv_bytes(csv)
        self.assertEqual(schema, RecordType.TRANSACTION)
        self.assertEqual(len(records), 3)

    def test_cdr_standard_headers(self):
        csv = b"caller,callee,call_time,duration,location,record_id\n123,456,2026-01-01T10:00:00,60,Loc1,C1\n"
        schema, records = parse_csv_bytes(csv)
        self.assertEqual(schema, RecordType.CDR)
        r = records[0]
        self.assertEqual(r["caller"], "123")
        self.assertEqual(r["callee"], "456")
        self.assertEqual(r["call_time"], "2026-01-01T10:00:00")
        self.assertEqual(r["duration"], 60)
        self.assertEqual(r["location"], "Loc1")
        self.assertEqual(r["record_id"], "C1")

    def test_cdr_without_optional_columns(self):
        csv = b"caller,callee,call_time\n111,222,2026-01-01T09:00:00\n"
        schema, records = parse_csv_bytes(csv)
        self.assertEqual(schema, RecordType.CDR)
        r = records[0]
        self.assertNotIn("duration", r)
        self.assertNotIn("location", r)

    def test_empty_bytes_rejected(self):
        with self.assertRaises(EmptyCsvError):
            parse_csv_bytes(b"")

    def test_header_only_rejected(self):
        with self.assertRaises(EmptyCsvError):
            parse_csv_bytes(b"source,target,amount,timestamp\n")

    def test_unrecognised_schema_rejected(self):
        with self.assertRaises(UnrecognisedCsvSchemaError):
            parse_csv_bytes(b"foo,bar,baz\n1,2,3\n")

    def test_transaction_missing_amount_rejected(self):
        """Without 'amount' column the schema is not recognised as TRANSACTION."""
        with self.assertRaises(UnrecognisedCsvSchemaError):
            parse_csv_bytes(b"source,target,timestamp\nA,B,2026-01-01\n")

    def test_transaction_empty_recipient_rejected(self):
        with self.assertRaises(MissingRequiredColumnsError):
            parse_csv_bytes(b"source,target,amount,timestamp\nA,,100,2026-01-01\n")

    def test_transaction_empty_sender_rejected(self):
        with self.assertRaises(MissingRequiredColumnsError):
            parse_csv_bytes(b"source,target,amount,timestamp\n,B,100,2026-01-01\n")

    def test_transaction_non_numeric_amount_rejected(self):
        with self.assertRaises(MissingRequiredColumnsError):
            parse_csv_bytes(b"source,target,amount,timestamp\nA,B,not_a_number,2026-01-01\n")

    def test_malformed_encoding_rejected(self):
        with self.assertRaises(CsvParseError):
            parse_csv_bytes(b"\x00\xFF\xFE\x00\xFF")

    def test_fingerprint_field_added(self):
        """upsert_structured_records stores _fp field for idempotency."""
        # Import the private helper to verify it doesn't break on any payload
        from app.services.csv_ingest import _row_fingerprint
        fp = _row_fingerprint(uuid.uuid4(), RecordType.TRANSACTION, {"sender": "A", "amount": 100})
        self.assertIsInstance(fp, str)
        self.assertEqual(len(fp), 64)  # SHA-256 hex


# ── Integration tests against real PostgreSQL ─────────────────────────────────

class CsvIngestTests(unittest.TestCase):
    """Integration tests: upload CSV via API, process it, verify StructuredRecords."""

    @classmethod
    def setUpClass(cls):
        # No Neo4j needed for CSV ingestion tests; suppress projection errors by
        # using a minimal setup. The existing FixtureDocumentProcessor handles
        # the extraction envelope.
        pass

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        os.environ["UPLOAD_DIR"] = self._tmp.name
        self.session = SessionLocal()
        app.dependency_overrides[get_ml_processor] = lambda: FixtureDocumentProcessor()

        self.user, password = create_test_user(self.session, role=UserRole.INVESTIGATOR)
        self.headers = login_headers(client, self.user.email, password)

        resp = client.post(
            "/api/cases",
            headers=self.headers,
            json={"title": f"CSV Ingest Test {uuid.uuid4().hex[:8]}"},
        )
        self.assertEqual(resp.status_code, 201, resp.text)
        self.case_id = resp.json()["id"]

    def tearDown(self):
        app.dependency_overrides.pop(get_ml_processor, None)
        self.session.close()
        self._tmp.cleanup()

    def _upload_csv(self, csv_bytes: bytes, name: str = "data.csv") -> str:
        resp = client.post(
            f"/api/cases/{self.case_id}/documents",
            headers=self.headers,
            files={"file": (name, BytesIO(csv_bytes), "text/csv")},
        )
        self.assertEqual(resp.status_code, 201, resp.text)
        return resp.json()["id"]

    def _process(self, doc_id: str) -> int:
        """Process document and return HTTP status code."""
        resp = client.post(
            f"/api/documents/{doc_id}/process",
            headers=self.headers,
        )
        return resp.status_code, resp

    def _struct_count(self, doc_id: str) -> int:
        return self.session.scalar(
            select(func.count())
            .select_from(StructuredRecord)
            .where(StructuredRecord.document_id == uuid.UUID(doc_id))
        )

    # -- transaction CSV --

    def test_transaction_csv_creates_structured_records(self):
        csv = (
            b"source,target,amount,timestamp\n"
            b"A,B,100,2026-01-01T10:00:00\n"
            b"B,C,50,2026-01-02T10:00:00\n"
        )
        doc_id = self._upload_csv(csv)
        status, resp = self._process(doc_id)
        self.assertEqual(status, 200, resp.text)
        self.assertEqual(self._struct_count(doc_id), 2)

        rows = self.session.scalars(
            select(StructuredRecord).where(
                StructuredRecord.document_id == uuid.UUID(doc_id)
            )
        ).all()
        for row in rows:
            self.assertEqual(row.record_type, RecordType.TRANSACTION)
            # Verify normalization
            self.assertIn("sender", row.raw_json)
            self.assertIn("recipient", row.raw_json)
            self.assertIn("amount", row.raw_json)
            self.assertIn("transaction_time", row.raw_json)
            self.assertIn("currency", row.raw_json)
            # Fingerprint stored
            self.assertIn("_fp", row.raw_json)

    def test_transaction_csv_sender_recipient_values(self):
        csv = b"source,target,amount,timestamp,currency\nBANK_A,BANK_B,100000,2026-01-01T10:00:00,USD\n"
        doc_id = self._upload_csv(csv)
        status, resp = self._process(doc_id)
        self.assertEqual(status, 200, resp.text)
        rows = self.session.scalars(
            select(StructuredRecord).where(
                StructuredRecord.document_id == uuid.UUID(doc_id)
            )
        ).all()
        self.assertEqual(len(rows), 1)
        payload = rows[0].raw_json
        self.assertEqual(payload["sender"], "BANK_A")
        self.assertEqual(payload["recipient"], "BANK_B")
        self.assertEqual(payload["amount"], 100000.0)
        self.assertEqual(payload["currency"], "USD")

    # -- CDR CSV --

    def test_cdr_csv_creates_structured_records(self):
        csv = b"caller,callee,call_time\n987,654,2026-01-01T10:00:00\n333,444,2026-01-02T11:00:00\n"
        doc_id = self._upload_csv(csv, "cdr.csv")
        status, resp = self._process(doc_id)
        self.assertEqual(status, 200, resp.text)
        self.assertEqual(self._struct_count(doc_id), 2)

        rows = self.session.scalars(
            select(StructuredRecord).where(
                StructuredRecord.document_id == uuid.UUID(doc_id)
            )
        ).all()
        for row in rows:
            self.assertEqual(row.record_type, RecordType.CDR)
            self.assertIn("caller", row.raw_json)
            self.assertIn("callee", row.raw_json)
            self.assertIn("call_time", row.raw_json)

    def test_cdr_csv_values_with_optional_fields(self):
        csv = b"caller,callee,call_time,duration,location,record_id\n+91111,+91999,2026-09-10T10:00:00,180,Market A,CDR001\n"
        doc_id = self._upload_csv(csv, "cdr.csv")
        status, resp = self._process(doc_id)
        self.assertEqual(status, 200, resp.text)
        rows = self.session.scalars(
            select(StructuredRecord).where(
                StructuredRecord.document_id == uuid.UUID(doc_id)
            )
        ).all()
        self.assertEqual(len(rows), 1)
        p = rows[0].raw_json
        self.assertEqual(p["caller"], "+91111")
        self.assertEqual(p["callee"], "+91999")
        self.assertEqual(p["duration"], 180)
        self.assertEqual(p["location"], "Market A")
        self.assertEqual(p["record_id"], "CDR001")

    # -- Idempotency --

    def test_reprocessing_csv_does_not_duplicate_records(self):
        csv = b"source,target,amount,timestamp\nA,B,100,2026-01-01T10:00:00\n"
        doc_id = self._upload_csv(csv)

        status1, _ = self._process(doc_id)
        self.assertEqual(status1, 200)
        count1 = self._struct_count(doc_id)
        self.assertEqual(count1, 1)

        status2, _ = self._process(doc_id)
        self.assertEqual(status2, 200)
        count2 = self._struct_count(doc_id)
        self.assertEqual(count2, 1, "Re-processing must NOT duplicate StructuredRecords")

    # -- Error handling --

    def test_unsupported_csv_columns_returns_422(self):
        csv = b"col1,col2,col3\nfoo,bar,baz\n"
        doc_id = self._upload_csv(csv, "unknown.csv")
        status, resp = self._process(doc_id)
        self.assertEqual(status, 422)
        detail = resp.json()["detail"]
        self.assertIn("CSV columns do not match any supported schema", detail)

    # -- TXT/PDF unaffected --

    def test_txt_document_still_processes(self):
        """Ensure the CSV path does not break TXT document processing."""
        txt_bytes = b"Rahul called Amit Kumar from 9876543210 in Bhubaneswar.\n"
        resp = client.post(
            f"/api/cases/{self.case_id}/documents",
            headers=self.headers,
            files={"file": ("report.txt", BytesIO(txt_bytes), "text/plain")},
        )
        self.assertEqual(resp.status_code, 201, resp.text)
        doc_id = resp.json()["id"]
        status, resp2 = self._process(doc_id)
        self.assertEqual(status, 200, resp2.text)
        # TXT creates 0 StructuredRecords (they go through entity extraction)
        self.assertEqual(self._struct_count(doc_id), 0)


if __name__ == "__main__":
    unittest.main()
