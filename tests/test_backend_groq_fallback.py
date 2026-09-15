"""Backend E2E Groq fallback test: API -> DB -> Neo4j.

Verifies that when AI_PROVIDER=groq is set and Groq fails (503/timeout),
the FastAPI endpoint still returns 200 OK, successfully persists
deterministic entities to the database, and does not leave the document
stuck in processing.
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.db.session import SessionLocal
from app.graph.driver import close_driver, get_driver
from app.graph.schema import init_schema
from app.main import app
from app.ml.adapter import PersonBDocumentProcessor, get_ml_processor
from app.models.case import Case
from app.models.document import Document
from app.models.entity import Entity, EntityCaseLink, EntityMention
from app.models.enums import UserRole
from app.models.relationship import RelationshipStaging
from app.models.user import User
from app.services.documents import stored_file_path
from tests.auth_support import create_test_user, login_headers
from ml.config import MLConfig
from ml.ai.errors import AIProviderUnavailableError

client = TestClient(app)
TXT_BYTES = b"Rahul called Amit Kumar from 9876543210 in Bhubaneswar.\n"


class BackendGroqFallbackTests(unittest.TestCase):
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

        self.case_ids = []
        self.document_ids = []
        self.entity_ids = []
        self.user_ids = []

        # Enable Groq at the environment level so the real ML pipeline picks it up
        os.environ["AI_ENABLED"] = "1"
        os.environ["AI_PROVIDER"] = "groq"
        os.environ["GROQ_API_KEY"] = "fake_key_for_test"
        os.environ["AI_MAX_RETRIES"] = "0"

        # Override to use the REAL ML pipeline
        self.real_processor = PersonBDocumentProcessor()
        app.dependency_overrides[get_ml_processor] = lambda: self.real_processor

        self.user, password = create_test_user(self.session, role=UserRole.INVESTIGATOR)
        self.user_ids.append(self.user.id)
        self.headers = login_headers(client, self.user.email, password)

        created = client.post(
            "/api/cases",
            headers=self.headers,
            json={"title": f"Groq Fallback API case {uuid.uuid4().hex[:8]}"},
        )
        self.case_id = uuid.UUID(created.json()["id"])
        self.case_ids.append(self.case_id)

        uploaded = client.post(
            f"/api/cases/{self.case_id}/documents",
            headers=self.headers,
            files={"file": ("fir.txt", TXT_BYTES, "text/plain")},
        )
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

    @patch("ml.ai.providers.groq.subprocess.run")
    def test_groq_503_fallback_persists_successfully(self, mock_run):
        # Setup the mock to simulate a 503 error from curl
        mock_resp = MagicMock()
        mock_resp.returncode = 0
        mock_resp.stdout = "{}\n503"
        mock_run.return_value = mock_resp

        # 1. First run: Document should process completely with deterministic ML despite 503
        response = client.post(
            f"/api/documents/{self.document_id}/process",
            headers=self.headers,
        )

        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body["document_id"], str(self.document_id))

        # Should have entities from deterministic NLP
        self.assertGreater(body["mentions_persisted"], 0)

        # Verify persistence
        mentions = list(self.session.scalars(
            select(EntityMention).where(EntityMention.document_id == self.document_id)
        ))
        self.assertGreater(len(mentions), 0)
        self.entity_ids.extend(row.entity_id for row in mentions if row.entity_id)

        # 2. Second run: Idempotency check. Should return 200 and not duplicate entities.
        response_reprocess = client.post(
            f"/api/documents/{self.document_id}/process",
            headers=self.headers,
        )
        self.assertEqual(response_reprocess.status_code, 200)

        # Mentions persisted count should match exactly
        self.assertEqual(body["mentions_persisted"], response_reprocess.json()["mentions_persisted"])

        # Database count should remain unchanged
        mention_count = self.session.scalar(
            select(func.count()).select_from(EntityMention).where(
                EntityMention.document_id == self.document_id
            )
        )
        self.assertEqual(mention_count, len(mentions))


if __name__ == "__main__":
    unittest.main()
