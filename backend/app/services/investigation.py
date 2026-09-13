"""Case-scoped shortest-path lookup on the derived Neo4j graph.

PostgreSQL remains source of truth for authorization and entity membership.
Neo4j is queried only after both endpoints are confirmed in the requested case.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.graph.driver import get_driver
from app.graph.schema import RELATIONSHIP_TYPES
from app.models.entity import Entity, EntityCaseLink
from app.models.enums import EntityType, RelationshipStatus, RelationshipType
from app.schemas.investigation import (
    InvestigationPathNode,
    InvestigationPathRelationship,
    InvestigationPathResult,
)

MAX_HOPS = 5
DEFAULT_HOPS = 3
ALLOWED_REL_TYPES = list(RELATIONSHIP_TYPES)


class InvalidHopLimitError(Exception):
    """Client requested a hop limit outside the server-enforced range."""


class EntityNotInCaseError(Exception):
    """Entity is missing or is not linked to the authorized case."""


def bounded_max_hops(max_hops: int) -> int:
    if type(max_hops) is not int or max_hops < 1 or max_hops > MAX_HOPS:
        raise InvalidHopLimitError()
    return max_hops


def _shortest_path_cypher(hops: int) -> str:
    """Variable-length bound is interpolated only after bounded_max_hops() (1..5)."""
    hops = bounded_max_hops(hops)
    return (
        "MATCH (source {entity_id: $source_id}) "
        "MATCH (target {entity_id: $target_id}) "
        "MATCH path = (source)-[r WHERE r.case_id = $case_id "
        "AND type(r) IN $allowed_types]-"
        f"{{1,{hops}}}"
        "(target) "
        "WITH path, length(path) AS hop_count "
        "ORDER BY hop_count ASC, "
        "reduce(acc = '', rel IN relationships(path) | acc + '|' + rel.relationship_id) ASC "
        "LIMIT 1 "
        "RETURN hop_count AS hop_count, "
        "[n IN nodes(path) | n.entity_id] AS entity_ids, "
        "[rel IN relationships(path) | { "
        "  relationship_id: rel.relationship_id, "
        "  relationship: type(rel), "
        "  confidence: rel.confidence, "
        "  status: rel.status, "
        "  source_document_id: rel.source_document_id, "
        "  evidence_snippet: rel.evidence_snippet, "
        "  case_id: rel.case_id "
        "}] AS relationships"
    )


def require_entity_in_case(
    session: Session, entity_id: uuid.UUID, case_id: uuid.UUID
) -> Entity:
    entity = session.get(Entity, entity_id)
    if entity is None:
        raise EntityNotInCaseError()
    link = session.scalar(
        select(EntityCaseLink).where(
            EntityCaseLink.entity_id == entity_id,
            EntityCaseLink.case_id == case_id,
        )
    )
    if link is None:
        raise EntityNotInCaseError()
    return entity


def _empty_result(
    *,
    source_entity_id: uuid.UUID,
    target_entity_id: uuid.UUID,
    case_id: uuid.UUID,
) -> InvestigationPathResult:
    return InvestigationPathResult(
        source_entity_id=source_entity_id,
        target_entity_id=target_entity_id,
        case_id=case_id,
        found=False,
        hop_count=None,
        nodes=[],
        relationships=[],
    )


def _same_entity_result(entity: Entity, case_id: uuid.UUID) -> InvestigationPathResult:
    return InvestigationPathResult(
        source_entity_id=entity.id,
        target_entity_id=entity.id,
        case_id=case_id,
        found=True,
        hop_count=0,
        nodes=[
            InvestigationPathNode(
                entity_id=entity.id,
                type=entity.type,
                name=entity.canonical_name,
            )
        ],
        relationships=[],
    )


def _hydrate_nodes(
    session: Session, entity_ids: list[uuid.UUID]
) -> list[InvestigationPathNode] | None:
    rows = {
        row.id: row
        for row in session.scalars(select(Entity).where(Entity.id.in_(entity_ids))).all()
    }
    nodes: list[InvestigationPathNode] = []
    for entity_id in entity_ids:
        entity = rows.get(entity_id)
        if entity is None:
            return None
        nodes.append(
            InvestigationPathNode(
                entity_id=entity.id,
                type=entity.type if isinstance(entity.type, EntityType) else EntityType(entity.type),
                name=entity.canonical_name,
            )
        )
    return nodes


def _parse_relationships(raw_rows: list[dict]) -> list[InvestigationPathRelationship] | None:
    parsed: list[InvestigationPathRelationship] = []
    for row in raw_rows:
        rel_type = row.get("relationship")
        if rel_type not in ALLOWED_REL_TYPES:
            return None
        rel_id = row.get("relationship_id")
        if not rel_id:
            return None
        try:
            status = RelationshipStatus(str(row.get("status")))
        except ValueError:
            return None
        confidence = row.get("confidence")
        if confidence is None:
            return None
        parsed.append(
            InvestigationPathRelationship(
                relationship_id=uuid.UUID(str(rel_id)),
                relationship=RelationshipType(rel_type),
                confidence=float(confidence),
                status=status,
                source_document_id=(
                    uuid.UUID(str(row["source_document_id"]))
                    if row.get("source_document_id")
                    else None
                ),
                evidence_snippet=row.get("evidence_snippet"),
                case_id=uuid.UUID(str(row["case_id"])) if row.get("case_id") else None,
            )
        )
    return parsed


def find_shortest_path(
    session: Session,
    *,
    case_id: uuid.UUID,
    source_entity_id: uuid.UUID,
    target_entity_id: uuid.UUID,
    max_hops: int = DEFAULT_HOPS,
    driver=None,
) -> InvestigationPathResult:
    hops = bounded_max_hops(max_hops)
    source = require_entity_in_case(session, source_entity_id, case_id)
    target = require_entity_in_case(session, target_entity_id, case_id)
    if source_entity_id == target_entity_id:
        return _same_entity_result(source, case_id)

    neo = driver or get_driver()
    with neo.session() as neo_session:
        record = neo_session.run(
            _shortest_path_cypher(hops),
            source_id=str(source_entity_id),
            target_id=str(target_entity_id),
            case_id=str(case_id),
            allowed_types=ALLOWED_REL_TYPES,
        ).single()
    if record is None:
        return _empty_result(
            source_entity_id=source_entity_id,
            target_entity_id=target_entity_id,
            case_id=case_id,
        )

    hop_count = int(record["hop_count"])
    if hop_count > hops or hop_count > MAX_HOPS:
        return _empty_result(
            source_entity_id=source_entity_id,
            target_entity_id=target_entity_id,
            case_id=case_id,
        )
    entity_ids = [uuid.UUID(str(value)) for value in record["entity_ids"]]
    nodes = _hydrate_nodes(session, entity_ids)
    relationships = _parse_relationships(list(record["relationships"] or []))
    if nodes is None or relationships is None:
        return _empty_result(
            source_entity_id=source_entity_id,
            target_entity_id=target_entity_id,
            case_id=case_id,
        )
    return InvestigationPathResult(
        source_entity_id=source.id,
        target_entity_id=target.id,
        case_id=case_id,
        found=True,
        hop_count=hop_count,
        nodes=nodes,
        relationships=relationships,
    )
