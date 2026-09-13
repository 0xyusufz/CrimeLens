"""Case management API tests. Uses CrimeLens PostgreSQL; cleans created rows."""

from __future__ import annotations

import sys
import unittest
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from app.config import dev_case_creator_email
from app.db.session import SessionLocal
from app.main import app
from app.models.case import Case
from app.models.user import User

client = TestClient(app)


class CaseManagementApiTests(unittest.TestCase):
    def setUp(self):
        self.session = SessionLocal()
        self.created_ids: list[uuid.UUID] = []

    def tearDown(self):
        try:
            self.session.rollback()
            for case_id in self.created_ids:
                row = self.session.get(Case, case_id)
                if row is not None:
                    self.session.delete(row)
            self.session.commit()
        except Exception:
            self.session.rollback()
        finally:
            self.session.close()

    def _track(self, payload: dict) -> uuid.UUID:
        case_id = uuid.UUID(payload["id"])
        self.created_ids.append(case_id)
        return case_id

    def test_create_list_get_and_validation(self):
        suffix = uuid.uuid4().hex[:8]
        title = f"API case {suffix}"
        chosen_id = str(uuid.uuid4())

        created = client.post(
            "/api/cases",
            json={
                "title": title,
                "description": "Opened from API test.",
                "status": "OPEN",
            },
        )
        self.assertEqual(created.status_code, 201, created.text)
        body = created.json()
        case_id = self._track(body)

        self.assertNotEqual(body["id"], chosen_id)
        uuid.UUID(body["id"])
        self.assertEqual(body["title"], title)
        self.assertEqual(body["description"], "Opened from API test.")
        self.assertEqual(body["status"], "OPEN")
        self.assertIn("case_number", body)
        self.assertTrue(body["case_number"].startswith("CL-"))
        self.assertNotIn("password_hash", body)
        self.assertNotIn("email", body)
        creator_id = uuid.UUID(body["created_by"])
        self.assertIsNotNone(body["created_at"])

        stored = self.session.get(Case, case_id)
        self.assertIsNotNone(stored)
        self.assertEqual(stored.title, title)
        self.assertEqual(stored.created_by, creator_id)
        self.assertEqual(stored.status.value, "OPEN")
        creator = self.session.get(User, creator_id)
        self.assertIsNotNone(creator)
        self.assertEqual(creator.email, dev_case_creator_email())

        listed = client.get("/api/cases")
        self.assertEqual(listed.status_code, 200, listed.text)
        items = listed.json()
        self.assertIsInstance(items, list)
        match = next((item for item in items if item["id"] == str(case_id)), None)
        self.assertIsNotNone(match)
        self.assertEqual(match["title"], title)
        self.assertEqual(match["status"], "OPEN")
        self.assertNotIn("description", match)
        self.assertNotIn("password_hash", match)
        created_at_values = [item["created_at"] for item in items]
        self.assertEqual(created_at_values, sorted(created_at_values, reverse=True))

        fetched = client.get(f"/api/cases/{case_id}")
        self.assertEqual(fetched.status_code, 200, fetched.text)
        self.assertEqual(fetched.json()["id"], str(case_id))
        self.assertEqual(fetched.json()["title"], title)

        missing = client.get(f"/api/cases/{uuid.uuid4()}")
        self.assertEqual(missing.status_code, 404)
        self.assertEqual(missing.json()["detail"], "Case not found")

        invalid = client.get("/api/cases/not-a-uuid")
        self.assertEqual(invalid.status_code, 422)

        bad_status = client.post(
            "/api/cases",
            json={"title": f"Bad status {suffix}", "status": "PENDING"},
        )
        self.assertEqual(bad_status.status_code, 422)

        closed = client.post(
            "/api/cases",
            json={"title": f"Closed API case {suffix}", "status": "CLOSED"},
        )
        self.assertEqual(closed.status_code, 201, closed.text)
        closed_body = closed.json()
        self._track(closed_body)
        self.assertEqual(closed_body["status"], "CLOSED")

        supplied_id = client.post(
            "/api/cases",
            json={"id": chosen_id, "title": f"Client UUID {suffix}"},
        )
        self.assertEqual(supplied_id.status_code, 422)
        self.assertIsNone(self.session.get(Case, uuid.UUID(chosen_id)))

        extra_creator = client.post(
            "/api/cases",
            json={
                "title": f"Client creator {suffix}",
                "created_by": str(uuid.uuid4()),
            },
        )
        self.assertEqual(extra_creator.status_code, 422)


if __name__ == "__main__":
    unittest.main()
