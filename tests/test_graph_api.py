"""Case graph / subgraph API tests. Cleans PostgreSQL and Neo4j fixtures."""

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
EXTRACTED_AT = datetime(2026, 9, 14, 9, 0, tzinfo=timezone.utc)


class CaseGraphApiTests(unittest.TestCase):
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
            self.session, role=UserRole.INVESTIGATOR, name="Graph Inv A"
        )
        self.inv_b, inv_b_pw = create_test_user(
            self.session, role=UserRole.INVESTIGATOR, name="Graph Inv B"
        )
        self.user_ids.extend([self.admin.id, self.inv_a.id, self.inv_b.id])
        self.admin_headers = login_headers(client, self.admin.email, admin_pw)
        self.inv_a_headers = login_headers(client, self.inv_a.email, inv_a_pw)
        self.inv_b_headers = login_headers(client, self.inv_b.email, inv_b_pw)

        created = client.post(
            "/api/cases",
            headers=self.inv_a_headers,
            json={"title": f"Graph case {uuid.uuid4().hex[:8]}"},
        )
        other = client.post(
            "/api/cases",
            headers=self.inv_b_headers,
            json={"title": f"Other graph case {uuid.uuid4().hex[:8]}"},
        )
        self.assertEqual(created.status_code, 201, created.text)
        self.assertEqual(other.status_code, 201, other.text)
        self.case_id = uuid.UUID(created.json()["id"])
        self.other_case_id = uuid.UUID(other.json()["id"])
        self.case_ids.extend([self.case_id, self.other_case_id])

        self.document = Document(
            case_id=self.case_id,
            filename="graph.txt",
            sha256_hash="d" * 64,
            uploaded_by=self.inv_a.id,
        )
        self.other_doc = Document(
            case_id=self.other_case_id,
            filename="other.txt",
            sha256_hash="e" * 64,
            uploaded_by=self.inv_b.id,
        )
        self.session.add_all([self.document, self.other_doc])
        self.session.flush()
        self.document_ids.extend([self.document.id, self.other_doc.id])

        self.alpha = Entity(type=EntityType.PERSON, canonical_name="Alpha")
        self.beta = Entity(type=EntityType.PERSON, canonical_name="Beta")
        self.gamma = Entity(type=EntityType.PERSON, canonical_name="Gamma")
        self.isolated = Entity(type=EntityType.PERSON, canonical_name="Isolated")
        self.foreign = Entity(type=EntityType.PERSON, canonical_name="Foreign")
        self.session.add_all(
            [self.alpha, self.beta, self.gamma, self.isolated, self.foreign]
        )
        self.session.flush()
        self.entity_ids.extend(
            [self.alpha.id, self.beta.id, self.gamma.id, self.isolated.id, self.foreign.id]
        )
        self.session.add_all(
            [
                EntityCaseLink(entity_id=self.alpha.id, case_id=self.case_id),
                EntityCaseLink(entity_id=self.beta.id, case_id=self.case_id),
                EntityCaseLink(entity_id=self.gamma.id, case_id=self.case_id),
                EntityCaseLink(entity_id=self.isolated.id, case_id=self.case_id),
                EntityCaseLink(entity_id=self.foreign.id, case_id=self.other_case_id),
            ]
        )
        self.rel_ab = RelationshipStaging(
            source_occurrence_id="g_ab",
            source_entity_id=self.alpha.id,
            target_entity_id=self.beta.id,
            relationship_type=RelationshipType.CALLED,
            confidence=0.98,
            status=RelationshipStatus.CONFIRMED,
            source_document_id=self.document.id,
            evidence_snippet="Alpha called Beta.",
            extracted_at=EXTRACTED_AT,
            case_id=self.case_id,
        )
        self.rel_bc = RelationshipStaging(
            source_occurrence_id="g_bc",
            source_entity_id=self.beta.id,
            target_entity_id=self.gamma.id,
            relationship_type=RelationshipType.ASSOCIATED_WITH,
            confidence=0.55,
            status=RelationshipStatus.PREDICTED,
            source_document_id=self.document.id,
            evidence_snippet="Beta associated with Gamma.",
            extracted_at=EXTRACTED_AT,
            case_id=self.case_id,
        )
        self.rel_foreign = RelationshipStaging(
            source_occurrence_id="g_foreign",
            source_entity_id=self.alpha.id,
            target_entity_id=self.foreign.id,
            relationship_type=RelationshipType.CALLED,
            confidence=0.40,
            status=RelationshipStatus.INFERRED,
            source_document_id=self.other_doc.id,
            evidence_snippet="Should not leak.",
            extracted_at=EXTRACTED_AT,
            case_id=self.other_case_id,
        )
        self.session.add_all([self.rel_ab, self.rel_bc, self.rel_foreign])
        self.session.commit()
        self.rel_ids.extend([self.rel_ab.id, self.rel_bc.id, self.rel_foreign.id])
        project_case_graph(self.case_id, self.session, driver=self.driver)
        project_case_graph(self.other_case_id, self.session, driver=self.driver)

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
        self.assertNotIn("elementid", text)
        self.assertNotIn("password", text)
        self.assertNotIn("access_token", text)
        if isinstance(payload, dict):
            for node in payload.get("nodes", []):
                self.assertEqual(set(node.keys()), {"entity_id", "type", "name"})
            for rel in payload.get("relationships", []):
                self.assertNotIn("id", rel)
                self.assertNotIn("neo4j_id", rel)

    def test_case_graph_auth_nodes_relationships_and_bounds(self):
        unauth = client.get(f"/api/cases/{self.case_id}/graph")
        self.assertEqual(unauth.status_code, 401)
        denied = client.get(
            f"/api/cases/{self.case_id}/graph",
            headers=self.inv_b_headers,
        )
        self.assertEqual(denied.status_code, 403)

        allowed = client.get(
            f"/api/cases/{self.case_id}/graph",
            headers=self.inv_a_headers,
        )
        self.assertEqual(allowed.status_code, 200, allowed.text)
        body = allowed.json()
        self.assertEqual(body["case_id"], str(self.case_id))
        node_ids = {node["entity_id"] for node in body["nodes"]}
        self.assertEqual(
            node_ids,
            {
                str(self.alpha.id),
                str(self.beta.id),
                str(self.gamma.id),
                str(self.isolated.id),
            },
        )
        self.assertNotIn(str(self.foreign.id), node_ids)
        rel_ids = {row["relationship_id"] for row in body["relationships"]}
        self.assertEqual(rel_ids, {str(self.rel_ab.id), str(self.rel_bc.id)})
        called = next(row for row in body["relationships"] if row["relationship"] == "CALLED")
        self.assertEqual(called["status"], "CONFIRMED")
        self.assertAlmostEqual(called["confidence"], 0.98)
        self.assertEqual(called["source_document_id"], str(self.document.id))
        self.assertEqual(called["evidence_snippet"], "Alpha called Beta.")
        self.assertEqual(called["source_entity_id"], str(self.alpha.id))
        self.assertEqual(called["target_entity_id"], str(self.beta.id))
        predicted = next(
            row for row in body["relationships"] if row["relationship"] == "ASSOCIATED_WITH"
        )
        self.assertEqual(predicted["status"], "PREDICTED")
        self.assertFalse(body["truncated"])
        self._assert_safe(body)

        bounded = client.get(
            f"/api/cases/{self.case_id}/graph",
            headers=self.inv_a_headers,
            params={"limit": 1},
        )
        self.assertEqual(bounded.status_code, 200)
        self.assertEqual(len(bounded.json()["relationships"]), 1)
        self.assertTrue(bounded.json()["truncated"])
        over = client.get(
            f"/api/cases/{self.case_id}/graph",
            headers=self.inv_a_headers,
            params={"limit": 501},
        )
        self.assertEqual(over.status_code, 422)

        admin = client.get(
            f"/api/cases/{self.case_id}/graph",
            headers=self.admin_headers,
        )
        self.assertEqual(admin.status_code, 200)
        self.assertEqual(len(admin.json()["relationships"]), 2)

        self.session.expire_all()
        events = [
            row
            for row in self.session.scalars(select(AuditLog)).all()
            if row.action == AuditAction.CASE_GRAPH_VIEWED.value
            and row.case_id == self.case_id
        ]
        self.assertTrue(events)
        for row in events:
            self.assertIn("relationship_count", row.details)
            self.assertNotIn("nodes", row.details)
            self.assertNotIn("password", row.details)


if __name__ == "__main__":
    unittest.main()
