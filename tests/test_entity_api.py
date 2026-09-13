"""Entity details and 1-hop connection API tests. Cleans PostgreSQL and Neo4j."""

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
from app.graph.driver import get_driver
from app.graph.projection import project_case_graph
from app.graph.schema import init_schema
from app.main import app
from app.models.audit import AuditLog
from app.models.case import Case
from app.models.document import Document
from app.models.entity import Entity, EntityCaseLink
from app.models.enums import (
    AuditAction,
    EntityType,
    RelationshipStatus,
    RelationshipType,
    UserRole,
)
from app.models.relationship import RelationshipStaging
from app.models.user import User
from tests.auth_support import create_test_user, login_headers

client = TestClient(app)
EXTRACTED_AT = datetime(2026, 9, 14, 8, 0, tzinfo=timezone.utc)


class EntityApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.driver = get_driver()
        cls.driver.verify_connectivity()
        init_schema(cls.driver)

    def setUp(self):
        self.session = SessionLocal()
        self.user_ids: list[uuid.UUID] = []
        self.case_ids: list[uuid.UUID] = []
        self.document_ids: list[uuid.UUID] = []
        self.entity_ids: list[uuid.UUID] = []
        self.rel_ids: list[uuid.UUID] = []
        self.admin, admin_pw = create_test_user(self.session, role=UserRole.ADMIN)
        self.inv_a, inv_a_pw = create_test_user(
            self.session, role=UserRole.INVESTIGATOR, name="Entity Inv A"
        )
        self.inv_b, inv_b_pw = create_test_user(
            self.session, role=UserRole.INVESTIGATOR, name="Entity Inv B"
        )
        self.user_ids.extend([self.admin.id, self.inv_a.id, self.inv_b.id])
        self.admin_headers = login_headers(client, self.admin.email, admin_pw)
        self.inv_a_headers = login_headers(client, self.inv_a.email, inv_a_pw)
        self.inv_b_headers = login_headers(client, self.inv_b.email, inv_b_pw)

        case_a = client.post(
            "/api/cases",
            headers=self.inv_a_headers,
            json={"title": f"Entity case A {uuid.uuid4().hex[:8]}"},
        )
        case_b = client.post(
            "/api/cases",
            headers=self.inv_b_headers,
            json={"title": f"Entity case B {uuid.uuid4().hex[:8]}"},
        )
        self.assertEqual(case_a.status_code, 201, case_a.text)
        self.assertEqual(case_b.status_code, 201, case_b.text)
        self.case_a_id = uuid.UUID(case_a.json()["id"])
        self.case_b_id = uuid.UUID(case_b.json()["id"])
        self.case_a_number = case_a.json()["case_number"]
        self.case_b_number = case_b.json()["case_number"]
        self.case_ids.extend([self.case_a_id, self.case_b_id])

        self.doc_a = Document(
            case_id=self.case_a_id,
            filename="entity-a.txt",
            sha256_hash="b" * 64,
            uploaded_by=self.inv_a.id,
        )
        self.doc_b = Document(
            case_id=self.case_b_id,
            filename="entity-b.txt",
            sha256_hash="c" * 64,
            uploaded_by=self.inv_b.id,
        )
        self.session.add_all([self.doc_a, self.doc_b])
        self.session.flush()
        self.document_ids.extend([self.doc_a.id, self.doc_b.id])

        self.person_a = Entity(type=EntityType.PERSON, canonical_name="Person A")
        self.person_b = Entity(type=EntityType.PERSON, canonical_name="Person B")
        self.person_c = Entity(type=EntityType.PERSON, canonical_name="Person C")
        self.person_y = Entity(type=EntityType.PERSON, canonical_name="Person Y")
        self.session.add_all([self.person_a, self.person_b, self.person_c, self.person_y])
        self.session.flush()
        self.entity_ids.extend(
            [self.person_a.id, self.person_b.id, self.person_c.id, self.person_y.id]
        )
        self.session.add_all(
            [
                EntityCaseLink(entity_id=self.person_a.id, case_id=self.case_a_id),
                EntityCaseLink(entity_id=self.person_b.id, case_id=self.case_a_id),
                EntityCaseLink(entity_id=self.person_c.id, case_id=self.case_a_id),
                EntityCaseLink(entity_id=self.person_a.id, case_id=self.case_b_id),
                EntityCaseLink(entity_id=self.person_y.id, case_id=self.case_b_id),
            ]
        )
        self.rel_ab = RelationshipStaging(
            source_occurrence_id="rel_ab",
            source_entity_id=self.person_a.id,
            target_entity_id=self.person_b.id,
            relationship_type=RelationshipType.CALLED,
            confidence=0.98,
            status=RelationshipStatus.CONFIRMED,
            source_document_id=self.doc_a.id,
            evidence_snippet="A called B.",
            extracted_at=EXTRACTED_AT,
            case_id=self.case_a_id,
        )
        self.rel_ac = RelationshipStaging(
            source_occurrence_id="rel_ac",
            source_entity_id=self.person_a.id,
            target_entity_id=self.person_c.id,
            relationship_type=RelationshipType.SENT_MONEY_TO,
            confidence=0.81,
            status=RelationshipStatus.INFERRED,
            source_document_id=self.doc_a.id,
            evidence_snippet="A sent money to C.",
            extracted_at=EXTRACTED_AT,
            case_id=self.case_a_id,
        )
        self.rel_ay = RelationshipStaging(
            source_occurrence_id="rel_ay",
            source_entity_id=self.person_a.id,
            target_entity_id=self.person_y.id,
            relationship_type=RelationshipType.CALLED,
            confidence=0.70,
            status=RelationshipStatus.PREDICTED,
            source_document_id=self.doc_b.id,
            evidence_snippet="A called Y in case B.",
            extracted_at=EXTRACTED_AT,
            case_id=self.case_b_id,
        )
        self.session.add_all([self.rel_ab, self.rel_ac, self.rel_ay])
        self.session.commit()
        self.rel_ids.extend([self.rel_ab.id, self.rel_ac.id, self.rel_ay.id])
        project_case_graph(self.case_a_id, self.session, driver=self.driver)
        project_case_graph(self.case_b_id, self.session, driver=self.driver)

    def tearDown(self):
        try:
            with self.driver.session() as neo:
                neo.run(
                    "MATCH (n) WHERE n.entity_id IN $entity_ids "
                    "OR n.case_id IN $case_ids OR n.document_id IN $document_ids "
                    "DETACH DELETE n",
                    entity_ids=[str(eid) for eid in self.entity_ids],
                    case_ids=[str(cid) for cid in self.case_ids],
                    document_ids=[str(did) for did in self.document_ids],
                )
            self.session.rollback()
            for rel_id in self.rel_ids:
                row = self.session.get(RelationshipStaging, rel_id)
                if row is not None:
                    self.session.delete(row)
            self.session.flush()
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

    def _assert_safe(self, payload) -> None:
        text = str(payload).lower()
        self.assertNotIn("element_id", text)
        self.assertNotIn("password", text)
        self.assertNotIn("access_token", text)
        self.assertNotIn("jwt_secret", text)

    def test_entity_details_auth_and_cases(self):
        unauth = client.get(f"/api/entities/{self.person_a.id}")
        self.assertEqual(unauth.status_code, 401)

        missing = client.get(f"/api/entities/{uuid.uuid4()}", headers=self.inv_a_headers)
        self.assertEqual(missing.status_code, 404)

        denied = client.get(f"/api/entities/{self.person_b.id}", headers=self.inv_b_headers)
        self.assertEqual(denied.status_code, 403)

        allowed = client.get(f"/api/entities/{self.person_a.id}", headers=self.inv_a_headers)
        self.assertEqual(allowed.status_code, 200, allowed.text)
        body = allowed.json()
        self.assertEqual(body["id"], str(self.person_a.id))
        self.assertEqual(body["type"], "PERSON")
        self.assertEqual(body["canonical_name"], "Person A")
        self.assertEqual(
            {item["case_id"] for item in body["cases"]},
            {str(self.case_a_id)},
        )
        self.assertEqual(body["cases"][0]["case_number"], self.case_a_number)
        self._assert_safe(body)

        admin = client.get(f"/api/entities/{self.person_a.id}", headers=self.admin_headers)
        self.assertEqual(admin.status_code, 200, admin.text)
        self.assertEqual(
            {item["case_id"] for item in admin.json()["cases"]},
            {str(self.case_a_id), str(self.case_b_id)},
        )

        self.session.expire_all()
        viewed = [
            row
            for row in self.session.scalars(select(AuditLog)).all()
            if row.action == AuditAction.ENTITY_VIEWED.value
            and row.resource_id == self.person_a.id
        ]
        self.assertTrue(viewed)
        for row in viewed:
            self.assertIn("case_count", row.details)
            self.assertNotIn("password", row.details)

    def test_connections_metadata_limit_and_isolation(self):
        unauth = client.get(f"/api/entities/{self.person_a.id}/connections")
        self.assertEqual(unauth.status_code, 401)

        denied_case = client.get(
            f"/api/entities/{self.person_a.id}/connections",
            headers=self.inv_a_headers,
            params={"case_id": str(self.case_b_id)},
        )
        self.assertEqual(denied_case.status_code, 403)

        denied_entity = client.get(
            f"/api/entities/{self.person_b.id}/connections",
            headers=self.inv_b_headers,
        )
        self.assertEqual(denied_entity.status_code, 403)

        inv_a = client.get(
            f"/api/entities/{self.person_a.id}/connections",
            headers=self.inv_a_headers,
        )
        self.assertEqual(inv_a.status_code, 200, inv_a.text)
        body = inv_a.json()
        self.assertEqual(body["entity_id"], str(self.person_a.id))
        neighbor_ids = {item["entity_id"] for item in body["connections"]}
        self.assertEqual(neighbor_ids, {str(self.person_b.id), str(self.person_c.id)})
        self.assertNotIn(str(self.person_y.id), neighbor_ids)
        called = next(item for item in body["connections"] if item["relationship"] == "CALLED")
        self.assertEqual(called["status"], "CONFIRMED")
        self.assertAlmostEqual(called["confidence"], 0.98)
        self.assertEqual(called["source_document_id"], str(self.doc_a.id))
        self.assertEqual(called["evidence_snippet"], "A called B.")
        self.assertEqual(called["relationship_id"], str(self.rel_ab.id))
        inferred = next(
            item for item in body["connections"] if item["relationship"] == "SENT_MONEY_TO"
        )
        self.assertEqual(inferred["status"], "INFERRED")
        self._assert_safe(body)

        limited = client.get(
            f"/api/entities/{self.person_a.id}/connections",
            headers=self.inv_a_headers,
            params={"limit": 1},
        )
        self.assertEqual(limited.status_code, 200)
        self.assertEqual(len(limited.json()["connections"]), 1)
        over = client.get(
            f"/api/entities/{self.person_a.id}/connections",
            headers=self.inv_a_headers,
            params={"limit": 101},
        )
        self.assertEqual(over.status_code, 422)

        inv_b = client.get(
            f"/api/entities/{self.person_a.id}/connections",
            headers=self.inv_b_headers,
        )
        self.assertEqual(inv_b.status_code, 200, inv_b.text)
        self.assertEqual(
            {item["entity_id"] for item in inv_b.json()["connections"]},
            {str(self.person_y.id)},
        )
        self.assertEqual(inv_b.json()["connections"][0]["status"], "PREDICTED")

        admin = client.get(
            f"/api/entities/{self.person_a.id}/connections",
            headers=self.admin_headers,
        )
        self.assertEqual(admin.status_code, 200)
        self.assertEqual(
            {item["entity_id"] for item in admin.json()["connections"]},
            {str(self.person_b.id), str(self.person_c.id), str(self.person_y.id)},
        )

        self.session.expire_all()
        queried = [
            row
            for row in self.session.scalars(select(AuditLog)).all()
            if row.action == AuditAction.ENTITY_CONNECTIONS_QUERIED.value
            and row.resource_id == self.person_a.id
        ]
        self.assertTrue(queried)
        for row in queried:
            self.assertIn("result_count", row.details)
            self.assertNotIn("connections", row.details)


if __name__ == "__main__":
    unittest.main()
