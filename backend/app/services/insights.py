"""Validate and persist Person B Pattern/Lead JSON as case intelligence outputs."""

from __future__ import annotations

import uuid
from typing import Any

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.document import Document, StructuredRecord
from app.models.entity import Entity, EntityCaseLink, EntityMention
from app.models.enums import IntelligenceKind
from app.models.intelligence import IntelligenceOutput
from app.models.relationship import RelationshipStaging
from app.schemas.insights import CaseInsights
from shared.schemas import Lead, Pattern


class IntelligenceContractError(Exception):
    """Pattern/Lead JSON did not match the shared contract."""


def _pattern_dump(pattern: Pattern) -> dict[str, Any]:
    return pattern.model_dump(mode="json")


def _lead_dump(lead: Lead) -> dict[str, Any]:
    return lead.model_dump(mode="json")


def _resolve_entity_ref(
    session: Session,
    case_id: uuid.UUID,
    raw: str,
    *,
    source_document_id: uuid.UUID | None,
) -> str:
    try:
        entity_id = uuid.UUID(raw)
    except ValueError:
        entity_id = None
    if entity_id is not None:
        link = session.scalar(
            select(EntityCaseLink).where(
                EntityCaseLink.entity_id == entity_id,
                EntityCaseLink.case_id == case_id,
            )
        )
        if link is not None and session.get(Entity, entity_id) is not None:
            return str(entity_id)

    mention_stmt = (
        select(EntityMention)
        .join(Document, Document.id == EntityMention.document_id)
        .where(
            Document.case_id == case_id,
            EntityMention.mention_id == raw,
            EntityMention.entity_id.is_not(None),
        )
        .order_by(EntityMention.created_at.asc(), EntityMention.id.asc())
    )
    if source_document_id is not None:
        mentioned = session.scalar(
            mention_stmt.where(EntityMention.document_id == source_document_id)
        )
        if mentioned is not None and mentioned.entity_id is not None:
            return str(mentioned.entity_id)
    mentioned = session.scalar(mention_stmt)
    if mentioned is not None and mentioned.entity_id is not None:
        return str(mentioned.entity_id)
    return raw


def _resolve_evidence_ref(session: Session, case_id: uuid.UUID, raw: str) -> str:
    try:
        ref_id = uuid.UUID(raw)
    except ValueError:
        ref_id = None
    if ref_id is not None:
        document = session.get(Document, ref_id)
        if document is not None and document.case_id == case_id:
            return str(document.id)
        record = session.get(StructuredRecord, ref_id)
        if record is not None and record.case_id == case_id:
            return str(record.id)
        rel = session.get(RelationshipStaging, ref_id)
        if rel is not None and rel.case_id == case_id:
            return str(rel.id)
        return raw

    rel = session.scalar(
        select(RelationshipStaging).where(
            RelationshipStaging.case_id == case_id,
            RelationshipStaging.source_occurrence_id == raw,
        )
    )
    if rel is not None:
        return str(rel.id)
    return raw


def _upsert_output(
    session: Session,
    *,
    case_id: uuid.UUID,
    source_document_id: uuid.UUID | None,
    kind: IntelligenceKind,
    source_id: str,
    payload: dict[str, Any],
) -> IntelligenceOutput:
    row = session.scalar(
        select(IntelligenceOutput).where(
            IntelligenceOutput.case_id == case_id,
            IntelligenceOutput.kind == kind,
            IntelligenceOutput.source_id == source_id,
        )
    )
    if row is None:
        row = IntelligenceOutput(
            case_id=case_id,
            source_document_id=source_document_id,
            kind=kind,
            source_id=source_id,
            payload=payload,
        )
        session.add(row)
    else:
        row.source_document_id = source_document_id
        row.payload = payload
    return row


def persist_patterns(
    session: Session,
    *,
    case_id: uuid.UUID,
    patterns: list[Pattern],
    source_document_id: uuid.UUID | None = None,
) -> int:
    """Upsert validated Pattern JSON for a backend-derived case_id."""
    for pattern in patterns:
        mapped = pattern.model_copy(
            update={
                "entities": [
                    _resolve_entity_ref(
                        session,
                        case_id,
                        item,
                        source_document_id=source_document_id,
                    )
                    for item in pattern.entities
                ],
                "evidence_ids": [
                    _resolve_evidence_ref(session, case_id, item)
                    for item in pattern.evidence_ids
                ],
            }
        )
        _upsert_output(
            session,
            case_id=case_id,
            source_document_id=source_document_id,
            kind=IntelligenceKind.PATTERN,
            source_id=pattern.id,
            payload=_pattern_dump(mapped),
        )
    session.flush()
    return len(patterns)


def persist_leads(
    session: Session,
    *,
    case_id: uuid.UUID,
    leads: list[Lead],
    source_document_id: uuid.UUID | None = None,
) -> int:
    for lead in leads:
        mapped = lead.model_copy(
            update={
                "entity_ids": [
                    _resolve_entity_ref(
                        session,
                        case_id,
                        item,
                        source_document_id=source_document_id,
                    )
                    for item in lead.entity_ids
                ],
                "evidence_ids": [
                    _resolve_evidence_ref(session, case_id, item)
                    for item in lead.evidence_ids
                ],
            }
        )
        _upsert_output(
            session,
            case_id=case_id,
            source_document_id=source_document_id,
            kind=IntelligenceKind.LEAD,
            source_id=lead.id,
            payload=_lead_dump(mapped),
        )
    session.flush()
    return len(leads)


def validate_patterns(raw_items: Any) -> list[Pattern]:
    if raw_items is None:
        return []
    if not isinstance(raw_items, list):
        raise IntelligenceContractError("patterns must be a list.")
    try:
        return [Pattern.model_validate(item) for item in raw_items]
    except ValidationError as exc:
        raise IntelligenceContractError("Pattern JSON failed contract validation.") from exc


def validate_leads(raw_items: Any) -> list[Lead]:
    if raw_items is None:
        return []
    if not isinstance(raw_items, list):
        raise IntelligenceContractError("leads must be a list.")
    try:
        return [Lead.model_validate(item) for item in raw_items]
    except ValidationError as exc:
        raise IntelligenceContractError("Lead JSON failed contract validation.") from exc


def list_case_insights(session: Session, case_id: uuid.UUID) -> CaseInsights:
    rows = list(
        session.scalars(
            select(IntelligenceOutput)
            .where(IntelligenceOutput.case_id == case_id)
            .order_by(IntelligenceOutput.created_at.asc(), IntelligenceOutput.source_id.asc())
        ).all()
    )
    patterns: list[Pattern] = []
    leads: list[Lead] = []
    for row in rows:
        if row.kind == IntelligenceKind.PATTERN:
            patterns.append(Pattern.model_validate(row.payload))
        elif row.kind == IntelligenceKind.LEAD:
            leads.append(Lead.model_validate(row.payload))
    return CaseInsights(case_id=case_id, patterns=patterns, leads=leads)
