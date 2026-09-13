"""PostgreSQL connectivity and users/cases/case_members smoke tests.

Uses the CrimeLens Docker database (host port from .env, expected 5433).
Does not print credentials. Cleans up test rows.
"""

from __future__ import annotations

import sys
import unittest
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT))

from sqlalchemy import inspect, text

from app.db.session import SessionLocal, engine
from app.models import (
    Case,
    CaseMember,
    CaseStatus,
    Document,
    RecordType,
    StructuredRecord,
    User,
    UserRole,
)


class PostgresFoundationTests(unittest.TestCase):
    def test_select_1(self):
        with engine.connect() as conn:
            value = conn.execute(text("SELECT 1")).scalar()
        self.assertEqual(value, 1)

    def test_core_tables_exist(self):
        inspector = inspect(engine)
        tables = set(inspector.get_table_names())
        self.assertTrue(
            {"users", "cases", "case_members", "documents", "structured_records"}.issubset(
                tables
            )
        )

    def test_insert_read_delete(self):
        session = SessionLocal()
        suffix = uuid.uuid4().hex[:8]
        user = User(
            name="Connectivity Tester",
            email=f"pg-test-{suffix}@example.invalid",
            password_hash="not-a-real-hash",
            role=UserRole.INVESTIGATOR,
        )
        case = None
        member = None
        try:
            session.add(user)
            session.flush()

            case = Case(
                case_number=f"TEST-{suffix}",
                title="Connectivity test case",
                description="Temporary row; deleted by test.",
                status=CaseStatus.OPEN,
                created_by=user.id,
            )
            session.add(case)
            session.flush()

            member = CaseMember(
                case_id=case.id,
                user_id=user.id,
                assigned_role="INVESTIGATOR",
            )
            session.add(member)
            session.flush()

            loaded_user = session.get(User, user.id)
            loaded_case = session.get(Case, case.id)
            loaded_member = session.get(CaseMember, member.id)
            self.assertIsNotNone(loaded_user)
            self.assertEqual(loaded_user.email, user.email)
            self.assertIsNotNone(loaded_case)
            self.assertEqual(loaded_case.created_by, user.id)
            self.assertIsNotNone(loaded_member)

            session.delete(member)
            session.delete(case)
            session.delete(user)
            session.commit()

            self.assertIsNone(session.get(User, user.id))
            self.assertIsNone(session.get(Case, case.id))
            self.assertIsNone(session.get(CaseMember, member.id))
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def test_documents_and_structured_records_insert_read_delete(self):
        session = SessionLocal()
        suffix = uuid.uuid4().hex[:8]
        user = User(
            name="Document Tester",
            email=f"doc-test-{suffix}@example.invalid",
            password_hash="not-a-real-hash",
            role=UserRole.INVESTIGATOR,
        )
        try:
            session.add(user)
            session.flush()

            case = Case(
                case_number=f"DOC-{suffix}",
                title="Document layer test case",
                status=CaseStatus.OPEN,
                created_by=user.id,
            )
            session.add(case)
            session.flush()

            document = Document(
                case_id=case.id,
                filename="cdr_and_txn.csv",
                sha256_hash="0" * 64,
                uploaded_by=user.id,
            )
            session.add(document)
            session.flush()

            cdr = StructuredRecord(
                case_id=case.id,
                document_id=document.id,
                record_type=RecordType.CDR,
                raw_json={
                    "caller": "9876543210",
                    "receiver": "9123456789",
                    "duration": 120,
                    "location": "Bhubaneswar",
                },
            )
            txn = StructuredRecord(
                case_id=case.id,
                document_id=document.id,
                record_type=RecordType.TRANSACTION,
                raw_json={
                    "sender_account": "ACC001",
                    "receiver_account": "ACC002",
                    "amount": 45000,
                    "location": "Bhubaneswar",
                },
            )
            session.add_all([cdr, txn])
            session.flush()

            loaded_doc = session.get(Document, document.id)
            loaded_cdr = session.get(StructuredRecord, cdr.id)
            loaded_txn = session.get(StructuredRecord, txn.id)
            self.assertIsNotNone(loaded_doc)
            self.assertEqual(loaded_doc.case_id, case.id)
            self.assertEqual(loaded_doc.uploaded_by, user.id)
            self.assertEqual(loaded_cdr.record_type, RecordType.CDR)
            self.assertEqual(loaded_cdr.raw_json["caller"], "9876543210")
            self.assertEqual(loaded_txn.record_type, RecordType.TRANSACTION)
            self.assertEqual(loaded_txn.raw_json["amount"], 45000)

            session.delete(txn)
            session.delete(cdr)
            session.delete(document)
            session.delete(case)
            session.delete(user)
            session.commit()

            self.assertIsNone(session.get(Document, document.id))
            self.assertIsNone(session.get(StructuredRecord, cdr.id))
            self.assertIsNone(session.get(StructuredRecord, txn.id))
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()


if __name__ == "__main__":
    unittest.main()
