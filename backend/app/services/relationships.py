"""PostgreSQL-backed relationship evidence. Neo4j is not used for authorization."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.models.enums import RelationshipStatus, RelationshipType
from app.models.relationship import RelationshipStaging
from app.models.user import User
from app.schemas.relationship import RelationshipEvidenceRead
from app.services.access import user_can_access_case


class RelationshipNotFoundError(Exception):
    pass


class RelationshipForbiddenError(Exception):
    """Relationship exists on a case the current user cannot access."""

    def __init__(self, case_id: uuid.UUID):
        self.case_id = case_id
        super().__init__("Not authorized")


def _relationship_type(value) -> RelationshipType:
    return value if isinstance(value, RelationshipType) else RelationshipType(value)


def _relationship_status(value) -> RelationshipStatus:
    return value if isinstance(value, RelationshipStatus) else RelationshipStatus(value)


def get_relationship_evidence(
    session: Session, user: User, relationship_id: uuid.UUID
) -> RelationshipEvidenceRead:
    row = session.get(RelationshipStaging, relationship_id)
    if row is None:
        raise RelationshipNotFoundError()
    if not user_can_access_case(session, user, row.case_id):
        raise RelationshipForbiddenError(row.case_id)
    return RelationshipEvidenceRead(
        relationship_id=row.id,
        case_id=row.case_id,
        relationship=_relationship_type(row.relationship_type),
        source_entity_id=row.source_entity_id,
        target_entity_id=row.target_entity_id,
        confidence=float(row.confidence),
        status=_relationship_status(row.status),
        source_document_id=row.source_document_id,
        source_record_id=row.source_record_id,
        evidence_snippet=row.evidence_snippet,
        extracted_at=row.extracted_at,
    )
