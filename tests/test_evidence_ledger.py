"""Evidence integrity ledger tests. Cleans created rows and files."""

from __future__ import annotations

import hashlib
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
from app.main import app
from app.models.audit import AuditLog
from app.models.case import Case
from app.models.document import Document
from app.models.enums import AuditAction, UserRole
from app.models.evidence import EvidenceBlock
from app.models.user import User
from app.services.documents import stored_file_path
from app.services.ledger import GENESIS_PREVIOUS_HASH, compute_block_hash
from tests.auth_support import create_test_user, login_headers

client = TestClient(app)
TXT_A = b"ledger evidence alpha\n"
TXT_B = b"ledger evidence beta\n"


class EvidenceLedgerApiTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        os.environ["UPLOAD_DIR"] = self._tmp.name
        self.session = SessionLocal()
        self.user_ids: list[uuid.UUID] = []
        self.case_ids: list[uuid.UUID] = []
        self.document_ids: list[uuid.UUID] = []
        self.admin, admin_pw = create_test_user(self.session, role=UserRole.ADMIN)
        self.inv_a, inv_a_pw = create_test_user(
            self.session, role=UserRole.INVESTIGATOR, name="Ledger Inv A"
        )
        self.inv_b, inv_b_pw = create_test_user(
            self.session, role=UserRole.INVESTIGATOR, name="Ledger Inv B"
        )
        self.user_ids.extend([self.admin.id, self.inv_a.id, self.inv_b.id])
        self.admin_headers = login_headers(client, self.admin.email, admin_pw)
        self.inv_a_headers = login_headers(client, self.inv_a.email, inv_a_pw)
        self.inv_b_headers = login_headers(client, self.inv_b.email, inv_b_pw)
        created = client.post(
            "/api/cases",
            headers=self.inv_a_headers,
            json={"title": f"Ledger case {uuid.uuid4().hex[:8]}"},
        )
        self.assertEqual(created.status_code, 201, created.text)
        self.case_id = uuid.UUID(created.json()["id"])
        self.case_ids.append(self.case_id)

    def tearDown(self):
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

    def _upload(self, data: bytes, name: str) -> uuid.UUID:
        response = client.post(
            f"/api/cases/{self.case_id}/documents",
            headers=self.inv_a_headers,
            files={"file": (name, data, "text/plain")},
        )
        self.assertEqual(response.status_code, 201, response.text)
        document_id = uuid.UUID(response.json()["id"])
        self.document_ids.append(document_id)
        return document_id

    def _assert_safe(self, payload) -> None:
        text = str(payload).lower()
        self.assertNotIn("password_hash", text)
        self.assertNotIn("access_token", text)
        self.assertNotIn("jwt_secret", text)
        self.assertNotIn("ledger evidence", text)
        self.assertNotIn(str(TXT_A), str(payload))
        self.assertNotIn(str(TXT_B), str(payload))

    def test_anchor_verify_chain_and_authorization(self):
        doc_a = self._upload(TXT_A, "a.txt")
        unanchored = client.get(
            f"/api/evidence/{doc_a}/verify",
            headers=self.inv_a_headers,
        )
        self.assertEqual(unanchored.status_code, 200, unanchored.text)
        self.assertFalse(unanchored.json()["anchored"])
        self.assertFalse(unanchored.json()["verified"])
        self.assertIsNone(unanchored.json()["data_hash"])

        self.assertEqual(
            client.post(f"/api/evidence/{doc_a}/anchor").status_code,
            401,
        )
        self.assertEqual(
            client.get(f"/api/evidence/{doc_a}/verify").status_code,
            401,
        )
        self.assertEqual(
            client.get(f"/api/cases/{self.case_id}/ledger").status_code,
            401,
        )
        for method in ("put", "patch", "delete"):
            response = getattr(client, method)(
                f"/api/evidence/{doc_a}/anchor",
                headers=self.inv_a_headers,
            )
            self.assertEqual(response.status_code, 405)

        denied_anchor = client.post(
            f"/api/evidence/{doc_a}/anchor",
            headers=self.inv_b_headers,
        )
        self.assertEqual(denied_anchor.status_code, 403)

        first = client.post(
            f"/api/evidence/{doc_a}/anchor",
            headers=self.inv_a_headers,
        )
        self.assertEqual(first.status_code, 200, first.text)
        first_body = first.json()
        self._assert_safe(first_body)
        expected_hash = hashlib.sha256(TXT_A).hexdigest()
        self.assertEqual(first_body["data_hash"], expected_hash)
        self.assertEqual(first_body["evidence_id"], str(doc_a))
        self.assertEqual(first_body["case_id"], str(self.case_id))
        self.assertEqual(first_body["actor"], str(self.inv_a.id))
        if first_body["block_index"] == 0:
            self.assertEqual(first_body["previous_hash"], GENESIS_PREVIOUS_HASH)
        else:
            previous = self.session.scalar(
                select(EvidenceBlock).where(
                    EvidenceBlock.block_index == first_body["block_index"] - 1
                )
            )
            self.assertIsNotNone(previous)
            self.assertEqual(first_body["previous_hash"], previous.block_hash)
        stored = self.session.get(EvidenceBlock, uuid.UUID(first_body["id"]))
        self.assertIsNotNone(stored)
        recomputed = compute_block_hash(
            block_index=stored.block_index,
            case_id=stored.case_id,
            evidence_id=stored.evidence_id,
            data_hash=stored.data_hash,
            previous_hash=stored.previous_hash,
            timestamp=stored.timestamp,
            actor=stored.actor,
        )
        self.assertEqual(recomputed, stored.block_hash)
        self.assertEqual(first_body["block_hash"], stored.block_hash)

        repeat = client.post(
            f"/api/evidence/{doc_a}/anchor",
            headers=self.inv_a_headers,
        )
        self.assertEqual(repeat.status_code, 200, repeat.text)
        self.assertEqual(repeat.json()["id"], first_body["id"])
        self.assertEqual(repeat.json()["block_index"], first_body["block_index"])
        count_a = self.session.scalar(
            select(func.count()).select_from(EvidenceBlock).where(
                EvidenceBlock.evidence_id == doc_a
            )
        )
        self.assertEqual(count_a, 1)

        doc_b = self._upload(TXT_B, "b.txt")
        second = client.post(
            f"/api/evidence/{doc_b}/anchor",
            headers=self.inv_a_headers,
        )
        self.assertEqual(second.status_code, 200, second.text)
        self.assertEqual(second.json()["previous_hash"], first_body["block_hash"])
        self.assertEqual(second.json()["block_index"], first_body["block_index"] + 1)
        self.assertNotEqual(second.json()["id"], first_body["id"])
        genesis = self.session.scalar(
            select(EvidenceBlock).where(EvidenceBlock.block_index == 0)
        )
        if genesis is not None:
            self.assertEqual(genesis.previous_hash, GENESIS_PREVIOUS_HASH)
        indexes = list(self.session.scalars(select(EvidenceBlock.block_index)))
        self.assertEqual(len(indexes), len(set(indexes)))

        intact = client.get(
            f"/api/evidence/{doc_a}/verify",
            headers=self.inv_a_headers,
        )
        self.assertEqual(intact.status_code, 200, intact.text)
        self.assertTrue(intact.json()["anchored"])
        self.assertTrue(intact.json()["verified"])
        self.assertEqual(intact.json()["data_hash"], expected_hash)
        self._assert_safe(intact.json())

        stored_file_path(doc_a).write_bytes(b"tampered-on-disk")
        mutated = client.get(
            f"/api/evidence/{doc_a}/verify",
            headers=self.inv_a_headers,
        )
        self.assertEqual(mutated.status_code, 200)
        self.assertTrue(mutated.json()["anchored"])
        self.assertFalse(mutated.json()["verified"])
        stored_file_path(doc_a).write_bytes(TXT_A)

        block_b = self.session.scalar(
            select(EvidenceBlock).where(EvidenceBlock.evidence_id == doc_b)
        )
        original_hash = block_b.block_hash
        block_b.block_hash = "a" * 64
        self.session.commit()
        tampered = client.get(
            f"/api/evidence/{doc_b}/verify",
            headers=self.inv_a_headers,
        )
        self.assertFalse(tampered.json()["verified"])
        block_b = self.session.get(EvidenceBlock, block_b.id)
        block_b.block_hash = original_hash
        self.session.commit()

        original_prev = block_b.previous_hash
        block_b.previous_hash = "1" * 64
        self.session.commit()
        broken = client.get(
            f"/api/evidence/{doc_b}/verify",
            headers=self.inv_a_headers,
        )
        self.assertFalse(broken.json()["verified"])
        block_b = self.session.get(EvidenceBlock, block_b.id)
        block_b.previous_hash = original_prev
        self.session.commit()

        denied_verify = client.get(
            f"/api/evidence/{doc_a}/verify",
            headers=self.inv_b_headers,
        )
        self.assertEqual(denied_verify.status_code, 403)
        denied_ledger = client.get(
            f"/api/cases/{self.case_id}/ledger",
            headers=self.inv_b_headers,
        )
        self.assertEqual(denied_ledger.status_code, 403)

        inv_ledger = client.get(
            f"/api/cases/{self.case_id}/ledger",
            headers=self.inv_a_headers,
        )
        self.assertEqual(inv_ledger.status_code, 200, inv_ledger.text)
        self._assert_safe(inv_ledger.json())
        inv_indexes = [item["block_index"] for item in inv_ledger.json()]
        self.assertEqual(inv_indexes, sorted(inv_indexes, reverse=True))
        self.assertEqual({item["evidence_id"] for item in inv_ledger.json()}, {str(doc_a), str(doc_b)})

        admin_ledger = client.get(
            f"/api/cases/{self.case_id}/ledger",
            headers=self.admin_headers,
        )
        self.assertEqual(admin_ledger.status_code, 200)
        self._assert_safe(admin_ledger.json())

        self.session.expire_all()
        anchored = [
            row.action
            for row in self.session.scalars(select(AuditLog)).all()
            if row.action == AuditAction.EVIDENCE_ANCHORED.value
            and row.resource_id == doc_a
        ]
        verified = [
            row
            for row in self.session.scalars(select(AuditLog)).all()
            if row.action == AuditAction.EVIDENCE_VERIFIED.value
            and row.resource_id == doc_a
        ]
        self.assertTrue(anchored)
        self.assertTrue(verified)
        for row in verified:
            self.assertNotIn("password", row.details)
            self.assertNotIn("access_token", row.details)


if __name__ == "__main__":
    unittest.main()
