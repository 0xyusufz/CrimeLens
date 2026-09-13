"""Relationship evidence API tests. Cleans created PostgreSQL rows."""

from __future__ import annotations

import sys
import unittest
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.session import SessionLocal
from app.main import app
from app.models.audit import AuditLog
from app.models.case import Case
from app.models.document import Document, StructuredRecord
from app.models.entity import Entity, EntityCaseLink
from app.models.enums import (
    AuditAction,
    EntityType,
    RecordType,
    RelationshipStatus,
    RelationshipType,
    UserRole,
)
from app.models.relationship import RelationshipStaging
from app.models.user import User
from tests.auth_support import create_test_user, login_headers

client = TestClient(app)
EXTRACTED_AT = datetime(2026, 9, 14, 10, 15, 30, tzinfo=timezone.utc)
SNIPPET = "Rahul called Amit on 12 August."


class RelationshipEvidenceApiTests(unittest.TestCase):
    def setUp(self):
        self.session = SessionLocal()
        self.user_ids: list[uuid.UUID] = []
        self.case_ids: list[uuid.UUID] = []
        self.document_ids: list[uuid.UUID] = []
        self.entity_ids: list[uuid.UUID] = []
        self.rel_ids: list[uuid.UUID] = []
        self.record_ids: list[uuid.UUID] = []
        self.admin, admin_pw = create_test_user(self.session, role=UserRole.ADMIN)
        self.inv_a, inv_a_pw = create_test_user(
            self.session, role=UserRole.INVESTIGATOR, name="Rel Inv A"
        )
        self.inv_b, inv_b_pw = create_test_user(
            self.session, role=UserRole.INVESTIGATOR, name="Rel Inv B"
        )
        self.user_ids.extend([self.admin.id, self.inv_a.id, self.inv_b.id])
        self.admin_headers = login_headers(client, self.admin.email, admin_pw)
        self.inv_a_headers = login_headers(client, self.inv_a.email, inv_a_pw)
        self.inv_b_headers = login_headers(client, self.inv_b.email, inv_b_pw)

        created = client.post(
            "/api/cases",
            headers=self.inv_a_headers,
            json={"title": f"Rel evidence {uuid.uuid4().hex[:8]}"},
        )
        other = client.post(
            "/api/cases",
            headers=self.inv_b_headers,
            json={"title": f"Other rel case {uuid.uuid4().hex[:8]}"},
        )
        self.assertEqual(created.status_code, 201, created.text)
        self.assertEqual(other.status_code, 201, other.text)
        self.case_id = uuid.UUID(created.json()["id"])
        self.other_case_id = uuid.UUID(other.json()["id"])
        self.case_ids.extend([self.case_id, self.other_case_id])

        self.document = Document(
            case_id=self.case_id,
            filename="call-note.txt",
            sha256_hash="f" * 64,
            uploaded_by=self.inv_a.id,
        )
        self.other_document = Document(
            case_id=self.other_case_id,
            filename="secret.txt",
            sha256_hash="e" * 64,
            uploaded_by=self.inv_b.id,
        )
        self.session.add_all([self.document, self.other_document])
        self.session.flush()
        self.document_ids.extend([self.document.id, self.other_document.id])

        self.record = StructuredRecord(
            case_id=self.case_id,
            document_id=self.document.id,
            record_type=RecordType.CDR,
            raw_json={"caller": "9876543210", "receiver": "9123456789"},
        )
        self.session.add(self.record)
        self.session.flush()
        self.record_ids.append(self.record.id)

        self.source = Entity(type=EntityType.PERSON, canonical_name="Rahul Sharma")
        self.target = Entity(type=EntityType.PERSON, canonical_name="Amit Kumar")
        self.other_entity = Entity(type=EntityType.PERSON, canonical_name="Hidden")
        self.session.add_all([self.source, self.target, self.other_entity])
        self.session.flush()
        self.entity_ids.extend([self.source.id, self.target.id, self.other_entity.id])
        self.session.add_all(
            [
                EntityCaseLink(entity_id=self.source.id, case_id=self.case_id),
                EntityCaseLink(entity_id=self.target.id, case_id=self.case_id),
                EntityCaseLink(entity_id=self.other_entity.id, case_id=self.other_case_id),
            ]
        )

        self.doc_rel = RelationshipStaging(
            source_occurrence_id="rel_doc",
            source_entity_id=self.source.id,
            target_entity_id=self.target.id,
            relationship_type=RelationshipType.CALLED,
            confidence=0.98,
            status=RelationshipStatus.CONFIRMED,
            source_document_id=self.document.id,
            source_record_id=None,
            evidence_snippet=SNIPPET,
            extracted_at=EXTRACTED_AT,
            case_id=self.case_id,
        )
        self.record_rel = RelationshipStaging(
            source_occurrence_id="rel_cdr",
            source_entity_id=self.source.id,
            target_entity_id=self.target.id,
            relationship_type=RelationshipType.CALLED,
            confidence=0.81,
            status=RelationshipStatus.INFERRED,
            source_document_id=self.document.id,
            source_record_id=self.record.id,
            evidence_snippet="CDR row linking Rahul and Amit.",
            extracted_at=EXTRACTED_AT,
            case_id=self.case_id,
        )
        self.hidden_rel = RelationshipStaging(
            source_occurrence_id="rel_hidden",
            source_entity_id=self.other_entity.id,
            target_entity_id=self.other_entity.id,
            relationship_type=RelationshipType.ASSOCIATED_WITH,
            confidence=0.40,
            status=RelationshipStatus.PREDICTED,
            source_document_id=self.other_document.id,
            evidence_snippet="Must not leak.",
            extracted_at=EXTRACTED_AT,
            case_id=self.other_case_id,
        )
        self.session.add_all([self.doc_rel, self.record_rel, self.hidden_rel])
        self.session.commit()
        self.rel_ids.extend([self.doc_rel.id, self.record_rel.id, self.hidden_rel.id])

    def tearDown(self):
        try:
            self.session.rollback()
            for rel_id in self.rel_ids:
                row = self.session.get(RelationshipStaging, rel_id)
                if row is not None:
                    self.session.delete(row)
            self.session.flush()
            for record_id in self.record_ids:
                row = self.session.get(StructuredRecord, record_id)
                if row is not None:
                    self.session.delete(row)
            for entity_id in self.entity_ids:
                row = self.session.get(Entity, entity_id)
                if row is not None:
                    self.session.delete(row)
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

    def _get(self, relationship_id, headers=None):
        return client.get(
            f"/api/relationships/{relationship_id}/evidence",
            headers=headers,
        )

    def _assert_safe(self, payload) -> None:
        text = str(payload).lower()
        self.assertNotIn("password", text)
        self.assertNotIn("password_hash", text)
        self.assertNotIn("access_token", text)
        self.assertNotIn("jwt_secret", text)
        self.assertNotIn("upload_dir", text)
        self.assertNotIn("/data/", text)
        self.assertNotIn("call-note.txt", text)
        dumped = str(payload)
        self.assertNotIn("b'\\x", dumped)
        self.assertNotIn("raw_json", text)

    def test_evidence_metadata_auth_and_audit(self):
        unauth = self._get(self.doc_rel.id)
        self.assertEqual(unauth.status_code, 401)

        missing = self._get(uuid.uuid4(), headers=self.inv_a_headers)
        self.assertEqual(missing.status_code, 404)
        self.assertEqual(missing.json()["detail"], "Relationship not found")

        denied = self._get(self.doc_rel.id, headers=self.inv_b_headers)
        self.assertEqual(denied.status_code, 403)
        self.assertNotIn(SNIPPET, denied.text)

        hidden = self._get(self.hidden_rel.id, headers=self.inv_a_headers)
        self.assertEqual(hidden.status_code, 403)
        self.assertNotIn("Must not leak", hidden.text)

        allowed = self._get(self.doc_rel.id, headers=self.inv_a_headers)
        self.assertEqual(allowed.status_code, 200, allowed.text)
        body = allowed.json()
        self.assertEqual(body["relationship_id"], str(self.doc_rel.id))
        self.assertEqual(body["case_id"], str(self.case_id))
        self.assertEqual(body["relationship"], "CALLED")
        self.assertEqual(body["source_entity_id"], str(self.source.id))
        self.assertEqual(body["target_entity_id"], str(self.target.id))
        self.assertAlmostEqual(body["confidence"], 0.98)
        self.assertEqual(body["status"], "CONFIRMED")
        self.assertEqual(body["source_document_id"], str(self.document.id))
        self.assertIsNone(body["source_record_id"])
        self.assertEqual(body["evidence_snippet"], SNIPPET)
        self.assertTrue(body["extracted_at"].startswith("2026-09-14T10:15:30"))
        self.assertNotIn("source_occurrence_id", body)
        self._assert_safe(body)

        with_record = self._get(self.record_rel.id, headers=self.inv_a_headers)
        self.assertEqual(with_record.status_code, 200, with_record.text)
        record_body = with_record.json()
        self.assertEqual(record_body["source_record_id"], str(self.record.id))
        self.assertEqual(record_body["status"], "INFERRED")
        self.assertAlmostEqual(record_body["confidence"], 0.81)
        self.assertEqual(record_body["source_document_id"], str(self.document.id))
        self._assert_safe(record_body)

        admin = self._get(self.doc_rel.id, headers=self.admin_headers)
        self.assertEqual(admin.status_code, 200)
        self.assertEqual(admin.json()["evidence_snippet"], SNIPPET)

        self.session.expire_all()
        events = [
            row
            for row in self.session.scalars(select(AuditLog)).all()
            if row.action == AuditAction.RELATIONSHIP_EVIDENCE_VIEWED.value
            and row.resource_id == self.doc_rel.id
        ]
        self.assertTrue(events)
        for row in events:
            self.assertEqual(row.result, "SUCCESS")
            self.assertEqual(row.case_id, self.case_id)
            self.assertNotIn("evidence_snippet", row.details)
            self.assertNotIn("password", row.details)
            self.assertNotIn("access_token", row.details)


if __name__ == "__main__":
    unittest.main()
