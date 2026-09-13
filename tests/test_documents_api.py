"""Document upload API tests. Uses CrimeLens PostgreSQL; cleans rows and files."""

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

from app.config import upload_dir
from app.db.session import SessionLocal
from app.main import app
from app.models.case import Case
from app.models.document import Document
from app.services.documents import stored_file_path

client = TestClient(app)

MINIMAL_PDF = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF\n"
CSV_BYTES = b"caller,receiver,duration\n9876543210,9123456789,120\n"
TXT_BYTES = b"Rahul called Amit Kumar.\n"


class DocumentApiTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        os.environ["UPLOAD_DIR"] = self._tmp.name
        os.environ.pop("MAX_UPLOAD_BYTES", None)
        self.session = SessionLocal()
        self.case_ids: list[uuid.UUID] = []
        self.document_ids: list[uuid.UUID] = []
        created = client.post(
            "/api/cases",
            json={"title": f"Doc API case {uuid.uuid4().hex[:8]}"},
        )
        self.assertEqual(created.status_code, 201, created.text)
        self.case_id = uuid.UUID(created.json()["id"])
        self.case_ids.append(self.case_id)

    def tearDown(self):
        try:
            self.session.rollback()
            for document_id in self.document_ids:
                path = stored_file_path(document_id)
                path.unlink(missing_ok=True)
                row = self.session.get(Document, document_id)
                if row is not None:
                    self.session.delete(row)
            for case_id in self.case_ids:
                case = self.session.get(Case, case_id)
                if case is not None:
                    self.session.delete(case)
            self.session.commit()
        except Exception:
            self.session.rollback()
        finally:
            self.session.close()
            self._tmp.cleanup()

    def _upload(self, filename: str, data: bytes, content_type: str, extra_form: dict | None = None):
        response = client.post(
            f"/api/cases/{self.case_id}/documents",
            files={"file": (filename, data, content_type)},
            data=extra_form or {},
        )
        if response.status_code == 201:
            self.document_ids.append(uuid.UUID(response.json()["id"]))
        return response

    def _assert_metadata_only(self, payload: dict) -> None:
        self.assertNotIn("path", payload)
        self.assertNotIn("storage_path", payload)
        self.assertNotIn("content", payload)
        self.assertNotIn("bytes", payload)
        self.assertNotIn("password_hash", payload)

    def test_upload_pdf_csv_txt_and_metadata(self):
        pdf = self._upload("statement.pdf", MINIMAL_PDF, "application/pdf")
        self.assertEqual(pdf.status_code, 201, pdf.text)
        pdf_body = pdf.json()
        pdf_id = uuid.UUID(pdf_body["id"])
        self._assert_metadata_only(pdf_body)
        self.assertEqual(pdf_body["filename"], "statement.pdf")
        self.assertEqual(pdf_body["case_id"], str(self.case_id))
        self.assertEqual(pdf_body["sha256_hash"], hashlib.sha256(MINIMAL_PDF).hexdigest())
        self.assertEqual(len(pdf_body["sha256_hash"]), 64)
        stored = self.session.get(Document, pdf_id)
        self.assertIsNotNone(stored)
        self.assertEqual(stored.filename, "statement.pdf")
        self.assertEqual(stored.sha256_hash, pdf_body["sha256_hash"])
        disk = stored_file_path(pdf_id)
        self.assertTrue(disk.is_file())
        self.assertEqual(disk.parent, upload_dir())
        self.assertEqual(disk.name, str(pdf_id))
        self.assertEqual(disk.read_bytes(), MINIMAL_PDF)

        csv = self._upload("cdr.csv", CSV_BYTES, "text/csv")
        self.assertEqual(csv.status_code, 201, csv.text)
        self.assertEqual(csv.json()["filename"], "cdr.csv")
        self.assertEqual(csv.json()["sha256_hash"], hashlib.sha256(CSV_BYTES).hexdigest())
        csv_id = uuid.UUID(csv.json()["id"])
        self.assertTrue(stored_file_path(csv_id).is_file())

        txt = self._upload("notes.txt", TXT_BYTES, "text/plain")
        self.assertEqual(txt.status_code, 201, txt.text)
        self.assertEqual(txt.json()["filename"], "notes.txt")
        self.assertEqual(txt.json()["sha256_hash"], hashlib.sha256(TXT_BYTES).hexdigest())

        listed = client.get(f"/api/cases/{self.case_id}/documents")
        self.assertEqual(listed.status_code, 200, listed.text)
        items = listed.json()
        self.assertEqual(len(items), 3)
        listed_ids = {item["id"] for item in items}
        self.assertEqual(listed_ids, {pdf.json()["id"], csv.json()["id"], txt.json()["id"]})
        timestamps = [item["uploaded_at"] for item in items]
        self.assertEqual(timestamps, sorted(timestamps, reverse=True))
        for item in items:
            self._assert_metadata_only(item)
            self.assertNotIn("file", item)

        fetched = client.get(f"/api/documents/{pdf_id}")
        self.assertEqual(fetched.status_code, 200, fetched.text)
        self.assertEqual(fetched.json()["id"], str(pdf_id))
        self.assertEqual(fetched.json()["filename"], "statement.pdf")
        self._assert_metadata_only(fetched.json())

    def test_backend_generates_document_uuid(self):
        chosen = str(uuid.uuid4())
        response = self._upload(
            "note.txt",
            TXT_BYTES,
            "text/plain",
            extra_form={"id": chosen, "document_id": chosen},
        )
        self.assertEqual(response.status_code, 201, response.text)
        self.assertNotEqual(response.json()["id"], chosen)
        uuid.UUID(response.json()["id"])
        self.assertIsNone(self.session.get(Document, uuid.UUID(chosen)))

    def test_original_filename_is_metadata_not_path(self):
        response = self._upload("../../etc/passwd.txt", TXT_BYTES, "text/plain")
        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual(response.json()["filename"], "passwd.txt")
        document_id = uuid.UUID(response.json()["id"])
        disk = stored_file_path(document_id)
        self.assertEqual(disk.name, str(document_id))
        self.assertNotIn("passwd", str(disk))
        self.assertTrue(disk.is_file())

    def test_nonexistent_case_and_document(self):
        missing_case = client.post(
            f"/api/cases/{uuid.uuid4()}/documents",
            files={"file": ("note.txt", TXT_BYTES, "text/plain")},
        )
        self.assertEqual(missing_case.status_code, 404)
        self.assertEqual(missing_case.json()["detail"], "Case not found")

        missing_list = client.get(f"/api/cases/{uuid.uuid4()}/documents")
        self.assertEqual(missing_list.status_code, 404)

        missing_doc = client.get(f"/api/documents/{uuid.uuid4()}")
        self.assertEqual(missing_doc.status_code, 404)
        self.assertEqual(missing_doc.json()["detail"], "Document not found")

        invalid = client.get("/api/documents/not-a-uuid")
        self.assertEqual(invalid.status_code, 422)

    def test_unsupported_empty_and_oversized_uploads(self):
        exe = self._upload("payload.exe", b"MZ\x90\x00not-an-evidence-file", "application/octet-stream")
        self.assertEqual(exe.status_code, 415)

        png = self._upload("photo.png", b"\x89PNG\r\n\x1a\n", "image/png")
        self.assertEqual(png.status_code, 415)

        empty = self._upload("empty.txt", b"", "text/plain")
        self.assertEqual(empty.status_code, 400)

        os.environ["MAX_UPLOAD_BYTES"] = "32"
        try:
            oversized = self._upload("big.txt", b"x" * 64, "text/plain")
            self.assertEqual(oversized.status_code, 413)
        finally:
            os.environ.pop("MAX_UPLOAD_BYTES", None)


if __name__ == "__main__":
    unittest.main()
