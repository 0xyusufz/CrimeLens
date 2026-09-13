"""PostgreSQL → Neo4j projection tests. Neo4j is derived from PostgreSQL."""

from __future__ import annotations

import sys
import unittest
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT))

from app.db.session import SessionLocal
from app.graph.driver import close_driver, get_driver
from app.graph.projection import project_case_graph
from app.graph.schema import init_schema
from app.models import (
    Case,
    CaseStatus,
    Document,
    Entity,
    EntityType,
    RelationshipStaging,
    RelationshipStatus,
    RelationshipType,
    User,
    UserRole,
)


class GraphProjectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.driver = get_driver()
        cls.driver.verify_connectivity()
        init_schema(cls.driver)

    @classmethod
    def tearDownClass(cls):
        close_driver()

    def test_project_case_graph_is_idempotent_and_preserves_occurrences(self):
        session = SessionLocal()
        suffix = uuid.uuid4().hex[:8]
        extracted_at = datetime(2026, 9, 13, 10, 30, tzinfo=timezone.utc)
        user = User(
            name="Projection Tester",
            email=f"proj-{suffix}@example.invalid",
            password_hash="not-a-real-hash",
            role=UserRole.INVESTIGATOR,
        )
        case = None
        document = None
        source = None
        target = None
        first = None
        second = None
        unresolved_target = None
        try:
            session.add(user)
            session.flush()
            case = Case(
                case_number=f"PROJ-{suffix}",
                title="Projection test case",
                status=CaseStatus.OPEN,
                created_by=user.id,
            )
            session.add(case)
            session.flush()
            document = Document(
                case_id=case.id,
                filename="proj.txt",
                sha256_hash="3" * 64,
                uploaded_by=user.id,
            )
            session.add(document)
            session.flush()
            source = Entity(type=EntityType.PERSON, canonical_name="Rahul Sharma")
            target = Entity(type=EntityType.PERSON, canonical_name="Amit Kumar")
            session.add_all([source, target])
            session.flush()
            first = RelationshipStaging(
                source_occurrence_id="rel_001",
                source_entity_id=None,
                target_entity_id=target.id,
                relationship_type=RelationshipType.CALLED,
                confidence=0.81,
                status=RelationshipStatus.INFERRED,
                source_document_id=document.id,
                evidence_snippet="Rahul called Amit Kumar.",
                extracted_at=extracted_at,
                case_id=case.id,
            )
            unresolved_target = RelationshipStaging(
                source_occurrence_id="rel_unresolved_target",
                source_entity_id=source.id,
                target_entity_id=None,
                relationship_type=RelationshipType.CALLED,
                confidence=0.72,
                status=RelationshipStatus.INFERRED,
                source_document_id=document.id,
                extracted_at=extracted_at,
                case_id=case.id,
            )
            session.add_all([first, unresolved_target])
            session.commit()

            stats = project_case_graph(case.id, session, driver=self.driver)
            self.assertEqual(stats["relationships_projected"], 0)
            self.assertEqual(stats["relationships_skipped"], 2)
            with self.driver.session() as neo:
                missing = neo.run(
                    "MATCH ()-[r:CALLED {relationship_id: $rid}]->() RETURN r",
                    rid=str(first.id),
                ).single()
            self.assertIsNone(missing)

            first.source_entity_id = source.id
            session.commit()
            stats = project_case_graph(case.id, session, driver=self.driver)
            self.assertEqual(stats["relationships_projected"], 1)
            self.assertEqual(stats["relationships_skipped"], 1)

            with self.driver.session() as neo:
                nodes = neo.run(
                    "MATCH (p:Person) WHERE p.entity_id IN $ids "
                    "RETURN p.entity_id AS entity_id",
                    ids=[str(source.id), str(target.id)],
                ).data()
                self.assertEqual({row["entity_id"] for row in nodes}, {str(source.id), str(target.id)})
                case_node = neo.run(
                    "MATCH (c:Case {case_id: $case_id}) RETURN c.case_id AS case_id",
                    case_id=str(case.id),
                ).single()
                self.assertEqual(case_node["case_id"], str(case.id))
                doc_node = neo.run(
                    "MATCH (d:Document {document_id: $document_id}) "
                    "RETURN d.document_id AS document_id, d.filename AS filename",
                    document_id=str(document.id),
                ).single()
                self.assertEqual(doc_node["document_id"], str(document.id))
                self.assertEqual(doc_node["filename"], "proj.txt")
                rel = neo.run(
                    "MATCH ()-[r:CALLED {relationship_id: $rid}]->() "
                    "RETURN r.status AS status, r.confidence AS confidence, "
                    "r.case_id AS case_id, r.evidence_snippet AS evidence_snippet, "
                    "r.source_document_id AS source_document_id",
                    rid=str(first.id),
                ).single()
                self.assertEqual(rel["status"], "INFERRED")
                self.assertAlmostEqual(rel["confidence"], 0.81)
                self.assertEqual(rel["case_id"], str(case.id))
                self.assertEqual(rel["evidence_snippet"], "Rahul called Amit Kumar.")
                self.assertEqual(rel["source_document_id"], str(document.id))
                still_unresolved = neo.run(
                    "MATCH ()-[r:CALLED {relationship_id: $rid}]->() RETURN r",
                    rid=str(unresolved_target.id),
                ).single()
            self.assertIsNone(still_unresolved)

            project_case_graph(case.id, session, driver=self.driver)
            with self.driver.session() as neo:
                count = neo.run(
                    "MATCH (:Person {entity_id: $src})-[r:CALLED]->(:Person {entity_id: $tgt}) "
                    "RETURN count(r) AS n",
                    src=str(source.id),
                    tgt=str(target.id),
                ).single()["n"]
            self.assertEqual(count, 1)

            second = RelationshipStaging(
                source_occurrence_id="rel_002",
                source_entity_id=source.id,
                target_entity_id=target.id,
                relationship_type=RelationshipType.CALLED,
                confidence=0.90,
                status=RelationshipStatus.CONFIRMED,
                source_document_id=document.id,
                evidence_snippet="Second distinct call.",
                extracted_at=extracted_at,
                case_id=case.id,
            )
            session.add(second)
            session.commit()
            project_case_graph(case.id, session, driver=self.driver)
            with self.driver.session() as neo:
                ids = {
                    row["rid"]
                    for row in neo.run(
                        "MATCH (:Person {entity_id: $src})-[r:CALLED]->(:Person {entity_id: $tgt}) "
                        "RETURN r.relationship_id AS rid",
                        src=str(source.id),
                        tgt=str(target.id),
                    )
                }
            self.assertEqual(ids, {str(first.id), str(second.id)})
        except Exception:
            session.rollback()
            raise
        finally:
            with self.driver.session() as neo:
                neo.run(
                    "MATCH (n) WHERE n.entity_id IN $entity_ids "
                    "OR n.case_id = $case_id OR n.document_id = $document_id "
                    "DETACH DELETE n",
                    entity_ids=[str(source.id), str(target.id)] if source and target else [],
                    case_id=str(case.id) if case else "",
                    document_id=str(document.id) if document else "",
                )
            try:
                session.rollback()
                for row in (second, unresolved_target, first):
                    if row is not None and getattr(row, "id", None):
                        loaded = session.get(RelationshipStaging, row.id)
                        if loaded is not None:
                            session.delete(loaded)
                if source is not None:
                    loaded = session.get(Entity, source.id)
                    if loaded is not None:
                        session.delete(loaded)
                if target is not None:
                    loaded = session.get(Entity, target.id)
                    if loaded is not None:
                        session.delete(loaded)
                if document is not None:
                    loaded = session.get(Document, document.id)
                    if loaded is not None:
                        session.delete(loaded)
                if case is not None:
                    loaded = session.get(Case, case.id)
                    if loaded is not None:
                        session.delete(loaded)
                loaded_user = session.get(User, user.id)
                if loaded_user is not None:
                    session.delete(loaded_user)
                session.commit()
            except Exception:
                session.rollback()
            session.close()


if __name__ == "__main__":
    unittest.main()
