"""Case insights API: validated Pattern/Lead JSON stored as intelligence outputs."""

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
from sqlalchemy import func, select

from app.db.session import SessionLocal
from app.graph.driver import get_driver
from app.graph.schema import init_schema
from app.main import app
from app.ml.adapter import FixtureDocumentProcessor, get_ml_processor
from app.models.audit import AuditLog
from app.models.case import Case
from app.models.document import Document
from app.models.enums import AuditAction, IntelligenceKind, UserRole
from app.models.intelligence import IntelligenceOutput
from app.models.relationship import RelationshipStaging
from app.models.user import User
from app.services.documents import stored_file_path
from app.services.insights import persist_leads, persist_patterns
from shared.schemas import Lead, Pattern
from tests.auth_support import create_test_user, login_headers

client = TestClient(app)
TXT_BYTES = b"Rahul called Amit Kumar from 9876543210 in Bhubaneswar.\n"


class PatternFixtureProcessor(FixtureDocumentProcessor):
    """Deterministic Person B-shaped pattern/lead JSON. No detection algorithms."""

    def detect_patterns(self, document_bytes, filename, document_id):
        return {
            "patterns": [
                {
                    "id": "pattern_001",
                    "type": "CIRCULAR_TRANSACTION",
                    "severity": "HIGH",
                    "status": "INFERRED",
                    "entities": ["mention_001", "mention_002", "mention_003"],
                    "explanation": "Potential circular transaction pattern detected.",
                    "evidence_ids": ["rel_001"],
                },
                {
                    "id": "pattern_002",
                    "type": "RAPID_TRANSFER_CHAIN",
                    "severity": "MEDIUM",
                    "status": "INFERRED",
                    "entities": ["mention_001", "mention_002"],
                    "explanation": "Potential rapid transfer chain detected.",
                    "evidence_ids": ["rel_001"],
                },
                {
                    "id": "pattern_003",
                    "type": "LOCATION_TIME_OVERLAP",
                    "severity": "LOW",
                    "status": "PREDICTED",
                    "entities": ["mention_001", "mention_004"],
                    "explanation": "Potential location/time overlap detected.",
                    "evidence_ids": ["rel_003"],
                },
            ],
            "leads": [
                {
                    "id": "lead_001",
                    "type": "FINANCIAL_NETWORK",
                    "priority": "HIGH",
                    "title": "Potential circular transaction network",
                    "explanation": "Shared counterparties in a short window.",
                    "entity_ids": ["mention_001", "mention_002"],
                    "evidence_ids": ["rel_001"],
                }
            ],
        }


class InsightsApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.driver = get_driver()
        cls.driver.verify_connectivity()
        init_schema(cls.driver)

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        os.environ["UPLOAD_DIR"] = self._tmp.name
        self.session = SessionLocal()
        self.user_ids: list[uuid.UUID] = []
        self.case_ids: list[uuid.UUID] = []
        self.document_ids: list[uuid.UUID] = []
        self.admin, admin_pw = create_test_user(self.session, role=UserRole.ADMIN)
        self.inv_a, inv_a_pw = create_test_user(
            self.session, role=UserRole.INVESTIGATOR, name="Insights Inv A"
        )
        self.inv_b, inv_b_pw = create_test_user(
            self.session, role=UserRole.INVESTIGATOR, name="Insights Inv B"
        )
        self.user_ids.extend([self.admin.id, self.inv_a.id, self.inv_b.id])
        self.admin_headers = login_headers(client, self.admin.email, admin_pw)
        self.inv_a_headers = login_headers(client, self.inv_a.email, inv_a_pw)
        self.inv_b_headers = login_headers(client, self.inv_b.email, inv_b_pw)
        created = client.post(
            "/api/cases",
            headers=self.inv_a_headers,
            json={"title": f"Insights case {uuid.uuid4().hex[:8]}"},
        )
        other = client.post(
            "/api/cases",
            headers=self.inv_b_headers,
            json={"title": f"Other insights {uuid.uuid4().hex[:8]}"},
        )
        self.assertEqual(created.status_code, 201, created.text)
        self.assertEqual(other.status_code, 201, other.text)
        self.case_id = uuid.UUID(created.json()["id"])
        self.other_case_id = uuid.UUID(other.json()["id"])
        self.case_ids.extend([self.case_id, self.other_case_id])
        uploaded = client.post(
            f"/api/cases/{self.case_id}/documents",
            headers=self.inv_a_headers,
            files={"file": ("fir.txt", TXT_BYTES, "text/plain")},
        )
        self.assertEqual(uploaded.status_code, 201, uploaded.text)
        self.document_id = uuid.UUID(uploaded.json()["id"])
        self.document_ids.append(self.document_id)

    def tearDown(self):
        app.dependency_overrides.pop(get_ml_processor, None)
        try:
            self.session.rollback()
            for document_id in self.document_ids:
                stored_file_path(document_id).unlink(missing_ok=True)
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

    def _process_with_patterns(self):
        app.dependency_overrides[get_ml_processor] = lambda: PatternFixtureProcessor()
        processed = client.post(
            f"/api/documents/{self.document_id}/process",
            headers=self.inv_a_headers,
        )
        self.assertEqual(processed.status_code, 200, processed.text)
        return processed.json()

    def _assert_safe(self, payload) -> None:
        text = str(payload).lower()
        self.assertNotIn("password", text)
        self.assertNotIn("password_hash", text)
        self.assertNotIn("access_token", text)
        self.assertNotIn("jwt_secret", text)
        self.assertNotIn("upload_dir", text)
        self.assertNotIn("/data/", text)
        self.assertNotIn(str(TXT_BYTES), str(payload))

    def test_empty_insights_and_authorization(self):
        unauth = client.get(f"/api/cases/{self.case_id}/insights")
        self.assertEqual(unauth.status_code, 401)
        denied = client.get(
            f"/api/cases/{self.case_id}/insights",
            headers=self.inv_b_headers,
        )
        self.assertEqual(denied.status_code, 403)
        empty = client.get(
            f"/api/cases/{self.case_id}/insights",
            headers=self.inv_a_headers,
        )
        self.assertEqual(empty.status_code, 200, empty.text)
        body = empty.json()
        self.assertEqual(body["case_id"], str(self.case_id))
        self.assertEqual(body["patterns"], [])
        self.assertEqual(body["leads"], [])
        self._assert_safe(body)

    def test_process_persists_insights_without_duplicates(self):
        first = self._process_with_patterns()
        self.assertGreaterEqual(first["entities_processed"], 1)
        self.assertGreaterEqual(first["relationships_persisted"], 1)

        insights = client.get(
            f"/api/cases/{self.case_id}/insights",
            headers=self.inv_a_headers,
        )
        self.assertEqual(insights.status_code, 200, insights.text)
        body = insights.json()
        self.assertEqual(len(body["patterns"]), 3)
        self.assertEqual(len(body["leads"]), 1)
        circular = next(item for item in body["patterns"] if item["id"] == "pattern_001")
        self.assertEqual(circular["type"], "CIRCULAR_TRANSACTION")
        self.assertEqual(circular["status"], "INFERRED")
        self.assertNotEqual(circular["status"], "CONFIRMED")
        self.assertEqual(circular["severity"], "HIGH")
        self.assertEqual(
            circular["explanation"],
            "Potential circular transaction pattern detected.",
        )
        self.assertTrue(circular["entities"])
        self.assertTrue(circular["evidence_ids"])
        for entity_id in circular["entities"]:
            uuid.UUID(entity_id)
        for evidence_id in circular["evidence_ids"]:
            uuid.UUID(evidence_id)
        predicted = next(item for item in body["patterns"] if item["id"] == "pattern_003")
        self.assertEqual(predicted["status"], "PREDICTED")
        self.assertNotEqual(predicted["status"], "CONFIRMED")
        lead = body["leads"][0]
        self.assertEqual(lead["id"], "lead_001")
        self.assertEqual(lead["priority"], "HIGH")
        self.assertNotIn("severity", lead)
        self.assertEqual(lead["status"], "REVIEW_REQUIRED")
        self._assert_safe(body)

        isolated = client.get(
            f"/api/cases/{self.other_case_id}/insights",
            headers=self.inv_b_headers,
        )
        self.assertEqual(isolated.status_code, 200)
        self.assertEqual(isolated.json()["patterns"], [])
        self.assertEqual(isolated.json()["leads"], [])

        admin = client.get(
            f"/api/cases/{self.case_id}/insights",
            headers=self.admin_headers,
        )
        self.assertEqual(admin.status_code, 200)
        self.assertEqual(len(admin.json()["patterns"]), 3)

        self._process_with_patterns()
        count = self.session.scalar(
            select(func.count()).select_from(IntelligenceOutput).where(
                IntelligenceOutput.case_id == self.case_id
            )
        )
        self.assertEqual(count, 4)
        pattern_ids = list(
            self.session.scalars(
                select(IntelligenceOutput.source_id).where(
                    IntelligenceOutput.case_id == self.case_id,
                    IntelligenceOutput.kind == IntelligenceKind.PATTERN,
                )
            )
        )
        self.assertEqual(sorted(pattern_ids), ["pattern_001", "pattern_002", "pattern_003"])

        self.session.expire_all()
        events = [
            row
            for row in self.session.scalars(select(AuditLog)).all()
            if row.action == AuditAction.CASE_INSIGHTS_VIEWED.value
            and row.case_id == self.case_id
        ]
        self.assertTrue(events)
        for row in events:
            self.assertIn("pattern_count", row.details)
            self.assertIn("lead_count", row.details)
            self.assertNotIn("patterns", row.details)
            self.assertNotIn("password", row.details)

        rel_count = self.session.scalar(
            select(func.count()).select_from(RelationshipStaging).where(
                RelationshipStaging.case_id == self.case_id
            )
        )
        self.assertGreaterEqual(rel_count, 1)

    def test_manual_persist_and_unavailable_processor_stays_empty(self):
        app.dependency_overrides[get_ml_processor] = lambda: FixtureDocumentProcessor()
        processed = client.post(
            f"/api/documents/{self.document_id}/process",
            headers=self.inv_a_headers,
        )
        self.assertEqual(processed.status_code, 200, processed.text)
        empty = client.get(
            f"/api/cases/{self.case_id}/insights",
            headers=self.inv_a_headers,
        )
        self.assertEqual(empty.json()["patterns"], [])
        self.assertEqual(empty.json()["leads"], [])

        pattern = Pattern.model_validate(
            {
                "id": "pattern_001",
                "type": "CIRCULAR_TRANSACTION",
                "severity": "HIGH",
                "status": "INFERRED",
                "entities": ["mention_001"],
                "explanation": "Potential circular transaction pattern detected.",
                "evidence_ids": ["rel_001"],
            }
        )
        lead = Lead.model_validate(
            {
                "id": "lead_001",
                "type": "FINANCIAL_NETWORK",
                "priority": "MEDIUM",
                "title": "Review financial network",
                "explanation": "Shared counterparties.",
                "entity_ids": ["mention_001"],
                "evidence_ids": ["rel_001"],
            }
        )
        persist_patterns(
            self.session,
            case_id=self.case_id,
            patterns=[pattern],
            source_document_id=self.document_id,
        )
        persist_leads(
            self.session,
            case_id=self.case_id,
            leads=[lead],
            source_document_id=self.document_id,
        )
        persist_patterns(
            self.session,
            case_id=self.case_id,
            patterns=[pattern],
            source_document_id=self.document_id,
        )
        self.session.commit()
        count = self.session.scalar(
            select(func.count()).select_from(IntelligenceOutput).where(
                IntelligenceOutput.case_id == self.case_id
            )
        )
        self.assertEqual(count, 2)
        filled = client.get(
            f"/api/cases/{self.case_id}/insights",
            headers=self.inv_a_headers,
        )
        self.assertEqual(len(filled.json()["patterns"]), 1)
        self.assertEqual(filled.json()["patterns"][0]["status"], "INFERRED")
        self.assertEqual(filled.json()["leads"][0]["priority"], "MEDIUM")


if __name__ == "__main__":
    unittest.main()
