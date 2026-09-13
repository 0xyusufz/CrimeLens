import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class EvidenceBlockRead(BaseModel):
    """Ledger metadata only. File bytes and filesystem paths are never included."""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: uuid.UUID
    block_index: int
    case_id: uuid.UUID
    evidence_id: uuid.UUID
    data_hash: str
    previous_hash: str
    timestamp: datetime
    actor: uuid.UUID
    block_hash: str


class EvidenceVerifyResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_id: uuid.UUID
    anchored: bool
    verified: bool
    data_hash: str | None
    block_hash: str | None
    previous_hash: str | None
