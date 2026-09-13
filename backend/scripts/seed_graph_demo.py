"""
Idempotent development data seed for Operation Nightfall.

Usage (from backend/ directory):
    .venv/bin/python3 scripts/seed_graph_demo.py

Running twice must produce no duplicates.
"""

from __future__ import annotations

import hashlib
import sys
import uuid
from datetime import datetime, timezone

sys.path.insert(0, ".")  # make app/ importable from backend/

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.graph.projection import project_case_graph
from app.models.case import Case
from app.models.document import Document
from app.models.entity import Entity, EntityCaseLink
from app.models.enums import (
    EntityType,
    RelationshipStatus,
    RelationshipType,
)
from app.models.relationship import RelationshipStaging
from app.models.user import User

# ─── Constants ────────────────────────────────────────────────────────────────

TARGET_CASE_NUMBER = "CL-7E106F4D14B7"
DEV_USER_EMAIL = "dev@crimelens.local"
SEED_DOCUMENT_FILENAME = "SEED_synthetic_nightfall_dev.pdf"

ENTITIES_SPEC: list[tuple[EntityType, str]] = [
    (EntityType.PERSON,       "Rahul Sharma"),
    (EntityType.PERSON,       "Amit Verma"),
    (EntityType.PHONE,        "9876543210"),
    (EntityType.BANK_ACCOUNT, "ACC-1001"),
    (EntityType.VEHICLE,      "OD-02-AB-1234"),
    (EntityType.LOCATION,     "Bhubaneswar"),
    (EntityType.ORGANIZATION, "Eastern Logistics Ltd"),
]

RELATIONSHIPS_SPEC = [
    # (source_name, target_name, rel_type, evidence_snippet)
    (
        "Rahul Sharma", "Amit Verma",
        RelationshipType.CALLED,
        "Telecom CDR analysis shows 14 calls between these subscribers "
        "between 2024-03-01 and 2024-04-15, totalling 47 minutes.",
    ),
    (
        "Rahul Sharma", "9876543210",
        RelationshipType.ASSOCIATED_WITH,
        "Subscriber registration records confirm that mobile number 9876543210 "
        "is registered under the name Rahul Sharma at address: 4B, MG Road, Cuttack.",
    ),
    (
        "Rahul Sharma", "OD-02-AB-1234",
        RelationshipType.USED_VEHICLE,
        "CCTV footage from Warehouse C entrance dated 2024-04-03 shows Rahul Sharma "
        "exiting vehicle OD-02-AB-1234 and entering the premises at 22:14 IST.",
    ),
    (
        "Amit Verma", "ACC-1001",
        RelationshipType.SENT_MONEY_TO,
        "Bank statement extract shows NEFT transfer of INR 5,00,000 from "
        "Amit Verma's personal account to ACC-1001 on 2024-04-10, reference NEFT24100007.",
    ),
    (
        "OD-02-AB-1234", "Bhubaneswar",
        RelationshipType.LOCATED_AT,
        "NH-16 toll plaza RFID log recorded vehicle OD-02-AB-1234 passing Bhubaneswar "
        "entry point on 2024-04-03 at 19:42 IST, consistent with CCTV sighting at warehouse.",
    ),
    (
        "Amit Verma", "Eastern Logistics Ltd",
        RelationshipType.WORKS_FOR,
        "Employment verification letter from Eastern Logistics Ltd HR department confirms "
        "Amit Verma holds the position of Senior Logistics Coordinator (employee ID EL-4421).",
    ),
]


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _get_or_create_entity(db: Session, etype: EntityType, name: str) -> tuple[Entity, bool]:
    entity = db.scalar(
        select(Entity).where(Entity.type == etype, Entity.canonical_name == name)
    )
    if entity:
        return entity, False
    entity = Entity(type=etype, canonical_name=name)
    db.add(entity)
    db.flush()
    return entity, True


def _get_or_create_link(db: Session, entity_id: uuid.UUID, case_id: uuid.UUID) -> bool:
    link = db.scalar(
        select(EntityCaseLink).where(
            EntityCaseLink.entity_id == entity_id,
            EntityCaseLink.case_id == case_id,
        )
    )
    if link:
        return False
    db.add(EntityCaseLink(entity_id=entity_id, case_id=case_id))
    db.flush()
    return True


def _occ_id(src_id: uuid.UUID, tgt_id: uuid.UUID, rel_type: RelationshipType) -> str:
    """Deterministic occurrence ID — same inputs always yield same string."""
    key = f"SEED|{src_id}|{tgt_id}|{rel_type.name}"
    return hashlib.sha256(key.encode()).hexdigest()[:48]


def _get_or_create_relationship(
    db: Session,
    *,
    case_id: uuid.UUID,
    source: Entity,
    target: Entity,
    rel_type: RelationshipType,
    doc_id: uuid.UUID,
    snippet: str,
) -> tuple[RelationshipStaging, bool]:
    occ_id = _occ_id(source.id, target.id, rel_type)
    rel = db.scalar(
        select(RelationshipStaging).where(
            RelationshipStaging.source_document_id == doc_id,
            RelationshipStaging.source_occurrence_id == occ_id,
        )
    )
    if rel:
        return rel, False
    rel = RelationshipStaging(
        source_occurrence_id=occ_id,
        source_entity_id=source.id,
        target_entity_id=target.id,
        relationship_type=rel_type,
        confidence=0.95,
        status=RelationshipStatus.CONFIRMED,
        source_document_id=doc_id,
        source_record_id=None,
        evidence_snippet=snippet,
        extracted_at=datetime.now(timezone.utc),
        case_id=case_id,
    )
    db.add(rel)
    db.flush()
    return rel, True


# ─── Main ─────────────────────────────────────────────────────────────────────


def main() -> None:
    db = SessionLocal()
    try:
        # 1. Resolve dev user
        user = db.scalar(select(User).where(User.email == DEV_USER_EMAIL))
        if user is None:
            print(f"ERROR: user {DEV_USER_EMAIL!r} not found — run the user creation script first.")
            sys.exit(1)

        # 2. Resolve case
        case = db.scalar(select(Case).where(Case.case_number == TARGET_CASE_NUMBER))
        if case is None:
            print(f"ERROR: case {TARGET_CASE_NUMBER!r} not found — create it in the database first.")
            sys.exit(1)

        # 3. Synthetic source document (idempotent by filename+case)
        doc = db.scalar(
            select(Document).where(
                Document.case_id == case.id,
                Document.filename == SEED_DOCUMENT_FILENAME,
            )
        )
        doc_created = False
        if doc is None:
            h = hashlib.sha256(SEED_DOCUMENT_FILENAME.encode()).hexdigest()
            doc = Document(
                case_id=case.id,
                filename=SEED_DOCUMENT_FILENAME,
                sha256_hash=h,
                uploaded_by=user.id,
            )
            db.add(doc)
            db.flush()
            doc_created = True

        # 4. Entities
        entity_map: dict[str, Entity] = {}
        entities_created = 0
        links_created = 0
        for etype, ename in ENTITIES_SPEC:
            entity, created = _get_or_create_entity(db, etype, ename)
            entity_map[ename] = entity
            if created:
                entities_created += 1
            if _get_or_create_link(db, entity.id, case.id):
                links_created += 1

        # 5. Relationships
        rel_list: list[RelationshipStaging] = []
        rels_created = 0
        for src_name, tgt_name, rtype, snippet in RELATIONSHIPS_SPEC:
            rel, created = _get_or_create_relationship(
                db,
                case_id=case.id,
                source=entity_map[src_name],
                target=entity_map[tgt_name],
                rel_type=rtype,
                doc_id=doc.id,
                snippet=snippet,
            )
            rel_list.append(rel)
            if created:
                rels_created += 1

        db.commit()

        # 6. Neo4j projection (uses existing project_case_graph)
        neo4j_result = project_case_graph(case.id, db)

        # ─── Report ───────────────────────────────────────────────────────────
        print()
        print("=" * 60)
        print("  CrimeLens · Development Seed Report")
        print("=" * 60)
        print(f"  Case Number       : {case.case_number}")
        print(f"  Case ID           : {case.id}")
        print(f"  Document          : {SEED_DOCUMENT_FILENAME}")
        print(f"  Document ID       : {doc.id}  {'[NEW]' if doc_created else '[reused]'}")
        print()
        print(f"  Entities          : {len(entity_map)} total  "
              f"({entities_created} created, {len(entity_map)-entities_created} reused)")
        for ename, e in entity_map.items():
            print(f"    {e.id}  {e.type.name:<14}  {e.canonical_name}")
        print()
        print(f"  Relationships     : {len(rel_list)} total  "
              f"({rels_created} created, {len(rel_list)-rels_created} reused)")
        for r in rel_list:
            src = next(e for e in entity_map.values() if e.id == r.source_entity_id)
            tgt = next(e for e in entity_map.values() if e.id == r.target_entity_id)
            print(f"    {r.id}  {src.canonical_name}  --{r.relationship_type.name}-->  {tgt.canonical_name}")
        print()
        print("  Neo4j Projection  :")
        for k, v in neo4j_result.items():
            print(f"    {k:<30}: {v}")
        print("=" * 60)
        print("  Seed complete. Run the script again to verify idempotency.")
        print("=" * 60)
        print()

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
