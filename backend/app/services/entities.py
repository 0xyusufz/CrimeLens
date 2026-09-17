"""Entity details and 1-hop connections. PostgreSQL authorizes; Neo4j is derived."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.graph.driver import get_driver
from app.graph.schema import RELATIONSHIP_TYPES
from app.models.case import Case
from app.models.document import Document
from app.models.entity import Entity, EntityCaseLink, EntityMention
from app.models.enums import EntityType, RelationshipStatus, RelationshipType
from app.models.user import User
from app.schemas.entity import (
    EntityAttributes,
    EntityCaseRef,
    EntityConnection,
    EntityConnectionsResult,
    EntityRead,
)
from app.services.access import user_can_access_case

ALLOWED_REL_TYPES = list(RELATIONSHIP_TYPES)
DEFAULT_CONNECTION_LIMIT = 100
MAX_CONNECTION_LIMIT = 100


class EntityNotFoundError(Exception):
    """Entity is missing or is not linked to any case."""


class EntityForbiddenError(Exception):
    """Entity exists but is only linked to cases the user cannot access."""


class EntityNotInCaseError(Exception):
    """Entity is not associated with the requested case."""


class InvalidConnectionLimitError(Exception):
    pass


def bounded_connection_limit(limit: int) -> int:
    if type(limit) is not int or limit < 1 or limit > MAX_CONNECTION_LIMIT:
        raise InvalidConnectionLimitError()
    return limit


def _entity_type(value) -> EntityType:
    return value if isinstance(value, EntityType) else EntityType(value)


def authorized_cases_for_entity(
    session: Session, user: User, entity_id: uuid.UUID
) -> list[Case]:
    links = list(
        session.scalars(
            select(EntityCaseLink).where(EntityCaseLink.entity_id == entity_id)
        ).all()
    )
    cases: list[Case] = []
    for link in links:
        if not user_can_access_case(session, user, link.case_id):
            continue
        case = session.get(Case, link.case_id)
        if case is not None:
            cases.append(case)
    cases.sort(key=lambda row: (row.created_at, row.id), reverse=True)
    return cases


def _case_link_count(session: Session, entity_id: uuid.UUID) -> int:
    links = session.scalars(
        select(EntityCaseLink).where(EntityCaseLink.entity_id == entity_id)
    ).all()
    return len(list(links))


def get_entity_for_user(
    session: Session, user: User, entity_id: uuid.UUID
) -> EntityRead:
    entity = session.get(Entity, entity_id)
    if entity is None:
        raise EntityNotFoundError()
    cases = authorized_cases_for_entity(session, user, entity_id)
    if not cases:
        if _case_link_count(session, entity_id) == 0:
            raise EntityNotFoundError()
        raise EntityForbiddenError()
    # Collect mentions to extract aliases, evidence snippets, and source documents
    mentions = list(
        session.scalars(
            select(EntityMention).where(EntityMention.entity_id == entity_id)
        ).all()
    )
    aliases = sorted(
        {
            m.name.strip()
            for m in mentions
            if m.name and m.name.strip() and m.name.strip().casefold() != entity.canonical_name.casefold()
        }
    )
    evidence_snippets = [
        m.evidence_snippet.strip()
        for m in mentions
        if m.evidence_snippet and m.evidence_snippet.strip()
    ]
    doc_ids = {m.document_id for m in mentions if m.document_id}
    source_docs: list[str] = []
    if doc_ids:
        docs = session.scalars(select(Document).where(Document.id.in_(doc_ids))).all()
        source_docs = sorted({doc.filename for doc in docs if doc.filename})

    # Collect connected attributes (phones, locations, vehicles, orgs) from 1-hop connections
    phone_numbers: list[str] = []
    locations: list[str] = []
    vehicles: list[str] = []
    organizations: list[str] = []
    try:
        conns = list_entity_connections(session, user, entity_id, limit=50)
        for c in conns.connections:
            if c.type == EntityType.PHONE and c.name not in phone_numbers:
                phone_numbers.append(c.name)
            elif c.type == EntityType.LOCATION and c.name not in locations:
                locations.append(c.name)
            elif c.type == EntityType.VEHICLE and c.name not in vehicles:
                vehicles.append(c.name)
            elif c.type == EntityType.ORGANIZATION and c.name not in organizations:
                organizations.append(c.name)
    except Exception:
        pass

    attributes = EntityAttributes(
        aliases=aliases,
        phone_numbers=phone_numbers,
        locations=locations,
        vehicles=vehicles,
        organizations=organizations,
        occupations=[],
        evidence_snippets=evidence_snippets,
        source_documents=source_docs,
    )

    return EntityRead(
        id=entity.id,
        type=_entity_type(entity.type),
        canonical_name=entity.canonical_name,
        cases=[EntityCaseRef(case_id=case.id, case_number=case.case_number) for case in cases],
        attributes=attributes,
    )


def _hydrate_entities(
    session: Session, entity_ids: list[uuid.UUID]
) -> dict[uuid.UUID, Entity]:
    if not entity_ids:
        return {}
    rows = session.scalars(select(Entity).where(Entity.id.in_(entity_ids))).all()
    return {row.id: row for row in rows}


def list_entity_connections(
    session: Session,
    user: User,
    entity_id: uuid.UUID,
    *,
    case_id: uuid.UUID | None = None,
    limit: int = DEFAULT_CONNECTION_LIMIT,
    driver=None,
) -> EntityConnectionsResult:
    cap = bounded_connection_limit(limit)
    entity = session.get(Entity, entity_id)
    if entity is None:
        raise EntityNotFoundError()

    if case_id is not None:
        if not user_can_access_case(session, user, case_id):
            raise EntityForbiddenError()
        link = session.scalar(
            select(EntityCaseLink).where(
                EntityCaseLink.entity_id == entity_id,
                EntityCaseLink.case_id == case_id,
            )
        )
        if link is None:
            raise EntityNotInCaseError()
        case_ids = [case_id]
    else:
        case_ids = [case.id for case in authorized_cases_for_entity(session, user, entity_id)]
        if not case_ids:
            if _case_link_count(session, entity_id) == 0:
                raise EntityNotFoundError()
            raise EntityForbiddenError()

    cypher = (
        "MATCH (source {entity_id: $entity_id})-[r WHERE r.case_id IN $case_ids "
        "AND type(r) IN $allowed_types]-(other) "
        "WHERE other.entity_id IS NOT NULL "
        "RETURN other.entity_id AS entity_id, "
        "type(r) AS relationship, "
        "r.relationship_id AS relationship_id, "
        "r.confidence AS confidence, "
        "r.status AS status, "
        "r.source_document_id AS source_document_id, "
        "r.evidence_snippet AS evidence_snippet, "
        "r.case_id AS case_id "
        "ORDER BY r.relationship_id ASC "
        "LIMIT $limit"
    )
    neo = driver or get_driver()
    with neo.session() as neo_session:
        rows = list(
            neo_session.run(
                cypher,
                entity_id=str(entity_id),
                case_ids=[str(value) for value in case_ids],
                allowed_types=ALLOWED_REL_TYPES,
                limit=cap,
            )
        )

    neighbor_ids = []
    parsed_rows: list[dict] = []
    for row in rows:
        try:
            neighbor_id = uuid.UUID(str(row["entity_id"]))
            rel_id = uuid.UUID(str(row["relationship_id"]))
        except (ValueError, TypeError, KeyError):
            continue
        rel_type = row.get("relationship")
        if rel_type not in ALLOWED_REL_TYPES:
            continue
        try:
            status = RelationshipStatus(str(row.get("status")))
        except ValueError:
            continue
        if row.get("confidence") is None:
            continue
        neighbor_ids.append(neighbor_id)
        parsed_rows.append(
            {
                "neighbor_id": neighbor_id,
                "relationship_id": rel_id,
                "relationship": RelationshipType(rel_type),
                "confidence": float(row["confidence"]),
                "status": status,
                "source_document_id": row.get("source_document_id"),
                "evidence_snippet": row.get("evidence_snippet"),
                "case_id": row.get("case_id"),
            }
        )

    entities = _hydrate_entities(session, neighbor_ids)
    connections: list[EntityConnection] = []
    for item in parsed_rows:
        neighbor = entities.get(item["neighbor_id"])
        if neighbor is None:
            continue
        source_document_id = item["source_document_id"]
        case_value = item["case_id"]
        connections.append(
            EntityConnection(
                entity_id=neighbor.id,
                type=_entity_type(neighbor.type),
                name=neighbor.canonical_name,
                relationship=item["relationship"],
                relationship_id=item["relationship_id"],
                confidence=item["confidence"],
                status=item["status"],
                source_document_id=(
                    uuid.UUID(str(source_document_id)) if source_document_id else None
                ),
                evidence_snippet=item["evidence_snippet"],
                case_id=uuid.UUID(str(case_value)) if case_value else None,
            )
        )
    return EntityConnectionsResult(entity_id=entity.id, connections=connections)
