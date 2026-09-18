from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.graph.projection import project_case_graph
from app.ml.adapter import (
    MlContractError,
    MlDocumentProcessor,
    collect_person_b_intelligence,
    run_document_processor,
)
from app.models.document import Document, StructuredRecord
from app.models.entity import Entity, EntityCaseLink, EntityMention
from app.models.enums import EntityType, RelationshipStatus, RelationshipType
from app.models.relationship import RelationshipStaging
from app.schemas.processing import DocumentProcessResult
from app.services.csv_ingest import CsvParseError, parse_csv_bytes, upsert_structured_records
from app.services.documents import get_document, read_stored_document_bytes
from app.services.insights import (
    IntelligenceContractError,
    persist_leads,
    persist_patterns,
    validate_leads,
    validate_patterns,
)
from shared.schemas import ExtractionEnvelope
from shared.schemas import EntityMention as MlEntityMention
from shared.schemas import Relationship as MlRelationship

from collections import defaultdict

from ml.resolution.resolver import (
    extract_alias_names,
    normalize_location,
    normalize_org,
    normalize_person_name,
)

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


def are_entities_equivalent(
    type_a: EntityType,
    name_a: str,
    type_b: EntityType,
    name_b: str,
    existing_case_persons: list[str] | None = None,
) -> tuple[bool, str]:
    """Check if two entity names represent the same real-world entity in a case.

    Returns (is_match, canonical_name_to_use).
    """
    if type_a != type_b:
        return False, name_a

    if type_a in STRONG_IDENTIFIER_TYPES:
        norm_a = normalize_identifier(type_a, name_a)
        norm_b = normalize_identifier(type_b, name_b)
        if norm_a == norm_b:
            return True, norm_a
        return False, name_a

    if type_a == EntityType.LOCATION:
        l_a = normalize_location(name_a)
        l_b = normalize_location(name_b)
        if l_a == l_b:
            best = name_a if len(name_a) >= len(name_b) else name_b
            return True, best
        return False, name_a

    if type_a == EntityType.ORGANIZATION:
        o_a = normalize_org(name_a)
        o_b = normalize_org(name_b)
        if o_a == o_b:
            best = name_a if len(name_a) >= len(name_b) else name_b
            return True, best
        # Acronym check (e.g. CBI vs Central Bureau of Investigation)
        words_a = o_a.split()
        words_b = o_b.split()
        acr_a = "".join(w[0] for w in words_a if w)
        acr_b = "".join(w[0] for w in words_b if w)
        if (len(acr_a) >= 2 and (acr_a == o_b or acr_a == acr_b)) or (len(acr_b) >= 2 and (acr_b == o_a)):
            best = name_a if len(words_a) >= len(words_b) else name_b
            return True, best
        return False, name_a

    if type_a == EntityType.EVENT:
        if name_a.strip().lower() == name_b.strip().lower():
            return True, name_a
        return False, name_a

    if type_a == EntityType.PERSON:
        # 1. Alias match (e.g. "Sanju @ Sanjib Sahu" vs "Sanjib Sahu")
        aliases_a = extract_alias_names(name_a)
        aliases_b = extract_alias_names(name_b)
        if len(aliases_a) > 1 or len(aliases_b) > 1:
            for a in aliases_a:
                p_a = normalize_person_name(a)
                for b in aliases_b:
                    p_b = normalize_person_name(b)
                    if p_a == p_b and p_a:
                        best = name_a if len(name_a) >= len(name_b) else name_b
                        return True, best

        p_a = normalize_person_name(name_a)
        p_b = normalize_person_name(name_b)
        if not p_a or not p_b:
            return False, name_a

        # 2. Exact normalized match (e.g. "Dr. Punjilal Meher" vs "Punjilal Meher")
        if p_a == p_b:
            best = p_a.title()
            return True, best

        w_a = p_a.split()
        w_b = p_b.split()

        # STRICT GUARDRAIL: If both have first names and they differ, NEVER MATCH!
        # (e.g. "Soumya Sekhar Sahu" vs "Sanjib Sahu")
        if w_a[0] != w_b[0]:
            return False, name_a

        # 3. Multi-word name prefix match (e.g. "Sushant Singh" vs "Sushant Singh Rajput")
        if len(w_a) >= 2 and len(w_b) >= 2:
            shorter, longer = (w_a, w_b) if len(w_a) < len(w_b) else (w_b, w_a)
            if longer[:len(shorter)] == shorter:
                best = name_a if len(w_a) >= len(w_b) else name_b
                return True, best

        # 4. Single-word name vs multi-word name (e.g. "Punjilal" vs "Punjilal Meher")
        if (len(w_a) == 1 and len(w_b) >= 2) or (len(w_b) == 1 and len(w_a) >= 2):
            single_w = w_a[0] if len(w_a) == 1 else w_b[0]
            full_name = name_b if len(w_a) == 1 else name_a
            if existing_case_persons:
                matching_persons = [
                    p for p in existing_case_persons
                    if normalize_person_name(p).split() and normalize_person_name(p).split()[0] == single_w
                ]
                distinct_matches = {
                    normalize_person_name(p) for p in matching_persons
                    if len(normalize_person_name(p).split()) >= 2
                }
                if len(distinct_matches) > 1:
                    return False, name_a
            return True, full_name

    return False, name_a


def resolve_canonical_entity(
    session: Session,
    *,
    case_id: uuid.UUID | None = None,
    entity_type: EntityType,
    name: str,
    existing_entity_id: uuid.UUID | None,
) -> uuid.UUID:
    """Reuse an existing mention's entity, or resolve against existing case entities.

    Entities in the same case sharing name, aliases, or normalized attributes
    are resolved into a single canonical entity.
    """
    if existing_entity_id is not None:
        return existing_entity_id

    # 1. Check against existing entities linked to this case
    if case_id is not None:
        case_entities = (
            session.query(Entity)
            .join(EntityCaseLink, EntityCaseLink.entity_id == Entity.id)
            .filter(EntityCaseLink.case_id == case_id, Entity.type == entity_type)
            .all()
        )
        existing_persons = [e.canonical_name for e in case_entities] if entity_type == EntityType.PERSON else None
        for existing in case_entities:
            is_match, best_name = are_entities_equivalent(
                entity_type, name, existing.type, existing.canonical_name, existing_persons
            )
            if is_match:
                if best_name and best_name != existing.canonical_name and len(best_name) > len(existing.canonical_name):
                    existing.canonical_name = best_name
                return existing.id

    # 2. Check strong identifier matches globally across database
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

    # 3. Mint a new canonical entity
    entity = Entity(type=entity_type, canonical_name=canonical_name)
    session.add(entity)
    session.flush()
    return entity.id


def consolidate_case_entities(session: Session, case_id: uuid.UUID) -> dict[str, int]:
    """Merge duplicate entities and normalize relationships within a case."""
    links = session.query(EntityCaseLink).filter(EntityCaseLink.case_id == case_id).all()
    entity_ids = [l.entity_id for l in links]
    if not entity_ids:
        return {"entities_merged": 0}

    entities = session.query(Entity).filter(Entity.id.in_(entity_ids)).all()
    by_type: dict[EntityType, list[Entity]] = defaultdict(list)
    for e in entities:
        by_type[e.type].append(e)

    merged_count = 0

    for etype, ent_list in by_type.items():
        if len(ent_list) < 2:
            continue

        existing_person_names = [e.canonical_name for e in ent_list] if etype == EntityType.PERSON else None

        parent: dict[uuid.UUID, uuid.UUID] = {e.id: e.id for e in ent_list}
        best_name_map: dict[uuid.UUID, str] = {e.id: e.canonical_name for e in ent_list}

        def find(i):
            if parent[i] == i:
                return i
            parent[i] = find(parent[i])
            return parent[i]

        def union(i, j, chosen_name):
            root_i = find(i)
            root_j = find(j)
            if root_i != root_j:
                parent[root_j] = root_i
                best_name_map[root_i] = chosen_name

        n = len(ent_list)
        for i in range(n):
            for j in range(i + 1, n):
                e1 = ent_list[i]
                e2 = ent_list[j]
                is_match, best_name = are_entities_equivalent(
                    e1.type, e1.canonical_name, e2.type, e2.canonical_name, existing_person_names
                )
                if is_match:
                    union(e1.id, e2.id, best_name)

        clusters: dict[uuid.UUID, list[Entity]] = defaultdict(list)
        for e in ent_list:
            clusters[find(e.id)].append(e)

        for root_id, members in clusters.items():
            if len(members) <= 1:
                continue

            canonical_ent = next((m for m in members if m.id == root_id), members[0])
            chosen_canonical_name = best_name_map.get(root_id, canonical_ent.canonical_name)
            canonical_ent.canonical_name = chosen_canonical_name

            for dup in members:
                if dup.id == canonical_ent.id:
                    continue

                session.query(EntityMention).filter(EntityMention.entity_id == dup.id).update(
                    {"entity_id": canonical_ent.id}, synchronize_session=False
                )

                session.query(RelationshipStaging).filter(
                    RelationshipStaging.case_id == case_id,
                    RelationshipStaging.source_entity_id == dup.id,
                ).update({"source_entity_id": canonical_ent.id}, synchronize_session=False)

                session.query(RelationshipStaging).filter(
                    RelationshipStaging.case_id == case_id,
                    RelationshipStaging.target_entity_id == dup.id,
                ).update({"target_entity_id": canonical_ent.id}, synchronize_session=False)

                session.query(EntityCaseLink).filter(
                    EntityCaseLink.case_id == case_id, EntityCaseLink.entity_id == dup.id
                ).delete(synchronize_session=False)

                other_links = session.query(EntityCaseLink).filter(EntityCaseLink.entity_id == dup.id).count()
                if other_links == 0:
                    session.query(Entity).filter(Entity.id == dup.id).delete(synchronize_session=False)

                merged_count += 1

    # Remove any self-loops created by merging
    session.query(RelationshipStaging).filter(
        RelationshipStaging.case_id == case_id,
        RelationshipStaging.source_entity_id == RelationshipStaging.target_entity_id,
    ).delete(synchronize_session=False)

    # Deduplicate identical relationships
    case_rels = (
        session.query(RelationshipStaging)
        .filter(RelationshipStaging.case_id == case_id)
        .order_by(RelationshipStaging.confidence.desc())
        .all()
    )
    seen_rel_signatures = set()
    for rel in case_rels:
        sig = (rel.source_entity_id, rel.target_entity_id, rel.relationship_type)
        if sig in seen_rel_signatures:
            session.delete(rel)
        else:
            seen_rel_signatures.add(sig)

    session.flush()
    return {"entities_merged": merged_count}


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
        case_id=document.case_id,
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


def _is_csv(filename: str) -> bool:
    return Path(filename).suffix.lower() == ".csv"


def process_uploaded_document(
    session: Session,
    document_id: uuid.UUID,
    processor: MlDocumentProcessor,
    driver=None,
) -> DocumentProcessResult:
    document = get_document(session, document_id)
    data = read_stored_document_bytes(document.id)

    # ── CSV ingestion: parse bytes → StructuredRecord rows BEFORE ML call ────
    # CsvParseError propagates up; the router maps it to HTTP 422.
    # TXT and PDF documents bypass this block entirely.
    if _is_csv(document.filename):
        record_type, payloads = parse_csv_bytes(data)
        # Persist rows now so collect_person_b_intelligence picks them up below.
        try:
            upsert_structured_records(
                session,
                document_id=document.id,
                case_id=document.case_id,
                record_type=record_type,
                payloads=payloads,
            )
            session.commit()
        except Exception:
            session.rollback()
            raise

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
        try:
            raw_patterns, raw_leads = collect_person_b_intelligence(
                processor, data, document.filename, document.id,
                session=session,
            )
            persist_patterns(
                session,
                case_id=document.case_id,
                patterns=validate_patterns(raw_patterns),
                source_document_id=document.id,
            )
            persist_leads(
                session,
                case_id=document.case_id,
                leads=validate_leads(raw_leads),
                source_document_id=document.id,
            )
        except (IntelligenceContractError, MlContractError):
            # Pattern/lead contract failure must not undo entities/relationships.
            pass

        consolidate_case_entities(session, document.case_id)
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
