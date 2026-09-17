"""Case-scoped subgraph for graph UI. Neo4j is derived; PostgreSQL hydrates nodes."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.graph.driver import get_driver
from app.graph.schema import RELATIONSHIP_TYPES
from app.models.entity import Entity, EntityCaseLink
from app.models.enums import EntityType, RelationshipStatus, RelationshipType
from app.schemas.entity import CaseGraphNode, CaseGraphRelationship, CaseGraphResult

ALLOWED_REL_TYPES = list(RELATIONSHIP_TYPES)
DEFAULT_GRAPH_LIMIT = 200
MAX_GRAPH_LIMIT = 500


class InvalidGraphLimitError(Exception):
    pass


class EntityNotInCaseError(Exception):
    pass


def bounded_graph_limit(limit: int) -> int:
    if type(limit) is not int or limit < 1 or limit > MAX_GRAPH_LIMIT:
        raise InvalidGraphLimitError()
    return limit


def _entity_type(value) -> EntityType:
    return value if isinstance(value, EntityType) else EntityType(value)


def _hydrate(session: Session, entity_ids: list[uuid.UUID]) -> dict[uuid.UUID, Entity]:
    unique = list(dict.fromkeys(entity_ids))
    if not unique:
        return {}
    rows = session.scalars(select(Entity).where(Entity.id.in_(unique))).all()
    return {row.id: row for row in rows}


def get_case_graph(
    session: Session,
    case_id: uuid.UUID,
    *,
    entity_id: uuid.UUID | None = None,
    limit: int = DEFAULT_GRAPH_LIMIT,
    driver=None,
    connected_only: bool = True,
) -> CaseGraphResult:
    cap = bounded_graph_limit(limit)
    if entity_id is not None:
        link = session.scalar(
            select(EntityCaseLink).where(
                EntityCaseLink.entity_id == entity_id,
                EntityCaseLink.case_id == case_id,
            )
        )
        if link is None or session.get(Entity, entity_id) is None:
            raise EntityNotInCaseError()
        cypher = (
            "MATCH (center {entity_id: $entity_id})-[r WHERE r.case_id = $case_id "
            "AND type(r) IN $allowed_types]-(other) "
            "WHERE other.entity_id IS NOT NULL "
            "RETURN startNode(r).entity_id AS source_entity_id, "
            "endNode(r).entity_id AS target_entity_id, "
            "type(r) AS relationship, "
            "r.relationship_id AS relationship_id, "
            "r.confidence AS confidence, "
            "r.status AS status, "
            "r.source_document_id AS source_document_id, "
            "r.evidence_snippet AS evidence_snippet "
            "ORDER BY r.relationship_id ASC "
            "LIMIT $fetch_limit"
        )
        params = {
            "entity_id": str(entity_id),
            "case_id": str(case_id),
            "allowed_types": ALLOWED_REL_TYPES,
            "fetch_limit": cap + 1,
        }
    else:
        cypher = (
            "MATCH (source)-[r WHERE r.case_id = $case_id "
            "AND type(r) IN $allowed_types]->(target) "
            "WHERE source.entity_id IS NOT NULL AND target.entity_id IS NOT NULL "
            "RETURN source.entity_id AS source_entity_id, "
            "target.entity_id AS target_entity_id, "
            "type(r) AS relationship, "
            "r.relationship_id AS relationship_id, "
            "r.confidence AS confidence, "
            "r.status AS status, "
            "r.source_document_id AS source_document_id, "
            "r.evidence_snippet AS evidence_snippet "
            "ORDER BY r.relationship_id ASC "
            "LIMIT $fetch_limit"
        )
        params = {
            "case_id": str(case_id),
            "allowed_types": ALLOWED_REL_TYPES,
            "fetch_limit": cap + 1,
        }

    neo = driver or get_driver()
    with neo.session() as neo_session:
        raw = list(neo_session.run(cypher, **params))

    truncated = len(raw) > cap
    raw = raw[:cap]
    relationships: list[CaseGraphRelationship] = []
    endpoint_ids: list[uuid.UUID] = []
    for row in raw:
        rel_type = row.get("relationship")
        if rel_type not in ALLOWED_REL_TYPES:
            continue
        try:
            status = RelationshipStatus(str(row.get("status")))
            source_id = uuid.UUID(str(row["source_entity_id"]))
            target_id = uuid.UUID(str(row["target_entity_id"]))
            rel_id = uuid.UUID(str(row["relationship_id"]))
        except (ValueError, TypeError, KeyError):
            continue
        if row.get("confidence") is None:
            continue
        source_document_id = row.get("source_document_id")
        relationships.append(
            CaseGraphRelationship(
                relationship_id=rel_id,
                source_entity_id=source_id,
                target_entity_id=target_id,
                relationship=RelationshipType(rel_type),
                confidence=float(row["confidence"]),
                status=status,
                source_document_id=(
                    uuid.UUID(str(source_document_id)) if source_document_id else None
                ),
                evidence_snippet=row.get("evidence_snippet"),
            )
        )
        endpoint_ids.extend([source_id, target_id])

    node_ids: list[uuid.UUID] = []
    if entity_id is not None:
        node_ids.append(entity_id)
        node_ids.extend(endpoint_ids)
    elif connected_only:
        # Connected-only rule: degree >= 1. Only entities participating in relationships appear.
        node_ids.extend(endpoint_ids)
    else:
        linked = list(
            session.scalars(
                select(EntityCaseLink.entity_id).where(EntityCaseLink.case_id == case_id)
            ).all()
        )
        node_ids.extend(linked)
        node_ids.extend(endpoint_ids)

    # Deduplicate node IDs while preserving deterministic order
    distinct_node_ids = list(dict.fromkeys(node_ids))
    entities = _hydrate(session, distinct_node_ids)
    nodes = [
        CaseGraphNode(
            entity_id=entity.id,
            type=_entity_type(entity.type),
            name=entity.canonical_name,
        )
        for entity in sorted(entities.values(), key=lambda row: str(row.id))
    ]
    return CaseGraphResult(
        case_id=case_id,
        nodes=nodes,
        relationships=relationships,
        truncated=truncated,
    )
