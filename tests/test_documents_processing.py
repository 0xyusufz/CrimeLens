"""Document processing API: ML contract → PostgreSQL → Neo4j.

Uses a deterministic FixtureDocumentProcessor, not Person B's ML models.
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.db.session import SessionLocal
from app.graph.driver import close_driver, get_driver
from app.graph.projection import project_case_graph
from app.graph.schema import init_schema
from app.main import app
from app.ml.adapter import FixtureDocumentProcessor, get_ml_processor
from app.models.case import Case
from app.models.document import Document
from app.models.entity import Entity, EntityCaseLink, EntityMention
from app.models.enums import RelationshipStatus, RelationshipType, UserRole
from app.models.relationship import RelationshipStaging
from app.models.user import User
from app.services.documents import stored_file_path
from tests.auth_support import create_test_user, login_headers

client = TestClient(app)
TXT_BYTES = b"Rahul called Amit Kumar from 9876543210 in Bhubaneswar.\n"


class InvalidContractProcessor:
    def process_document(self, document_bytes, filename, document_id):
        return {"document_id": document_id, "entities": "not-a-list"}


class DocumentProcessingApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.driver = get_driver()
        cls.driver.verify_connectivity()
        init_schema(cls.driver)

    @classmethod
    def tearDownClass(cls):
        close_driver()

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        os.environ["UPLOAD_DIR"] = self._tmp.name
        self.session = SessionLocal()
        self.case_ids: list[uuid.UUID] = []
        self.document_ids: list[uuid.UUID] = []
        self.entity_ids: list[uuid.UUID] = []
        self.user_ids: list[uuid.UUID] = []
        app.dependency_overrides[get_ml_processor] = lambda: FixtureDocumentProcessor()
        self.user, password = create_test_user(self.session, role=UserRole.INVESTIGATOR)
        self.user_ids.append(self.user.id)
        self.headers = login_headers(client, self.user.email, password)
        created = client.post(
            "/api/cases",
            headers=self.headers,
            json={"title": f"Process API case {uuid.uuid4().hex[:8]}"},
        )
        self.assertEqual(created.status_code, 201, created.text)
        self.case_id = uuid.UUID(created.json()["id"])
        self.case_ids.append(self.case_id)
        uploaded = client.post(
            f"/api/cases/{self.case_id}/documents",
            headers=self.headers,
            files={"file": ("fir.txt", TXT_BYTES, "text/plain")},
        )
        self.assertEqual(uploaded.status_code, 201, uploaded.text)
        self.document_id = uuid.UUID(uploaded.json()["id"])
        self.document_ids.append(self.document_id)

    def tearDown(self):
        app.dependency_overrides.pop(get_ml_processor, None)
        try:
            self.session.rollback()
            with self.driver.session() as neo:
                neo.run(
                    "MATCH (n) WHERE n.case_id = $case_id OR n.document_id = $document_id "
                    "OR n.entity_id IN $entity_ids DETACH DELETE n",
                    case_id=str(self.case_id),
                    document_id=str(self.document_id),
                    entity_ids=[str(eid) for eid in self.entity_ids],
                )
            for document_id in self.document_ids:
                stored_file_path(document_id).unlink(missing_ok=True)
                for mention in self.session.scalars(
                    select(EntityMention).where(EntityMention.document_id == document_id)
                ).all():
                    self.session.delete(mention)
                for rel in self.session.scalars(
                    select(RelationshipStaging).where(
                        RelationshipStaging.source_document_id == document_id
                    )
                ).all():
                    self.session.delete(rel)
            for case_id in self.case_ids:
                for link in self.session.scalars(
                    select(EntityCaseLink).where(EntityCaseLink.case_id == case_id)
                ).all():
                    self.entity_ids.append(link.entity_id)
                    self.session.delete(link)
                case = self.session.get(Case, case_id)
                if case is not None:
                    self.session.delete(case)
            self.session.flush()
            for user_id in self.user_ids:
                user = self.session.get(User, user_id)
                if user is not None:
                    self.session.delete(user)
            for entity_id in set(self.entity_ids):
                leftover_link = self.session.scalar(
                    select(EntityCaseLink).where(EntityCaseLink.entity_id == entity_id)
                )
                leftover_mention = self.session.scalar(
                    select(EntityMention).where(EntityMention.entity_id == entity_id)
                )
                leftover_rel = self.session.scalar(
                    select(RelationshipStaging).where(
                        (RelationshipStaging.source_entity_id == entity_id)
                        | (RelationshipStaging.target_entity_id == entity_id)
                    )
                )
                if leftover_link is None and leftover_mention is None and leftover_rel is None:
                    entity = self.session.get(Entity, entity_id)
                    if entity is not None:
                        self.session.delete(entity)
            self.session.commit()
        except Exception:
            self.session.rollback()
        finally:
            self.session.close()
            self._tmp.cleanup()

    def _process(self):
        return client.post(
            f"/api/documents/{self.document_id}/process",
            headers=self.headers,
        )

    def test_valid_extraction_persists_and_projects(self):
        response = self._process()
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body["document_id"], str(self.document_id))
        self.assertEqual(body["case_id"], str(self.case_id))
        self.assertEqual(body["mentions_persisted"], 4)
        self.assertEqual(body["entities_processed"], 4)
        self.assertEqual(body["relationships_processed"], 3)
        self.assertEqual(body["relationships_persisted"], 3)
        self.assertEqual(body["relationships_unresolved"], 0)

        mentions = list(
            self.session.scalars(
                select(EntityMention).where(EntityMention.document_id == self.document_id)
            )
        )
        self.assertEqual(len(mentions), 4)
        self.assertTrue(all(row.entity_id is not None for row in mentions))
        mention_ids = {row.mention_id for row in mentions}
        self.assertEqual(
            mention_ids,
            {"mention_001", "mention_002", "mention_003", "mention_004"},
        )
        self.entity_ids.extend(row.entity_id for row in mentions if row.entity_id)

        entities = [self.session.get(Entity, eid) for eid in set(self.entity_ids)]
        self.assertTrue(all(entity is not None for entity in entities))
        self.assertTrue(all(isinstance(entity.id, uuid.UUID) for entity in entities))

        links = list(
            self.session.scalars(
                select(EntityCaseLink).where(EntityCaseLink.case_id == self.case_id)
            )
        )
        self.assertEqual(len(links), 4)

        staged = list(
            self.session.scalars(
                select(RelationshipStaging).where(
                    RelationshipStaging.source_document_id == self.document_id
                )
            )
        )
        self.assertEqual(len(staged), 3)
        by_occ = {row.source_occurrence_id: row for row in staged}
        self.assertEqual(by_occ["rel_001"].status, RelationshipStatus.CONFIRMED)
        self.assertEqual(by_occ["rel_002"].status, RelationshipStatus.INFERRED)
        self.assertEqual(by_occ["rel_003"].status, RelationshipStatus.PREDICTED)
        self.assertEqual(by_occ["rel_001"].relationship_type, RelationshipType.CALLED)
        self.assertEqual(by_occ["rel_001"].evidence_snippet, "Rahul called Amit Kumar.")
        self.assertEqual(by_occ["rel_001"].source_document_id, self.document_id)
        self.assertEqual(by_occ["rel_001"].case_id, self.case_id)
        self.assertAlmostEqual(by_occ["rel_001"].confidence, 0.98)
        self.assertEqual(
            by_occ["rel_001"].extracted_at,
            datetime(2026, 9, 13, 10, 30, tzinfo=timezone.utc),
        )
        self.assertNotEqual(by_occ["rel_001"].status, RelationshipStatus.INFERRED)
        self.assertNotEqual(by_occ["rel_002"].status, RelationshipStatus.CONFIRMED)
        self.assertNotEqual(by_occ["rel_003"].status, RelationshipStatus.CONFIRMED)

        with self.driver.session() as neo:
            confirmed = neo.run(
                "MATCH ()-[r:CALLED {relationship_id: $rid}]->() "
                "RETURN r.status AS status, r.confidence AS confidence, "
                "r.evidence_snippet AS evidence, r.source_document_id AS doc, "
                "r.case_id AS case_id",
                rid=str(by_occ["rel_001"].id),
            ).single()
        self.assertIsNotNone(confirmed)
        self.assertEqual(confirmed["status"], "CONFIRMED")
        self.assertAlmostEqual(confirmed["confidence"], 0.98)
        self.assertEqual(confirmed["evidence"], "Rahul called Amit Kumar.")
        self.assertEqual(confirmed["doc"], str(self.document_id))
        self.assertEqual(confirmed["case_id"], str(self.case_id))

        inferred = by_occ["rel_002"]
        predicted = by_occ["rel_003"]
        with self.driver.session() as neo:
            self.assertIsNotNone(
                neo.run(
                    "MATCH ()-[r:ASSOCIATED_WITH {relationship_id: $rid}]->() RETURN r",
                    rid=str(inferred.id),
                ).single()
            )
            pred = neo.run(
                "MATCH ()-[r:LOCATED_AT {relationship_id: $rid}]->() RETURN r.status AS status",
                rid=str(predicted.id),
            ).single()
        self.assertEqual(pred["status"], "PREDICTED")

    def test_unresolved_relationship_is_not_projected(self):
        response = self._process()
        self.assertEqual(response.status_code, 200, response.text)
        mention = self.session.scalar(
            select(EntityMention).where(
                EntityMention.document_id == self.document_id,
                EntityMention.mention_id == "mention_001",
            )
        )
        self.assertIsNotNone(mention.entity_id)
        self.entity_ids.append(mention.entity_id)
        unresolved = RelationshipStaging(
            source_occurrence_id="rel_unresolved",
            source_entity_id=mention.entity_id,
            target_entity_id=None,
            relationship_type=RelationshipType.CALLED,
            confidence=0.5,
            status=RelationshipStatus.INFERRED,
            source_document_id=self.document_id,
            evidence_snippet="Unresolved endpoint fixture.",
            extracted_at=datetime(2026, 9, 13, 10, 30, tzinfo=timezone.utc),
            case_id=self.case_id,
        )
        self.session.add(unresolved)
        self.session.commit()
        stats = project_case_graph(self.case_id, self.session, driver=self.driver)
        self.assertGreaterEqual(stats["relationships_skipped"], 1)
        with self.driver.session() as neo:
            missing = neo.run(
                "MATCH ()-[r {relationship_id: $rid}]->() RETURN r",
                rid=str(unresolved.id),
            ).single()
        self.assertIsNone(missing)

    def test_reprocess_is_idempotent(self):
        first = self._process()
        self.assertEqual(first.status_code, 200, first.text)
        second = self._process()
        self.assertEqual(second.status_code, 200, second.text)
        self.assertEqual(first.json()["mentions_persisted"], second.json()["mentions_persisted"])
        self.assertEqual(
            first.json()["relationships_persisted"],
            second.json()["relationships_persisted"],
        )
        mention_count = self.session.scalar(
            select(func.count()).select_from(EntityMention).where(
                EntityMention.document_id == self.document_id
            )
        )
        rel_count = self.session.scalar(
            select(func.count()).select_from(RelationshipStaging).where(
                RelationshipStaging.source_document_id == self.document_id
            )
        )
        self.assertEqual(mention_count, 4)
        self.assertEqual(rel_count, 3)
        for row in self.session.scalars(
            select(EntityMention).where(EntityMention.document_id == self.document_id)
        ):
            if row.entity_id:
                self.entity_ids.append(row.entity_id)
        with self.driver.session() as neo:
            called = neo.run(
                "MATCH ()-[r:CALLED]->() WHERE r.source_document_id = $doc RETURN count(r) AS n",
                doc=str(self.document_id),
            ).single()["n"]
        self.assertEqual(called, 1)

    def test_missing_document_and_missing_file(self):
        missing = client.post(
            f"/api/documents/{uuid.uuid4()}/process",
            headers=self.headers,
        )
        self.assertEqual(missing.status_code, 404)
        self.assertEqual(missing.json()["detail"], "Document not found")

        stored_file_path(self.document_id).unlink()
        gone = self._process()
        self.assertEqual(gone.status_code, 500)
        self.assertEqual(gone.json()["detail"], "The stored document file is missing.")
        mention_count = self.session.scalar(
            select(func.count()).select_from(EntityMention).where(
                EntityMention.document_id == self.document_id
            )
        )
        self.assertEqual(mention_count, 0)

    def test_invalid_ml_output_does_not_persist(self):
        app.dependency_overrides[get_ml_processor] = lambda: InvalidContractProcessor()
        response = self._process()
        self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual(response.json()["detail"], "ML output failed contract validation.")
        mention_count = self.session.scalar(
            select(func.count()).select_from(EntityMention).where(
                EntityMention.document_id == self.document_id
            )
        )
        rel_count = self.session.scalar(
            select(func.count()).select_from(RelationshipStaging).where(
                RelationshipStaging.source_document_id == self.document_id
            )
        )
        self.assertEqual(mention_count, 0)
        self.assertEqual(rel_count, 0)


if __name__ == "__main__":
    unittest.main()
