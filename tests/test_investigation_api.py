"""Multi-hop investigation path API tests. Cleans PostgreSQL and Neo4j fixtures."""

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
EXTRACTED_AT = datetime(2026, 9, 13, 12, 0, tzinfo=timezone.utc)


class InvestigationPathApiTests(unittest.TestCase):
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
            self.session, role=UserRole.INVESTIGATOR, name="Path Inv A"
        )
        self.inv_b, inv_b_pw = create_test_user(
            self.session, role=UserRole.INVESTIGATOR, name="Path Inv B"
        )
        self.user_ids.extend([self.admin.id, self.inv_a.id, self.inv_b.id])
        self.admin_headers = login_headers(client, self.admin.email, admin_pw)
        self.inv_a_headers = login_headers(client, self.inv_a.email, inv_a_pw)
        self.inv_b_headers = login_headers(client, self.inv_b.email, inv_b_pw)

        created = client.post(
            "/api/cases",
            headers=self.inv_a_headers,
            json={"title": f"Investigation case {uuid.uuid4().hex[:8]}"},
        )
        self.assertEqual(created.status_code, 201, created.text)
        self.case_id = uuid.UUID(created.json()["id"])
        self.case_ids.append(self.case_id)

        self.document = Document(
            case_id=self.case_id,
            filename="path.txt",
            sha256_hash="a" * 64,
            uploaded_by=self.inv_a.id,
        )
        self.session.add(self.document)
        self.session.flush()
        self.document_ids.append(self.document.id)

        names = ["A", "B", "C", "D", "E", "F", "Z"]
        self.entities: dict[str, Entity] = {}
        for name in names:
            entity = Entity(type=EntityType.PERSON, canonical_name=f"Person {name}")
            self.session.add(entity)
            self.session.flush()
            self.session.add(EntityCaseLink(entity_id=entity.id, case_id=self.case_id))
            self.entities[name] = entity
            self.entity_ids.append(entity.id)

        chain = [
            (
                "A",
                "B",
                RelationshipType.CALLED,
                0.98,
                RelationshipStatus.CONFIRMED,
                "A called B.",
            ),
            (
                "B",
                "C",
                RelationshipType.SENT_MONEY_TO,
                0.81,
                RelationshipStatus.INFERRED,
                "B sent money to C.",
            ),
            (
                "C",
                "D",
                RelationshipType.ASSOCIATED_WITH,
                0.55,
                RelationshipStatus.PREDICTED,
                "C associated with D.",
            ),
            (
                "D",
                "E",
                RelationshipType.CALLED,
                0.90,
                RelationshipStatus.CONFIRMED,
                "D called E.",
            ),
            (
                "E",
                "F",
                RelationshipType.CALLED,
                0.88,
                RelationshipStatus.CONFIRMED,
                "E called F.",
            ),
        ]
        self.rels: dict[tuple[str, str], RelationshipStaging] = {}
        for index, (src, tgt, rel_type, confidence, rel_status, snippet) in enumerate(chain, start=1):
            row = RelationshipStaging(
                source_occurrence_id=f"rel_{index:03d}",
                source_entity_id=self.entities[src].id,
                target_entity_id=self.entities[tgt].id,
                relationship_type=rel_type,
                confidence=confidence,
                status=rel_status,
                source_document_id=self.document.id,
                evidence_snippet=snippet,
                extracted_at=EXTRACTED_AT,
                case_id=self.case_id,
            )
            self.session.add(row)
            self.session.flush()
            self.rels[(src, tgt)] = row
            self.rel_ids.append(row.id)
        self.session.commit()
        project_case_graph(self.case_id, self.session, driver=self.driver)

    def tearDown(self):
        try:
            with self.driver.session() as neo:
                neo.run(
                    "MATCH (n) WHERE n.entity_id IN $entity_ids "
                    "OR n.case_id = $case_id OR n.document_id IN $document_ids "
                    "DETACH DELETE n",
                    entity_ids=[str(eid) for eid in self.entity_ids],
                    case_id=str(self.case_id) if self.case_ids else "",
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

    def _path(self, headers, source: str, target: str, max_hops: int | None = None, **extra):
        params = {
            "case_id": str(self.case_id),
            "source_entity_id": extra.get("source_entity_id", str(self.entities[source].id)),
            "target_entity_id": extra.get("target_entity_id", str(self.entities[target].id)),
        }
        if max_hops is not None:
            params["max_hops"] = max_hops
        if "raw_source" in extra:
            params["source_entity_id"] = extra["raw_source"]
        if "raw_target" in extra:
            params["target_entity_id"] = extra["raw_target"]
        return client.get("/api/investigation/path", headers=headers, params=params)

    def _assert_no_internal_ids(self, payload) -> None:
        text = str(payload).lower()
        self.assertNotIn("element_id", text)
        self.assertNotIn("elementid", text)
        self.assertNotIn("password", text)
        self.assertNotIn("access_token", text)
        self.assertNotIn("jwt_secret", text)
        if isinstance(payload, dict):
            self.assertNotIn("identity", payload)
            for node in payload.get("nodes", []):
                self.assertEqual(set(node.keys()), {"entity_id", "type", "name"})
            for rel in payload.get("relationships", []):
                self.assertNotIn("id", rel)
                self.assertNotIn("neo4j_id", rel)

    def test_one_two_three_hop_and_max_five(self):
        one = self._path(self.inv_a_headers, "A", "B", max_hops=3)
        self.assertEqual(one.status_code, 200, one.text)
        body = one.json()
        self.assertTrue(body["found"])
        self.assertEqual(body["hop_count"], 1)
        self.assertEqual(
            [node["entity_id"] for node in body["nodes"]],
            [str(self.entities["A"].id), str(self.entities["B"].id)],
        )
        rel = body["relationships"][0]
        self.assertEqual(rel["relationship"], "CALLED")
        self.assertEqual(rel["status"], "CONFIRMED")
        self.assertAlmostEqual(rel["confidence"], 0.98)
        self.assertEqual(rel["source_document_id"], str(self.document.id))
        self.assertEqual(rel["evidence_snippet"], "A called B.")
        self.assertEqual(rel["relationship_id"], str(self.rels[("A", "B")].id))
        self.assertEqual(rel["case_id"], str(self.case_id))
        self._assert_no_internal_ids(body)

        two = self._path(self.inv_a_headers, "A", "C")
        self.assertEqual(two.status_code, 200, two.text)
        self.assertEqual(two.json()["hop_count"], 2)
        self.assertEqual(len(two.json()["relationships"]), 2)

        three = self._path(self.inv_a_headers, "A", "D", max_hops=3)
        self.assertEqual(three.status_code, 200, three.text)
        self.assertEqual(three.json()["hop_count"], 3)
        self.assertEqual(
            [node["name"] for node in three.json()["nodes"]],
            ["Person A", "Person B", "Person C", "Person D"],
        )
        statuses = [row["status"] for row in three.json()["relationships"]]
        self.assertEqual(statuses, ["CONFIRMED", "INFERRED", "PREDICTED"])

        limited = self._path(self.inv_a_headers, "A", "F", max_hops=3)
        self.assertEqual(limited.status_code, 200)
        self.assertFalse(limited.json()["found"])
        self.assertIsNone(limited.json()["hop_count"])
        self.assertEqual(limited.json()["nodes"], [])
        self.assertEqual(limited.json()["relationships"], [])

        five = self._path(self.inv_a_headers, "A", "F", max_hops=5)
        self.assertEqual(five.status_code, 200, five.text)
        self.assertTrue(five.json()["found"])
        self.assertEqual(five.json()["hop_count"], 5)

    def test_max_hops_over_five_rejected(self):
        response = self._path(self.inv_a_headers, "A", "B", max_hops=6)
        self.assertEqual(response.status_code, 422)

    def test_no_path_found_false(self):
        response = self._path(self.inv_a_headers, "A", "Z", max_hops=5)
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertFalse(body["found"])
        self.assertIsNone(body["hop_count"])
        self.assertEqual(body["nodes"], [])
        self.assertEqual(body["relationships"], [])

    def test_shortest_path_prefers_direct_edge(self):
        shortcut = RelationshipStaging(
            source_occurrence_id="rel_shortcut",
            source_entity_id=self.entities["A"].id,
            target_entity_id=self.entities["D"].id,
            relationship_type=RelationshipType.CALLED,
            confidence=0.70,
            status=RelationshipStatus.CONFIRMED,
            source_document_id=self.document.id,
            evidence_snippet="A called D directly.",
            extracted_at=EXTRACTED_AT,
            case_id=self.case_id,
        )
        self.session.add(shortcut)
        self.session.commit()
        self.rel_ids.append(shortcut.id)
        project_case_graph(self.case_id, self.session, driver=self.driver)

        response = self._path(self.inv_a_headers, "A", "D", max_hops=5)
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertTrue(body["found"])
        self.assertEqual(body["hop_count"], 1)
        self.assertEqual(body["relationships"][0]["relationship_id"], str(shortcut.id))
        self.assertEqual(body["relationships"][0]["evidence_snippet"], "A called D directly.")

    def test_invalid_uuids_and_missing_entities(self):
        invalid_source = self._path(
            self.inv_a_headers, "A", "B", raw_source="not-a-uuid"
        )
        self.assertEqual(invalid_source.status_code, 422)
        invalid_target = self._path(
            self.inv_a_headers, "A", "B", raw_target="not-a-uuid"
        )
        self.assertEqual(invalid_target.status_code, 422)

        missing = uuid.uuid4()
        missing_source = self._path(
            self.inv_a_headers, "A", "B", source_entity_id=str(missing)
        )
        self.assertEqual(missing_source.status_code, 404)
        missing_target = self._path(
            self.inv_a_headers, "A", "B", target_entity_id=str(missing)
        )
        self.assertEqual(missing_target.status_code, 404)
        self.assertEqual(missing_source.json()["detail"], "Entity not found")

    def test_authorization_and_audit(self):
        unauth = client.get(
            "/api/investigation/path",
            params={
                "case_id": str(self.case_id),
                "source_entity_id": str(self.entities["A"].id),
                "target_entity_id": str(self.entities["B"].id),
            },
        )
        self.assertEqual(unauth.status_code, 401)

        denied = self._path(self.inv_b_headers, "A", "D")
        self.assertEqual(denied.status_code, 403)

        allowed = self._path(self.inv_a_headers, "A", "D", max_hops=3)
        self.assertEqual(allowed.status_code, 200)
        self.assertTrue(allowed.json()["found"])

        admin = self._path(self.admin_headers, "A", "D", max_hops=3)
        self.assertEqual(admin.status_code, 200)
        self.assertTrue(admin.json()["found"])
        self._assert_no_internal_ids(admin.json())

        self.session.expire_all()
        events = [
            row
            for row in self.session.scalars(select(AuditLog)).all()
            if row.action == AuditAction.INVESTIGATION_PATH_QUERIED.value
            and row.case_id == self.case_id
        ]
        self.assertTrue(events)
        for row in events:
            self.assertEqual(row.details.get("found"), True)
            self.assertIn("max_hops", row.details)
            self.assertNotIn("password", row.details)
            self.assertNotIn("access_token", row.details)
            self.assertNotIn("nodes", row.details)


if __name__ == "__main__":
    unittest.main()
