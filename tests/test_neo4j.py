"""Neo4j derived-graph foundation tests. No PostgreSQL data projection."""

from __future__ import annotations

import sys
import unittest
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT))

from app.graph.driver import close_driver, get_driver
from app.graph.schema import CONSTRAINTS, init_schema, list_constraint_names


class Neo4jFoundationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.driver = get_driver()
        cls.driver.verify_connectivity()

    @classmethod
    def tearDownClass(cls):
        close_driver()

    def test_return_1(self):
        with self.driver.session() as session:
            value = session.run("RETURN 1 AS ok").single()["ok"]
        self.assertEqual(value, 1)

    def test_schema_initialization(self):
        created = init_schema(self.driver)
        existing = list_constraint_names(self.driver)
        expected = {name for name, _ in CONSTRAINTS}
        self.assertEqual(set(created), expected)
        self.assertTrue(expected.issubset(existing))

    def test_temporary_person_node_create_read_delete(self):
        entity_id = str(uuid.uuid4())
        with self.driver.session() as session:
            session.run(
                "MERGE (p:Person {entity_id: $entity_id}) "
                "ON CREATE SET p.label = $label",
                entity_id=entity_id,
                label="temporary-test-node",
            )
            found = session.run(
                "MATCH (p:Person {entity_id: $entity_id}) "
                "RETURN p.entity_id AS entity_id, p.label AS label, elementId(p) AS neo4j_id",
                entity_id=entity_id,
            ).single()
            self.assertIsNotNone(found)
            self.assertEqual(found["entity_id"], entity_id)
            self.assertEqual(found["label"], "temporary-test-node")
            self.assertNotEqual(found["neo4j_id"], entity_id)

            session.run(
                "MATCH (p:Person {entity_id: $entity_id}) DETACH DELETE p",
                entity_id=entity_id,
            )
            gone = session.run(
                "MATCH (p:Person {entity_id: $entity_id}) RETURN p",
                entity_id=entity_id,
            ).single()
            self.assertIsNone(gone)


if __name__ == "__main__":
    unittest.main()
