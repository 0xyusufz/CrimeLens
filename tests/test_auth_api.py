"""JWT login and case-level authorization tests."""

from __future__ import annotations

import sys
import unittest
import uuid
from datetime import timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from app.db.session import SessionLocal
from app.main import app
from app.models.case import Case
from app.models.document import Document
from app.models.enums import UserRole
from app.models.user import User
from app.services.auth import create_access_token
from tests.auth_support import create_test_user, login_headers

client = TestClient(app)
TXT_BYTES = b"authorization probe\n"


class AuthApiTests(unittest.TestCase):
    def setUp(self):
        self.session = SessionLocal()
        self.user_ids: list[uuid.UUID] = []
        self.case_ids: list[uuid.UUID] = []
        self.document_ids: list[uuid.UUID] = []
        self.admin, self.admin_password = create_test_user(
            self.session, role=UserRole.ADMIN, name="Auth Admin"
        )
        self.inv_a, self.inv_a_password = create_test_user(
            self.session, role=UserRole.INVESTIGATOR, name="Investigator A"
        )
        self.inv_b, self.inv_b_password = create_test_user(
            self.session, role=UserRole.INVESTIGATOR, name="Investigator B"
        )
        self.user_ids.extend([self.admin.id, self.inv_a.id, self.inv_b.id])
        self.admin_headers = login_headers(client, self.admin.email, self.admin_password)
        self.inv_a_headers = login_headers(client, self.inv_a.email, self.inv_a_password)
        self.inv_b_headers = login_headers(client, self.inv_b.email, self.inv_b_password)

    def tearDown(self):
        try:
            self.session.rollback()
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
                user = self.session.get(User, user_id)
                if user is not None:
                    self.session.delete(user)
            self.session.commit()
        except Exception:
            self.session.rollback()
        finally:
            self.session.close()

    def _create_case(self, headers: dict, title: str) -> dict:
        response = client.post("/api/cases", headers=headers, json={"title": title})
        self.assertEqual(response.status_code, 201, response.text)
        body = response.json()
        self.case_ids.append(uuid.UUID(body["id"]))
        return body

    def test_login_valid_and_invalid(self):
        ok = client.post(
            "/api/auth/login",
            json={"email": self.inv_a.email, "password": self.inv_a_password},
        )
        self.assertEqual(ok.status_code, 200, ok.text)
        payload = ok.json()
        self.assertIn("access_token", payload)
        self.assertEqual(payload["token_type"], "bearer")
        self.assertEqual(payload["user"]["id"], str(self.inv_a.id))
        self.assertEqual(payload["user"]["email"], self.inv_a.email)
        self.assertEqual(payload["user"]["role"], "INVESTIGATOR")
        self.assertNotIn("password_hash", payload)
        self.assertNotIn("password_hash", payload["user"])
        self.assertNotIn("password", payload)
        self.assertNotIn("password", payload["user"])

        bad_pw = client.post(
            "/api/auth/login",
            json={"email": self.inv_a.email, "password": "wrong-password"},
        )
        self.assertEqual(bad_pw.status_code, 401)
        self.assertEqual(bad_pw.json()["detail"], "Invalid email or password")

        missing = client.post(
            "/api/auth/login",
            json={"email": "nobody@example.invalid", "password": "whatever"},
        )
        self.assertEqual(missing.status_code, 401)
        self.assertEqual(missing.json()["detail"], "Invalid email or password")

    def test_jwt_valid_invalid_and_expired(self):
        listed = client.get("/api/cases", headers=self.inv_a_headers)
        self.assertEqual(listed.status_code, 200)

        invalid = client.get(
            "/api/cases",
            headers={"Authorization": "Bearer not-a-real-token"},
        )
        self.assertEqual(invalid.status_code, 401)

        expired = create_access_token(self.inv_a, expires_delta=timedelta(seconds=-30))
        expired_resp = client.get(
            "/api/cases",
            headers={"Authorization": f"Bearer {expired}"},
        )
        self.assertEqual(expired_resp.status_code, 401)

        unauth = client.get("/api/cases")
        self.assertEqual(unauth.status_code, 401)

    def test_admin_and_investigator_case_access(self):
        case_a = self._create_case(self.inv_a_headers, f"Alpha {uuid.uuid4().hex[:8]}")
        case_b = self._create_case(self.inv_b_headers, f"Beta {uuid.uuid4().hex[:8]}")

        admin_list = client.get("/api/cases", headers=self.admin_headers)
        self.assertEqual(admin_list.status_code, 200)
        admin_ids = {item["id"] for item in admin_list.json()}
        self.assertIn(case_a["id"], admin_ids)
        self.assertIn(case_b["id"], admin_ids)
        self.assertNotIn("password_hash", admin_list.text)

        admin_get = client.get(f"/api/cases/{case_a['id']}", headers=self.admin_headers)
        self.assertEqual(admin_get.status_code, 200)

        own = client.get(f"/api/cases/{case_a['id']}", headers=self.inv_a_headers)
        self.assertEqual(own.status_code, 200)

        inv_a_list = client.get("/api/cases", headers=self.inv_a_headers)
        inv_a_ids = {item["id"] for item in inv_a_list.json()}
        self.assertIn(case_a["id"], inv_a_ids)
        self.assertNotIn(case_b["id"], inv_a_ids)

        forbidden = client.get(f"/api/cases/{case_b['id']}", headers=self.inv_a_headers)
        self.assertEqual(forbidden.status_code, 403)
        self.assertEqual(forbidden.json()["detail"], "Not authorized")

        self.assertEqual(case_a["created_by"], str(self.inv_a.id))
        self.assertEqual(case_b["created_by"], str(self.inv_b.id))

    def test_document_and_process_endpoints_enforce_case_access(self):
        case_a = self._create_case(self.inv_a_headers, f"Docs {uuid.uuid4().hex[:8]}")
        upload = client.post(
            f"/api/cases/{case_a['id']}/documents",
            headers=self.inv_a_headers,
            files={"file": ("note.txt", TXT_BYTES, "text/plain")},
        )
        self.assertEqual(upload.status_code, 201, upload.text)
        document_id = upload.json()["id"]
        self.document_ids.append(uuid.UUID(document_id))
        self.assertNotIn("password_hash", upload.json())
        self.assertEqual(upload.json()["uploaded_by"], str(self.inv_a.id))

        denied_list = client.get(
            f"/api/cases/{case_a['id']}/documents",
            headers=self.inv_b_headers,
        )
        self.assertEqual(denied_list.status_code, 403)

        denied_get = client.get(
            f"/api/documents/{document_id}",
            headers=self.inv_b_headers,
        )
        self.assertEqual(denied_get.status_code, 403)

        denied_upload = client.post(
            f"/api/cases/{case_a['id']}/documents",
            headers=self.inv_b_headers,
            files={"file": ("other.txt", TXT_BYTES, "text/plain")},
        )
        self.assertEqual(denied_upload.status_code, 403)

        denied_process = client.post(
            f"/api/documents/{document_id}/process",
            headers=self.inv_b_headers,
        )
        self.assertEqual(denied_process.status_code, 403)

        allowed_get = client.get(
            f"/api/documents/{document_id}",
            headers=self.inv_a_headers,
        )
        self.assertEqual(allowed_get.status_code, 200)
        admin_get = client.get(
            f"/api/documents/{document_id}",
            headers=self.admin_headers,
        )
        self.assertEqual(admin_get.status_code, 200)


if __name__ == "__main__":
    unittest.main()
