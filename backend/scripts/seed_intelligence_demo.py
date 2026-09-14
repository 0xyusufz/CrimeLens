"""
Idempotent development data seed for Intelligence/Patterns.

Usage:
    .venv/bin/python3 scripts/seed_intelligence_demo.py
"""

from __future__ import annotations

import sys
import uuid
import hashlib
from datetime import datetime, timedelta, timezone

sys.path.insert(0, ".")

from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.case import Case
from app.models.document import Document, StructuredRecord
from app.models.enums import RecordType
from app.models.user import User

TARGET_CASE_NUMBER = "CL-7E106F4D14B7"
DEV_USER_EMAIL = "dev@crimelens.local"
SEED_DOCUMENT_FILENAME = "SEED_synthetic_intelligence_dev.json"

def main():
    db = SessionLocal()
    try:
        user = db.scalar(select(User).where(User.email == DEV_USER_EMAIL))
        if user is None:
            print("ERROR: User not found.")
            sys.exit(1)

        case = db.scalar(select(Case).where(Case.case_number == TARGET_CASE_NUMBER))
        if case is None:
            print("ERROR: Case not found.")
            sys.exit(1)

        doc = db.scalar(select(Document).where(Document.case_id == case.id, Document.filename == SEED_DOCUMENT_FILENAME))
        if doc is None:
            doc = Document(
                case_id=case.id,
                filename=SEED_DOCUMENT_FILENAME,
                sha256_hash=hashlib.sha256(SEED_DOCUMENT_FILENAME.encode()).hexdigest(),
                uploaded_by=user.id,
            )
            db.add(doc)
        # Write dummy bytes to satisfy processing in case they were deleted
        from app.services.documents import stored_file_path
        stored_file_path(doc.id).write_bytes(b"{}")

        # Generate synthetic StructuredRecords
        # Fixed base_time for idempotency
        base_time = datetime(2024, 4, 15, 12, 0, 0, tzinfo=timezone.utc)
        
        records_to_create = [
            # 1. CIRCULAR_TRANSACTION (A -> B -> C -> A within 30 days)
            (RecordType.TRANSACTION, {"source": "Rahul Sharma", "target": "Amit Verma", "amount": 10000, "timestamp": (base_time - timedelta(days=20)).isoformat()}),
            (RecordType.TRANSACTION, {"source": "Amit Verma", "target": "Eastern Logistics Ltd", "amount": 9500, "timestamp": (base_time - timedelta(days=15)).isoformat()}),
            (RecordType.TRANSACTION, {"source": "Eastern Logistics Ltd", "target": "Rahul Sharma", "amount": 9000, "timestamp": (base_time - timedelta(days=10)).isoformat()}),
            
            # 2. RAPID_TRANSFER_CHAIN (A -> B -> C within 48 hours)
            (RecordType.TRANSACTION, {"source": "ACC-1001", "target": "Unknown-1", "amount": 50000, "timestamp": (base_time - timedelta(hours=40)).isoformat()}),
            (RecordType.TRANSACTION, {"source": "Unknown-1", "target": "Unknown-2", "amount": 49000, "timestamp": (base_time - timedelta(hours=20)).isoformat()}),
            
            # 3. LOCATION_TIME_OVERLAP (Two entities same location within 2 hours)
            (RecordType.CDR, {"entity": "Rahul Sharma", "location": "Bhubaneswar", "timestamp": (base_time - timedelta(hours=1)).isoformat()}),
            (RecordType.CDR, {"entity": "Amit Verma", "location": "Bhubaneswar", "timestamp": (base_time - timedelta(hours=1, minutes=30)).isoformat()}),
        ]

        created = 0
        for rtype, payload in records_to_create:
            # Idempotency check via exact JSON match
            existing = db.scalar(
                select(StructuredRecord).where(
                    StructuredRecord.case_id == case.id,
                    StructuredRecord.document_id == doc.id,
                    StructuredRecord.record_type == rtype,
                    StructuredRecord.raw_json == payload
                )
            )
            if not existing:
                record = StructuredRecord(
                    case_id=case.id,
                    document_id=doc.id,
                    record_type=rtype,
                    raw_json=payload
                )
                db.add(record)
                created += 1

        db.commit()
        
        # Trigger ML pipeline to detect and persist patterns/leads
        from app.services.processing import process_uploaded_document
        from app.ml.adapter import get_ml_processor
        processor = get_ml_processor()
        process_uploaded_document(db, doc.id, processor)
        
        print(f"Seed complete. Created {created} synthetic StructuredRecords.")
        print("Triggered ML pipeline successfully.")

    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    main()
