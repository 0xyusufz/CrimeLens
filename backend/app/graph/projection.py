"""Project PostgreSQL canonical data into Neo4j. Neo4j is derived, not source of truth."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.graph.driver import get_driver
from app.graph.schema import ENTITY_LABELS, RELATIONSHIP_TYPES, init_schema
from app.models import Case, Document, Entity, EntityCaseLink, RelationshipStaging
from app.models.enums import EntityType, RelationshipType

ENTITY_LABEL_MAP = {
    EntityType.PERSON: "Person",
    EntityType.PHONE: "Phone",
    EntityType.BANK_ACCOUNT: "BankAccount",
    EntityType.VEHICLE: "Vehicle",
    EntityType.ORGANIZATION: "Organization",
    EntityType.LOCATION: "Location",
    EntityType.EVENT: "Event",
}

ALLOWED_LABELS = frozenset(ENTITY_LABELS)
ALLOWED_REL_TYPES = frozenset(RELATIONSHIP_TYPES)


def _id(value: UUID | str | None) -> str | None:
    if value is None:
        return None
    return str(value)


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()


def _rel_type_name(rel_type: RelationshipType | str) -> str:
    name = rel_type.value if isinstance(rel_type, RelationshipType) else str(rel_type)
    if name not in ALLOWED_REL_TYPES:
        raise ValueError(f"unsupported relationship type: {name}")
    return name


def project_entity(entity: Entity, driver=None) -> None:
    label = ENTITY_LABEL_MAP[entity.type]
    if label not in ALLOWED_LABELS:
        raise ValueError(f"unsupported entity label: {label}")
    driver = driver or get_driver()
    extra: dict[str, Any] = {}
    if label == "Phone":
        extra["number"] = entity.canonical_name
    elif label == "Vehicle":
        extra["registration"] = entity.canonical_name
    cypher = (
        f"MERGE (n:{label} {{entity_id: $entity_id}}) "
        "SET n.name = $name, n.canonical_name = $name"
    )
    if extra:
        sets = ", ".join(f"n.{key} = ${key}" for key in extra)
        cypher = f"{cypher}, {sets}"
    with driver.session() as session:
        session.run(
            cypher,
            entity_id=_id(entity.id),
            name=entity.canonical_name,
            **extra,
        )


def project_case(case: Case, driver=None) -> None:
    driver = driver or get_driver()
    with driver.session() as session:
        session.run(
            "MERGE (c:Case {case_id: $case_id}) "
            "SET c.title = $title, c.case_number = $case_number",
            case_id=_id(case.id),
            title=case.title,
            case_number=case.case_number,
        )


def project_document(document: Document, driver=None) -> None:
    driver = driver or get_driver()
    with driver.session() as session:
        session.run(
            "MERGE (d:Document {document_id: $document_id}) "
            "SET d.filename = $filename, d.case_id = $case_id",
            document_id=_id(document.id),
            filename=document.filename,
            case_id=_id(document.case_id),
        )


def project_relationship(
    rel: RelationshipStaging,
    source: Entity | None = None,
    target: Entity | None = None,
    driver=None,
) -> bool:
    """MERGE one staging occurrence. Skip if canonical endpoints are missing."""
    if rel.source_entity_id is None or rel.target_entity_id is None:
        return False
    driver = driver or get_driver()
    if source is not None:
        project_entity(source, driver=driver)
    if target is not None:
        project_entity(target, driver=driver)
    rel_type = _rel_type_name(rel.relationship_type)
    status = rel.status.value if hasattr(rel.status, "value") else str(rel.status)
    cypher = (
        "MATCH (a {entity_id: $source_entity_id}) "
        "MATCH (b {entity_id: $target_entity_id}) "
        "OPTIONAL MATCH ()-[old_r {relationship_id: $relationship_id}]-() "
        f"WHERE startNode(old_r) <> a OR endNode(old_r) <> b OR type(old_r) <> '{rel_type}' "
        "DELETE old_r "
        "WITH a, b "
        f"MERGE (a)-[r:{rel_type} {{relationship_id: $relationship_id}}]->(b) "
        "SET r.confidence = $confidence, "
        "    r.status = $status, "
        "    r.case_id = $case_id, "
        "    r.evidence_snippet = $evidence_snippet, "
        "    r.source_document_id = $source_document_id, "
        "    r.source_record_id = $source_record_id, "
        "    r.extracted_at = $extracted_at"
    )
    with driver.session() as session:
        result = session.run(
            cypher,
            source_entity_id=_id(rel.source_entity_id),
            target_entity_id=_id(rel.target_entity_id),
            relationship_id=_id(rel.id),
            confidence=float(rel.confidence),
            status=status,
            case_id=_id(rel.case_id),
            evidence_snippet=rel.evidence_snippet,
            source_document_id=_id(rel.source_document_id),
            source_record_id=_id(rel.source_record_id),
            extracted_at=_iso(rel.extracted_at),
        )
        summary = result.consume()
        return summary.counters.relationships_created in (0, 1)


def project_case_graph(case_id: UUID, db: Session, driver=None) -> dict[str, int]:
    """Project one case's canonical graph from PostgreSQL into Neo4j."""
    driver = driver or get_driver()
    init_schema(driver)
    case = db.get(Case, case_id)
    if case is None:
        raise ValueError(f"unknown case_id: {case_id}")

    project_case(case, driver=driver)

    documents = db.query(Document).filter(Document.case_id == case_id).all()
    for document in documents:
        project_document(document, driver=driver)

    linked_ids = [
        row.entity_id
        for row in db.query(EntityCaseLink).filter(EntityCaseLink.case_id == case_id)
    ]
    staged = (
        db.query(RelationshipStaging)
        .filter(RelationshipStaging.case_id == case_id)
        .all()
    )
    entity_ids = set(linked_ids)
    for rel in staged:
        if rel.source_entity_id:
            entity_ids.add(rel.source_entity_id)
        if rel.target_entity_id:
            entity_ids.add(rel.target_entity_id)

    entities = {entity.id: entity for entity in db.query(Entity).filter(Entity.id.in_(entity_ids))}
    for entity in entities.values():
        project_entity(entity, driver=driver)

    # Reconcile relationships: prune any edges in Neo4j for this case that no longer exist in DB
    active_rel_ids = [str(r.id) for r in staged]
    with driver.session() as s:
        s.run(
            "MATCH ()-[r {case_id: $case_id}]->() "
            "WHERE NOT r.relationship_id IN $active_rel_ids "
            "DELETE r",
            case_id=str(case_id),
            active_rel_ids=active_rel_ids,
        )
        # Prune any orphaned disconnected nodes left behind after deduplication
        s.run("MATCH (n) WHERE NOT (n)--() AND NOT n:Case AND NOT n:Document DELETE n")

    projected = 0
    skipped = 0
    for rel in staged:
        source = entities.get(rel.source_entity_id) if rel.source_entity_id else None
        target = entities.get(rel.target_entity_id) if rel.target_entity_id else None
        if project_relationship(rel, source=source, target=target, driver=driver):
            projected += 1
        else:
            skipped += 1

    return {
        "entities": len(entities),
        "documents": len(documents),
        "relationships_projected": projected,
        "relationships_skipped": skipped,
    }
