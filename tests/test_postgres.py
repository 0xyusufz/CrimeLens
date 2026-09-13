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
from app.models import Case, CaseMember, CaseStatus, User, UserRole


class PostgresFoundationTests(unittest.TestCase):
    def test_select_1(self):
        with engine.connect() as conn:
            value = conn.execute(text("SELECT 1")).scalar()
        self.assertEqual(value, 1)

    def test_core_tables_exist(self):
        inspector = inspect(engine)
        tables = set(inspector.get_table_names())
        self.assertTrue({"users", "cases", "case_members"}.issubset(tables))

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


if __name__ == "__main__":
    unittest.main()
