import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DocumentRead(BaseModel):
    """Document metadata. File bytes and filesystem paths are never included."""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: uuid.UUID
    case_id: uuid.UUID
    filename: str
    sha256_hash: str
    uploaded_by: uuid.UUID
    uploaded_at: datetime
