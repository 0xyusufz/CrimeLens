"""Append-only audit trail tests. Cleans created rows."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.session import SessionLocal
from app.graph.driver import get_driver
from app.main import app
from app.ml.adapter import FixtureDocumentProcessor, get_ml_processor
from app.models.audit import AuditLog
from app.models.case import Case
from app.models.document import Document
from app.models.enums import AuditAction, UserRole
from app.models.user import User
from tests.auth_support import create_test_user, login_headers

client = TestClient(app)
TXT_BYTES = b"audit evidence note\n"


class InvalidContractProcessor:
    def process_document(self, document_bytes, filename, document_id):
        return {"document_id": document_id, "entities": "not-a-list"}


class AuditApiTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        os.environ["UPLOAD_DIR"] = self._tmp.name
        self.session = SessionLocal()
        self.user_ids: list[uuid.UUID] = []
        self.case_ids: list[uuid.UUID] = []
        self.document_ids: list[uuid.UUID] = []
        self.admin, self.admin_password = create_test_user(self.session, role=UserRole.ADMIN)
        self.inv_a, self.inv_a_password = create_test_user(
            self.session, role=UserRole.INVESTIGATOR, name="Audit Inv A"
        )
        self.inv_b, self.inv_b_password = create_test_user(
            self.session, role=UserRole.INVESTIGATOR, name="Audit Inv B"
        )
        self.user_ids.extend([self.admin.id, self.inv_a.id, self.inv_b.id])
        self.admin_headers = login_headers(client, self.admin.email, self.admin_password)
        self.inv_a_headers = login_headers(client, self.inv_a.email, self.inv_a_password)
        self.inv_b_headers = login_headers(client, self.inv_b.email, self.inv_b_password)

    def tearDown(self):
        app.dependency_overrides.pop(get_ml_processor, None)
        try:
            self.session.rollback()
            driver = get_driver()
            with driver.session() as neo:
                neo.run(
                    "MATCH (n) WHERE n.case_id IN $case_ids OR n.document_id IN $document_ids "
                    "DETACH DELETE n",
                    case_ids=[str(cid) for cid in self.case_ids],
                    document_ids=[str(did) for did in self.document_ids],
                )
            for document_id in self.document_ids:
                row = self.session.get(Document, document_id)
                if row is not None:
                    self.session.delete(row)
            for case_id in self.case_ids:
                case = self.session.get(Case, case_id)
                if case is not None:
                    self.session.delete(case)
            self.session.flush()
            for user_id in self.user_ids:
                for row in self.session.scalars(
                    select(AuditLog).where(AuditLog.user_id == user_id)
                ).all():
                    self.session.delete(row)
                user = self.session.get(User, user_id)
                if user is not None:
                    self.session.delete(user)
            self.session.commit()
        except Exception:
            self.session.rollback()
        finally:
            self.session.close()
            self._tmp.cleanup()

    def _actions(self, **filters) -> list[str]:
        stmt = select(AuditLog).order_by(AuditLog.created_at.asc())
        rows = list(self.session.scalars(stmt))
        matched = []
        for row in rows:
            ok = True
            for key, value in filters.items():
                if getattr(row, key) != value:
                    ok = False
                    break
            if ok:
                matched.append(row.action)
        return matched

    def _assert_safe(self, payload) -> None:
        text = str(payload).lower()
        self.assertNotIn("password_hash", text)
        self.assertNotIn("access_token", text)
        self.assertNotIn("jwt_secret", text)
        self.assertNotIn("bearer ", text)

    def test_login_and_case_document_audit_trail(self):
        fail = client.post(
            "/api/auth/login",
            json={"email": self.inv_a.email, "password": "wrong-password"},
        )
        self.assertEqual(fail.status_code, 401)
        self.session.expire_all()
        failures = [
            row
            for row in self.session.scalars(select(AuditLog)).all()
            if row.action == AuditAction.LOGIN_FAILURE.value and row.user_id == self.inv_a.id
        ]
        self.assertTrue(failures)
        self.assertEqual(failures[-1].details.get("email"), self.inv_a.email.lower())
        self.assertNotIn("password", failures[-1].details)

        successes = [
            row
            for row in self.session.scalars(select(AuditLog)).all()
            if row.action == AuditAction.LOGIN_SUCCESS.value and row.user_id == self.inv_a.id
        ]
        self.assertTrue(successes)

        created = client.post(
            "/api/cases",
            headers=self.inv_a_headers,
            json={"title": f"Audit case {uuid.uuid4().hex[:8]}"},
        )
        self.assertEqual(created.status_code, 201, created.text)
        case_id = uuid.UUID(created.json()["id"])
        self.case_ids.append(case_id)
        self.session.expire_all()
        self.assertIn(
            AuditAction.CASE_CREATED.value,
            self._actions(case_id=case_id, user_id=self.inv_a.id),
        )

        fetched = client.get(f"/api/cases/{case_id}", headers=self.inv_a_headers)
        self.assertEqual(fetched.status_code, 200)
        denied = client.get(f"/api/cases/{case_id}", headers=self.inv_b_headers)
        self.assertEqual(denied.status_code, 403)
        self.session.expire_all()
        actions = self._actions(case_id=case_id)
        self.assertIn(AuditAction.CASE_ACCESS_GRANTED.value, actions)
        self.assertIn(AuditAction.CASE_ACCESS_DENIED.value, actions)

        uploaded = client.post(
            f"/api/cases/{case_id}/documents",
            headers=self.inv_a_headers,
            files={"file": ("note.txt", TXT_BYTES, "text/plain")},
        )
        self.assertEqual(uploaded.status_code, 201, uploaded.text)
        document_id = uuid.UUID(uploaded.json()["id"])
        self.document_ids.append(document_id)
        viewed = client.get(f"/api/documents/{document_id}", headers=self.inv_a_headers)
        self.assertEqual(viewed.status_code, 200)
        self.session.expire_all()
        self.assertIn(
            AuditAction.DOCUMENT_UPLOADED.value,
            self._actions(resource_id=document_id),
        )
        self.assertIn(
            AuditAction.DOCUMENT_VIEWED.value,
            self._actions(resource_id=document_id),
        )

        app.dependency_overrides[get_ml_processor] = lambda: FixtureDocumentProcessor()
        processed = client.post(
            f"/api/documents/{document_id}/process",
            headers=self.inv_a_headers,
        )
        self.assertEqual(processed.status_code, 200, processed.text)
        self.session.expire_all()
        self.assertIn(
            AuditAction.DOCUMENT_PROCESSED.value,
            self._actions(resource_id=document_id),
        )

        app.dependency_overrides[get_ml_processor] = lambda: InvalidContractProcessor()
        failed_process = client.post(
            f"/api/documents/{document_id}/process",
            headers=self.inv_a_headers,
        )
        self.assertEqual(failed_process.status_code, 422)
        self.session.expire_all()
        process_rows = [
            row
            for row in self.session.scalars(select(AuditLog)).all()
            if row.resource_id == document_id
            and row.action
            in {
                AuditAction.DOCUMENT_PROCESSED.value,
                AuditAction.DOCUMENT_PROCESS_FAILED.value,
            }
        ]
        self.assertEqual(
            sum(1 for row in process_rows if row.action == AuditAction.DOCUMENT_PROCESSED.value),
            1,
        )
        self.assertTrue(
            any(row.action == AuditAction.DOCUMENT_PROCESS_FAILED.value for row in process_rows)
        )

        unauth = client.get(f"/api/cases/{case_id}/audit")
        self.assertEqual(unauth.status_code, 401)

        inv_b_audit = client.get(f"/api/cases/{case_id}/audit", headers=self.inv_b_headers)
        self.assertEqual(inv_b_audit.status_code, 403)

        inv_a_audit = client.get(f"/api/cases/{case_id}/audit", headers=self.inv_a_headers)
        self.assertEqual(inv_a_audit.status_code, 200, inv_a_audit.text)
        self._assert_safe(inv_a_audit.json())
        listed_actions = [item["action"] for item in inv_a_audit.json()]
        self.assertIn(AuditAction.CASE_CREATED.value, listed_actions)
        self.assertIn(AuditAction.DOCUMENT_UPLOADED.value, listed_actions)
        timestamps = [item["created_at"] for item in inv_a_audit.json()]
        self.assertEqual(timestamps, sorted(timestamps, reverse=True))

        admin_audit = client.get(f"/api/cases/{case_id}/audit", headers=self.admin_headers)
        self.assertEqual(admin_audit.status_code, 200)
        self._assert_safe(admin_audit.json())
        admin_actions = {item["action"] for item in admin_audit.json()}
        self.assertIn(AuditAction.CASE_CREATED.value, admin_actions)

        deleted = client.delete(f"/api/cases/{case_id}/audit", headers=self.admin_headers)
        self.assertIn(deleted.status_code, {404, 405, 422})
        patched = client.patch(
            f"/api/cases/{case_id}/audit",
            headers=self.admin_headers,
            json={"action": "TAMPERED"},
        )
        self.assertIn(patched.status_code, {404, 405, 422})


if __name__ == "__main__":
    unittest.main()
