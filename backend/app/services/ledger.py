"""Lightweight append-only, hash-linked evidence ledger for tamper-evidence.

This is not a blockchain and does not store evidence bytes.

block_hash = SHA-256 of UTF-8 JSON with sort_keys=True and separators=(',', ':')
over this object:

{
  "actor": "<uuid>",
  "block_index": <int>,
  "case_id": "<uuid>",
  "data_hash": "<64 hex>",
  "evidence_id": "<uuid>",
  "previous_hash": "<64 hex or 0>",
  "timestamp": "<YYYY-MM-DDTHH:MM:SS.ffffffZ>"
}

UUIDs are lowercase hyphenated. data_hash is lowercase hex of SHA-256(file bytes).
The first ledger block uses previous_hash = "0".
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.evidence import EvidenceBlock
from app.models.user import User
from app.services.documents import (
    StoredFileMissingError,
    read_stored_document_bytes,
    sha256_hex,
)

GENESIS_PREVIOUS_HASH = "0"


class EvidenceHashMismatchError(Exception):
    """Stored file SHA-256 does not match documents.sha256_hash."""


def _timestamp_canonical(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def canonical_block_payload(
    *,
    block_index: int,
    case_id: uuid.UUID,
    evidence_id: uuid.UUID,
    data_hash: str,
    previous_hash: str,
    timestamp: datetime,
    actor: uuid.UUID,
) -> str:
    payload = {
        "actor": str(actor),
        "block_index": int(block_index),
        "case_id": str(case_id),
        "data_hash": data_hash.lower(),
        "evidence_id": str(evidence_id),
        "previous_hash": previous_hash,
        "timestamp": _timestamp_canonical(timestamp),
    }
    return json.dumps(payload, separators=(",", ":"), sort_keys=True)


def compute_block_hash(
    *,
    block_index: int,
    case_id: uuid.UUID,
    evidence_id: uuid.UUID,
    data_hash: str,
    previous_hash: str,
    timestamp: datetime,
    actor: uuid.UUID,
) -> str:
    canonical = canonical_block_payload(
        block_index=block_index,
        case_id=case_id,
        evidence_id=evidence_id,
        data_hash=data_hash,
        previous_hash=previous_hash,
        timestamp=timestamp,
        actor=actor,
    )
    return sha256_hex(canonical.encode("utf-8"))


def get_anchor_for_document(session: Session, document_id: uuid.UUID) -> EvidenceBlock | None:
    return session.scalar(
        select(EvidenceBlock).where(EvidenceBlock.evidence_id == document_id)
    )


def list_case_ledger(session: Session, case_id: uuid.UUID) -> list[EvidenceBlock]:
    stmt = (
        select(EvidenceBlock)
        .where(EvidenceBlock.case_id == case_id)
        .order_by(EvidenceBlock.block_index.desc())
    )
    return list(session.scalars(stmt).all())


def _previous_block(session: Session, block_index: int) -> EvidenceBlock | None:
    if block_index <= 0:
        return None
    return session.scalar(
        select(EvidenceBlock).where(EvidenceBlock.block_index == block_index - 1)
    )


def verify_block_integrity(session: Session, block: EvidenceBlock) -> bool:
    expected = compute_block_hash(
        block_index=block.block_index,
        case_id=block.case_id,
        evidence_id=block.evidence_id,
        data_hash=block.data_hash,
        previous_hash=block.previous_hash,
        timestamp=block.timestamp,
        actor=block.actor,
    )
    if expected != block.block_hash:
        return False
    if block.block_index == 0:
        return block.previous_hash == GENESIS_PREVIOUS_HASH
    previous = _previous_block(session, block.block_index)
    if previous is None:
        return False
    return block.previous_hash == previous.block_hash


def anchor_document(
    session: Session,
    document: Document,
    actor: User,
) -> tuple[EvidenceBlock, bool]:
    """Return (block, created). created is False when the document was already anchored."""
    existing = get_anchor_for_document(session, document.id)
    if existing is not None:
        return existing, False

    data = read_stored_document_bytes(document.id)
    data_hash = sha256_hex(data)
    if data_hash != document.sha256_hash.lower():
        raise EvidenceHashMismatchError()

    session.execute(text("LOCK TABLE evidence_blocks IN EXCLUSIVE MODE"))
    existing = get_anchor_for_document(session, document.id)
    if existing is not None:
        session.rollback()
        return existing, False

    last = session.scalar(
        select(EvidenceBlock).order_by(EvidenceBlock.block_index.desc()).limit(1)
    )
    if last is None:
        block_index = 0
        previous_hash = GENESIS_PREVIOUS_HASH
    else:
        block_index = last.block_index + 1
        previous_hash = last.block_hash

    timestamp = datetime.now(timezone.utc)
    block_hash = compute_block_hash(
        block_index=block_index,
        case_id=document.case_id,
        evidence_id=document.id,
        data_hash=data_hash,
        previous_hash=previous_hash,
        timestamp=timestamp,
        actor=actor.id,
    )
    block = EvidenceBlock(
        block_index=block_index,
        case_id=document.case_id,
        evidence_id=document.id,
        data_hash=data_hash,
        previous_hash=previous_hash,
        timestamp=timestamp,
        actor=actor.id,
        block_hash=block_hash,
    )
    session.add(block)
    session.flush()
    return block, True


def verify_document(session: Session, document: Document) -> dict:
    block = get_anchor_for_document(session, document.id)
    if block is None:
        return {
            "document_id": document.id,
            "anchored": False,
            "verified": False,
            "data_hash": None,
            "block_hash": None,
            "previous_hash": None,
        }
    try:
        current = sha256_hex(read_stored_document_bytes(document.id))
    except StoredFileMissingError:
        return {
            "document_id": document.id,
            "anchored": True,
            "verified": False,
            "data_hash": block.data_hash,
            "block_hash": block.block_hash,
            "previous_hash": block.previous_hash,
        }
    file_ok = current == block.data_hash.lower() == document.sha256_hash.lower()
    chain_ok = verify_block_integrity(session, block)
    return {
        "document_id": document.id,
        "anchored": True,
        "verified": bool(file_ok and chain_ok),
        "data_hash": block.data_hash,
        "block_hash": block.block_hash,
        "previous_hash": block.previous_hash,
    }
