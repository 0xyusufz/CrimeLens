from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.graph.projection import project_case_graph
from app.ml.adapter import MlDocumentProcessor, run_document_processor
from app.models.document import Document, StructuredRecord
from app.models.entity import Entity, EntityCaseLink, EntityMention
from app.models.enums import EntityType, RelationshipStatus, RelationshipType
from app.models.relationship import RelationshipStaging
from app.schemas.processing import DocumentProcessResult
from app.services.documents import get_document, read_stored_document_bytes
from shared.schemas import ExtractionEnvelope
from shared.schemas import EntityMention as MlEntityMention
from shared.schemas import Relationship as MlRelationship

STRONG_IDENTIFIER_TYPES = frozenset(
    {
        EntityType.PHONE,
        EntityType.BANK_ACCOUNT,
        EntityType.VEHICLE,
    }
)


class GraphProjectionError(Exception):
    pass


def _aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def normalize_identifier(entity_type: EntityType, name: str) -> str:
    trimmed = name.strip()
    if entity_type == EntityType.PHONE:
        compact = "".join(ch for ch in trimmed if ch.isdigit() or ch == "+")
        return compact or trimmed
    if entity_type == EntityType.BANK_ACCOUNT:
        return "".join(trimmed.split())
    if entity_type == EntityType.VEHICLE:
        return "".join(trimmed.split()).upper()
    return trimmed


def _db_entity_type(ml_type) -> EntityType:
    return EntityType(ml_type.value if hasattr(ml_type, "value") else str(ml_type))


def _db_rel_type(ml_type) -> RelationshipType:
    return RelationshipType(ml_type.value if hasattr(ml_type, "value") else str(ml_type))


def _db_rel_status(ml_status) -> RelationshipStatus:
    return RelationshipStatus(
        ml_status.value if hasattr(ml_status, "value") else str(ml_status)
    )


def resolve_canonical_entity(
    session: Session,
    *,
    entity_type: EntityType,
    name: str,
    existing_entity_id: uuid.UUID | None,
) -> uuid.UUID:
    """Reuse an existing mention's entity, or a strong-identifier match.

    Name-only types always mint a new canonical UUID unless this mention
    already has one (idempotent reprocess). Never fuzzy-merge names.
    """
    if existing_entity_id is not None:
        return existing_entity_id

    canonical_name = normalize_identifier(entity_type, name)
    if entity_type in STRONG_IDENTIFIER_TYPES:
        found = session.scalar(
            select(Entity)
            .where(Entity.type == entity_type, Entity.canonical_name == canonical_name)
            .order_by(Entity.created_at.asc(), Entity.id.asc())
            .limit(1)
        )
        if found is not None:
            return found.id

    entity = Entity(type=entity_type, canonical_name=canonical_name)
    session.add(entity)
    session.flush()
    return entity.id


def _ensure_case_link(session: Session, entity_id: uuid.UUID, case_id: uuid.UUID) -> None:
    existing = session.scalar(
        select(EntityCaseLink).where(
            EntityCaseLink.entity_id == entity_id,
            EntityCaseLink.case_id == case_id,
        )
    )
    if existing is None:
        session.add(EntityCaseLink(entity_id=entity_id, case_id=case_id))


def _upsert_mention(
    session: Session,
    document: Document,
    mention: MlEntityMention,
) -> uuid.UUID:
    entity_type = _db_entity_type(mention.type)
    row = session.scalar(
        select(EntityMention).where(
            EntityMention.document_id == document.id,
            EntityMention.mention_id == mention.id,
        )
    )
    entity_id = resolve_canonical_entity(
        session,
        entity_type=entity_type,
        name=mention.name,
        existing_entity_id=row.entity_id if row is not None else None,
    )
    _ensure_case_link(session, entity_id, document.case_id)
    if row is None:
        session.add(
            EntityMention(
                document_id=document.id,
                entity_id=entity_id,
                mention_id=mention.id,
                entity_type=entity_type,
                name=mention.name,
                confidence=mention.confidence,
            )
        )
    else:
        row.entity_id = entity_id
        row.entity_type = entity_type
        row.name = mention.name
        row.confidence = mention.confidence
    return entity_id


def _parse_record_id(session: Session, raw: str | None) -> uuid.UUID | None:
    if not raw:
        return None
    try:
        record_id = uuid.UUID(raw)
    except ValueError:
        return None
    record = session.get(StructuredRecord, record_id)
    if record is None:
        return None
    return record.id


def _upsert_relationship(
    session: Session,
    document: Document,
    rel: MlRelationship,
    mention_to_entity: dict[str, uuid.UUID | None],
) -> RelationshipStaging:
    source_id = mention_to_entity.get(rel.source_entity_id)
    target_id = mention_to_entity.get(rel.target_entity_id)
    record_id = _parse_record_id(session, rel.source_record_id)
    extracted_at = _aware(rel.extracted_at)
    rel_type = _db_rel_type(rel.relationship)
    rel_status = _db_rel_status(rel.status)

    row = session.scalar(
        select(RelationshipStaging).where(
            RelationshipStaging.source_document_id == document.id,
            RelationshipStaging.source_occurrence_id == rel.id,
        )
    )
    if row is None:
        row = RelationshipStaging(
            source_occurrence_id=rel.id,
            source_entity_id=source_id,
            target_entity_id=target_id,
            relationship_type=rel_type,
            confidence=rel.confidence,
            status=rel_status,
            source_document_id=document.id,
            source_record_id=record_id,
            evidence_snippet=rel.evidence_snippet,
            extracted_at=extracted_at,
            case_id=document.case_id,
        )
        session.add(row)
    else:
        row.source_entity_id = source_id
        row.target_entity_id = target_id
        row.relationship_type = rel_type
        row.confidence = rel.confidence
        row.status = rel_status
        row.source_record_id = record_id
        row.evidence_snippet = rel.evidence_snippet
        row.extracted_at = extracted_at
        row.case_id = document.case_id
    return row


def persist_extraction(
    session: Session,
    document: Document,
    envelope: ExtractionEnvelope,
) -> tuple[list[RelationshipStaging], set[uuid.UUID]]:
    mention_to_entity: dict[str, uuid.UUID | None] = {}
    entity_ids: set[uuid.UUID] = set()
    for mention in envelope.entities:
        entity_id = _upsert_mention(session, document, mention)
        mention_to_entity[mention.id] = entity_id
        entity_ids.add(entity_id)
    session.flush()

    staged: list[RelationshipStaging] = []
    for rel in envelope.relationships:
        staged.append(_upsert_relationship(session, document, rel, mention_to_entity))
    session.flush()
    return staged, entity_ids


def process_uploaded_document(
    session: Session,
    document_id: uuid.UUID,
    processor: MlDocumentProcessor,
    driver=None,
) -> DocumentProcessResult:
    document = get_document(session, document_id)
    data = read_stored_document_bytes(document.id)
    envelope = run_document_processor(
        processor,
        data,
        document.filename,
        document.id,
    )
    try:
        staged, entity_ids = persist_extraction(session, document, envelope)
        unresolved = sum(
            1
            for row in staged
            if row.source_entity_id is None or row.target_entity_id is None
        )
        session.commit()
    except Exception:
        session.rollback()
        raise

    try:
        project_case_graph(document.case_id, session, driver=driver)
    except Exception as exc:
        raise GraphProjectionError("Graph projection failed.") from exc
    return DocumentProcessResult(
        document_id=document.id,
        case_id=document.case_id,
        entities_processed=len(entity_ids),
        mentions_persisted=len(envelope.entities),
        relationships_processed=len(envelope.relationships),
        relationships_persisted=len(staged),
        relationships_unresolved=unresolved,
    )
